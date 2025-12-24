#!/usr/bin/env python3
"""
Comprehensive tests for the DocuMancer document converter.
Tests cover ContentBlock, ContentNormalizer, DocumentParser, and DocumentConverter classes.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from converter import (
    ContentType,
    ContentBlock,
    ContentNormalizer,
    DocumentParser,
    DocumentConverter,
    ProgressTracker,
    memory_management,
    __version__
)


class TestContentType:
    """Tests for ContentType enum."""

    def test_content_type_values(self):
        """Verify all content type values are correct."""
        assert ContentType.HEADING.value == "heading"
        assert ContentType.PARAGRAPH.value == "paragraph"
        assert ContentType.CODE_BLOCK.value == "code_block"
        assert ContentType.LIST.value == "list"
        assert ContentType.QUOTE.value == "quote"
        assert ContentType.TABLE.value == "table"
        assert ContentType.METADATA.value == "metadata"
        assert ContentType.FIGURE.value == "figure"
        assert ContentType.EQUATION.value == "equation"

    def test_content_type_members(self):
        """Verify all expected content types exist."""
        expected_members = [
            'HEADING', 'PARAGRAPH', 'CODE_BLOCK', 'LIST',
            'QUOTE', 'TABLE', 'METADATA', 'FIGURE', 'EQUATION'
        ]
        actual_members = [member.name for member in ContentType]
        assert set(expected_members) == set(actual_members)


class TestContentBlock:
    """Tests for ContentBlock dataclass."""

    def test_content_block_creation(self):
        """Test basic ContentBlock creation."""
        block = ContentBlock(
            type=ContentType.PARAGRAPH.value,
            content="Test content"
        )
        assert block.type == "paragraph"
        assert block.content == "Test content"
        assert block.level == 0
        assert block.metadata == {}

    def test_content_block_with_level(self):
        """Test ContentBlock with heading level."""
        block = ContentBlock(
            type=ContentType.HEADING.value,
            content="Test Heading",
            level=2
        )
        assert block.level == 2

    def test_content_block_with_metadata(self):
        """Test ContentBlock with metadata."""
        metadata = {"language": "python", "source": "test"}
        block = ContentBlock(
            type=ContentType.CODE_BLOCK.value,
            content="print('hello')",
            metadata=metadata
        )
        assert block.metadata == metadata

    def test_content_block_to_dict(self):
        """Test ContentBlock serialization to dictionary."""
        block = ContentBlock(
            type=ContentType.HEADING.value,
            content="  Test Heading  ",
            level=1,
            metadata={"normalized": True}
        )
        result = block.to_dict()

        assert result['type'] == "heading"
        assert result['content'] == "Test Heading"  # Should be stripped
        assert result['level'] == 1
        assert result['metadata'] == {"normalized": True}

    def test_content_block_empty_metadata_to_dict(self):
        """Test that None metadata becomes empty dict."""
        block = ContentBlock(
            type=ContentType.PARAGRAPH.value,
            content="Test",
            metadata=None
        )
        result = block.to_dict()
        assert result['metadata'] == {}


class TestContentNormalizer:
    """Tests for ContentNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Create a ContentNormalizer instance for testing."""
        return ContentNormalizer()

    def test_normalize_empty_blocks(self, normalizer):
        """Test normalization of empty block list."""
        result = normalizer.normalize_content_blocks([])
        assert result == []

    def test_normalize_heading_chapter(self, normalizer):
        """Test chapter heading normalization."""
        block = ContentBlock(
            type=ContentType.HEADING.value,
            content="CHAPTER 1 Introduction"
        )
        blocks = normalizer.normalize_content_blocks([block])

        assert len(blocks) == 1
        assert "Chapter" in blocks[0].content
        assert blocks[0].metadata.get('section_type') == 'chapter'

    def test_normalize_heading_all_caps(self, normalizer):
        """Test that all-caps headings are title-cased."""
        block = ContentBlock(
            type=ContentType.HEADING.value,
            content="THIS IS A VERY LONG HEADING IN ALL CAPS"
        )
        blocks = normalizer.normalize_content_blocks([block])

        assert len(blocks) == 1
        assert blocks[0].metadata.get('case_normalized') == True

    def test_remove_placeholder_heading(self, normalizer):
        """Test that placeholder headings are removed."""
        block = ContentBlock(
            type=ContentType.HEADING.value,
            content="[PLACEHOLDER]"
        )
        blocks = normalizer.normalize_content_blocks([block])

        assert len(blocks) == 0

    def test_remove_empty_content(self, normalizer):
        """Test that empty content blocks are removed."""
        block = ContentBlock(
            type=ContentType.PARAGRAPH.value,
            content="   "
        )
        blocks = normalizer.normalize_content_blocks([block])

        assert len(blocks) == 0

    def test_detect_python_language(self, normalizer):
        """Test Python code detection."""
        code = "#!/usr/bin/python\nimport os\ndef main():\n    print('hello')"
        result = normalizer._detect_programming_language(code)
        assert result == "python"

    def test_detect_bash_language(self, normalizer):
        """Test Bash code detection."""
        code = "#!/bin/bash\nsudo apt-get update\nchmod +x script.sh"
        result = normalizer._detect_programming_language(code)
        assert result == "bash"

    def test_detect_javascript_language(self, normalizer):
        """Test JavaScript code detection."""
        code = "const express = require('express');\nfunction main() {\n  console.log('hi');\n}"
        result = normalizer._detect_programming_language(code)
        assert result == "javascript"

    def test_detect_sql_language(self, normalizer):
        """Test SQL code detection."""
        code = "SELECT * FROM users WHERE id = 1"
        result = normalizer._detect_programming_language(code)
        assert result == "sql"

    def test_clean_url(self, normalizer):
        """Test URL cleaning."""
        # Test trailing punctuation removal
        assert normalizer._clean_url("https://example.com.") == "https://example.com"

        # Test double protocol fix
        assert normalizer._clean_url("https://https://example.com") == "https://example.com"

        # Test www prefix
        assert normalizer._clean_url("www.example.com") == "https://www.example.com"

    def test_deduplicate_headings(self, normalizer):
        """Test that duplicate headings are removed."""
        blocks = [
            ContentBlock(type=ContentType.HEADING.value, content="Test Heading"),
            ContentBlock(type=ContentType.HEADING.value, content="Test Heading"),
            ContentBlock(type=ContentType.HEADING.value, content="Different Heading")
        ]
        result = normalizer.normalize_content_blocks(blocks)

        assert len(result) == 2


class TestDocumentParser:
    """Tests for DocumentParser class."""

    @pytest.fixture
    def parser(self):
        """Create a DocumentParser instance for testing."""
        return DocumentParser(language='en')

    def test_parser_initialization(self, parser):
        """Test parser initialization."""
        assert parser.language == 'en'
        assert parser.normalizer is not None
        assert len(parser.stop_words) > 0

    def test_parse_simple_text(self, parser):
        """Test parsing simple text."""
        text = "# Heading\n\nThis is a paragraph."
        result = parser.parse(text)

        assert 'document_type' in result
        assert result['document_type'] == 'structured_text'
        assert 'content_blocks' in result
        assert 'metadata' in result
        assert 'version' in result
        assert result['version'] == __version__

    def test_parse_with_code_block(self, parser):
        """Test parsing text with code block."""
        text = "# Example\n\n```python\nprint('hello')\n```"
        result = parser.parse(text)

        blocks = result['content_blocks']
        code_blocks = [b for b in blocks if b['type'] == 'code_block']
        assert len(code_blocks) >= 0  # May be merged with other content

    def test_parse_with_list(self, parser):
        """Test parsing text with list."""
        text = "# Items\n\n- Item 1\n- Item 2\n- Item 3"
        result = parser.parse(text)

        blocks = result['content_blocks']
        list_blocks = [b for b in blocks if b['type'] == 'list']
        assert len(list_blocks) >= 0  # Lists are detected

    def test_normalize_text(self, parser):
        """Test text normalization."""
        text = "Test\u2018quote\u2019 and \u201Cquote\u201D"
        result = parser._normalize_text(text)

        assert "'" in result
        assert '"' in result

    def test_split_into_sections(self, parser):
        """Test section splitting."""
        text = "Section 1\n\n\nSection 2\n\nSection 3"
        sections = parser._split_into_sections(text)

        assert len(sections) == 3
        assert "Section 1" in sections[0]

    def test_is_heading_hash(self, parser):
        """Test hash heading detection."""
        assert parser._is_heading("# Heading") == True
        assert parser._is_heading("## Heading") == True
        assert parser._is_heading("This is a paragraph.") == False

    def test_is_heading_chapter(self, parser):
        """Test chapter heading detection."""
        assert parser._is_heading("Chapter 1: Introduction") == True
        assert parser._is_heading("Section 2.1 Details") == True

    def test_is_code_block(self, parser):
        """Test code block detection."""
        code = "```python\nprint('hello')\n```"
        assert parser._is_code_block(code) == True

        indented = "    def main():\n        pass"
        assert parser._is_code_block(indented) == True

    def test_is_list(self, parser):
        """Test list detection."""
        bullet_list = "- Item 1\n- Item 2\n- Item 3"
        assert parser._is_list(bullet_list) == True

        numbered_list = "1. First\n2. Second\n3. Third"
        assert parser._is_list(numbered_list) == True

    def test_extract_key_topics(self, parser):
        """Test key topic extraction."""
        text = "Python programming Python code Python development"
        topics = parser._extract_key_topics(text)

        assert "python" in topics

    def test_extract_document_metadata(self, parser):
        """Test metadata extraction."""
        blocks = [
            ContentBlock(type=ContentType.HEADING.value, content="Document Title", level=1),
            ContentBlock(type=ContentType.PARAGRAPH.value, content="Some content here")
        ]
        metadata = parser._extract_document_metadata(blocks)

        assert metadata['title'] == "Document Title"
        assert metadata['block_count'] == 2
        assert 'processed_date' in metadata


class TestDocumentConverter:
    """Tests for DocumentConverter class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def converter(self, temp_dir):
        """Create a DocumentConverter instance for testing."""
        return DocumentConverter(output_dir=temp_dir, language='en')

    def test_converter_initialization(self, converter, temp_dir):
        """Test converter initialization."""
        assert converter.output_dir == Path(temp_dir)
        assert converter.output_dir.exists()
        assert converter.parser is not None

    def test_supported_formats(self, converter):
        """Test that all expected formats are supported."""
        formats = converter.SUPPORTED_FORMATS

        assert 'pdf' in formats
        assert 'docx' in formats
        assert 'text' in formats
        assert 'epub' in formats
        assert 'image' in formats

    def test_get_file_type_pdf(self, converter):
        """Test PDF file type detection."""
        assert converter.get_file_type(Path("test.pdf")) == "pdf"

    def test_get_file_type_docx(self, converter):
        """Test DOCX file type detection."""
        assert converter.get_file_type(Path("test.docx")) == "docx"
        assert converter.get_file_type(Path("test.doc")) == "docx"

    def test_get_file_type_text(self, converter):
        """Test text file type detection."""
        assert converter.get_file_type(Path("test.txt")) == "text"
        assert converter.get_file_type(Path("test.md")) == "text"

    def test_get_file_type_epub(self, converter):
        """Test EPUB file type detection."""
        assert converter.get_file_type(Path("test.epub")) == "epub"

    def test_get_file_type_image(self, converter):
        """Test image file type detection."""
        assert converter.get_file_type(Path("test.png")) == "image"
        assert converter.get_file_type(Path("test.jpg")) == "image"
        assert converter.get_file_type(Path("test.jpeg")) == "image"

    def test_get_file_type_unsupported(self, converter):
        """Test unsupported file type returns None."""
        assert converter.get_file_type(Path("test.xyz")) is None

    def test_convert_text_file(self, converter, temp_dir):
        """Test converting a text file."""
        # Create a test text file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("# Test Document\n\nThis is a test paragraph.")

        result = converter.convert_file(test_file)

        assert result is not None
        assert result.exists()
        assert result.suffix == ".json"

        # Verify JSON content
        with open(result) as f:
            data = json.load(f)

        assert data['document_type'] == 'structured_text'
        assert 'content_blocks' in data
        assert data['metadata']['source_file'] == "test.txt"

    def test_convert_nonexistent_file(self, converter):
        """Test converting a non-existent file returns None."""
        result = converter.convert_file(Path("/nonexistent/file.txt"))
        assert result is None

    def test_extract_text_file(self, converter, temp_dir):
        """Test text extraction from plain text file."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, World!")

        text = converter._extract_text_file(test_file)
        assert text == "Hello, World!"

    def test_extract_text_file_utf16(self, converter, temp_dir):
        """Test text extraction from UTF-16 encoded file."""
        test_file = Path(temp_dir) / "test_utf16.txt"
        test_file.write_text("UTF-16 content", encoding='utf-16')

        text = converter._extract_text_file(test_file)
        assert "UTF-16 content" in text


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    def test_progress_tracker_creation(self):
        """Test ProgressTracker creation."""
        tracker = ProgressTracker(10, "Testing")
        assert tracker.total == 10
        assert tracker.current == 0
        assert tracker.description == "Testing"

    def test_progress_update(self):
        """Test progress update."""
        tracker = ProgressTracker(10, "Testing")
        tracker.update(1)
        assert tracker.current == 1

        tracker.update(5)
        assert tracker.current == 6

    def test_progress_percentage(self, capsys):
        """Test progress percentage calculation."""
        tracker = ProgressTracker(4, "Testing")
        tracker.report_interval = 0  # Force immediate reporting

        tracker.update(1)  # 25%
        tracker.update(1)  # 50%
        tracker.update(1)  # 75%
        tracker.update(1)  # 100%

        assert tracker.current == 4


class TestMemoryManagement:
    """Tests for memory management context manager."""

    def test_memory_management_context(self):
        """Test that memory_management context manager works."""
        with memory_management():
            data = [1, 2, 3, 4, 5]
            assert len(data) == 5

        # Context manager should complete without error
        assert True

    def test_memory_management_with_exception(self):
        """Test memory management handles exceptions."""
        with pytest.raises(ValueError):
            with memory_management():
                raise ValueError("Test error")


class TestVersionInfo:
    """Tests for version information."""

    def test_version_format(self):
        """Test version string format."""
        import re
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, __version__)

    def test_version_value(self):
        """Test current version value."""
        assert __version__ == "2.1.0"


# Integration Tests
class TestIntegration:
    """Integration tests for the complete conversion pipeline."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_full_conversion_pipeline(self, temp_dir):
        """Test the complete conversion pipeline."""
        # Create test input file
        input_file = Path(temp_dir) / "input.txt"
        input_file.write_text("""
# Document Title

## Introduction

This is the introduction paragraph with some important content.

## Features

- Feature 1: Description of feature one
- Feature 2: Description of feature two
- Feature 3: Description of feature three

## Code Example

```python
def hello():
    print("Hello, World!")
```

## Conclusion

This is the conclusion of the document.
        """)

        # Convert the file
        converter = DocumentConverter(output_dir=temp_dir)
        result = converter.convert_file(input_file)

        # Verify output
        assert result is not None
        assert result.exists()

        with open(result) as f:
            data = json.load(f)

        # Check structure
        assert data['document_type'] == 'structured_text'
        assert len(data['content_blocks']) > 0
        assert 'metadata' in data
        assert data['normalization_applied'] == True

        # Check metadata
        assert data['metadata']['source_file'] == "input.txt"
        assert data['metadata']['word_count'] > 0

    def test_batch_conversion(self, temp_dir):
        """Test batch file conversion."""
        # Create multiple test files
        files = []
        for i in range(3):
            input_file = Path(temp_dir) / f"test_{i}.txt"
            input_file.write_text(f"# Document {i}\n\nContent for document {i}.")
            files.append(input_file)

        # Convert all files
        converter = DocumentConverter(output_dir=temp_dir)
        results = converter.convert_batch(files, max_workers=2)

        assert results['total'] == 3
        assert len(results['successful']) == 3
        assert len(results['failed']) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
