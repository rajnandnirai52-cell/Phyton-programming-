"""Persists a history of file operations (as batches of moves) so the most
recent one can be undone, and so the user can review what was done."""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

from .exceptions import StorageError

LOG_DIR = "data"
LOG_FILE = os.path.join(LOG_DIR, "operations_log.json")


class OperationLogger:
    def __init__(self, log_path: str = LOG_FILE):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        if not os.path.exists(self.log_path):
            self._write([])

    # ---------- low-level ----------
    def _write(self, entries: list) -> None:
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except OSError as exc:
            raise StorageError(f"Could not write operation log: {exc}") from exc

    def _read(self) -> list:
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise StorageError(f"Operation log is corrupted: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"Could not read operation log: {exc}") from exc

    # ---------- public API ----------
    def history(self) -> List[dict]:
        return self._read()

    def record(self, op_type: str, description: str, moves: List[dict]) -> dict:
        """moves: list of {"src": ..., "dst": ...} representing what actually
        happened (dst is the real path used, after any collision renaming)."""
        entry = {
            "id": uuid.uuid4().hex[:8],
            "type": op_type,
            "description": description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "moves": moves,
            "undone": False,
        }
        entries = self._read()
        entries.append(entry)
        self._write(entries)
        return entry

    def last_undoable(self) -> Optional[dict]:
        entries = self._read()
        for entry in reversed(entries):
            if not entry.get("undone"):
                return entry
        return None

    def mark_undone(self, entry_id: str) -> None:
        entries = self._read()
        for entry in entries:
            if entry["id"] == entry_id:
                entry["undone"] = True
                break
        self._write(entries)
