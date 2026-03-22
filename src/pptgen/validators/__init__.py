"""Public validator exports for the pptgen.validators package."""

from .deck_validator import ValidationResult, validate_deck

__all__ = ["validate_deck", "ValidationResult"]
