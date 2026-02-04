#!/usr/bin/env python3
"""
Zettelkasten Note Parser
========================
Parses XML output from Zettelkasten prompt and converts to Markdown format.

Usage:
    python z.py input.xml
    python z.py input.xml --output notes.md
    python z.py input.xml --stdout
    python z.py input.xml --split
    python z.py input.xml --split --output my_notes/
"""

import xml.etree.ElementTree as ET
import re
import argparse
import sys
import json
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
#                            CONFIGURATION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ConfigManager:
    """Manages saved configuration for Author, Reference, and Chapter fields."""
    
    CONFIG_FILE = Path.home() / ".zettelkasten_config.json"
    
    @classmethod
    def load(cls) -> dict:
        """Load saved configuration."""
        if cls.CONFIG_FILE.exists():
            try:
                return json.loads(cls.CONFIG_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"author": "", "reference": "", "chapter": ""}
    
    @classmethod
    def save(cls, author: str = "", reference: str = "", chapter: str = "") -> None:
        """Save configuration to file."""
        try:
            config = {"author": author, "reference": reference, "chapter": chapter}
            cls.CONFIG_FILE.write_text(
                json.dumps(config, indent=2),
                encoding="utf-8"
            )
        except IOError:
            pass  # Silently fail if we can't write config
    
    @classmethod
    def get_prefilled(cls, key: str) -> str:
        """Get prefilled value for a key."""
        config = cls.load()
        return config.get(key, "")

# ═══════════════════════════════════════════════════════════════════════════════
#                               DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
#                               XML PARSER
# ═══════════════════════════════════════════════════════════════════════════════

