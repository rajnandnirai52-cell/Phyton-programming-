"""Console UI for the File Organizer Tool."""

from .manager import FileOrganizer
from .exceptions import OrganizerError

MENU = """
==============================
 FILE ORGANIZER TOOL
==============================
1. Categorize files in a folder
2. Find duplicate files (report only)
3. Quarantine duplicate files
4. Batch rename files
5. View operation log
6. Undo last operation
0. Exit
==============================
"""


def _progress(msg: str) -> None:
    # \r rewrites the same line so the screen doesn't fill with updates
    print(f"\r{msg:<60}", end="", flush=True)


def print_duplicate_report(groups: dict) -> None:
    if not groups:
        print("No duplicate files found.")
        return
    print(f"\nFound {len(groups)} duplicate group(s):")
    for i, (file_hash, paths) in enumerate(groups.items(), start=1):
        print(f"\nGroup {i} (hash {file_hash[:10]}...):")
        for p in paths:
            print(f"  {p}")


def print_log(entries: list) -> None:
    if not entries:
        print("No operations logged yet.")
        return
    print(f"\n{'ID':<10}{'Type':<22}{'Time':<20}{'Files':<7}{'Undone':<7}")
    print("-" * 66)
    for e in entries:
        print(
            f"{e['id']:<10}{e['type']:<22}{e['timestamp']:<20}"
            f"{len(e['moves']):<7}{('yes' if e['undone'] else 'no'):<7}"
        )


def main() -> None:
    organizer = FileOrganizer()

    print("File Organizer Tool")
    while True:
        print(MENU)
        choice = input("Select an option: ").strip()

        try:
            if choice == "1":
                folder = input("Folder to organize: ").strip()
                recursive = input("Include subfolders? (y/N): ").strip().lower() == "y"
                result = organizer.categorize(folder, recursive)
                print(f"Moved {result['moved']} file(s):")
                for cat, count in result["by_category"].items():
                    print(f"  {cat}: {count}")

            elif choice == "2":
                folder = input("Folder to scan: ").strip()
                recursive = input("Include subfolders? (Y/n): ").strip().lower() != "n"
                print("Scanning (press Ctrl+C to cancel)...")
                groups = organizer.find_duplicates(folder, recursive, progress=_progress)
                print()
                print_duplicate_report(groups)

            elif choice == "3":
                folder = input("Folder to scan: ").strip()
                recursive = input("Include subfolders? (Y/n): ").strip().lower() != "n"
                print("Scanning (press Ctrl+C to cancel)...")
                result = organizer.quarantine_duplicates(folder, recursive, progress=_progress)
                print()
                print(
                    f"Found {result['groups_found']} duplicate group(s); "
                    f"quarantined {result['quarantined']} file(s)."
                )

            elif choice == "4":
                folder = input("Folder to rename files in: ").strip()
                print("Pattern placeholders: {name} {ext} {index} {parent}")
                pattern = input("Rename pattern (e.g. '{name}_{index}'): ").strip()
                ext_filter = input("Only rename files with extension (blank = all): ").strip() or None
                start_in = input("Start index [1]: ").strip()
                start_index = int(start_in) if start_in else 1
                recursive = input("Include subfolders? (y/N): ").strip().lower() == "y"
                result = organizer.batch_rename(folder, pattern, ext_filter, start_index, recursive)
                print(f"Renamed {result['renamed']} file(s).")

            elif choice == "5":
                print_log(organizer.logger.history())

            elif choice == "6":
                result = organizer.undo_last()
                print(f"Undid '{result['description']}' — restored {result['restored']} file(s).")
                if result["failed"]:
                    print(f"Could not restore {len(result['failed'])} file(s) (already moved/missing):")
                    for f in result["failed"]:
                        print(f"  {f}")

            elif choice == "0":
                print("Goodbye.")
                break

            else:
                print("Invalid option, please choose again.")

        except KeyboardInterrupt:
            print("\nCancelled. Nothing was changed.")
        except OrganizerError as exc:
            print(f"Error: {exc}")
        except ValueError:
            print("Please enter a valid number.")
        except Exception as exc:
            print(f"Unexpected error: {exc}")


if __name__ == "__main__":
    main()
