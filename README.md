# File Organizer Tool

A Python tool that automatically organizes messy folders — console UI by
default, optional Tkinter GUI.

## Features
- **Automatic categorization** — sorts files into subfolders (Images, Documents,
  Spreadsheets, Presentations, Audio, Video, Archives, Code, Executables, Others)
  based on extension
- **Duplicate detection** — finds files with identical content via SHA-256 hashing,
  using a 3-stage filter (group by size → hash first 64 KB → full hash) so big folders
  stay fast. Skips `.git`, `node_modules`, `venv`, `__pycache__` etc., ignores empty
  files and symlinks, shows live progress, and Ctrl+C cancels safely
- **Duplicate quarantine** — moves all but one copy of each duplicate group into a
  `_duplicates_quarantine` folder rather than deleting them, so it's always reversible
- **Batch rename** — rename many files at once using a pattern with placeholders:
  `{name}`, `{ext}`, `{index}`, `{parent}`
- **Operation log** — every categorize / quarantine / rename run is recorded with a
  timestamp and the exact file moves it made
- **Undo last operation** — reverses the most recent operation, move for move
- **Optional Tkinter GUI** — folder picker, one-click actions, a rename dialog, and
  an in-window log/undo panel

## Structure
```
main.py                        # entry point: `python main.py` or `python main.py --gui`
organizer_system/
    categories.py               # extension → category mapping
    duplicates.py               # SHA-256-based duplicate detection
    logger.py                   # operation_log.json — records move batches for undo
    manager.py                  # FileOrganizer: categorize / dedupe / rename / undo
    cli.py                      # console UI
    gui.py                      # optional Tkinter UI
    exceptions.py                # custom exception hierarchy
data/                           # created automatically on first run
    operations_log.json
```

## Run it
```bash
python main.py            # console mode
python main.py --gui      # Tkinter GUI (requires tkinter — see below)
```

If `tkinter` isn't installed, `--gui` prints a message and falls back to console mode.
On Debian/Ubuntu: `sudo apt install python3-tk`. It ships with the standard python.org
installers on Windows and macOS.

## How undo works
Every mutating operation (categorize, quarantine, rename) is really just a batch of
file **moves**, so they all share one undo mechanism: the exact `(src, dst)` pairs that
happened are logged, and "undo" simply moves each `dst` back to its `src`, most-recent
operation first. Only the single most recent (not-yet-undone) operation can be undone —
there's no multi-step undo stack.

Both the forward operations and undo use a **two-phase move** internally (rename
everything to a private temp name first, then to the real target) so that renaming or
restoring a batch of files never produces a surprise `" (1)"` suffix just because of
the order files happened to be processed in.

## Safety notes
- Duplicates are **quarantined, never deleted** — nothing this tool does is permanently
  destructive; everything can be undone as long as you haven't manually touched the
  files afterward.
- If a file that was moved has since been renamed/deleted/moved again by something
  else, undo reports it under `"failed"` rather than raising — you get a summary of
  what could and couldn't be restored.
- Filename collisions during any move are resolved by appending `" (1)"`, `" (2)"`, etc.
  — existing files are never overwritten.
