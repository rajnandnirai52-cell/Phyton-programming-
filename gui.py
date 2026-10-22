"""Optional Tkinter GUI for the File Organizer Tool.

Run with:  python main.py --gui
(falls back to the console UI if Tkinter isn't available on this system)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .manager import FileOrganizer
from .exceptions import OrganizerError


class OrganizerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Organizer Tool")
        self.geometry("640x480")

        self.organizer = FileOrganizer()
        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)

        self._build_layout()

    # ---------- layout ----------
    def _build_layout(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Folder:").pack(side="left")
        ttk.Entry(top, textvariable=self.folder_var, width=50).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(top, text="Browse...", command=self._browse).pack(side="left")

        ttk.Checkbutton(self, text="Include subfolders", variable=self.recursive_var).pack(anchor="w", padx=10)

        actions = ttk.Frame(self, padding=10)
        actions.pack(fill="x")
        ttk.Button(actions, text="Categorize Files", command=self._categorize).pack(side="left", padx=3)
        ttk.Button(actions, text="Find Duplicates", command=self._find_duplicates).pack(side="left", padx=3)
        ttk.Button(actions, text="Quarantine Duplicates", command=self._quarantine).pack(side="left", padx=3)
        ttk.Button(actions, text="Batch Rename...", command=self._open_rename_dialog).pack(side="left", padx=3)
        ttk.Button(actions, text="Undo Last", command=self._undo).pack(side="left", padx=3)

        ttk.Label(self, text="Output / Operation Log:").pack(anchor="w", padx=10)
        self.output = tk.Text(self, height=18, wrap="word")
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ttk.Button(self, text="Refresh Operation Log", command=self._show_log).pack(pady=(0, 10))

    # ---------- helpers ----------
    def _browse(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.folder_var.set(path)

    def _log(self, text: str) -> None:
        self.output.insert("end", text + "\n")
        self.output.see("end")

    def _get_folder(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("No folder", "Please choose a folder first.")
            return None
        return folder

    # ---------- actions ----------
    def _categorize(self) -> None:
        folder = self._get_folder()
        if not folder:
            return
        try:
            result = self.organizer.categorize(folder, self.recursive_var.get())
        except OrganizerError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._log(f"Categorized {result['moved']} file(s):")
        for cat, count in result["by_category"].items():
            self._log(f"  {cat}: {count}")

    def _find_duplicates(self) -> None:
        folder = self._get_folder()
        if not folder:
            return
        try:
            groups = self.organizer.find_duplicates(folder, self.recursive_var.get())
        except OrganizerError as exc:
            messagebox.showerror("Error", str(exc))
            return
        if not groups:
            self._log("No duplicate files found.")
            return
        self._log(f"Found {len(groups)} duplicate group(s):")
        for i, (file_hash, paths) in enumerate(groups.items(), start=1):
            self._log(f"  Group {i} ({file_hash[:10]}...):")
            for p in paths:
                self._log(f"    {p}")

    def _quarantine(self) -> None:
        folder = self._get_folder()
        if not folder:
            return
        try:
            result = self.organizer.quarantine_duplicates(folder, self.recursive_var.get())
        except OrganizerError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._log(
            f"Found {result['groups_found']} duplicate group(s); "
            f"quarantined {result['quarantined']} file(s)."
        )

    def _undo(self) -> None:
        try:
            result = self.organizer.undo_last()
        except OrganizerError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self._log(f"Undid '{result['description']}' — restored {result['restored']} file(s).")
        if result["failed"]:
            self._log(f"Could not restore {len(result['failed'])} file(s) (already moved/missing).")

    def _show_log(self) -> None:
        entries = self.organizer.logger.history()
        if not entries:
            self._log("No operations logged yet.")
            return
        self._log("--- Operation Log ---")
        for e in entries:
            status = "undone" if e["undone"] else "active"
            self._log(f"[{e['id']}] {e['type']} — {e['description']} ({status})")

    # ---------- batch rename dialog ----------
    def _open_rename_dialog(self) -> None:
        folder = self._get_folder()
        if not folder:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Batch Rename")
        dialog.geometry("380x220")
        dialog.transient(self)

        form = ttk.Frame(dialog, padding=15)
        form.pack(fill="both", expand=True)

        ttk.Label(form, text="Pattern (e.g. '{name}_{index}'):").grid(row=0, column=0, sticky="w", pady=4)
        pattern_entry = ttk.Entry(form)
        pattern_entry.insert(0, "{name}_{index}")
        pattern_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Extension filter (blank = all):").grid(row=1, column=0, sticky="w", pady=4)
        ext_entry = ttk.Entry(form)
        ext_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Start index:").grid(row=2, column=0, sticky="w", pady=4)
        index_entry = ttk.Entry(form)
        index_entry.insert(0, "1")
        index_entry.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(
            form, text="Placeholders: {name} {ext} {index} {parent}", foreground="gray"
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        form.columnconfigure(1, weight=1)

        def do_rename():
            pattern = pattern_entry.get().strip()
            ext = ext_entry.get().strip() or None
            try:
                start_index = int(index_entry.get().strip() or "1")
                result = self.organizer.batch_rename(
                    folder, pattern, ext, start_index, self.recursive_var.get()
                )
            except (OrganizerError, ValueError) as exc:
                messagebox.showerror("Error", str(exc))
                return
            self._log(f"Renamed {result['renamed']} file(s).")
            dialog.destroy()

        ttk.Button(form, text="Rename", command=do_rename).grid(row=4, column=0, columnspan=2, pady=15)


def main() -> None:
    app = OrganizerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
