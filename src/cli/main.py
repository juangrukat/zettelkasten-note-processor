#!/usr/bin/env python3
"""
Zettelkasten Note Parser - CLI Entry Point
==========================================
Parses XML output from Zettelkasten prompt and converts to Markdown format.

Usage:
    python -m src.cli.main input.xml
    python -m src.cli.main input.xml --output notes.md
    python -m src.cli.main input.xml --stdout
    python -m src.cli.main input.xml --split
    python -m src.cli.main input.xml --split --output my_notes/
    python -m src.cli.main input.xml --author "John Doe" --reference "Book Title"
"""

import argparse
import sys
from pathlib import Path
from src.core.processor import ZettelkastenProcessor
from src.config.manager import ConfigManager


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


def prompt_for_author_reference() -> tuple[str, str, str]:
    """Interactively prompt for author, reference, and chapter with prefill support.
    
    Returns:
        Tuple of (author, reference, chapter) - may be empty strings if not provided
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
    
    return author, reference, chapter


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
