"""Tests for the pptgen error taxonomy (Stage 6A — PR 1).

Verifies that:
- ErrorCategory enum values are correct strings
- PptgenError base class carries a category attribute
- All errors defined in errors/__init__.py have the expected category
- New Stage-6A error types (InputSizeError, WorkspaceError, etc.) have correct categories
- Scattered in-module errors (PipelineError, APIError, etc.) carry category attributes
"""

import pytest

from pptgen.errors import (
    ErrorCategory,
    PptgenError,
    YAMLLoadError,
    ParseError,
    RegistryError,
    TemplateLoadError,
    TemplateCompatibilityError,
    InputSizeError,
    WorkspaceError,
    ConfigurationError,
    PptgenTimeoutError,
)


# ---------------------------------------------------------------------------
# ErrorCategory
# ---------------------------------------------------------------------------

class TestErrorCategory:
    def test_is_str_enum(self):
        assert isinstance(ErrorCategory.VALIDATION, str)

    def test_all_expected_categories_present(self):
        expected = {
            "validation", "connector", "ai_provider", "planning",
            "rendering", "configuration", "workspace", "timeout", "system",
        }
        actual = {c.value for c in ErrorCategory}
        assert actual == expected


# ---------------------------------------------------------------------------
# PptgenError base class
# ---------------------------------------------------------------------------

class TestPptgenErrorBase:
    def test_has_category_attribute(self):
        err = PptgenError("boom")
        assert hasattr(err, "category")

    def test_default_category_is_system(self):
        assert PptgenError.category == ErrorCategory.SYSTEM

    def test_is_exception(self):
        with pytest.raises(PptgenError):
            raise PptgenError("test")


# ---------------------------------------------------------------------------
# Errors defined in errors/__init__.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc_class,expected_category", [
    (YAMLLoadError,              ErrorCategory.VALIDATION),
    (ParseError,                 ErrorCategory.VALIDATION),
    (RegistryError,              ErrorCategory.CONFIGURATION),
    (TemplateLoadError,          ErrorCategory.CONFIGURATION),
    (TemplateCompatibilityError, ErrorCategory.CONFIGURATION),
    (InputSizeError,             ErrorCategory.VALIDATION),
    (WorkspaceError,             ErrorCategory.WORKSPACE),
    (ConfigurationError,         ErrorCategory.CONFIGURATION),
    (PptgenTimeoutError,         ErrorCategory.TIMEOUT),
])
def test_error_category(exc_class, expected_category):
    assert exc_class.category == expected_category


class TestPptgenErrorInheritance:
    def test_yaml_load_error_is_pptgen_error(self):
        assert issubclass(YAMLLoadError, PptgenError)

    def test_input_size_error_is_pptgen_error(self):
        assert issubclass(InputSizeError, PptgenError)

    def test_workspace_error_is_pptgen_error(self):
        assert issubclass(WorkspaceError, PptgenError)

    def test_configuration_error_is_pptgen_error(self):
        assert issubclass(ConfigurationError, PptgenError)

    def test_timeout_error_is_pptgen_error(self):
        assert issubclass(PptgenTimeoutError, PptgenError)


# ---------------------------------------------------------------------------
# Scattered in-module errors carry category attribute
# ---------------------------------------------------------------------------

class TestScatteredErrorCategories:
    def test_pipeline_error_has_category(self):
        from pptgen.pipeline.generation_pipeline import PipelineError
        from pptgen.errors import ErrorCategory
        assert PipelineError.category == ErrorCategory.SYSTEM

    def test_input_router_error_has_category(self):
        from pptgen.input_router.router import InputRouterError
        from pptgen.errors import ErrorCategory
        assert InputRouterError.category == ErrorCategory.VALIDATION

    def test_routing_table_error_has_category(self):
        from pptgen.input_router.routing_table_loader import RoutingTableError
        from pptgen.errors import ErrorCategory
        assert RoutingTableError.category == ErrorCategory.CONFIGURATION

    def test_api_error_has_category(self):
        from pptgen.api.service import APIError
        from pptgen.errors import ErrorCategory
        assert APIError.category == ErrorCategory.VALIDATION

    def test_api_error_preserves_status_code(self):
        from pptgen.api.service import APIError
        err = APIError("bad request", status_code=422)
        assert err.status_code == 422
        assert str(err) == "bad request"

    def test_playbook_not_found_error_has_category(self):
        from pptgen.playbook_engine.playbook_loader import PlaybookNotFoundError
        from pptgen.errors import ErrorCategory
        assert PlaybookNotFoundError.category == ErrorCategory.CONFIGURATION

    def test_unknown_strategy_error_has_category(self):
        from pptgen.playbook_engine.execution_strategy import UnknownStrategyError
        from pptgen.errors import ErrorCategory
        assert UnknownStrategyError.category == ErrorCategory.CONFIGURATION

    def test_unknown_connector_error_has_category(self):
        from pptgen.connectors.connector_factory import UnknownConnectorError
        from pptgen.errors import ErrorCategory
        assert UnknownConnectorError.category == ErrorCategory.CONFIGURATION

    def test_batch_error_has_category(self):
        from pptgen.orchestration.batch_generator import BatchError
        from pptgen.errors import ErrorCategory
        assert BatchError.category == ErrorCategory.SYSTEM


# ---------------------------------------------------------------------------
# New error type instantiation and raise behaviour
# ---------------------------------------------------------------------------

class TestNewErrorTypes:
    def test_input_size_error_raises(self):
        with pytest.raises(InputSizeError, match="exceeds"):
            raise InputSizeError("Input exceeds 512 KB limit.")

    def test_workspace_error_raises(self):
        with pytest.raises(WorkspaceError):
            raise WorkspaceError("Cannot create workspace directory.")

    def test_pptgen_timeout_error_does_not_shadow_builtin(self):
        # Ensure built-in TimeoutError is unaffected
        assert PptgenTimeoutError is not TimeoutError
        assert issubclass(PptgenTimeoutError, PptgenError)
