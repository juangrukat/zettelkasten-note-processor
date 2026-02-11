"""
Controller layer for Zettelkasten GUI.
Handles business logic, no Tkinter dependencies.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from src.core.processor import ZettelkastenProcessor
from src.config.manager import ConfigManager
from src.events import EventDispatcher, EventType, Event


@dataclass
class ProcessingResult:
    """Result of processing XML content."""
    success: bool
    message: str
    output_paths: List[Path] = None
    error: Optional[str] = None


class ZettelkastenController:
    """
    Controller for Zettelkasten note processing.
    Bridges the view and the processor without any GUI dependencies.
    Uses event system for communication.
    """

    def __init__(self, event_dispatcher: EventDispatcher = None):
        self.event_dispatcher = event_dispatcher or EventDispatcher()

    def load_config(self) -> dict:
        """Load saved configuration from config manager."""
        return ConfigManager.load()

    def save_config(
        self,
        author: str = "",
        reference: str = "",
        chapter: str = "",
        output_dir: str = ""
    ) -> None:
        """Save configuration to config manager."""
        ConfigManager.save(
            author=author,
            reference=reference,
            chapter=chapter,
            output_dir=output_dir
        )

    def process_xml(
        self,
        xml_content: str,
        author: str = "",
        reference: str = "",
        chapter: str = "",
        output_dir: Optional[Path] = None,
        split_notes: bool = False
    ) -> ProcessingResult:
        """
        Process XML content and generate Markdown output.

        Args:
            xml_content: Raw XML string to parse
            author: Optional author name
            reference: Optional reference source
            chapter: Optional chapter information
            output_dir: Directory for output (default: current directory)
            split_notes: If True, save each note as separate file

        Returns:
            ProcessingResult with success status and paths
        """
        if not xml_content.strip():
            return ProcessingResult(
                success=False,
                message="No XML content provided",
                error="Empty input"
            )

        self.event_dispatcher.dispatch_status("Parsing XML...")

        try:
            processor = ZettelkastenProcessor(xml_content)
            processor.parse()

            # Apply metadata to all notes
            if author or reference or chapter:
                processor.set_author_reference_chapter(
                    author=author or None,
                    reference=reference or None,
                    chapter=chapter or None
                )

            # Save the config for next time
            self.save_config(
                author=author,
                reference=reference,
                chapter=chapter,
                output_dir=str(output_dir) if output_dir else ""
            )

            if not output_dir:
                output_dir = Path.cwd()

            if split_notes:
                self.event_dispatcher.dispatch_status("Saving individual notes...")
                saved_paths = processor.save_individual(output_dir)
                self.event_dispatcher.dispatch_processing_completed(
                    data={"saved_paths": saved_paths}
                )
                return ProcessingResult(
                    success=True,
                    message=f"Saved {len(saved_paths)} notes to {output_dir}",
                    output_paths=saved_paths
                )
            else:
                self.event_dispatcher.dispatch_status("Saving combined notes...")
                output_path = output_dir / "zettelkasten_notes.md"
                saved_path = processor.save(output_path)
                self.event_dispatcher.dispatch_processing_completed(
                    data={"saved_paths": [saved_path]}
                )
                return ProcessingResult(
                    success=True,
                    message=f"Saved to {saved_path}",
                    output_paths=[saved_path]
                )

        except ValueError as e:
            self.event_dispatcher.dispatch_error(str(e))
            return ProcessingResult(
                success=False,
                message=f"Parse error: {e}",
                error=str(e)
            )
        except Exception as e:
            self.event_dispatcher.dispatch_error(str(e))
            return ProcessingResult(
                success=False,
                message=f"Unexpected error: {e}",
                error=str(e)
            )

    def get_output_preview(self, xml_content: str) -> str:
        """
        Generate a preview of the output without saving.

        Args:
            xml_content: Raw XML string to parse

        Returns:
            Formatted Markdown preview or error message
        """
        if not xml_content.strip():
            return "(No content to preview)"

        try:
            processor = ZettelkastenProcessor(xml_content)
            processor.parse()
            return processor.format()
        except Exception as e:
            return f"Preview error: {e}"
