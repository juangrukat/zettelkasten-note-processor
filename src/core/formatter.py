"""
Markdown Formatter
===================

Responsible for formatting Note objects into Markdown.
"""

import re
from typing import List
from datetime import datetime
from src.core import Note


class MarkdownFormatter:
    """Formats parsed data as clean Markdown."""
    
    @staticmethod
    def format_notes(notes: List[Note]) -> str:
        """Convert notes to Markdown format."""
        lines = [
            "# Zettelkasten Notes",
            "",
            f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
            f"> **Total Notes:** {len(notes)}",
            "",
            "---",
            "",
        ]
        
        # Table of Contents
        lines.append("## Table of Contents")
        lines.append("")
        for i, note in enumerate(notes, 1):
            anchor = MarkdownFormatter._slugify(note.title)
            lines.append(f"{i}. [{note.title}](#{anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Individual notes
        for note in notes:
            lines.append(MarkdownFormatter._format_single_note(note))
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_single_note(note: Note, include_title_header: bool = True) -> str:
        """Format a single note as Markdown.
        
        Args:
            note: The note to format
            include_title_header: Whether to include the title as an H2 header
        """
        lines = []
        
        # Title as header (optional, for combined output)
        if include_title_header:
            lines.append(f"## {note.title}")
            lines.append("")
        
        # Metadata block (YAML frontmatter style)
        lines.append("---")
        lines.append(f'title: "{note.title}"')
        
        # Author, Reference, and Chapter in frontmatter (under title, optional)
        if note.author:
            lines.append(f'author: "{note.author}"')
        if note.reference:
            lines.append(f'reference: "{note.reference}"')
        if note.chapter:
            lines.append(f'chapter: "{note.chapter}"')
        
        lines.append(f"created: {note.created_at}")
        
        # Tags in YAML list format
        if note.tags:
            lines.append("tags:")
            for tag in note.tags:
                # Convert -- to / for nested tags
                formatted_tag = tag.replace("--", "/")
                # Replace disallowed characters with underscores: space . : ; , ? ! @ * + = ~ \ ? > < |
                formatted_tag = re.sub(r'[\s.:;,?!@*+=~\\?<>|]', '_', formatted_tag)
                # Ensure no consecutive underscores
                formatted_tag = re.sub(r'_+', '_', formatted_tag)
                # Remove leading/trailing underscores
                formatted_tag = formatted_tag.strip('_')
                if formatted_tag:  # Only add non-empty tags
                    lines.append(f"  - {formatted_tag}")
        
        # Mentions (formatted as [[link]] without @)
        if note.mentions:
            lines.append("mentions:")
            for mention in note.mentions:
                # Remove @ prefix and format as [[link]]
                clean_mention = mention.lstrip('@')
                lines.append(f'  - "[[{clean_mention}]]"')
        
        # Connections
        if note.connections:
            lines.append("connections:")
            for conn in note.connections:
                lines.append(f'  - "[[{conn}]]"')
        
        lines.append("---")
        lines.append("")
        
        # Principle (highlighted)
        lines.append("### 💡 Core Principle")
        lines.append("")
        lines.append(f"> {note.principle}")
        lines.append("")
        
        # Content
        lines.append("### 📝 Content")
        lines.append("")
        lines.append(note.content)
        lines.append("")
        
        # Evidence
        lines.append("### 📚 Evidence")
        lines.append("")
        if note.evidence == "[NO_DIRECT_EVIDENCE]":
            lines.append("*No direct evidence provided in source.*")
        else:
            lines.append(f"> {note.evidence}")
        lines.append("")
        
        # Why It Matters
        lines.append("### 🎯 Why It Matters")
        lines.append("")
        lines.append(note.why_it_matters)
        lines.append("")
        
        # Recall Question
        lines.append("### ❓ Recall Question")
        lines.append("")
        lines.append(f"**Q:** {note.recall_question}")
        lines.append("")
        lines.append("---")
        
        return "\n".join(lines)
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug.strip('-')
