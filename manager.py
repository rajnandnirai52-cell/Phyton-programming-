"""Core operations: categorize files, quarantine duplicates, batch rename,
and undo the most recent operation. All mutating operations go through
`_execute_moves`, which is collision-safe and feeds the operation logger,
so every one of them can be undone the same generic way."""

import os
import shutil
import uuid
from typing import Dict, List, Optional

from .categories import category_for
from .duplicates import find_duplicates
from .logger import OperationLogger
from .exceptions import PathNotFoundError, InvalidInputError, NothingToUndoError

QUARANTINE_FOLDER_NAME = "_duplicates_quarantine"


def _require_dir(path: str) -> None:
    if not os.path.isdir(path):
        raise PathNotFoundError(f"Directory not found: '{path}'.")


def _unique_destination(dst: str) -> str:
    """If dst already exists, append ' (1)', ' (2)', ... before the extension
    until a free path is found."""
    if not os.path.exists(dst):
        return dst
    base, ext = os.path.splitext(dst)
    counter = 1
    candidate = f"{base} ({counter}){ext}"
    while os.path.exists(candidate):
        counter += 1
        candidate = f"{base} ({counter}){ext}"
    return candidate


class FileOrganizer:
    def __init__(self, logger: Optional[OperationLogger] = None):
        self.logger = logger or OperationLogger()

    # ---------- internal move executor (shared by all operations) ----------
    def _execute_moves(self, planned: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """planned: list of {"src": ..., "dst": ...} (requested destinations).
        Executes them one by one, resolving collisions, and returns the list
        of {"src": ..., "dst": ...} that actually happened (for logging)."""
        executed = []
        for item in planned:
            src, dst = item["src"], item["dst"]
            if not os.path.exists(src):
                continue  # source vanished or was already handled; skip silently
            final_dst = _unique_destination(dst)
            os.makedirs(os.path.dirname(final_dst) or ".", exist_ok=True)
            shutil.move(src, final_dst)
            executed.append({"src": src, "dst": final_dst})
        return executed

    # ---------- categorize ----------
    def categorize(self, source_dir: str, recursive: bool = False) -> dict:
        _require_dir(source_dir)

        if recursive:
            candidates = [
                os.path.join(root, name)
                for root, _dirs, files in os.walk(source_dir)
                for name in files
            ]
        else:
            candidates = [
                os.path.join(source_dir, name)
                for name in os.listdir(source_dir)
                if os.path.isfile(os.path.join(source_dir, name))
            ]

        planned = []
        by_category: Dict[str, int] = {}
        for path in candidates:
            name = os.path.basename(path)
            category = category_for(name)
            dest_dir = os.path.join(source_dir, category)
            planned.append({"src": path, "dst": os.path.join(dest_dir, name)})
            by_category[category] = by_category.get(category, 0) + 1

        executed = self._execute_moves(planned)
        if executed:
            self.logger.record(
                "categorize",
                f"Categorized {len(executed)} file(s) in '{source_dir}'.",
                executed,
            )
        return {"moved": len(executed), "by_category": by_category}

    # ---------- duplicates ----------
    def find_duplicates(self, directory: str, recursive: bool = True, progress=None) -> Dict[str, List[str]]:
        _require_dir(directory)
        return find_duplicates(directory, recursive, progress=progress)

    def quarantine_duplicates(
        self, directory: str, recursive: bool = True, keep: str = "first", progress=None
    ) -> dict:
        """Moves all but one copy of each duplicate group into a quarantine
        subfolder (reversible via undo) rather than deleting them outright."""
        _require_dir(directory)
        groups = find_duplicates(directory, recursive, progress=progress)

        planned = []
        quarantine_dir = os.path.join(directory, QUARANTINE_FOLDER_NAME)
        for _hash, paths in groups.items():
            ordered = sorted(paths, key=lambda p: os.path.getmtime(p))
            keeper = ordered[0] if keep == "first" else ordered[-1]
            for path in paths:
                if path == keeper:
                    continue
                planned.append(
                    {"src": path, "dst": os.path.join(quarantine_dir, os.path.basename(path))}
                )

        executed = self._execute_moves(planned)
        if executed:
            self.logger.record(
                "quarantine_duplicates",
                f"Quarantined {len(executed)} duplicate file(s) from '{directory}'.",
                executed,
            )
        return {"groups_found": len(groups), "quarantined": len(executed)}

    # ---------- batch rename ----------
    def batch_rename(
        self,
        directory: str,
        pattern: str,
        extension_filter: Optional[str] = None,
        start_index: int = 1,
        recursive: bool = False,
    ) -> dict:
        _require_dir(directory)
        if not pattern or "{name}" not in pattern and "{index}" not in pattern:
            raise InvalidInputError(
                "Pattern should include at least one of {name} or {index} to avoid collisions."
            )

        if recursive:
            candidates = [
                os.path.join(root, name)
                for root, _dirs, files in os.walk(directory)
                for name in sorted(files)
            ]
        else:
            candidates = [
                os.path.join(directory, name)
                for name in sorted(os.listdir(directory))
                if os.path.isfile(os.path.join(directory, name))
            ]

        if extension_filter:
            ext = extension_filter if extension_filter.startswith(".") else f".{extension_filter}"
            candidates = [p for p in candidates if p.lower().endswith(ext.lower())]

        planned = []
        index = start_index
        for path in candidates:
            folder = os.path.dirname(path)
            stem, ext = os.path.splitext(os.path.basename(path))
            try:
                new_name = pattern.format(name=stem, ext=ext.lstrip("."), index=index, parent=os.path.basename(folder))
            except (KeyError, IndexError) as exc:
                raise InvalidInputError(f"Invalid pattern placeholder: {exc}") from exc
            if not new_name.lower().endswith(ext.lower()) and "{ext}" not in pattern:
                new_name += ext
            planned.append({"src": path, "dst": os.path.join(folder, new_name)})
            index += 1

        # Two-phase move: rename every file to a private temp name first, then
        # to its real target name. Without this, renaming a.txt -> existing_1.txt
        # could collide with an as-yet-unrenamed existing_1.txt later in the same
        # batch, producing a confusing " (1)" suffix purely due to processing order.
        temp_moves = [
            {"src": item["src"], "dst": item["src"] + f".__rename_tmp_{i}__"}
            for i, item in enumerate(planned)
        ]
        for item in temp_moves:
            os.rename(item["src"], item["dst"])

        final_moves = [
            {"src": temp["dst"], "dst": final["dst"]}
            for temp, final in zip(temp_moves, planned)
        ]
        executed_final = self._execute_moves(final_moves)

        # Log using the *original* source paths so undo restores the true originals.
        executed = [
            {"src": orig["src"], "dst": final["dst"]}
            for orig, final in zip(planned, executed_final)
        ]
        if executed:
            self.logger.record(
                "batch_rename",
                f"Renamed {len(executed)} file(s) in '{directory}' using pattern '{pattern}'.",
                executed,
            )
        return {"renamed": len(executed)}

    # ---------- undo ----------
    def undo_last(self) -> dict:
        entry = self.logger.last_undoable()
        if entry is None:
            raise NothingToUndoError("There is no operation to undo.")

        # Two-phase restore, same reasoning as batch_rename: if move A's
        # destination is the same path move B's original source lives at,
        # restoring in a naive single pass can find that path "occupied" by
        # a file this very undo hasn't relocated yet, and misfile it under a
        # " (1)" suffix. Clearing every dst to a private temp name first
        # removes that ordering hazard entirely.
        temp_holders = []  # (move, temp_path or None if dst was already missing)
        for move in entry["moves"]:
            dst = move["dst"]
            if os.path.exists(dst):
                temp_path = dst + f".__undo_tmp_{uuid.uuid4().hex[:8]}__"
                os.rename(dst, temp_path)
                temp_holders.append((move, temp_path))
            else:
                temp_holders.append((move, None))

        restored = 0
        failed = []
        for move, temp_path in temp_holders:
            if temp_path is None:
                failed.append(move["dst"])
                continue
            final_src = _unique_destination(move["src"])
            os.makedirs(os.path.dirname(final_src) or ".", exist_ok=True)
            shutil.move(temp_path, final_src)
            restored += 1

        self.logger.mark_undone(entry["id"])
        return {
            "operation": entry["type"],
            "description": entry["description"],
            "restored": restored,
            "failed": failed,
        }
