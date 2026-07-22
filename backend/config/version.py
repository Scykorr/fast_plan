from pathlib import Path

# Prefer monorepo root (local: backend/config → ../../VERSION).
# Docker image copies VERSION next to the Django app (/app/VERSION).
_VERSION_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "VERSION",
    Path(__file__).resolve().parents[1] / "VERSION",
    Path("/VERSION"),
)


def get_product_version() -> str:
    for path in _VERSION_CANDIDATES:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return "0.0.0"
