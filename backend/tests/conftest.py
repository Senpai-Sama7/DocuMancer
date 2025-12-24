#!/usr/bin/env python3
"""
Pytest configuration and fixtures for DocuMancer tests.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a session-scoped test data directory."""
    with tempfile.TemporaryDirectory(prefix="documancer_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_output_dir():
    """Create a test output directory."""
    with tempfile.TemporaryDirectory(prefix="documancer_output_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return """
# Sample Document

## Introduction

This is a sample document for testing the DocuMancer converter.

## Features

- Feature 1: Automatic format detection
- Feature 2: AI-optimized JSON output
- Feature 3: Multi-format support

## Code Example

```python
def convert_document(path):
    converter = DocumentConverter()
    return converter.convert_file(path)
```

## Conclusion

Thank you for using DocuMancer.
"""


@pytest.fixture
def sample_text_file(temp_output_dir, sample_text_content):
    """Create a sample text file for testing."""
    file_path = temp_output_dir / "sample.txt"
    file_path.write_text(sample_text_content)
    return file_path


@pytest.fixture
def sample_markdown_file(temp_output_dir):
    """Create a sample markdown file for testing."""
    content = """
# Markdown Document

This is a **bold** and *italic* text.

## Code Block

```javascript
console.log('Hello, World!');
```

## List

1. First item
2. Second item
3. Third item

## Links

Visit [example](https://example.com) for more info.
"""
    file_path = temp_output_dir / "sample.md"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def empty_file(temp_output_dir):
    """Create an empty file for testing."""
    file_path = temp_output_dir / "empty.txt"
    file_path.write_text("")
    return file_path


@pytest.fixture
def unicode_file(temp_output_dir):
    """Create a file with unicode content for testing."""
    content = """
# Unicode Test

日本語テキスト (Japanese text)
中文文本 (Chinese text)
한국어 텍스트 (Korean text)
Текст на русском (Russian text)
العربية (Arabic text)

## Emoji Test

🎉 🚀 💻 📚 ✨
"""
    file_path = temp_output_dir / "unicode.txt"
    file_path.write_text(content, encoding='utf-8')
    return file_path


# Skip markers for optional dependencies
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "requires_pdf: mark test as requiring PyMuPDF"
    )
    config.addinivalue_line(
        "markers", "requires_docx: mark test as requiring python-docx"
    )
    config.addinivalue_line(
        "markers", "requires_ocr: mark test as requiring pytesseract"
    )
    config.addinivalue_line(
        "markers", "requires_epub: mark test as requiring ebooklib"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
