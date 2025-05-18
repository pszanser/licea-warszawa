"""
Unit tests for scripts.config.test_constants.
Testing framework: pytest.
Covering all public constants and functions, including edge cases.
"""

import pytest
import importlib
from scripts.config import test_constants

def test_DEFAULT_VALUE_exists_and_is_int():
    # Presence
    assert hasattr(test_constants, "DEFAULT_VALUE"), "DEFAULT_VALUE should be defined"
    # Type
    assert isinstance(test_constants.DEFAULT_VALUE, int), "DEFAULT_VALUE should be an int"
    # Value
    assert test_constants.DEFAULT_VALUE == 100

@pytest.mark.parametrize("threshold", test_constants.THRESHOLDS)
def test_THRESHOLDS_member_types(threshold):
    assert isinstance(threshold, int), "Each threshold should be an int"

def test_THRESHOLDS_length_and_entries():
    assert len(test_constants.THRESHOLDS) == 3
    assert 20 in test_constants.THRESHOLDS

@pytest.mark.parametrize("key,value", list(test_constants.OPTIONS.items()))
def test_OPTIONS_member_types_and_keys(key, value):
    assert isinstance(key, str), "Option keys should be strings"
    assert isinstance(value, bool), "Option values should be bools"

def test_OPTIONS_length_and_entries():
    assert len(test_constants.OPTIONS) == 2
    assert "opt1" in test_constants.OPTIONS

@pytest.mark.parametrize("stype", test_constants.SUPPORTED_TYPES)
def test_SUPPORTED_TYPES_member_types(stype):
    assert isinstance(stype, str), "Each supported type should be a string"

def test_SUPPORTED_TYPES_length_and_entries():
    assert len(test_constants.SUPPORTED_TYPES) == 3
    assert "int" in test_constants.SUPPORTED_TYPES

def test_parse_constant_happy_path():
    result = test_constants.parse_constant("A")
    assert result == 1

def test_parse_constant_invalid_raises_value_error():
    with pytest.raises(ValueError):
        test_constants.parse_constant("INVALID")

def test_dynamic_constant_default(monkeypatch):
    # Ensure default when env var is not set
    monkeypatch.delenv("DYNAMIC", raising=False)
    importlib.reload(test_constants)
    assert test_constants.DYNAMIC == "default_value"

def test_dynamic_constant_from_env(monkeypatch):
    monkeypatch.setenv("DYNAMIC", "custom")
    importlib.reload(test_constants)
    assert test_constants.DYNAMIC == "custom"