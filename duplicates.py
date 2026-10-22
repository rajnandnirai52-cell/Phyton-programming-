"""Duplicate file detection via content hashing (SHA-256).

Three-stage filter so large folders stay fast:
  1. group by file size        (files with a unique size can't be duplicates)
  2. hash only the first 64 KB (cheap check that rules out most size-matches)
  3. full SHA-256 hash         (only for files that still look identical)
"""

import hashlib
import os
from typing import Callable, Dict, List, Optional

CHUNK_SIZE = 65536
QUICK_HASH_BYTES = 65536

# Folders that are never worth scanning (huge, auto-generated, or ours).
IGNORED_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".idea", ".vscode", "site-packages", "_duplicates_quarantine",
}

ProgressFn = Optional[Callable[[str], None]]


def _hash_file(path: str, limit: Optional[int] = None) -> str:
    """SHA-256 of a file. If `limit` is given, only the first `limit` bytes."""
    hasher = hashlib.sha256()
    remaining = limit
    with open(path, "rb") as f:
        while True:
            size = CHUNK_SIZE if remaining is None else min(CHUNK_SIZE, remaining)
            if size == 0:
                break
            chunk = f.read(size)
            if not chunk:
                break
            hasher.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return hasher.hexdigest()


def _iter_files(directory: str, recursive: bool):
    if recursive:
        for root, dirs, files in os.walk(directory, onerror=lambda e: None):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]  # prune in place
            for name in files:
                path = os.path.join(root, name)
                if not os.path.islink(path):
                    yield path
    else:
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if os.path.isfile(path) and not os.path.islink(path):
                yield path


def find_duplicates(
    directory: str,
    recursive: bool = True,
    min_size: int = 1,
    progress: ProgressFn = None,
) -> Dict[str, List[str]]:
    """Group files by content hash. Only groups with 2+ files are returned.
    `min_size` skips tiny files (default 1 byte skips empty files, which would
    all trivially match each other). `progress` receives status strings."""
    say = progress or (lambda _msg: None)

    # Stage 1: size buckets
    by_size: Dict[int, List[str]] = {}
    count = 0
    for path in _iter_files(directory, recursive):
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if size < min_size:
            continue
        by_size.setdefault(size, []).append(path)
        count += 1
        if count % 500 == 0:
            say(f"Scanning... {count} files found")
    say(f"Scanned {count} files.")

    size_candidates = [p for paths in by_size.values() if len(paths) > 1 for p in paths]

    # Stage 2: quick hash of the first 64 KB
    by_quick: Dict[tuple, List[str]] = {}
    for i, path in enumerate(size_candidates, start=1):
        try:
            key = (os.path.getsize(path), _hash_file(path, QUICK_HASH_BYTES))
        except OSError:
            continue  # unreadable / permission denied / vanished: skip it
        by_quick.setdefault(key, []).append(path)
        if i % 200 == 0:
            say(f"Quick-checking {i}/{len(size_candidates)} candidates...")

    full_candidates = [p for paths in by_quick.values() if len(paths) > 1 for p in paths]

    # Stage 3: full hash only where it matters
    by_hash: Dict[str, List[str]] = {}
    for i, path in enumerate(full_candidates, start=1):
        try:
            by_hash.setdefault(_hash_file(path), []).append(path)
        except OSError:
            continue
        if i % 50 == 0 or i == len(full_candidates):
            say(f"Fully hashing {i}/{len(full_candidates)} files...")

    return {h: paths for h, paths in by_hash.items() if len(paths) > 1}
