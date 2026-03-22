"""Custom exceptions for the pptgen platform."""


class PptgenError(Exception):
    """Base exception for all pptgen errors."""


class YAMLLoadError(PptgenError):
    """Raised when a YAML file cannot be read or parsed by PyYAML."""


class ParseError(PptgenError):
    """Raised when YAML content does not conform to the DeckFile model structure."""


class RegistryError(PptgenError):
    """Raised when the template registry cannot be loaded or is malformed."""


class TemplateLoadError(PptgenError):
    """Raised when a template .pptx file cannot be opened."""


class TemplateCompatibilityError(PptgenError):
    """Raised when a template is missing a required layout or placeholder."""
