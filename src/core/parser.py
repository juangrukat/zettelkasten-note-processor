"""
Zettelkasten XML Parser
========================

Responsible for parsing XML content into Note objects.
"""

import xml.etree.ElementTree as ET
import re
from typing import List
from datetime import datetime
from src.core import Note


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
