#!/usr/bin/env python3
"""
Zettelkasten Note Parser
========================
Parses XML output from Zettelkasten prompt and converts to YAML and clean text formats.

Usage:
    python zettel_parser.py input.xml --output-dir ./output
    python zettel_parser.py input.xml --format yaml
    python zettel_parser.py input.xml --format markdown
    python zettel_parser.py input.xml --format all
    
    # From clipboard (requires pyperclip)
    python zettel_parser.py --clipboard --format all
"""

import xml.etree.ElementTree as ET
import re
import argparse
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
from pathlib import Path
from datetime import datetime
import json

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


@dataclass
class Gap:
    """Represents a single gap identified in gap analysis."""
    gap_type: str
    missing_element: str
    why_it_matters: str
    source_location: str
    suggested_note_title: str


@dataclass
class CoverageAssessment:
    """Coverage statistics from gap analysis."""
    pillars_captured: str
    causal_chains_captured: str
    meta_argument_captured: str
    overall_signal_capture: str


@dataclass
class GapAnalysis:
    """Represents the complete gap analysis output."""
    coverage: CoverageAssessment
    gaps: List[Gap]
    verdict: str
    recommendation: str


# ═══════════════════════════════════════════════════════════════════════════════
#                               XML PARSER
# ═══════════════════════════════════════════════════════════════════════════════

