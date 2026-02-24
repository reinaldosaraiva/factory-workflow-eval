#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.notes_repo import get_db_path, initialize_database


def main() -> None:
    db_path = get_db_path()
    initialize_database(db_path)
    print(f"migrations applied to {db_path}")


if __name__ == "__main__":
    main()
