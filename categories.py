"""Extension-to-category mapping for automatic file categorization."""

CATEGORY_MAP = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".tex"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx", ".odp"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".html", ".css", ".json", ".xml", ".sh"},
    "Executables": {".exe", ".msi", ".apk", ".appimage", ".deb"},
}

OTHER_CATEGORY = "Others"


def category_for(filename: str) -> str:
    """Return the category folder name for a given filename, based on its extension."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for category, extensions in CATEGORY_MAP.items():
        if ext in extensions:
            return category
    return OTHER_CATEGORY
