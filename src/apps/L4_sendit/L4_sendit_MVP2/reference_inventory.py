# Deterministic local reference inventory for the L4 sendit MVP2 Stage 2 step.

from pathlib import Path

from src.apps.L4_sendit.L4_sendit_MVP2.models import ReferenceInventoryItem


REFERENCE_HINTS = {
    "index.md": "main SPK documentation index and broad rules",
    "zalacznik-C.md": "attachment C",
    "zalacznik-D.md": "attachment D",
    "zalacznik-E.md": "declaration template",
    "zalacznik-F.md": "attachment F",
    "zalacznik-G.md": "attachment G and abbreviations",
    "zalacznik-H.md": "attachment H",
    "dodatkowe-wagony.md": "additional wagon information",
    "trasy-wylaczone.png": "disabled routes list with route codes and route availability status",
}


# Build a compact deterministic inventory of local SPK reference files.
def build_reference_inventory(repo_root: Path, references_dir: Path) -> list[ReferenceInventoryItem]:
    repo_root = repo_root.resolve()
    references_dir = references_dir.resolve()

    if not references_dir.exists():
        raise ValueError(f"References directory does not exist: {references_dir}")

    inventory: list[ReferenceInventoryItem] = []
    for reference_file in sorted(references_dir.iterdir(), key=lambda path: path.name):
        if not reference_file.is_file():
            continue

        inventory.append(
            ReferenceInventoryItem(
                path=_to_repo_relative_path(repo_root, reference_file),
                source_type=_detect_source_type(reference_file),
                size_bytes=reference_file.stat().st_size,
                hint=REFERENCE_HINTS.get(reference_file.name, "local SPK reference file"),
            )
        )

    if not inventory:
        raise ValueError(f"No reference files found under: {references_dir}")

    return inventory


# Convert a local file path into the repository-relative path used in artifacts.
def _to_repo_relative_path(repo_root: Path, file_path: Path) -> str:
    return file_path.resolve().relative_to(repo_root).as_posix()


# Classify one local reference file into the source types accepted by Stage 2.
def _detect_source_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return "markdown"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image"

    return "other"
