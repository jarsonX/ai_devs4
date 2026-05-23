# Tile-by-tile image parser for the L7 electricity puzzle.

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from src.apps.L7_electricity.L7_electricity_gpt_5_5.config import AppConfig
from src.apps.L7_electricity.L7_electricity_gpt_5_5.logging_utils import write_json_file
from src.apps.L7_electricity.L7_electricity_gpt_5_5.models import Board, Coordinate, Tile, all_coordinates


MAX_TILE_PARSE_ATTEMPTS = 2
MIN_BOARD_SIDE_LENGTH = 3
DARK_PIXEL_THRESHOLD = 96
MIN_SIGNAL_BANDS = 4
ROW_SIGNAL_RATIO = 0.32
COLUMN_SIGNAL_RATIO = 0.57
MIN_ROW_SPAN_RATIO = 0.45
MIN_COLUMN_SPAN_RATIO = 0.30
MAX_GRID_SPACING_RATIO = 1.35
MIN_CELL_SIZE_PIXELS = 24
TILE_INNER_MARGIN_RATIO = 0.06
MIN_TILE_INNER_MARGIN_PIXELS = 4
PARSER_CACHE_VERSION = "2026-05-23-prompt-v2"


# Store one deterministic crop generated from the source board image.
@dataclass(frozen=True)
class TileCrop:
    coordinate: Coordinate
    image_path: Path
    box: tuple[int, int, int, int]


# Store one dark-signal band detected in row or column profiles.
@dataclass(frozen=True)
class SignalBand:
    start: int
    end: int
    peak_index: int
    peak_value: int
    total_value: int

    # Return one inclusive-center estimate for regularity checks.
    @property
    def center(self) -> float:
        return (self.start + self.end) / 2


# Store one validated parser result for a single tile crop.
@dataclass(frozen=True)
class ParsedTileResult:
    coordinate: Coordinate
    tile: Tile
    confidence: str
    attempts_used: int
    crop_path: Path
    raw_payload: dict[str, Any]


# Store the collected result of parsing one full board image.
@dataclass(frozen=True)
class BoardParseResult:
    board: Board
    image_path: Path
    cache_file: Path
    source_sha256: str
    model_name: str
    used_cache: bool
    tile_results: tuple[ParsedTileResult, ...]


# Store one structured parser failure with enough detail for debugging.
@dataclass(frozen=True)
class ParserFailureRecord:
    image_path: Path
    source_sha256: str
    model_name: str
    stage: str
    message: str
    coordinate_label: str | None = None
    attempts_used: int | None = None
    raw_payload: dict[str, Any] | None = None


# Signal one parser failure that should stop downstream solving immediately.
class ImageParserError(RuntimeError):
    # Store the structured failure record together with the human-readable error.
    def __init__(self, record: ParserFailureRecord) -> None:
        super().__init__(record.message)
        self.record = record


# Validate one structured tile record returned by the vision model.
class TileParsePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coordinate: str
    exits: list[Literal["up", "right", "down", "left"]]
    confidence: Literal["high", "medium", "low"]

    # Validate that the coordinate matches the supported 3x3 board format.
    @field_validator("coordinate")
    @classmethod
    def validate_coordinate(cls, value: str) -> str:
        return Coordinate.from_label(value).label

    # Validate that exits are unique and match one supported tile shape size.
    @field_validator("exits")
    @classmethod
    def validate_exits(cls, value: list[str]) -> list[str]:
        unique_exits = list(dict.fromkeys(value))
        if len(unique_exits) != len(value):
            raise ValueError("exits must not contain duplicates.")
        if len(unique_exits) not in {2, 3}:
            raise ValueError("exits must contain exactly 2 or 3 values.")
        return unique_exits


