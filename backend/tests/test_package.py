"""Smoke tests for the Phase 1 backend package foundation."""

from app import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_python_version_meets_minimum() -> None:
    import sys

    assert sys.version_info >= (3, 12)
