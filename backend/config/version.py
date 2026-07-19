from pathlib import Path

# repo root: backend/config/version.py → ../../VERSION
_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"


def get_product_version() -> str:
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
