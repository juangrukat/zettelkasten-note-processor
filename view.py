"""
View layer for Zettelkasten GUI.
Tkinter widgets and layout, delegates all logic to controller.
Uses event system for communication.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
from controller import ZettelkastenController, ProcessingResult
from src.events import EventType, Event


class LabeledEntry(ttk.Frame):
    """Single-purpose widget: label + entry pair."""

    def __init__(
        self,
        parent: tk.Widget,
        label_text: str,
        width: int = 40,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

        self.label = ttk.Label(self, text=label_text, width=12, anchor="w")
        self.label.pack(side=tk.LEFT)

        self.entry = ttk.Entry(self, width=width)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

    def get_value(self) -> str:
        """Get current entry value."""
        return self.entry.get().strip()

    def set_value(self, value: str) -> None:
        """Set entry value."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

    def bind_return(self, callback) -> None:
        """Bind Return key to callback."""
        self.entry.bind("<Return>", callback)


class DirectorySelector(ttk.Frame):
    """Widget for selecting a directory path with a browse button."""

    def __init__(
        self,
        parent: tk.Widget,
        label_text: str,
        width: int = 40,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

        self.label = ttk.Label(self, text=label_text, width=12, anchor="w")
        self.label.pack(side=tk.LEFT)

        self.entry = ttk.Entry(self, width=width)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        self.browse_btn = ttk.Button(
            self,
            text="Browse...",
            command=self._browse_directory,
            width=10
        )
        self.browse_btn.pack(side=tk.LEFT, padx=(5, 0))

    def _browse_directory(self) -> None:
        """Open directory browser dialog."""
        current = self.entry.get().strip()
        initial_dir = current if current and Path(current).exists() else str(Path.home())

        selected = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=initial_dir,
            mustexist=True
        )
        if selected:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, selected)

    def get_value(self) -> str:
        """Get current directory path."""
        return self.entry.get().strip()

    def set_value(self, value: str) -> None:
        """Set directory path."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)


class ZettelkastenView:
    """
    Main application window for Zettelkasten processor.
    Thin wrapper around Tkinter, delegates all logic to controller.
    Uses event system for communication.
    """

    def __init__(self, root: tk.Tk, controller: ZettelkastenController):
        self.root = root
        self.controller = controller

        self.root.title("Zettelkasten Note Processor")
        self.root.geometry("700x600")
        self.root.minsize(600, 400)

        # Set up event listeners
        self._setup_event_listeners()

        self._create_widgets()
        self._load_saved_config()

    def _setup_event_listeners(self) -> None:
        """Set up event listeners for controller events."""
        self.controller.event_dispatcher.add_listener(
            EventType.STATUS_UPDATED,
            self._on_status_updated
        )
        self.controller.event_dispatcher.add_listener(
            EventType.ERROR_OCCURRED,
            self._on_error_occurred
        )
        self.controller.event_dispatcher.add_listener(
            EventType.PROCESSING_STARTED,
            self._on_processing_started
        )
        self.controller.event_dispatcher.add_listener(
            EventType.PROCESSING_COMPLETED,
            self._on_processing_completed
        )

    def _create_widgets(self) -> None:
        """Create and layout all widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # XML text area expands

        # === Metadata Section ===
        meta_frame = ttk.LabelFrame(main_frame, text="Metadata (saved between sessions)", padding="5")
        meta_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        meta_frame.columnconfigure(0, weight=1)

        self.author_entry = LabeledEntry(meta_frame, "Author:")
        self.author_entry.grid(row=0, column=0, sticky="ew", pady=2)

        self.reference_entry = LabeledEntry(meta_frame, "Reference:")
        self.reference_entry.grid(row=1, column=0, sticky="ew", pady=2)

        self.chapter_entry = LabeledEntry(meta_frame, "Chapter:")
        self.chapter_entry.grid(row=2, column=0, sticky="ew", pady=2)

        self.output_dir_entry = DirectorySelector(meta_frame, "Save to:")
        self.output_dir_entry.grid(row=3, column=0, sticky="ew", pady=2)

        # === Options Section ===
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.split_var = tk.BooleanVar(value=False)
        self.split_check = ttk.Checkbutton(
            options_frame,
            text="Save each note as separate file",
            variable=self.split_var
        )
        self.split_check.pack(side=tk.LEFT)

        # === XML Input Section ===
        input_frame = ttk.LabelFrame(main_frame, text="Paste XML Content", padding="5")
        input_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.xml_text = tk.Text(input_frame, wrap=tk.WORD, height=15)
        self.xml_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for text area
        scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=self.xml_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.xml_text.configure(yscrollcommand=scrollbar.set)

        # === Button Section ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(0, 5))

        self.process_btn = ttk.Button(
            button_frame,
            text="Process XML",
            command=self._on_process
        )
        self.process_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.preview_btn = ttk.Button(
            button_frame,
            text="Preview",
            command=self._on_preview
        )
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_btn = ttk.Button(
            button_frame,
            text="Clear",
            command=self._on_clear
        )
        self.clear_btn.pack(side=tk.LEFT)

        # === Status Section ===
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, sticky="ew")

        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            relief=tk.SUNKEN,
            anchor="w"
        )
        self.status_label.pack(fill=tk.X)

    def _load_saved_config(self) -> None:
        """Load and apply saved configuration."""
        config = self.controller.load_config()
        self.author_entry.set_value(config.get("author", ""))
        self.reference_entry.set_value(config.get("reference", ""))
        self.chapter_entry.set_value(config.get("chapter", ""))
        self.output_dir_entry.set_value(config.get("output_dir", ""))

    def _get_metadata(self) -> tuple[str, str, str, str]:
        """Get current metadata values."""
        return (
            self.author_entry.get_value(),
            self.reference_entry.get_value(),
            self.chapter_entry.get_value(),
            self.output_dir_entry.get_value()
        )

    def _get_xml_content(self) -> str:
        """Get XML content from text area."""
        return self.xml_text.get("1.0", tk.END)

    def _update_status(self, message: str) -> None:
        """Update status bar message."""
        self.status_label.configure(text=message)
        self.root.update_idletasks()

    def _on_status_updated(self, event: Event) -> None:
        """Handle status update events."""
        self._update_status(event.data)

    def _on_error_occurred(self, event: Event) -> None:
        """Handle error events."""
        self._update_status(f"Error: {event.data}")

    def _on_processing_started(self, event: Event) -> None:
        """Handle processing started event."""
        self._update_status("Processing...")

    def _on_processing_completed(self, event: Event) -> None:
        """Handle processing completed event."""
        self._update_status("Ready")

    def _on_process(self) -> None:
        """Handle Process button click."""
        xml_content = self._get_xml_content()
        author, reference, chapter, output_dir_str = self._get_metadata()

        # Use saved output directory or prompt
        output_dir = output_dir_str.strip()
        if not output_dir:
            output_dir = filedialog.askdirectory(
                title="Select Output Directory",
                mustexist=True
            )
            if not output_dir:
                return
            # Save the selected directory for next time
            self.output_dir_entry.set_value(output_dir)

        output_path = Path(output_dir)
        if not output_path.exists():
            messagebox.showerror("Error", f"Directory does not exist: {output_dir}")
            return

        split_notes = self.split_var.get()

        result = self.controller.process_xml(
            xml_content=xml_content,
            author=author,
            reference=reference,
            chapter=chapter,
            output_dir=output_path,
            split_notes=split_notes
        )

        # Save config with current output directory
        self.controller.save_config(
            author=author,
            reference=reference,
            chapter=chapter,
            output_dir=str(output_path)
        )

        self._handle_result(result)

    def _on_preview(self) -> None:
        """Handle Preview button click."""
        xml_content = self._get_xml_content()
        preview = self.controller.get_output_preview(xml_content)

        # Show preview in a simple dialog
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Output Preview")
        preview_window.geometry("600x500")

        text_widget = tk.Text(preview_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert("1.0", preview)
        text_widget.configure(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(text_widget, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)

        ttk.Button(preview_window, text="Close", command=preview_window.destroy).pack(pady=5)

    def _on_clear(self) -> None:
        """Handle Clear button click."""
        self.xml_text.delete("1.0", tk.END)
        self._update_status("Cleared")

    def _handle_result(self, result: ProcessingResult) -> None:
        """Handle processing result."""
        if result.success:
            messagebox.showinfo("Success", result.message)
            self._update_status("Ready")
        else:
            messagebox.showerror("Error", result.message)
            self._update_status(f"Error: {result.error}")

    def run(self) -> None:
        """Start the main event loop."""
        self.root.mainloop()
