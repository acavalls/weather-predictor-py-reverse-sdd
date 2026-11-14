"""Domain error base classes."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""

    pass


class ValidationError(DomainError):
    """Raised when a value object fails validation."""

    pass


class NotFoundError(DomainError):
    """Raised when a requested resource is not found."""

    pass
