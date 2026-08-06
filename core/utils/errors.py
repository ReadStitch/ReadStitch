"""Custom exceptions for ReadStitch application."""


class ReadStitchError(Exception):
    """Base exception for all ReadStitch errors."""


class DirectoryException(ReadStitchError):
    """Raised when there's an issue with directory operations."""


class ProfileException(ReadStitchError):
    """Raised when there's an issue with profile operations."""