class ZettelkastenParser:
    """Parses XML output from Zettelkasten prompt."""
    
    def __init__(self, xml_content: str):
        self.xml_content = self._clean_xml(xml_content)
        self.root = None
        self.notes: List[Note] = []
        self.gap_analysis: Optional[GapAnalysis] = None
        self.mode: str = "unknown"
        
    def _clean_xml(self, xml_content: str) -> str:
        """Clean XML content of common issues."""
        # Remove markdown code fences if present
        xml_content = re.sub(r'^```xml?\s*\n?', '', xml_content, flags=re.MULTILINE)
        xml_content = re.sub(r'\n?```\s*$', '', xml_content, flags=re.MULTILINE)
        
        # Strip leading/trailing whitespace
        xml_content = xml_content.strip()
        
        return xml_content
    
    def parse(self) -> Union[List[Note], GapAnalysis]:
        """Parse the XML and return appropriate data structure."""
        try:
            self.root = ET.fromstring(self.xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        
        # Detect mode based on root element
        if self.root.tag == "notes":
            self.mode = "notes"
            return self._parse_notes()
        elif self.root.tag == "gap_analysis":
            self.mode = "gap_analysis"
            return self._parse_gap_analysis()
        else:
            # Try to find nested elements
            notes_elem = self.root.find(".//notes")
            gap_elem = self.root.find(".//gap_analysis")
            
            if notes_elem is not None:
                self.mode = "notes"
                self.root = notes_elem
                return self._parse_notes()
            elif gap_elem is not None:
                self.mode = "gap_analysis"
                self.root = gap_elem
                return self._parse_gap_analysis()
            else:
                raise ValueError(f"Unknown root element: {self.root.tag}")
    
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
    
    def _parse_gap_analysis(self) -> GapAnalysis:
        """Parse gap analysis from XML."""
        # Parse coverage assessment
        coverage_elem = self.root.find("coverage_assessment")
        coverage = CoverageAssessment(
            pillars_captured=self._get_text(coverage_elem, "pillars_captured"),
            causal_chains_captured=self._get_text(coverage_elem, "causal_chains_captured"),
            meta_argument_captured=self._get_text(coverage_elem, "meta_argument_captured"),
            overall_signal_capture=self._get_text(coverage_elem, "overall_signal_capture"),
        )
        
        # Parse gaps
        gaps = []
        critical_gaps_elem = self.root.find("critical_gaps")
        if critical_gaps_elem is not None:
            gaps_text = critical_gaps_elem.text
            if gaps_text and "[NONE_IDENTIFIED]" not in gaps_text:
                for gap_elem in critical_gaps_elem.findall("gap"):
                    gap = Gap(
                        gap_type=gap_elem.get("type", "Unknown"),
                        missing_element=self._get_text(gap_elem, "missing_element"),
                        why_it_matters=self._get_text(gap_elem, "why_it_matters"),
                        source_location=self._get_text(gap_elem, "source_location"),
                        suggested_note_title=self._get_text(gap_elem, "suggested_note_title"),
                    )
                    gaps.append(gap)
        
        self.gap_analysis = GapAnalysis(
            coverage=coverage,
            gaps=gaps,
            verdict=self._get_text(self.root, "verdict"),
            recommendation=self._get_text(self.root, "recommendation"),
        )
        
        return self.gap_analysis
    
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
#                               YAML FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

class YAMLFormatter:
    """Formats parsed data as YAML."""
    
    @staticmethod
    def format_notes(notes: List[Note]) -> str:
        """Convert notes to YAML format."""
        output_lines = ["---", "# Zettelkasten Notes", f"# Generated: {datetime.now().isoformat()}", 
                        f"# Count: {len(notes)}", "---", ""]
        
        for note in notes:
            output_lines.append(YAMLFormatter._format_single_note(note))
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    @staticmethod
    def _format_single_note(note: Note) -> str:
        """Format a single note as YAML."""
        lines = []
        lines.append(f"- id: {note.id}")
        lines.append(f"  title: \"{YAMLFormatter._escape_yaml(note.title)}\"")
        lines.append(f"  created_at: {note.created_at}")
        lines.append("")
        
        # Tags
        lines.append("  tags:")
        for tag in note.tags:
            lines.append(f"    - \"{YAMLFormatter._escape_yaml(tag)}\"")
        
        # Mentions
        lines.append("  mentions:")
        if note.mentions:
            for mention in note.mentions:
                lines.append(f"    - \"{mention}\"")
        else:
            lines.append("    []")
        
        # Connections
        lines.append("  connections:")
        for conn in note.connections:
            lines.append(f"    - \"[[{conn}]]\"")
        
        lines.append("")
        lines.append(f"  principle: |")
        lines.append(f"    {note.principle}")
        
        lines.append("")
        lines.append(f"  content: |")
        for content_line in note.content.split("\n"):
            lines.append(f"    {content_line}")
        
        lines.append("")
        lines.append(f"  evidence: |")
        evidence_text = note.evidence if note.evidence != "[NO_DIRECT_EVIDENCE]" else "No direct evidence provided."
        lines.append(f"    {evidence_text}")
        
        lines.append("")
        lines.append(f"  why_it_matters: |")
        lines.append(f"    {note.why_it_matters}")
        
        lines.append("")
        lines.append(f"  recall_question: \"{YAMLFormatter._escape_yaml(note.recall_question)}\"")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_gap_analysis(analysis: GapAnalysis) -> str:
        """Convert gap analysis to YAML format."""
        lines = ["---", "# Gap Analysis Report", f"# Generated: {datetime.now().isoformat()}", "---", ""]
        
        lines.append("coverage_assessment:")
        lines.append(f"  pillars_captured: \"{analysis.coverage.pillars_captured}\"")
        lines.append(f"  causal_chains_captured: \"{analysis.coverage.causal_chains_captured}\"")
        lines.append(f"  meta_argument_captured: \"{analysis.coverage.meta_argument_captured}\"")
        lines.append(f"  overall_signal_capture: \"{analysis.coverage.overall_signal_capture}\"")
        lines.append("")
        
        lines.append(f"verdict: \"{analysis.verdict}\"")
        lines.append("")
        
        lines.append("critical_gaps:")
        if analysis.gaps:
            for gap in analysis.gaps:
                lines.append(f"  - type: \"{gap.gap_type}\"")
                lines.append(f"    missing_element: |")
                lines.append(f"      {gap.missing_element}")
                lines.append(f"    why_it_matters: |")
                lines.append(f"      {gap.why_it_matters}")
                lines.append(f"    source_location: \"{gap.source_location}\"")
                lines.append(f"    suggested_note_title: \"{YAMLFormatter._escape_yaml(gap.suggested_note_title)}\"")
                lines.append("")
        else:
            lines.append("  []  # No critical gaps identified")
        
        lines.append("")
        lines.append("recommendation: |")
        for rec_line in analysis.recommendation.split("\n"):
            lines.append(f"  {rec_line}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _escape_yaml(text: str) -> str:
        """Escape special characters for YAML strings."""
        return text.replace("\\", "\\\\").replace('"', '\\"')


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
    def _format_single_note(note: Note) -> str:
        """Format a single note as Markdown."""
        lines = []
        
        # Title
        lines.append(f"## {note.title}")
        lines.append("")
        
        # Metadata block (YAML frontmatter style)
        lines.append("---")
        lines.append(f"id: {note.id}")
        lines.append(f"created: {note.created_at}")
        
        # Tags in YAML list format with / for nested tags
        if note.tags:
            lines.append("tags:")
            for tag in note.tags:
                # Convert -- to / for nested tags
                formatted_tag = tag.replace("--", "/")
                lines.append(f"  - {formatted_tag}")
        
        # Mentions
        if note.mentions:
            lines.append("mentions:")
            for mention in note.mentions:
                lines.append(f"  - {mention}")
        
            mention_links = [f"`{m}`" for m in note.mentions]
            lines.append(", ".join(mention_links))
            lines.append("")
        
        # Connections
        lines.append("**Connections:**")
        conn_links = [f"[[{c}]]" for c in note.connections]
        lines.append(" · ".join(conn_links))
        lines.append("")
        lines.append("</details>")
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
    def format_gap_analysis(analysis: GapAnalysis) -> str:
        """Convert gap analysis to Markdown format."""
        lines = [
            "# Gap Analysis Report",
            "",
            f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]
        
        # Coverage Assessment
        lines.append("## 📊 Coverage Assessment")
        lines.append("")
        lines.append("| Metric | Status |")
        lines.append("|--------|--------|")
        lines.append(f"| Structural Pillars | {analysis.coverage.pillars_captured} |")
        lines.append(f"| Causal Chains | {analysis.coverage.causal_chains_captured} |")
        lines.append(f"| Meta-Argument | {analysis.coverage.meta_argument_captured} |")
        lines.append(f"| **Overall Signal Capture** | **{analysis.coverage.overall_signal_capture}** |")
        lines.append("")
        
        # Verdict
        verdict_emoji = {
            "COMPLETE": "✅",
            "MINOR_GAPS": "🔶",
            "SIGNIFICANT_GAPS": "⚠️",
            "MISSING_FOUNDATION": "🚨"
        }.get(analysis.verdict, "❓")
        
        lines.append(f"## {verdict_emoji} Verdict: `{analysis.verdict}`")
        lines.append("")
        
        # Critical Gaps
        lines.append("## 🔍 Critical Gaps")
        lines.append("")
        
        if analysis.gaps:
            for i, gap in enumerate(analysis.gaps, 1):
                type_emoji = {
                    "Structural Pillar": "🏛️",
                    "Causal Chain": "🔗",
                    "Meta-Argument": "🎭"
                }.get(gap.gap_type, "📌")
                
                lines.append(f"### {i}. {type_emoji} {gap.gap_type}")
                lines.append("")
                lines.append(f"**Missing Element:**")
                lines.append(f"> {gap.missing_element}")
                lines.append("")
                lines.append(f"**Why It Matters:** {gap.why_it_matters}")
                lines.append("")
                lines.append(f"**Source Location:** {gap.source_location}")
                lines.append("")
                lines.append(f"**Suggested Note Title:** `{gap.suggested_note_title}`")
                lines.append("")
        else:
            lines.append("✅ **No critical gaps identified.** Your notes capture the essential signal.")
            lines.append("")
        
        # Recommendation
        lines.append("## 💬 Recommendation")
        lines.append("")
        lines.append(analysis.recommendation)
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug.strip('-')


# ═══════════════════════════════════════════════════════════════════════════════
#                            PLAIN TEXT FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

class PlainTextFormatter:
    """Formats parsed data as clean plain text."""
    
    @staticmethod
    def format_notes(notes: List[Note]) -> str:
        """Convert notes to plain text format."""
        lines = [
            "=" * 80,
            "ZETTELKASTEN NOTES",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total Notes: {len(notes)}",
            "=" * 80,
            "",
        ]
        
        for i, note in enumerate(notes, 1):
            lines.append(PlainTextFormatter._format_single_note(note, i))
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_single_note(note: Note, index: int) -> str:
        """Format a single note as plain text."""
        lines = []
        
        lines.append("-" * 80)
        lines.append(f"NOTE {index}: {note.title}")
        lines.append("-" * 80)
        lines.append("")
        
        lines.append(f"ID: {note.id}")
        lines.append(f"Created: {note.created_at}")
        lines.append("")
        
        lines.append("TAGS:")
        for tag in note.tags:
            lines.append(f"  • {tag.replace('--', ' > ')}")
        lines.append("")
        
        if note.mentions:
            lines.append("MENTIONS:")
            lines.append(f"  {', '.join(note.mentions)}")
            lines.append("")
        
        lines.append("CONNECTIONS:")
        lines.append(f"  {' | '.join(note.connections)}")
        lines.append("")
        
        lines.append("PRINCIPLE:")
        lines.append(f"  {note.principle}")
        lines.append("")
        
        lines.append("CONTENT:")
        for content_line in note.content.split("\n"):
            lines.append(f"  {content_line}")
        lines.append("")
        
        lines.append("EVIDENCE:")
        if note.evidence == "[NO_DIRECT_EVIDENCE]":
            lines.append("  [No direct evidence provided]")
        else:
            lines.append(f"  {note.evidence}")
        lines.append("")
        
        lines.append("WHY IT MATTERS:")
        lines.append(f"  {note.why_it_matters}")
        lines.append("")
        
        lines.append("RECALL QUESTION:")
        lines.append(f"  Q: {note.recall_question}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_gap_analysis(analysis: GapAnalysis) -> str:
        """Convert gap analysis to plain text format."""
        lines = [
            "=" * 80,
            "GAP ANALYSIS REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 80,
            "",
            "COVERAGE ASSESSMENT",
            "-" * 40,
            f"  Structural Pillars:    {analysis.coverage.pillars_captured}",
            f"  Causal Chains:         {analysis.coverage.causal_chains_captured}",
            f"  Meta-Argument:         {analysis.coverage.meta_argument_captured}",
            f"  Overall Signal:        {analysis.coverage.overall_signal_capture}",
            "",
            f"VERDICT: {analysis.verdict}",
            "",
        ]
        
        lines.append("CRITICAL GAPS")
        lines.append("-" * 40)
        
        if analysis.gaps:
            for i, gap in enumerate(analysis.gaps, 1):
                lines.append(f"\n  [{i}] {gap.gap_type}")
                lines.append(f"      Missing: {gap.missing_element}")
                lines.append(f"      Why: {gap.why_it_matters}")
                lines.append(f"      Location: {gap.source_location}")
                lines.append(f"      Suggested Title: {gap.suggested_note_title}")
        else:
            lines.append("  No critical gaps identified.")
        
        lines.append("")
        lines.append("RECOMMENDATION")
        lines.append("-" * 40)
        lines.append(f"  {analysis.recommendation}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#                            JSON FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

class JSONFormatter:
    """Formats parsed data as JSON."""
    
    @staticmethod
    def format_notes(notes: List[Note]) -> str:
        """Convert notes to JSON format."""
        data = {
            "metadata": {
                "type": "zettelkasten_notes",
                "generated": datetime.now().isoformat(),
                "count": len(notes)
            },
            "notes": [asdict(note) for note in notes]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def format_gap_analysis(analysis: GapAnalysis) -> str:
        """Convert gap analysis to JSON format."""
        data = {
            "metadata": {
                "type": "gap_analysis",
                "generated": datetime.now().isoformat()
            },
            "coverage_assessment": asdict(analysis.coverage),
            "verdict": analysis.verdict,
            "critical_gaps": [asdict(gap) for gap in analysis.gaps],
            "recommendation": analysis.recommendation
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
#                               MAIN PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class ZettelkastenProcessor:
    """Main processor that orchestrates parsing and formatting."""
    
    FORMATTERS = {
        "yaml": YAMLFormatter,
        "markdown": MarkdownFormatter,
        "md": MarkdownFormatter,
        "text": PlainTextFormatter,
        "txt": PlainTextFormatter,
        "json": JSONFormatter,
    }
    
    FILE_EXTENSIONS = {
        "yaml": ".yaml",
        "markdown": ".md",
        "md": ".md",
        "text": ".txt",
        "txt": ".txt",
        "json": ".json",
    }
    
    def __init__(self, xml_content: str):
        self.parser = ZettelkastenParser(xml_content)
        self.data = None
        self.mode = None
    
    def parse(self):
        """Parse the XML content."""
        self.data = self.parser.parse()
        self.mode = self.parser.mode
        return self
    
    def format(self, format_type: str) -> str:
        """Format the parsed data in the specified format."""
        if self.data is None:
            raise ValueError("No data parsed. Call parse() first.")
        
        format_type = format_type.lower()
        if format_type not in self.FORMATTERS:
            raise ValueError(f"Unknown format: {format_type}. Available: {list(self.FORMATTERS.keys())}")
        
        formatter = self.FORMATTERS[format_type]
        
        if self.mode == "notes":
            return formatter.format_notes(self.data)
        elif self.mode == "gap_analysis":
            return formatter.format_gap_analysis(self.data)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def save(self, output_path: Path, format_type: str):
        """Save formatted output to file."""
        content = self.format(format_type)
        
        # Ensure correct extension
        expected_ext = self.FILE_EXTENSIONS.get(format_type.lower(), ".txt")
        if output_path.suffix != expected_ext:
            output_path = output_path.with_suffix(expected_ext)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        
        return output_path
    
    def save_all(self, output_dir: Path, base_name: str = "zettelkasten"):
        """Save in all formats to output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        for fmt in ["yaml", "markdown", "text", "json"]:
            ext = self.FILE_EXTENSIONS[fmt]
            output_path = output_dir / f"{base_name}{ext}"
            self.save(output_path, fmt)
            saved_files.append(output_path)
        
        return saved_files


# ═══════════════════════════════════════════════════════════════════════════════
#                               CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Parse Zettelkasten XML output and convert to various formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.xml --format yaml
  %(prog)s input.xml --format markdown --output notes.md
  %(prog)s input.xml --format all --output-dir ./output
  %(prog)s --clipboard --format yaml
        """
    )
    
    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        help="Input XML file path"
    )
    
    parser.add_argument(
        "--clipboard", "-c",
        action="store_true",
        help="Read XML from clipboard (requires pyperclip)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["yaml", "markdown", "md", "text", "txt", "json", "all"],
        default="yaml",
        help="Output format (default: yaml)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (for single format)"
    )
    
    parser.add_argument(
        "--output-dir", "-d",
        type=Path,
        help="Output directory (for --format all)"
    )
    
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print output to stdout instead of file"
    )
    
    args = parser.parse_args()
    
    # Get XML content
    if args.clipboard:
        try:
            import pyperclip
            xml_content = pyperclip.paste()
        except ImportError:
            print("Error: pyperclip not installed. Run: pip install pyperclip", file=sys.stderr)
            sys.exit(1)
    elif args.input_file:
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
    
    # Process
    try:
        processor = ZettelkastenProcessor(xml_content)
        processor.parse()
        
        if args.format == "all":
            if args.stdout:
                print("Error: --stdout cannot be used with --format all", file=sys.stderr)
                sys.exit(1)
            
            output_dir = args.output_dir or Path("./output")
            base_name = args.input_file.stem if args.input_file else "zettelkasten"
            saved_files = processor.save_all(output_dir, base_name)
            
            print(f"Saved {len(saved_files)} files to {output_dir}:")
            for f in saved_files:
                print(f"  - {f}")
        else:
            if args.stdout:
                print(processor.format(args.format))
            elif args.output:
                saved_path = processor.save(args.output, args.format)
                print(f"Saved to: {saved_path}")
            else:
                # Default output path
                base_name = args.input_file.stem if args.input_file else "zettelkasten"
                ext = ZettelkastenProcessor.FILE_EXTENSIONS.get(args.format, ".txt")
                output_path = Path(f"{base_name}_output{ext}")
                saved_path = processor.save(output_path, args.format)
                print(f"Saved to: {saved_path}")
                
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()