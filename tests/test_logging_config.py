"""Tests for app.logging_config — pure config builder + dictConfig wiring."""
from __future__ import annotations

import logging

from app.logging_config import build_logging_config, configure_logging


def test_build_logging_config_contains_json_formatter() -> None:
    cfg = build_logging_config("INFO")
    assert cfg["formatters"]["json"]["()"].endswith("JsonFormatter")
    assert cfg["handlers"]["default"]["formatter"] == "json"
    assert cfg["root"]["level"] == "INFO"


def test_configure_logging_applies_level() -> None:
    configure_logging("DEBUG")
    assert logging.getLogger("app").level == logging.DEBUG
    # restore quieter state for the rest of the suite
    configure_logging("WARNING")
