#!/usr/bin/env python3
"""
Zettelkasten Note Processor - GUI Entry Point
============================================
Simple Tkinter front end using modular architecture.

Usage:
    python main.py
"""

import tkinter as tk
from controller import ZettelkastenController
from view import ZettelkastenView


def main() -> None:
    """Application entry point - wires layers together."""
    # Create the root window
    root = tk.Tk()

    # Create controller (logic layer)
    controller = ZettelkastenController()

    # Create view (presentation layer), inject controller
    app = ZettelkastenView(root, controller)

    # Run the application
    app.run()


if __name__ == "__main__":
    main()