class ZettelkastenParser:
    """Parses XML output from Zettelkasten prompt."""
    
    def __init__(self, xml_content: str):
        self.xml_content = self._clean_xml(xml_content)
        self.root = None
        self.notes: List[Note] = []
        
    def _clean_xml(self, xml_content: str) -> str:
        """Clean XML content of common issues."""
        # Remove markdown code fences if present
        xml_content = re.sub(r'^```xml?\s*\n?', '', xml_content, flags=re.MULTILINE)
        xml_content = re.sub(r'\n?```\s*$', '', xml_content, flags=re.MULTILINE)
        
        # Strip leading/trailing whitespace
        xml_content = xml_content.strip()
        
        return xml_content
    
    def parse(self) -> List[Note]:
        """Parse the XML and return list of notes."""
        try:
            self.root = ET.fromstring(self.xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        
        # Find notes element (may be root or nested)
        notes_elem = self.root if self.root.tag == "notes" else self.root.find(".//notes")
        
        if notes_elem is None:
            raise ValueError(f"No <notes> element found in XML")
        
        self.root = notes_elem
        return self._parse_notes()
    
    def _parse_notes(self) -> List[Note]:
        """Parse notes from XML."""
        self.notes = []
        timestamp = datetime.now().isoformat()
        
        for idx, note_elem in enumerate(self.root.findall("note"), start=1):
            note = Note(
                id=f"note_{idx:03d}",
                created_at=timestamp,
                title=self._get_text(note_elem, "title"),
                tags=self._parse_pipe_list(self._get_text(note_elem, "tags")),
                mentions=self._parse_mentions(self._get_text(note_elem, "mentions")),
                connections=self._parse_connections(self._get_text(note_elem, "connections")),
                principle=self._get_text(note_elem, "principle"),
                content=self._parse_content(self._get_text(note_elem, "content")),
                evidence=self._get_text(note_elem, "evidence"),
                why_it_matters=self._get_text(note_elem, "why_it_matters"),
                recall_question=self._get_text(note_elem, "recall_question"),
            )
            self.notes.append(note)
        
        return self.notes
    
    def _get_text(self, parent: Optional[ET.Element], tag: str) -> str:
        """Safely get text content from a child element."""
        if parent is None:
            return ""
        elem = parent.find(tag)
        if elem is None:
            return ""
        return (elem.text or "").strip()
    
    def _parse_pipe_list(self, text: str) -> List[str]:
        """Parse pipe-separated list into Python list."""
        if not text or text == "[NO_MENTIONS]":
            return []
        return [item.strip() for item in text.split("|") if item.strip()]
    
    def _parse_mentions(self, text: str) -> List[str]:
        """Parse @mentions from pipe-separated string."""
        if not text or text == "[NO_MENTIONS]":
            return []
        mentions = []
        for item in text.split("|"):
            item = item.strip()
            if item.startswith("@"):
                mentions.append(item)
            elif item:
                mentions.append(f"@{item}")
        return mentions
    
    def _parse_connections(self, text: str) -> List[str]:
        """Parse [[connections]] from pipe-separated string."""
        if not text:
            return []
        connections = []
        # Extract content within [[ ]]
        pattern = r'\[\[([^\]]+)\]\]'
        matches = re.findall(pattern, text)
        for match in matches:
            connections.append(match.strip())
        return connections
    
    def _parse_content(self, text: str) -> str:
        """Parse content field, converting tokens to proper formatting."""
        if not text:
            return ""
        # Convert [BREAK] to newlines
        text = text.replace("[BREAK]", "\n\n")
        # Convert [BULLET] to bullet points
        text = text.replace("[BULLET] ", "\n• ")
        text = text.replace("[BULLET]", "\n• ")
        return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
#                            MARKDOWN FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
#                               MAIN PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class ZettelkastenProcessor:
    """Main processor that orchestrates parsing and formatting."""
    
    def __init__(self, xml_content: str):
        self.parser = ZettelkastenParser(xml_content)
        self.notes: List[Note] = []
    
    def parse(self):
        """Parse the XML content."""
        self.notes = self.parser.parse()
        return self
    
    def format(self) -> str:
        """Format the parsed notes as Markdown (combined output)."""
        if not self.notes:
            raise ValueError("No notes parsed. Call parse() first.")
        return MarkdownFormatter.format_notes(self.notes)
    
    def format_single(self, note: Note) -> str:
        """Format a single note as Markdown with frontmatter (no H2 title)."""
        return MarkdownFormatter._format_single_note(note, include_title_header=False)
    
    def save(self, output_path: Path) -> Path:
        """Save formatted output to a single file."""
        content = self.format()
        
        # Ensure .md extension
        if output_path.suffix != ".md":
            output_path = output_path.with_suffix(".md")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        
        return output_path
    
    def save_individual(self, output_dir: Path) -> List[Path]:
        """Save each note as an individual file.
        
        Args:
            output_dir: Directory to save individual note files
            
        Returns:
            List of paths to saved files
        """
        if not self.notes:
            raise ValueError("No notes parsed. Call parse() first.")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths: List[Path] = []
        
        for note in self.notes:
            content = self.format_single(note)
            filename = note.get_filename()
            file_path = output_dir / filename
            
            # Handle duplicate filenames by appending a number
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = output_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            file_path.write_text(content, encoding="utf-8")
            saved_paths.append(file_path)
        
        return saved_paths
    
    def set_author_reference_chapter(self, author: Optional[str] = None, reference: Optional[str] = None, chapter: Optional[str] = None) -> None:
        """Set author, reference, and chapter for all notes.
        
        Args:
            author: Author name (optional)
            reference: Reference source (optional)
            chapter: Chapter information (optional)
        """
        for note in self.notes:
            if author:
                note.author = author
            if reference:
                note.reference = reference
            if chapter:
                note.chapter = chapter


# ═══════════════════════════════════════════════════════════════════════════════
#                               CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def prompt_with_prefill(prompt_text: str, prefill: str = "") -> str:
    """Prompt user with optional prefill value.
    
    Args:
        prompt_text: The prompt to display
        prefill: Value to prefill (shown in brackets, used if user just presses Enter)
        
    Returns:
        User input, or prefill if empty input
    """
    if prefill:
        full_prompt = f"{prompt_text} [{prefill}]: "
    else:
        full_prompt = f"{prompt_text}: "
    
    try:
        user_input = input(full_prompt).strip()
        return user_input if user_input else prefill
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)


