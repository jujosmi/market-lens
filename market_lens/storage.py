"""Local, single-user watchlist persistence using a small JSON file."""

import json
import os
from pathlib import Path

from .config import DEFAULT_WATCHLIST, MAX_WATCHLIST_SIZE


WATCHLIST_PATH = Path(__file__).resolve().parent.parent / ".market_lens_watchlist.json"


def load_watchlist(path: Path = WATCHLIST_PATH) -> list[str]:
    try:
        symbols = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(symbols, list):
            return DEFAULT_WATCHLIST.copy()
        cleaned = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
        return cleaned[:MAX_WATCHLIST_SIZE] or DEFAULT_WATCHLIST.copy()
    except (OSError, json.JSONDecodeError):
        return DEFAULT_WATCHLIST.copy()


def save_watchlist(symbols: list[str], path: Path = WATCHLIST_PATH) -> None:
    cleaned = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(cleaned[:MAX_WATCHLIST_SIZE], indent=2), encoding="utf-8")
    os.replace(temporary, path)
