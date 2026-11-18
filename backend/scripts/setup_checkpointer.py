"""Initialize LangChain PostgreSQL checkpointer tables once."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.checkpointer import setup_checkpointer_schema
from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    setup_checkpointer_schema(settings)
    print("Checkpointer schema initialized.")


if __name__ == "__main__":
    main()
