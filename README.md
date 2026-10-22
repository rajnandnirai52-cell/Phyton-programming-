# Quiz Application

A Python quiz app with a console UI (default) and an optional Tkinter GUI.

## Features
- Random question selection from a JSON question bank, optionally filtered by category
- Per-question countdown timer (console: `select`-based on Linux/macOS with a threaded
  fallback on Windows; GUI: a live `after()`-driven countdown)
- Negative marking scheme (default: correct **+4**, wrong **-1**, unanswered **0** — tunable)
- Leaderboard: every attempt is recorded and ranked by score, filterable by category
- Category-based quizzes (General Knowledge, Science, Programming, History by default —
  just edit `data/questions.json` to add your own)
- Optional Tkinter GUI with the same engine/leaderboard underneath
- Custom exceptions for empty question banks, insufficient questions, and bad input

## Structure
```
main.py                        # entry point: `python main.py` or `python main.py --gui`
quiz_system/
    models.py                  # Question, LeaderboardEntry dataclasses
    storage.py                 # loads questions.json, loads/saves leaderboard.json
    engine.py                  # QuizEngine (selection) + Scorer (negative marking)
    leaderboard.py             # add results, ranked top-N
    cli.py                     # console UI with countdown timer
    gui.py                     # optional Tkinter UI
    exceptions.py               # custom exception hierarchy
data/                          # created automatically on first run
    questions.json             # seeded with 12 sample questions across 4 categories
    leaderboard.json
```

## Run it
```bash
python main.py            # console mode
python main.py --gui      # Tkinter GUI (requires tkinter, see below)
```

If `tkinter` isn't installed, `--gui` prints a message and falls back to console mode.
On Debian/Ubuntu, install it with `sudo apt install python3-tk`. It ships with the
standard python.org installers on Windows and macOS.

## Adjusting the marking scheme
Edit the `Scorer` defaults in `quiz_system/engine.py`:
```python
class Scorer:
    def __init__(self, correct_marks=4.0, wrong_marks=-1.0, unanswered_marks=0.0):
        ...
```

## Adding your own questions
Edit `data/questions.json` — each entry needs:
```json
{
  "id": "q13",
  "category": "Geography",
  "question": "What is the longest river in the world?",
  "options": ["Amazon", "Nile", "Yangtze", "Mississippi"],
  "answer_index": 1,
  "difficulty": "medium"
}
```
`answer_index` is the 0-based index into `options` of the correct choice. New categories
are picked up automatically — no code changes needed.

## Notes
- Console timer: on Linux/macOS it uses `select()` on stdin, so a timed-out question never
  leaves a dangling background thread waiting on the next keystroke. On Windows (no `select`
  on stdin) it falls back to a daemon-thread approach; a keystroke that arrives *after* a
  timeout on that platform is simply discarded rather than double-counted.
- `NotEnoughQuestionsError` is raised if you ask for more questions than exist in a category.
