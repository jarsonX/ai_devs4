# Reference file loading helpers for the L4 sendit MVP1 pipeline.

from pathlib import Path


# Load the SPK declaration template text from the local references.
def load_declaration_template(references_dir: Path) -> str:
    template_path = references_dir / "zalacznik-E.md"
    return template_path.read_text(encoding="utf-8")
