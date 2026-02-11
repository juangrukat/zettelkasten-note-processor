"""
Zettelkasten Processor
=======================

Main processor that orchestrates parsing and formatting with dependency injection.
"""

from typing import List, Optional
from pathlib import Path
from src.core.parser import ZettelkastenParser
from src.core.formatter import MarkdownFormatter
from src.core import Note


class ZettelkastenProcessor:
    """Main processor that orchestrates parsing and formatting."""
    
    def __init__(
        self, 
        xml_content: str,
        parser: ZettelkastenParser = None,
        formatter: MarkdownFormatter = None
    ):
        """
        Initialize the processor with optional parser and formatter overrides.
        
        Args:
            xml_content: XML content to process
            parser: Optional custom parser instance (defaults to ZettelkastenParser)
            formatter: Optional custom formatter instance (defaults to MarkdownFormatter)
        """
        self.xml_content = xml_content
        self.parser = parser or ZettelkastenParser(xml_content)
        self.formatter = formatter or MarkdownFormatter()
        self.notes: List[Note] = []
    
    def parse(self):
        """Parse the XML content."""
        self.notes = self.parser.parse()
        return self
    
    def format(self) -> str:
        """Format the parsed notes as Markdown (combined output)."""
        if not self.notes:
            raise ValueError("No notes parsed. Call parse() first.")
        return self.formatter.format_notes(self.notes)
    
    def format_single(self, note: Note) -> str:
        """Format a single note as Markdown with frontmatter (no H2 title)."""
        return self.formatter._format_single_note(note, include_title_header=False)
    
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
