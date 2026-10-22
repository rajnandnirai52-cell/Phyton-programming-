"""
File Organizer Tool
---------------------
Console UI by default; pass --gui for the optional Tkinter interface.

Run with:
    python main.py          # console mode
    python main.py --gui    # Tkinter GUI mode
"""

import sys


def main() -> None:
    if "--gui" in sys.argv:
        try:
            from organizer_system.gui import main as gui_main
        except ImportError:
            print("Tkinter is not available on this system. Falling back to console mode.\n")
        else:
            gui_main()
            return

    from organizer_system.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
