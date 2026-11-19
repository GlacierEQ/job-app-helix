"""Shared exceptions for required in-repository evidence sources."""

from __future__ import annotations


class PortfolioSourceError(RuntimeError):
    """Raised when a required in-repository portfolio source is missing or empty.

    In-repository evidence sources fail closed: a missing manifest or record
    directory must raise, never silently produce an empty result.
    """
