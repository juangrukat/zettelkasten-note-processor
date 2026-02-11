"""
Core Zettelkasten Components
=============================

This module contains the core processing components:
- parser: XML parsing functionality
- formatter: Markdown formatting functionality
- processor: Main orchestrator for parsing and formatting
- models: Data models (Note, etc.)
"""

from dataclasses import dataclass, field
from typing import List, Optional
import re
from datetime import datetime
from pathlib import Path


@dataclass
class Note:
    """Represents a single Zettelkasten note."""
    title: str
    tags: List[str]
    mentions: List[str]
    connections: List[str]
    principle: str
    content: str
    evidence: str
    why_it_matters: str
    recall_question: str
    
    # Metadata (not from XML, added during processing)
    id: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None
    reference: Optional[str] = None
    chapter: Optional[str] = None
    
    def get_filename(self, suffix: str = ".md") -> str:
        """Generate a safe filename from the note title."""
        # Remove non-alphanumeric characters (except spaces and hyphens)
        safe = re.sub(r'[^\w\s-]', '', self.title)
        # Replace spaces and underscores with hyphens
        safe = re.sub(r'[\s_]+', '-', safe)
        # Convert to lowercase
        safe = safe.lower()
        # Limit length to avoid overly long filenames
        safe = safe[:80].strip('-')
        return f"{safe}{suffix}"
