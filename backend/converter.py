#!/usr/bin/env python3
"""
Enhanced Document to AI-Optimized JSON Converter v2.1.0
Converts PDF, DOCX, TXT, EPUB, and images to structured JSON for AI comprehension
Focus: Speed, accuracy, memory efficiency, AI-ready output format, and semantic cleanup
"""

import io
import json
import logging
import re
import sys
import os
import gc
import time
import mimetypes
import tempfile
import shutil
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Set, Iterator, Generator
from enum import Enum
import hashlib

# [Previous imports and setup remain the same...]
# Configure logging with color support for console
try:
    import colorama
    colorama.init()
    
    class ColorFormatter(logging.Formatter):
        """Colored log formatter"""
        COLORS = {
            'DEBUG': '\033[94m',    # Blue
            'INFO': '\033[92m',     # Green
            'WARNING': '\033[93m',  # Yellow
            'ERROR': '\033[91m',    # Red
            'CRITICAL': '\033[91m\033[1m',  # Bold Red
            'RESET': '\033[0m'      # Reset
        }

        def format(self, record):
            log_message = super().format(record)
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            return f"{color}{log_message}{self.COLORS['RESET']}"
    
    # Configure colored console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Configure file handler with regular formatting
    file_handler = logging.FileHandler('converter.log', 'a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Set up logger with both handlers
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
except ImportError:
    # Fall back to standard logging if colorama is not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('converter.log', 'a')
        ]
    )
    logger = logging.getLogger(__name__)

# Version information
__version__ = "2.1.0"
logger.info(f"Document Converter v{__version__} initializing")

# Import dependencies with graceful degradation
DEPENDENCIES = {
    'core': ['fitz', 'PIL', 'pytesseract', 'docx'],
    'enhanced': ['nltk', 'langdetect', 'ebooklib', 'pdf2image'],
    'optional': ['magic', 'hocr-tools', 'colorama']
}

# Dictionary to track available modules
available_modules = {}

# Core dependencies
try:
    import fitz  # PyMuPDF
    available_modules['fitz'] = True
except ImportError as e:
    logger.error(f"Missing core dependency: PyMuPDF - {e}")
    available_modules['fitz'] = False

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    available_modules['PIL'] = True
except ImportError as e:
    logger.error(f"Missing core dependency: Pillow - {e}")
    available_modules['PIL'] = False

try:
    import pytesseract
    available_modules['pytesseract'] = True
except ImportError as e:
    logger.error(f"Missing core dependency: pytesseract - {e}")
    available_modules['pytesseract'] = False

try:
    from docx import Document as DocxDocument
    available_modules['docx'] = True
except ImportError as e:
    logger.error(f"Missing core dependency: python-docx - {e}")
    available_modules['docx'] = False

# Enhanced dependencies
try:
    import nltk
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    available_modules['nltk'] = True
except ImportError:
    logger.warning("NLTK not available. Topic extraction will be limited.")
    available_modules['nltk'] = False

try:
    from langdetect import detect as detect_language
    available_modules['langdetect'] = True
except ImportError:
    logger.warning("langdetect not available. Automatic language detection will be disabled.")
    available_modules['langdetect'] = False

try:
    import ebooklib
    from ebooklib import epub
    import html2text
    available_modules['ebooklib'] = True
except ImportError:
    logger.warning("ebooklib or html2text not available. EPUB processing will be disabled.")
    available_modules['ebooklib'] = False

try:
    import pdf2image
    available_modules['pdf2image'] = True
except ImportError:
    logger.warning("pdf2image not available. Alternative OCR pipeline will be disabled.")
    available_modules['pdf2image'] = False

# Optional dependencies
try:
    import magic
    available_modules['magic'] = True
except ImportError:
    logger.debug("python-magic not available. Will rely on file extensions for type detection.")
    available_modules['magic'] = False

# Verify critical dependencies
missing_critical = [dep for dep, available in 
                   {k: available_modules.get(k, False) for k in ['fitz', 'PIL', 'pytesseract', 'docx']}.items() 
                   if not available]

if missing_critical:
    logger.error("Missing critical dependencies. Install with:")
    logger.error("pip install PyMuPDF Pillow pytesseract python-docx")
    if not sys.argv[0].endswith('pytest'):  # Don't exit if running tests
        sys.exit(1)


