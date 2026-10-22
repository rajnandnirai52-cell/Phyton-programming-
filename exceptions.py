"""Custom exceptions used across the File Organizer Tool."""


class OrganizerError(Exception):
    """Base exception for all app-specific errors."""


class PathNotFoundError(OrganizerError):
    """Raised when a given source/target directory does not exist."""


class InvalidInputError(OrganizerError):
    """Raised when user-supplied data fails validation."""


class NothingToUndoError(OrganizerError):
    """Raised when undo is requested but the operation log is empty."""


class StorageError(OrganizerError):
    """Raised when reading/writing the operation log fails."""