# Parse board images into validated domain objects using a narrow vision step.
class ImageParser:
    # Store app configuration and an injectable OpenAI client.
    def __init__(
        self,
        config: AppConfig,
        client: OpenAI | Any | None = None,
    ) -> None:
        self.config = config
        self.client = client or OpenAI(api_key=config.vision.openai_api_key)

    # Parse the current board image and always ignore stale cache.
    def parse_current_board(self) -> BoardParseResult:
        return self.parse_board_image(
            self.config.paths.current_board_file,
            allow_cache=False,
        )

    # Parse the solved reference board image and allow cache reuse.
    def parse_solved_board(self) -> BoardParseResult:
        return self.parse_board_image(
            self.config.paths.solved_board_file,
            allow_cache=True,
        )

    # Parse one board PNG into a validated board object and parser metadata.
    def parse_board_image(
        self,
        image_path: Path,
        *,
        allow_cache: bool,
    ) -> BoardParseResult:
        source_path = image_path.resolve()
        if not source_path.exists():
            record = ParserFailureRecord(
                image_path=source_path,
                source_sha256="missing-file",
                model_name=self.config.vision.model_name,
                stage="load_image",
                message=f"Board image does not exist: {source_path}",
            )
            self._save_failure_record(record)
            raise ImageParserError(record)

        source_bytes = source_path.read_bytes()
        if not source_bytes:
            record = ParserFailureRecord(
                image_path=source_path,
                source_sha256="empty-file",
                model_name=self.config.vision.model_name,
                stage="load_image",
                message=f"Board image is empty: {source_path}",
            )
            self._save_failure_record(record)
            raise ImageParserError(record)

        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        cache_file = self._get_board_cache_file(source_path)

        if allow_cache:
            cached_result = self._load_cached_result(cache_file, source_path, source_sha256)
            if cached_result is not None:
                return cached_result

        try:
            tile_crops = self._crop_board_into_tiles(source_path)
            tile_results = tuple(
                self._parse_tile_with_retry(tile_crop, source_path, source_sha256)
                for tile_crop in tile_crops
            )
            board = Board(
                tiles={
                    tile_result.coordinate: tile_result.tile
                    for tile_result in tile_results
                }
            )
        except ImageParserError:
            raise
        except Exception as error:
            record = ParserFailureRecord(
                image_path=source_path,
                source_sha256=source_sha256,
                model_name=self.config.vision.model_name,
                stage="assemble_board",
                message=f"Board parsing failed for {source_path.name}: {error}",
            )
            self._save_failure_record(record)
            raise ImageParserError(record) from error

        result = BoardParseResult(
            board=board,
            image_path=source_path,
            cache_file=cache_file,
            source_sha256=source_sha256,
            model_name=self.config.vision.model_name,
            used_cache=False,
            tile_results=tile_results,
        )
        self._save_cached_result(result)
        return result

    # Build one cache file path for the parsed result of a given board image.
    def _get_board_cache_file(self, image_path: Path) -> Path:
        return self.config.paths.cache_dir / f"{image_path.stem}_parsed.json"

    # Load one cached parse result only when the source image and model still match.
    def _load_cached_result(
        self,
        cache_file: Path,
        image_path: Path,
        source_sha256: str,
    ) -> BoardParseResult | None:
        if not cache_file.exists():
            return None

        try:
            cache_payload = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if cache_payload.get("source_sha256") != source_sha256:
            return None
        if cache_payload.get("model_name") != self.config.vision.model_name:
            return None
        if cache_payload.get("parser_cache_version") != PARSER_CACHE_VERSION:
            return None

        tile_results = tuple(
            ParsedTileResult(
                coordinate=Coordinate.from_label(cast(str, item["coordinate"])),
                tile=Tile.from_exit_names(cast(list[str], item["exits"])),
                confidence=cast(str, item["confidence"]),
                attempts_used=int(item["attempts_used"]),
                crop_path=Path(cast(str, item["crop_path"])),
                raw_payload=cast(dict[str, Any], item["raw_payload"]),
            )
            for item in cast(list[dict[str, Any]], cache_payload["tile_results"])
        )

        return BoardParseResult(
            board=Board.from_label_map(cast(dict[str, list[str]], cache_payload["board_map"])),
            image_path=image_path,
            cache_file=cache_file,
            source_sha256=source_sha256,
            model_name=self.config.vision.model_name,
            used_cache=True,
            tile_results=tile_results,
        )

    # Save one parsed board result for later solved-board cache reuse.
    def _save_cached_result(self, result: BoardParseResult) -> None:
        cache_payload = {
            "parsed_at": self._current_timestamp(),
            "image_path": str(result.image_path),
            "source_sha256": result.source_sha256,
            "model_name": result.model_name,
            "parser_cache_version": PARSER_CACHE_VERSION,
            "board_map": result.board.to_label_map(),
            "tile_results": [
                {
                    "coordinate": tile_result.coordinate.label,
                    "exits": tile_result.tile.to_exit_names(),
                    "confidence": tile_result.confidence,
                    "attempts_used": tile_result.attempts_used,
                    "crop_path": str(tile_result.crop_path),
                    "raw_payload": tile_result.raw_payload,
                }
                for tile_result in result.tile_results
            ],
        }
        write_json_file(result.cache_file, cache_payload)
        self._save_raw_tile_payloads(result)

    # Save one raw per-tile payload artifact for debugging and prompt iteration.
    def _save_raw_tile_payloads(self, result: BoardParseResult) -> None:
        raw_payload_file = result.cache_file.with_name(f"{result.image_path.stem}_tile_payloads.json")
        write_json_file(
            raw_payload_file,
            {
                "image_path": str(result.image_path),
                "source_sha256": result.source_sha256,
                "model_name": result.model_name,
                "tile_payloads": [
                    {
                        "coordinate": tile_result.coordinate.label,
                        "confidence": tile_result.confidence,
                        "attempts_used": tile_result.attempts_used,
                        "crop_path": str(tile_result.crop_path),
                        "raw_payload": tile_result.raw_payload,
                    }
                    for tile_result in result.tile_results
                ],
            },
        )

    # Save one structured parser failure artifact to the configured output path.
    def _save_failure_record(self, record: ParserFailureRecord) -> None:
        write_json_file(
            self.config.paths.parser_failure_file,
            {
                "failed_at": self._current_timestamp(),
                "image_path": str(record.image_path),
                "source_sha256": record.source_sha256,
                "model_name": record.model_name,
                "stage": record.stage,
                "coordinate": record.coordinate_label,
                "attempts_used": record.attempts_used,
                "message": record.message,
                "raw_payload": record.raw_payload,
            },
        )

    # Deterministically crop a 3x3 board image into tile PNG files.
    def _crop_board_into_tiles(self, image_path: Path) -> tuple[TileCrop, ...]:
        image_module = _require_pillow_image_module()
        tile_output_dir = self.config.paths.tile_cache_dir / image_path.stem
        tile_output_dir.mkdir(parents=True, exist_ok=True)

        with image_module.open(image_path) as image:
            width, height = image.size
            if width < MIN_BOARD_SIDE_LENGTH or height < MIN_BOARD_SIDE_LENGTH:
                raise ValueError(
                    "Board image is too small for 3x3 cropping. "
                    f"Size: {width}x{height}."
                )

            board_box, row_bands, column_bands = self._detect_board_box(image)
            self._save_board_detection_artifacts(
                image=image,
                image_path=image_path,
                board_box=board_box,
                row_bands=row_bands,
                column_bands=column_bands,
            )

            board_left, board_top, board_right, board_bottom = board_box
            board_width = board_right - board_left
            board_height = board_bottom - board_top
            x_edges = _build_grid_edges(board_width)
            y_edges = _build_grid_edges(board_height)
            tile_crops: list[TileCrop] = []

            for coordinate in all_coordinates():
                left = board_left + x_edges[coordinate.column - 1]
                right = board_left + x_edges[coordinate.column]
                top = board_top + y_edges[coordinate.row - 1]
                bottom = board_top + y_edges[coordinate.row]
                crop_box = (left, top, right, bottom)
                if left >= right or top >= bottom:
                    raise ValueError(
                        "Computed an invalid tile crop box for "
                        f"{coordinate.label}: {crop_box}."
                    )
                tile_image = image.crop(crop_box)
                prepared_tile_image = _apply_inner_tile_crop(tile_image)
                output_path = tile_output_dir / f"{coordinate.label}.png"
                prepared_tile_image.save(output_path, format="PNG")
                tile_crops.append(
                    TileCrop(
                        coordinate=coordinate,
                        image_path=output_path,
                        box=crop_box,
                    )
                )

        return tuple(tile_crops)

    # Detect the board rectangle from dark line signals in the full source image.
    def _detect_board_box(
        self,
        image: Any,
    ) -> tuple[
        tuple[int, int, int, int],
        tuple[SignalBand, SignalBand, SignalBand, SignalBand],
        tuple[SignalBand, SignalBand, SignalBand, SignalBand],
    ]:
        grayscale_image = image.convert("L")
        width, height = grayscale_image.size
        row_counts, column_counts = _build_dark_signal_profiles(grayscale_image)

        row_bands = _find_signal_bands(
            row_counts,
            min_value=max(MIN_CELL_SIZE_PIXELS, round(width * ROW_SIGNAL_RATIO)),
        )
        column_bands = _find_signal_bands(
            column_counts,
            min_value=max(MIN_CELL_SIZE_PIXELS, round(height * COLUMN_SIGNAL_RATIO)),
        )

        selected_row_bands = _select_grid_bands(
            row_bands,
            axis_length=height,
            min_span_ratio=MIN_ROW_SPAN_RATIO,
        )
        selected_column_bands = _select_grid_bands(
            column_bands,
            axis_length=width,
            min_span_ratio=MIN_COLUMN_SPAN_RATIO,
        )

        board_left = selected_column_bands[0].start
        board_top = selected_row_bands[0].start
        board_right = selected_column_bands[-1].end + 1
        board_bottom = selected_row_bands[-1].end + 1

        if board_left >= board_right or board_top >= board_bottom:
            raise ValueError(
                "Detected an invalid board rectangle. "
                f"Box: {(board_left, board_top, board_right, board_bottom)}."
            )

        return (
            (board_left, board_top, board_right, board_bottom),
            selected_row_bands,
            selected_column_bands,
        )

    # Save one cropped-board image and one JSON detection summary for debugging.
    def _save_board_detection_artifacts(
        self,
        *,
        image: Any,
        image_path: Path,
        board_box: tuple[int, int, int, int],
        row_bands: tuple[SignalBand, SignalBand, SignalBand, SignalBand],
        column_bands: tuple[SignalBand, SignalBand, SignalBand, SignalBand],
    ) -> None:
        board_crop_path = self.config.paths.cache_dir / f"{image_path.stem}_board_crop.png"
        detection_payload_path = self.config.paths.cache_dir / f"{image_path.stem}_board_detection.json"

        image.crop(board_box).save(board_crop_path, format="PNG")
        write_json_file(
            detection_payload_path,
            {
                "generated_at": self._current_timestamp(),
                "image_path": str(image_path.resolve()),
                "board_box": {
                    "left": board_box[0],
                    "top": board_box[1],
                    "right": board_box[2],
                    "bottom": board_box[3],
                    "width": board_box[2] - board_box[0],
                    "height": board_box[3] - board_box[1],
                },
                "selected_row_bands": [_band_to_dict(band) for band in row_bands],
                "selected_column_bands": [_band_to_dict(band) for band in column_bands],
                "board_crop_path": str(board_crop_path),
            },
        )

    # Parse one tile with one bounded retry when validation or confidence fails.
    def _parse_tile_with_retry(
        self,
        tile_crop: TileCrop,
        source_path: Path,
        source_sha256: str,
    ) -> ParsedTileResult:
        last_error: Exception | None = None
        last_raw_payload: dict[str, Any] | None = None

        for attempt in range(1, MAX_TILE_PARSE_ATTEMPTS + 1):
            try:
                parsed_tile_result = self._parse_tile_once(tile_crop, attempt)
                last_raw_payload = parsed_tile_result.raw_payload
            except Exception as error:
                last_error = error
                if attempt >= MAX_TILE_PARSE_ATTEMPTS:
                    break
                continue

            if parsed_tile_result.confidence != "low":
                return parsed_tile_result

            last_error = ValueError(
                f"Tile {tile_crop.coordinate.label} returned low confidence."
            )
            if attempt >= MAX_TILE_PARSE_ATTEMPTS:
                break

        if last_error is None:
            last_error = RuntimeError("Tile parsing failed without an explicit error.")

        record = ParserFailureRecord(
            image_path=source_path,
            source_sha256=source_sha256,
            model_name=self.config.vision.model_name,
            stage="parse_tile",
            message=f"Tile parsing failed for {tile_crop.coordinate.label}: {last_error}",
            coordinate_label=tile_crop.coordinate.label,
            attempts_used=MAX_TILE_PARSE_ATTEMPTS,
            raw_payload=last_raw_payload,
        )
        self._save_failure_record(record)
        raise ImageParserError(record) from last_error

    # Parse one tile image into a validated tile result with strict schema checks.
    def _parse_tile_once(self, tile_crop: TileCrop, attempt: int) -> ParsedTileResult:
        response = self.client.responses.create(
            model=self.config.vision.model_name,
            input=self._build_tile_input(tile_crop, attempt),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tile_parse_payload",
                    "schema": TileParsePayload.model_json_schema(),
                    "strict": True,
                }
            },
        )

        output_text = getattr(response, "output_text", "")
        if not isinstance(output_text, str) or not output_text.strip():
            raise ValueError(
                f"Model output for {tile_crop.coordinate.label} is empty."
            )

        try:
            raw_payload = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Model output for {tile_crop.coordinate.label} is not valid JSON."
            ) from error

        try:
            payload = TileParsePayload.model_validate(raw_payload)
        except ValidationError as error:
            raise ValueError(
                f"Model output for {tile_crop.coordinate.label} failed schema validation: {error}"
            ) from error

        if payload.coordinate != tile_crop.coordinate.label:
            raise ValueError(
                "Model echoed the wrong coordinate. "
                f"Expected {tile_crop.coordinate.label}, got {payload.coordinate}."
            )

        return ParsedTileResult(
            coordinate=tile_crop.coordinate,
            tile=Tile.from_exit_names(payload.exits),
            confidence=payload.confidence,
            attempts_used=attempt,
            crop_path=tile_crop.image_path,
            raw_payload=raw_payload,
        )

    # Build the exact multimodal input payload for one tile image classification call.
    def _build_tile_input(self, tile_crop: TileCrop, attempt: int) -> list[dict[str, object]]:
        prompt = self._build_tile_prompt(tile_crop.coordinate, attempt)
        return [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": _to_data_url(tile_crop.image_path),
                    },
                ],
            }
        ]

    # Build the narrow parser prompt for one tile crop.
    def _build_tile_prompt(self, coordinate: Coordinate, attempt: int) -> str:
        lines = [
            "You are reading one tile from a 3x3 cable puzzle.",
            "Return JSON only.",
            f"Coordinate: {coordinate.label}",
            "List only the cable exits where a thick black cable enters from a tile edge toward the center.",
            "Do not count the thin puzzle grid border as a cable.",
            "Allowed exits: up, right, down, left.",
            "Return exactly 2 or 3 unique exits.",
            "If the tile has 3 exits, identify the single missing side and return the other 3 sides.",
            "If the tile has 2 exits, decide whether they are opposite sides or adjacent sides.",
            "Also return confidence as high, medium, or low.",
            "Do not explain.",
        ]
        if attempt > 1:
            lines.extend(
                [
                    "This is a retry because the previous answer was invalid or low confidence.",
                    "Be stricter about visible tile edges and return only certain exits.",
                    "Check carefully whether a side shows a real thick cable segment or only the thin border line.",
                ]
            )

        return "\n".join(lines)

    # Return one UTC timestamp for cache metadata.
    def _current_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