class ContentType(Enum):
    """Content classification for AI processing"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST = "list"
    QUOTE = "quote"
    TABLE = "table"
    METADATA = "metadata"
    FIGURE = "figure"
    EQUATION = "equation"


@dataclass
class ContentBlock:
    """Structured content block for AI consumption"""
    type: str
    content: str
    level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'type': self.type,
            'content': self.content.strip(),
            'level': self.level,
            'metadata': self.metadata or {}
        }


class ContentNormalizer:
    """Advanced content normalizer for semantic cleanup and structure improvement"""
    
    def __init__(self):
        self.url_cache = set()
        self.heading_patterns = self._compile_heading_patterns()
        self.language_patterns = self._compile_language_patterns()
        self.placeholder_patterns = self._compile_placeholder_patterns()
        
    def _compile_heading_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for heading normalization"""
        return {
            'chapter_variations': re.compile(r'^(Chapter|CHAPTER|Ch\.?|chapter)\s*(\d+|[IVXLCDM]+)[\s:\-]*(.*)$', re.IGNORECASE),
            'section_variations': re.compile(r'^(Section|SECTION|Sec\.?|section)\s*(\d+(?:\.\d+)*)[\s:\-]*(.*)$', re.IGNORECASE),
            'part_variations': re.compile(r'^(Part|PART|part)\s*(\d+|[IVXLCDM]+)[\s:\-]*(.*)$', re.IGNORECASE),
            'lab_step': re.compile(r'^(Lab|LAB|Step|STEP)\s*(\d+)[\s:\-]*(.*)$', re.IGNORECASE),
            'exercise': re.compile(r'^(Exercise|EXERCISE|Ex\.?)\s*(\d+)[\s:\-]*(.*)$', re.IGNORECASE),
            'duplicate_heading': re.compile(r'^(.+?)\s*\1\s*$', re.IGNORECASE),  # Detect duplicated text
            'yard_line': re.compile(r'^[\-_=]{3,}.*yard.*line.*[\-_=]{3,}$', re.IGNORECASE),
            'placeholder_heading': re.compile(r'^[\[\(]?\s*(placeholder|todo|tbd|xxx|fixme)\s*[\]\)]?$', re.IGNORECASE)
        }
    
    def _compile_language_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for programming language detection"""
        return {
            'bash': re.compile(r'(?:#!/bin/bash|#!/bin/sh|\$\s+|sudo\s+|chmod\s+|grep\s+|awk\s+|sed\s+|ls\s+|cd\s+|mkdir\s+)', re.IGNORECASE),
            'powershell': re.compile(r'(?:PS\s*>|Get-|Set-|New-|Remove-|\$\w+\s*=|Import-Module|cmdlet)', re.IGNORECASE),
            'python': re.compile(r'(?:#!/usr/bin/python|import\s+\w+|from\s+\w+\s+import|def\s+\w+|class\s+\w+|print\()', re.IGNORECASE),
            'javascript': re.compile(r'(?:function\s+\w+|var\s+\w+|let\s+\w+|const\s+\w+|console\.log|require\()', re.IGNORECASE),
            'sql': re.compile(r'(?:SELECT\s+|FROM\s+|WHERE\s+|INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM|CREATE\s+TABLE)', re.IGNORECASE),
            'yaml': re.compile(r'(?:^[\s]*[\w\-]+:\s*$|^[\s]*-\s+[\w\-]+:|version:\s*[\d\.]+)', re.MULTILINE),
            'json': re.compile(r'(?:^\s*[\{\[]|"[\w\-]+"\s*:\s*|^\s*[\}\]])', re.MULTILINE),
            'dockerfile': re.compile(r'(?:FROM\s+|RUN\s+|COPY\s+|ADD\s+|WORKDIR\s+|EXPOSE\s+)', re.IGNORECASE),
            'xml': re.compile(r'(?:<\?xml|<[\w\-]+[^>]*>|</[\w\-]+>)', re.IGNORECASE),
            'css': re.compile(r'(?:[\w\-]+\s*\{|[\w\-]+:\s*[\w\-#]+;|\.[a-zA-Z][\w\-]*\s*\{)', re.IGNORECASE)
        }
    
    def _compile_placeholder_patterns(self) -> List[re.Pattern]:
        """Compile patterns for placeholder detection"""
        return [
            re.compile(r'^[\-_=]{3,}.*yard.*line.*[\-_=]{3,}$', re.IGNORECASE),
            re.compile(r'^[\[\(]?\s*(placeholder|todo|tbd|xxx|fixme|coming\s+soon)\s*[\]\)]?$', re.IGNORECASE),
            re.compile(r'^[\-_=]{10,}$'),  # Long lines of separators
            re.compile(r'^\.{10,}$'),      # Long lines of dots
            re.compile(r'^\s*\.\s*\.\s*\.\s*$')  # Ellipsis patterns
        ]
    
    def normalize_content_blocks(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Apply comprehensive normalization to content blocks"""
        logger.info("Starting content normalization and semantic cleanup")
        
        # Phase 1: Clean individual blocks
        cleaned_blocks = []
        for block in blocks:
            normalized_block = self._normalize_individual_block(block)
            if normalized_block:  # Only add non-empty blocks
                cleaned_blocks.append(normalized_block)
        
        # Phase 2: Structural improvements
        structured_blocks = self._improve_structure(cleaned_blocks)
        
        # Phase 3: Deduplicate and merge similar content
        final_blocks = self._deduplicate_content(structured_blocks)
        
        logger.info(f"Normalization complete: {len(blocks)} -> {len(final_blocks)} blocks")
        return final_blocks
    
    def _normalize_individual_block(self, block: ContentBlock) -> Optional[ContentBlock]:
        """Normalize a single content block"""
        if not block.content.strip():
            return None
        
        # Handle different block types
        if block.type == ContentType.HEADING.value:
            return self._normalize_heading(block)
        elif block.type == ContentType.CODE_BLOCK.value:
            return self._normalize_code_block(block)
        elif block.type == ContentType.LIST.value:
            return self._normalize_list(block)
        elif block.type == ContentType.PARAGRAPH.value:
            return self._normalize_paragraph(block)
        else:
            return block
    
    def _normalize_heading(self, block: ContentBlock) -> Optional[ContentBlock]:
        """Normalize heading blocks"""
        content = block.content.strip()
        
        # Check for placeholder headings
        if any(pattern.match(content) for pattern in self.placeholder_patterns):
            logger.debug(f"Removing placeholder heading: {content}")
            return None
        
        # Handle yard line placeholders - convert to proper subsections
        yard_match = self.heading_patterns['yard_line'].match(content)
        if yard_match:
            # Extract meaningful content from yard line
            yard_content = re.sub(r'[\-_=]', '', content).strip()
            if len(yard_content) > 5:  # Has meaningful content
                block.content = f"Section: {yard_content.title()}"
                block.metadata['normalized'] = True
                block.metadata['original_format'] = 'yard_line'
            else:
                return None  # Remove meaningless yard lines
        
        # Normalize chapter/section numbering
        for pattern_name, pattern in self.heading_patterns.items():
            if pattern_name.endswith('_variations'):
                match = pattern.match(content)
                if match:
                    prefix = match.group(1).title()
                    number = match.group(2)
                    title = match.group(3).strip() if len(match.groups()) > 2 else ""
                    
                    if title:
                        block.content = f"{prefix} {number}: {title}"
                    else:
                        block.content = f"{prefix} {number}"
                    
                    block.metadata['section_type'] = prefix.lower()
                    block.metadata['section_number'] = number
                    block.metadata['normalized'] = True
                    break
        
        # Remove duplicate text in headings
        duplicate_match = self.heading_patterns['duplicate_heading'].match(content)
        if duplicate_match:
            block.content = duplicate_match.group(1).strip()
            block.metadata['had_duplicate'] = True
        
        # Normalize casing for consistency
        if block.content.isupper() and len(block.content) > 10:
            block.content = block.content.title()
            block.metadata['case_normalized'] = True
        
        return block
    
    def _normalize_code_block(self, block: ContentBlock) -> Optional[ContentBlock]:
        """Normalize and enhance code blocks"""
        content = block.content.strip()
        
        # Skip very short "code" blocks that are likely titles
        if len(content) < 10 and not any(char in content for char in ['{', '}', '(', ')', ';', '=']):
            # This might be a title, convert to heading
            new_block = ContentBlock(
                type=ContentType.HEADING.value,
                content=content,
                level=block.level or 3,
                metadata={**block.metadata, 'converted_from': 'code_block'}
            )
            return new_block
        
        # Detect and tag programming language
        detected_language = self._detect_programming_language(content)
        if detected_language:
            block.metadata['language'] = detected_language
            block.metadata['language_confidence'] = 'detected'
        
        # Add source context
        if 'source_type' in block.metadata:
            block.metadata['source_context'] = block.metadata['source_type']
        
        # Clean up command-line artifacts
        if detected_language in ['bash', 'powershell']:
            content = self._clean_command_line_content(content)
            block.content = content
        
        return block
    
    def _normalize_list(self, block: ContentBlock) -> Optional[ContentBlock]:
        """Normalize list blocks and detect semantic lists from paragraphs"""
        content = block.content.strip()
        
        # Detect if this should be converted to a semantic list
        lines = content.split('\n')
        
        # Check for tool inventories, lab steps, etc.
        if self._is_semantic_list(lines):
            block.metadata['semantic_list'] = True
            
            # Improve list formatting
            normalized_items = []
            for line in lines:
                line = line.strip()
                if line:
                    # Remove redundant bullets/numbers if already present
                    clean_line = re.sub(r'^[\-\*\+•]\s*', '', line)
                    clean_line = re.sub(r'^\d+[\.\)]\s*', '', clean_line)
                    normalized_items.append(clean_line)
            
            block.content = '\n'.join(normalized_items)
            block.metadata['normalized'] = True
        
        return block
    
    def _normalize_paragraph(self, block: ContentBlock) -> Optional[ContentBlock]:
        """Normalize paragraph blocks and clean URLs"""
        content = block.content.strip()
        
        # Clean URLs in the content
        if 'urls' in block.metadata:
            cleaned_urls = []
            for url in block.metadata['urls']:
                clean_url = self._clean_url(url)
                if clean_url and clean_url not in self.url_cache:
                    cleaned_urls.append(clean_url)
                    self.url_cache.add(clean_url)
            
            block.metadata['urls'] = cleaned_urls
            
            # Update content with cleaned URLs
            for original_url in block.metadata.get('urls', []):
                clean_url = self._clean_url(original_url)
                if clean_url != original_url:
                    content = content.replace(original_url, clean_url)
        
        # Detect if this paragraph should be converted to a list
        if self._should_convert_to_list(content):
            list_items = self._extract_list_items(content)
            if list_items:
                return ContentBlock(
                    type=ContentType.LIST.value,
                    content='\n'.join(list_items),
                    level=block.level,
                    metadata={
                        **block.metadata,
                        'converted_from': 'paragraph',
                        'list_type': 'semantic',
                        'item_count': len(list_items)
                    }
                )
        
        block.content = content
        return block
    
    def _detect_programming_language(self, code: str) -> Optional[str]:
        """Detect programming language from code content"""
        # Check for shebang
        if code.startswith('#!/'):
            if 'python' in code[:50]:
                return 'python'
            elif any(shell in code[:50] for shell in ['bash', 'sh']):
                return 'bash'
        
        # Pattern-based detection
        for language, pattern in self.language_patterns.items():
            if pattern.search(code):
                return language
        
        # Fallback to simple heuristics
        if any(keyword in code.lower() for keyword in ['select ', 'from ', 'where ']):
            return 'sql'
        elif code.strip().startswith(('<?xml', '<html', '<!')):
            return 'xml'
        elif re.search(r'^\s*[\{\[]', code, re.MULTILINE) and '"' in code:
            return 'json'
        
        return 'text'  # Default fallback
    
    def _clean_command_line_content(self, content: str) -> str:
        """Clean command line artifacts from code blocks"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove command prompts but preserve the command
            line = re.sub(r'^[\$#]\s*', '', line)
            line = re.sub(r'^PS\s*>\s*', '', line)
            line = re.sub(r'^\w+@\w+:\w*\$\s*', '', line)  # user@host:~$
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _clean_url(self, url: str) -> str:
        """Clean and normalize URLs"""
        if not url:
            return ""
        
        # Strip trailing punctuation
        url = re.sub(r'[.,;:!?\]\)]+$', '', url.strip())
        
        # Remove redundant protocols
        url = re.sub(r'^https?://https?://', 'https://', url)
        
        # Normalize common variations
        url = re.sub(r'^www\.', 'https://www.', url)
        if not url.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
            if '.' in url and not url.startswith('/'):
                url = f'https://{url}'
        
        return url
    
    def _is_semantic_list(self, lines: List[str]) -> bool:
        """Detect if content should be formatted as a semantic list"""
        if len(lines) < 2:
            return False
        
        # Check for tool inventories
        tool_indicators = ['tool', 'software', 'application', 'utility', 'command', 'package']
        if any(indicator in '\n'.join(lines).lower() for indicator in tool_indicators):
            return True
        
        # Check for step-by-step content
        step_indicators = ['step', 'phase', 'stage', 'procedure', 'process']
        if any(indicator in '\n'.join(lines).lower() for indicator in step_indicators):
            return True
        
        # Check for inventory/checklist patterns
        checklist_patterns = [
            r'^\s*[\-\*\+•]\s*\w+',  # Already bulleted
            r'^\s*\d+[\.\)]\s*\w+',   # Already numbered
            r'^\s*[A-Z][a-z]+:\s*',   # Label: description
            r'^\s*\w+\s*-\s*\w+'      # Item - description
        ]
        
        pattern_matches = 0
        for line in lines:
            if any(re.match(pattern, line) for pattern in checklist_patterns):
                pattern_matches += 1
        
        return pattern_matches >= len(lines) * 0.6  # 60% of lines match patterns
    
    def _should_convert_to_list(self, content: str) -> bool:
        """Check if paragraph content should be converted to a list"""
        # Look for multiple sentences that follow list-like patterns
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) < 3:
            return False
        
        list_indicators = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check for list-like patterns
            if (sentence.lower().startswith(('first', 'second', 'third', 'next', 'then', 'finally')) or
                re.match(r'^\d+[\.\)]\s*', sentence) or
                sentence.startswith(('- ', '* ', '• ')) or
                ': ' in sentence and len(sentence.split(':')) == 2):
                list_indicators += 1
        
        return list_indicators >= len([s for s in sentences if s.strip()]) * 0.5
    
    def _extract_list_items(self, content: str) -> List[str]:
        """Extract list items from paragraph content"""
        # Try different splitting methods
        items = []
        
        # First try splitting by periods, then by patterns
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:
                # Clean up list markers
                sentence = re.sub(r'^(first|second|third|next|then|finally)[\s,]*', '', sentence, flags=re.IGNORECASE)
                sentence = re.sub(r'^\d+[\.\)]\s*', '', sentence)
                sentence = re.sub(r'^[\-\*\+•]\s*', '', sentence)
                
                if sentence:
                    items.append(sentence.strip())
        
        return items
    
    def _improve_structure(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Improve overall document structure"""
        improved_blocks = []
        current_context = {'chapter': None, 'section': None, 'subsection': None}
        
        for block in blocks:
            # Add structural context to metadata
            if block.type == ContentType.HEADING.value:
                self._update_context(block, current_context)
            
            # Add context information to all blocks
            block.metadata['structural_context'] = current_context.copy()
            
            # Merge very short adjacent paragraphs
            if (block.type == ContentType.PARAGRAPH.value and 
                improved_blocks and 
                improved_blocks[-1].type == ContentType.PARAGRAPH.value and
                len(block.content) < 100 and len(improved_blocks[-1].content) < 100):
                
                # Merge with previous paragraph
                improved_blocks[-1].content += " " + block.content
                if 'urls' in block.metadata:
                    prev_urls = improved_blocks[-1].metadata.get('urls', [])
                    improved_blocks[-1].metadata['urls'] = prev_urls + block.metadata['urls']
                continue
            
            improved_blocks.append(block)
        
        return improved_blocks
    
    def _update_context(self, block: ContentBlock, context: Dict[str, str]):
        """Update structural context based on heading"""
        level = block.level
        content = block.content
        
        if level == 1 or 'chapter' in block.metadata.get('section_type', ''):
            context['chapter'] = content
            context['section'] = None
            context['subsection'] = None
        elif level == 2 or 'section' in block.metadata.get('section_type', ''):
            context['section'] = content
            context['subsection'] = None
        elif level >= 3:
            context['subsection'] = content
    
    def _deduplicate_content(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Remove duplicate content blocks"""
        seen_content = set()
        unique_blocks = []
        
        for block in blocks:
            # Create a hash of the content for comparison
            content_hash = hashlib.md5(block.content.encode('utf-8')).hexdigest()
            
            # For headings, also check for semantic duplicates
            if block.type == ContentType.HEADING.value:
                normalized_content = re.sub(r'\s+', ' ', block.content.lower().strip())
                semantic_hash = hashlib.md5(normalized_content.encode('utf-8')).hexdigest()
                
                if semantic_hash in seen_content:
                    logger.debug(f"Removing duplicate heading: {block.content}")
                    continue
                seen_content.add(semantic_hash)
            else:
                if content_hash in seen_content:
                    logger.debug(f"Removing duplicate content block")
                    continue
                seen_content.add(content_hash)
            
            unique_blocks.append(block)
        
        return unique_blocks


class ProgressTracker:
    """Tracks and reports progress of long-running operations"""
    
    def __init__(self, total_items: int, description: str = "Processing"):
        self.total = total_items
        self.current = 0
        self.start_time = time.time()
        self.description = description
        self.last_report_time = 0
        self.report_interval = 1.0  # seconds between progress reports
        
    def update(self, items_completed: int = 1) -> None:
        """Update progress and print status if interval elapsed"""
        self.current += items_completed
        current_time = time.time()
        
        # Report if first update, last update, or interval has passed
        if (self.current == 1 or 
            self.current == self.total or 
            current_time - self.last_report_time > self.report_interval):
            
            percentage = min(100, int((self.current / self.total) * 100))
            elapsed = current_time - self.start_time
            
            if self.current > 0 and elapsed > 0:
                items_per_sec = self.current / elapsed
                eta = (self.total - self.current) / items_per_sec if items_per_sec > 0 else 0
                eta_str = f", ETA: {int(eta)}s" if self.current < self.total else ""
                
                logger.info(f"{self.description}: {percentage}% ({self.current}/{self.total}{eta_str})")
            else:
                logger.info(f"{self.description}: {percentage}% ({self.current}/{self.total})")
                
            self.last_report_time = current_time


@contextmanager
def memory_management():
    """Context manager for controlled memory cleanup"""
    try:
        yield
    finally:
        # Force garbage collection
        gc.collect()


class DocumentParser:
    """Advanced parser for AI-readable structured content with enhanced normalization"""
    
    def __init__(self, language: str = 'auto'):
        self.patterns = self._compile_patterns()
        self.code_indicators = {
            'prefixes': ['$', '#', '>>>', '>', 'C:\\', '~/', 'PS>', 'λ '],
            'extensions': ['.py', '.js', '.html', '.css', '.sql', '.sh', '.bat', '.c', '.cpp', '.java', '.rb', '.php'],
            'keywords': [
                'def ', 'function ', 'class ', 'import ', 'from ', 'SELECT ', 'FROM ', 'WHERE ', 'var ', 
                'const ', 'let ', 'public ', 'private ', 'static ', 'void ', 'int ', 'string ', 'bool ',
                'package ', '@Override', '#include', '#define', 'module', 'namespace'
            ]
        }
        
        self.language = language
        self.normalizer = ContentNormalizer()
        # Initialize stopwords for topic extraction
        self._initialize_nlp_resources()
            
    def _initialize_nlp_resources(self):
        """Initialize NLP resources for text analysis"""
        self.stop_words = set()
        
        if available_modules.get('nltk', False):
            try:
                # Default to English stopwords
                self.stop_words = set(stopwords.words('english'))
                logger.debug("NLTK stopwords loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load NLTK stopwords: {e}")
        else:
            # Basic English stopwords if NLTK is not available
            logger.debug("Using basic stopwords set (NLTK not available)")
            self.stop_words = {
                'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'until', 'while',
                'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
                'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in',
                'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
                'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
                'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
            }
    
    def parse(self, text: str, source_type: str = None) -> Dict[str, Any]:
        """Parse text into AI-optimized JSON structure with enhanced normalization"""
        word_count = len(text.split())
        logger.info(f"Parsing {word_count} words of content")
        
        # Auto-detect language if requested
        if self.language == 'auto' and available_modules.get('langdetect', False):
            try:
                # Take a sample of text for efficiency
                sample_size = min(5000, len(text))
                sample = text[:sample_size]
                detected_lang = detect_language(sample)
                logger.info(f"Detected document language: {detected_lang}")
                
                # Update stopwords if possible
                if available_modules.get('nltk', False):
                    try:
                        self.stop_words = set(stopwords.words(detected_lang))
                    except Exception:
                        logger.debug(f"No NLTK stopwords available for {detected_lang}, using English")
            except Exception as e:
                logger.warning(f"Language detection failed: {e}")
        
        # Use progress tracker for large documents
        progress = ProgressTracker(5, "Text processing")
        
        # Normalize text
        with memory_management():
            text = self._normalize_text(text)
            progress.update()
        
        # Split into logical sections
        with memory_management():
            sections = self._split_into_sections(text)
            progress.update()
        
        # Process each section
        content_blocks = []
        total_sections = len(sections)
        section_progress = ProgressTracker(total_sections, "Processing sections")
        
        for section in sections:
            with memory_management():
                blocks = self._process_section(section, source_type)
                content_blocks.extend(blocks)
                section_progress.update()
        
        progress.update()
        
        # Apply content normalization and semantic cleanup
        with memory_management():
            content_blocks = self.normalizer.normalize_content_blocks(content_blocks)
            progress.update()
        
        # Extract document metadata and key topics
        with memory_management():
            metadata = self._extract_document_metadata(content_blocks)
            all_text = " ".join([block.content for block in content_blocks 
                              if block.type in [ContentType.PARAGRAPH.value, ContentType.HEADING.value]])
            key_topics = self._extract_key_topics(all_text)
            progress.update()
        
        # Build final structure
        result = {
            'document_type': 'structured_text',
            'metadata': metadata,
            'content_blocks': [block.to_dict() for block in content_blocks],
            'summary': self._generate_summary(content_blocks, key_topics),
            'version': __version__,
            'normalization_applied': True
        }
        
        logger.info(f"Parsed into {len(content_blocks)} content blocks with {len(key_topics)} key topics")
        return result
    
    # [Rest of the DocumentParser methods remain the same as in the previous version...]
    # I'll include the key methods here, but the full implementation would include all methods
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for content detection"""
        return {
            # Heading patterns - multiple formats
            'heading_hash': re.compile(r'^(#{1,6})\s+(.+)$'),
            'heading_underline': re.compile(r'^(.+)\n([=\-])\2{2,}$', re.MULTILINE),
            'heading_numbered': re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)$'),
            'heading_chapter': re.compile(r'^(Chapter|Section|Part|CHAPTER|SECTION|PART|Ch\.?|Sec\.?)\s*(\d+|[IVXLCDM]+)[\s:\-]*(.*)$', re.IGNORECASE),
            
            # Code block patterns
            'code_fence': re.compile(r'^```(\w+)?\n(.*?)^```$', re.MULTILINE | re.DOTALL),
            'code_indent': re.compile(r'^(    .+)$', re.MULTILINE),
            'code_line': re.compile(r'^[\$#>]\s*(.+)$'),
            
            # List patterns
            'bullet_list': re.compile(r'^[\s]*[-\*\+•◦◘○●]\s+(.+)$'),
            'numbered_list': re.compile(r'^[\s]*(\d+|[a-z]|[A-Z]|[ivxlcdm]+|[IVXLCDM]+)[.)\]]\s+(.+)$'),
            
            # Quote patterns
            'blockquote': re.compile(r'^>\s*(.+)$'),
            
            # Table patterns (simple)
            'table_row': re.compile(r'^\|(.+)\|$'),
            'table_separator': re.compile(r'^[\|\+][-\+\|]+[\|\+]$'),
            
            # Figure and equation patterns
            'figure_caption': re.compile(r'^(Figure|Fig\.?|Table|Tbl\.?)\s*(\d+(?:\.\d+)*)[\.:]\s*(.+)$', re.IGNORECASE),
            'equation': re.compile(r'^\s*\$\$(.*?)\$\$\s*$', re.DOTALL),
            
            # Metadata patterns
            'url': re.compile(r'https?://[^\s<>"{}|\\^`[\]]+'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'file_path': re.compile(r'[/\\]?[\w\-./\\]+\.\w{1,6}'),
            'date': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'),
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent processing"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Fix common OCR issues
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'[''']', "'", text)
        text = re.sub(r'—', '-', text)
        text = re.sub(r'…', '...', text)
        
        # Fix line-breaking hyphenation common in OCR
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # Fix broken paragraphs (no space after period at end of line)
        text = re.sub(r'(\w)\.(\n)(\w)', r'\1. \3', text)
        
        # Normalize Unicode spaces
        text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', text)
        
        # Normalize bullets and list markers
        text = re.sub(r'[•◦◘○●]', '•', text)
        
        return text.strip()
    
    # [Include all other methods from the previous implementation...]


# [Include the DocumentConverter class and main function from the previous implementation...]

# The rest of the file remains largely the same, with the key addition being
# the ContentNormalizer class and its integration into the DocumentParser


if __name__ == '__main__':
    main()