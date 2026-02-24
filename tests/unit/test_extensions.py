"""
Unit tests for core.parsers.extensions — supported file extension constants.
"""

import pytest


@pytest.mark.unit
class TestExtensions:
    def test_image_extensions_are_set(self):
        from core.parsers.extensions import IMAGE_EXTENSIONS

        assert isinstance(IMAGE_EXTENSIONS, set)
        assert ".jpg" in IMAGE_EXTENSIONS
        assert ".png" in IMAGE_EXTENSIONS
        assert ".jpeg" in IMAGE_EXTENSIONS

    def test_supported_extensions_include_images(self):
        from core.parsers.extensions import IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS

        for ext in IMAGE_EXTENSIONS:
            assert ext in SUPPORTED_EXTENSIONS

    def test_supported_extensions_include_documents(self):
        from core.parsers.extensions import SUPPORTED_EXTENSIONS

        doc_types = {".pdf", ".doc", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".md"}
        for ext in doc_types:
            assert ext in SUPPORTED_EXTENSIONS

    def test_supported_extensions_include_web_formats(self):
        from core.parsers.extensions import SUPPORTED_EXTENSIONS

        assert ".html" in SUPPORTED_EXTENSIONS
        assert ".xml" in SUPPORTED_EXTENSIONS

    def test_unsupported_extensions(self):
        from core.parsers.extensions import SUPPORTED_EXTENSIONS

        assert ".exe" not in SUPPORTED_EXTENSIONS
        assert ".zip" not in SUPPORTED_EXTENSIONS
        assert ".py" not in SUPPORTED_EXTENSIONS
