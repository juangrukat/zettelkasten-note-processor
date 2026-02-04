"""
Controller layer for Zettelkasten GUI.
Handles business logic, no Tkinter dependencies.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Callable
import json
from noter import ConfigManager, ZettelkastenProcessor, Note


# Local config file in the same directory as the script
LOCAL_CONFIG_FILE = Path(__file__).parent / "zettelkasten_config.json"


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
    """

    def __init__(self):
        self._status_callback: Optional[Callable[[str], None]] = None

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for status messages."""
        self._status_callback = callback

    def _notify_status(self, message: str) -> None:
        """Send status message via callback if set."""
        if self._status_callback:
            self._status_callback(message)

    def load_config(self) -> dict:
        """Load saved configuration from local directory."""
        if LOCAL_CONFIG_FILE.exists():
            try:
                config = json.loads(LOCAL_CONFIG_FILE.read_text(encoding="utf-8"))
                # Ensure all expected keys exist
                config.setdefault("author", "")
                config.setdefault("reference", "")
                config.setdefault("chapter", "")
                config.setdefault("output_dir", "")
                return config
            except (json.JSONDecodeError, IOError):
                pass
        return {"author": "", "reference": "", "chapter": "", "output_dir": ""}

    def save_config(
        self,
        author: str = "",
        reference: str = "",
        chapter: str = "",
        output_dir: str = ""
    ) -> None:
        """Save configuration to local directory."""
        try:
            config = {
                "author": author,
                "reference": reference,
                "chapter": chapter,
                "output_dir": output_dir
            }
            LOCAL_CONFIG_FILE.write_text(
                json.dumps(config, indent=2),
                encoding="utf-8"
            )
        except IOError:
            pass  # Silently fail if we can't write config

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

        self._notify_status("Parsing XML...")

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

            # Save the config for next time (output_dir saved separately by view)
            self.save_config(author=author, reference=reference, chapter=chapter, output_dir=str(output_dir) if output_dir else "")

            if not output_dir:
                output_dir = Path.cwd()

            if split_notes:
                self._notify_status("Saving individual notes...")
                saved_paths = processor.save_individual(output_dir)
                return ProcessingResult(
                    success=True,
                    message=f"Saved {len(saved_paths)} notes to {output_dir}",
                    output_paths=saved_paths
                )
            else:
                self._notify_status("Saving combined notes...")
                output_path = output_dir / "zettelkasten_notes.md"
                saved_path = processor.save(output_path)
                return ProcessingResult(
                    success=True,
                    message=f"Saved to {saved_path}",
                    output_paths=[saved_path]
                )

        except ValueError as e:
            return ProcessingResult(
                success=False,
                message=f"Parse error: {e}",
                error=str(e)
            )
        except Exception as e:
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
