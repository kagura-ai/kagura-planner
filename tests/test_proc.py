"""Tests for kagura_planner.proc — as_text normalisation."""
from __future__ import annotations

from kagura_planner.proc import as_text


def test_as_text_bytes_decoded():
    assert as_text(b"hello") == "hello"


def test_as_text_bytes_with_replacement():
    result = as_text(b"\xff\xfe")
    assert isinstance(result, str)


def test_as_text_str_passthrough():
    assert as_text("hi") == "hi"


def test_as_text_none_returns_empty():
    assert as_text(None) == ""


def test_as_text_empty_string():
    assert as_text("") == ""


def test_as_text_empty_bytes():
    assert as_text(b"") == ""
