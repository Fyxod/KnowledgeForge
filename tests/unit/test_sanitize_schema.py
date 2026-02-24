"""
Unit tests for core.utils.sanitize_schema — recursive schema sanitization.
"""

import copy

import pytest


@pytest.mark.unit
class TestSanitizeSchema:
    def test_removes_additional_properties_top_level(self):
        from core.utils.sanitize_schema import sanitize_schema

        schema = {"type": "object", "additionalProperties": False, "properties": {}}
        result = sanitize_schema(schema)
        assert "additionalProperties" not in result

    def test_removes_additional_properties_nested(self):
        from core.utils.sanitize_schema import sanitize_schema

        schema = {
            "type": "object",
            "properties": {
                "child": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                }
            },
        }
        result = sanitize_schema(schema)
        assert "additionalProperties" not in result["properties"]["child"]

    def test_preserves_other_keys(self):
        from core.utils.sanitize_schema import sanitize_schema

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = sanitize_schema(schema)
        assert result["type"] == "object"
        assert result["properties"]["name"]["type"] == "string"

    def test_handles_empty_dict(self):
        from core.utils.sanitize_schema import sanitize_schema

        result = sanitize_schema({})
        assert result == {}

    def test_handles_list_input(self):
        from core.utils.sanitize_schema import sanitize_schema

        schema = [
            {"additionalProperties": True, "type": "object"},
            {"type": "string"},
        ]
        result = sanitize_schema(schema)
        assert "additionalProperties" not in result[0]

    def test_deeply_nested(self):
        from core.utils.sanitize_schema import sanitize_schema

        schema = {"a": {"b": {"c": {"additionalProperties": False, "type": "object"}}}}
        result = sanitize_schema(schema)
        assert "additionalProperties" not in result["a"]["b"]["c"]

    def test_returns_same_reference(self):
        from core.utils.sanitize_schema import sanitize_schema

        schema = {"type": "object"}
        result = sanitize_schema(schema)
        assert result is schema

    def test_string_value_passthrough(self):
        from core.utils.sanitize_schema import sanitize_schema

        # Non-dict, non-list should just return as-is
        result = sanitize_schema("hello")
        assert result == "hello"
