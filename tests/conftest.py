"""Shared pytest fixtures for the pptgen test suite."""

from pathlib import Path

import pytest

from pptgen.registry.registry import TemplateRegistry


@pytest.fixture
def project_root() -> Path:
    """Absolute path to the repository root."""
    return Path(__file__).parent.parent


@pytest.fixture
def examples_dir(project_root: Path) -> Path:
    return project_root / "examples"


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def real_registry_path(project_root: Path) -> Path:
    return project_root / "templates" / "registry.yaml"


@pytest.fixture
def test_registry(fixtures_dir: Path) -> TemplateRegistry:
    """TemplateRegistry loaded from the test fixture registry file."""
    return TemplateRegistry.from_file(fixtures_dir / "test_registry.yaml")