def prompt_for_author_reference() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Interactively prompt for author, reference, and chapter with prefill support.
    
    Returns:
        Tuple of (author, reference, chapter) - may be None if not provided
    """
    # Load saved config for prefilling
    config = ConfigManager.load()
    
    print("\n📝 Optional Metadata (press Enter to skip or use prefilled value):\n")
    
    # Prompt for author
    author = prompt_with_prefill("Author", config.get("author", ""))
    
    # Prompt for reference
    reference = prompt_with_prefill("Reference", config.get("reference", ""))
    
    # Prompt for chapter
    chapter = prompt_with_prefill("Chapter", config.get("chapter", ""))
    
    # Save for next time (only non-empty values)
    ConfigManager.save(
        author=author if author else config.get("author", ""),
        reference=reference if reference else config.get("reference", ""),
        chapter=chapter if chapter else config.get("chapter", "")
    )
    
    # Convert empty strings to None
    return author or None, reference or None, chapter or None


def main():
    parser = argparse.ArgumentParser(
        description="Parse Zettelkasten XML output and convert to Markdown format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.xml
  %(prog)s input.xml --output notes.md
  %(prog)s input.xml --stdout
  %(prog)s input.xml --split
  %(prog)s input.xml --split --output my_notes/
  %(prog)s input.xml --author "John Doe" --reference "Book Title"
        """
    )
    
    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        help="Input XML file path"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: input_file.md)"
    )
    
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print output to stdout instead of file"
    )
    
    parser.add_argument(
        "--split", "-s",
        action="store_true",
        help="Save each note as an individual file (uses output as directory)"
    )
    
    parser.add_argument(
        "--author", "-a",
        type=str,
        help="Author name (optional, prompts in interactive mode)"
    )
    
    parser.add_argument(
        "--reference", "-r",
        type=str,
        help="Reference source (optional, prompts in interactive mode)"
    )
    
    parser.add_argument(
        "--chapter", "-c",
        type=str,
        help="Chapter (optional, prompts in interactive mode)"
    )
    
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Skip interactive prompts (use with --author/--reference/--chapter or for batch processing)"
    )
    
    args = parser.parse_args()
    
    # Get XML content
    if args.input_file:
        if not args.input_file.exists():
            print(f"Error: File not found: {args.input_file}", file=sys.stderr)
            sys.exit(1)
        xml_content = args.input_file.read_text(encoding="utf-8")
    else:
        # Read from stdin
        xml_content = sys.stdin.read()
    
    if not xml_content.strip():
        print("Error: No XML content provided", file=sys.stderr)
        sys.exit(1)
    
    # Determine if we should prompt for author/reference/chapter
    # Only prompt if: interactive terminal, not --no-prompt, and not already provided via args
    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    should_prompt = (
        is_interactive 
        and not args.no_prompt 
        and args.author is None 
        and args.reference is None
        and args.chapter is None
    )
    
    author = args.author
    reference = args.reference
    chapter = args.chapter
    
    if should_prompt:
        author, reference, chapter = prompt_for_author_reference()
    
    # Process
    try:
        processor = ZettelkastenProcessor(xml_content)
        processor.parse()
        
        # Apply author/reference/chapter to all notes if provided
        if author or reference or chapter:
            processor.set_author_reference_chapter(author, reference, chapter)
        
        if args.stdout:
            print(processor.format())
        elif args.split:
            # Split into individual files
            if args.output:
                output_dir = args.output
            else:
                base_name = args.input_file.stem if args.input_file else "notes"
                output_dir = Path(f"{base_name}_notes")
            
            saved_paths = processor.save_individual(output_dir)
            print(f"Saved {len(saved_paths)} notes to: {output_dir}/")
            for path in saved_paths:
                print(f"  - {path.name}")
        elif args.output:
            saved_path = processor.save(args.output)
            print(f"Saved to: {saved_path}")
        else:
            # Default output path
            base_name = args.input_file.stem if args.input_file else "zettelkasten"
            output_path = Path(f"{base_name}.md")
            saved_path = processor.save(output_path)
            print(f"Saved to: {saved_path}")
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