# Build one base64 data URL for a local image file.
def _to_data_url(image_path: Path) -> str:
    image_bytes = image_path.read_bytes()
    mime_type, _ = mimetypes.guess_type(str(image_path))
    resolved_mime_type = mime_type or "image/png"
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{resolved_mime_type};base64,{encoded_image}"


# Build one stable 0-1-2-3 grid edge sequence for equal-width tile crops.
def _build_grid_edges(total_length: int) -> tuple[int, int, int, int]:
    return tuple(round((total_length * index) / 3) for index in range(4))


# Apply one light inner crop to suppress grid borders before vision parsing.
def _apply_inner_tile_crop(tile_image: Any) -> Any:
    width, height = tile_image.size
    min_dimension = min(width, height)
    proposed_margin = max(
        MIN_TILE_INNER_MARGIN_PIXELS,
        round(min_dimension * TILE_INNER_MARGIN_RATIO),
    )
    max_margin_x = max(0, (width - MIN_CELL_SIZE_PIXELS) // 2)
    max_margin_y = max(0, (height - MIN_CELL_SIZE_PIXELS) // 2)
    margin = min(proposed_margin, max_margin_x, max_margin_y)

    if margin <= 0:
        return tile_image

    return tile_image.crop((margin, margin, width - margin, height - margin))


# Build dark-pixel count profiles for every row and every column in one image.
def _build_dark_signal_profiles(image: Any) -> tuple[list[int], list[int]]:
    width, height = image.size
    pixels = image.load()
    row_counts = [
        sum(1 for x in range(width) if pixels[x, y] <= DARK_PIXEL_THRESHOLD)
        for y in range(height)
    ]
    column_counts = [
        sum(1 for y in range(height) if pixels[x, y] <= DARK_PIXEL_THRESHOLD)
        for x in range(width)
    ]
    return row_counts, column_counts


# Collapse one thresholded signal profile into contiguous high-signal bands.
def _find_signal_bands(values: list[int], min_value: int) -> tuple[SignalBand, ...]:
    bands: list[SignalBand] = []
    start_index: int | None = None

    for index, value in enumerate(values):
        if value >= min_value:
            if start_index is None:
                start_index = index
            continue

        if start_index is not None:
            bands.append(_build_signal_band(values, start_index, index - 1))
            start_index = None

    if start_index is not None:
        bands.append(_build_signal_band(values, start_index, len(values) - 1))

    return tuple(bands)


# Build one summarized signal band object from one inclusive index range.
def _build_signal_band(values: list[int], start: int, end: int) -> SignalBand:
    band_values = values[start : end + 1]
    peak_offset, peak_value = max(enumerate(band_values), key=lambda item: item[1])
    return SignalBand(
        start=start,
        end=end,
        peak_index=start + peak_offset,
        peak_value=peak_value,
        total_value=sum(band_values),
    )


# Select the most board-like quartet of grid-line bands from one signal axis.
def _select_grid_bands(
    bands: tuple[SignalBand, ...],
    *,
    axis_length: int,
    min_span_ratio: float,
) -> tuple[SignalBand, SignalBand, SignalBand, SignalBand]:
    if len(bands) < MIN_SIGNAL_BANDS:
        raise ValueError(
            "Not enough line-signal bands were detected to isolate the board. "
            f"Detected {len(bands)} bands."
        )

    best_combo: tuple[SignalBand, SignalBand, SignalBand, SignalBand] | None = None
    best_score: float | None = None
    min_span = axis_length * min_span_ratio

    for raw_combo in itertools.combinations(bands, 4):
        combo = cast(tuple[SignalBand, SignalBand, SignalBand, SignalBand], raw_combo)
        centers = [band.center for band in combo]
        spacings = [centers[index + 1] - centers[index] for index in range(3)]

        if min(spacings) < MIN_CELL_SIZE_PIXELS:
            continue

        span = centers[-1] - centers[0]
        if span < min_span:
            continue

        spacing_ratio = max(spacings) / min(spacings)
        if spacing_ratio > MAX_GRID_SPACING_RATIO:
            continue

        signal_score = sum(
            (band.peak_value * 6) + round(_band_average_value(band) * 2)
            for band in combo
        )
        score = signal_score + span - (spacing_ratio * 100)
        if best_score is None or score > best_score:
            best_score = score
            best_combo = combo

    if best_combo is None:
        raise ValueError(
            "Could not find a regular 4-line grid pattern for board isolation."
        )

    return best_combo


# Convert one signal band into a JSON-friendly debug structure.
def _band_to_dict(band: SignalBand) -> dict[str, int | float]:
    return {
        "start": band.start,
        "end": band.end,
        "peak_index": band.peak_index,
        "peak_value": band.peak_value,
        "total_value": band.total_value,
        "center": band.center,
    }


# Return the mean signal level inside one detected band.
def _band_average_value(band: SignalBand) -> float:
    return band.total_value / ((band.end - band.start) + 1)


# Load Pillow lazily so the module stays importable before dependency install.
def _require_pillow_image_module() -> Any:
    try:
        from PIL import Image
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Pillow is required for board image cropping. "
            "Install it before running image parsing."
        ) from error

    return Image
