"""Entrada sencilla para ejecutar el analisis desde la raiz del proyecto."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tiktok_analytics.cli import main  # noqa: E402


if __name__ == "__main__":
    main()

