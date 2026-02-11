"""
Configuration Manager
======================

Manages saved configuration for Author, Reference, Chapter, and Output Directory.
"""

import json
from pathlib import Path
from typing import Dict, Optional


class ConfigManager:
    """Manages saved configuration for Zettelkasten processor."""
    
    DEFAULT_CONFIG: Dict[str, str] = {
        "author": "",
        "reference": "", 
        "chapter": "",
        "output_dir": ""
    }
    
    @classmethod
    def get_config_file(cls) -> Path:
        """Get the configuration file path (local to the script)."""
        return Path(__file__).parent.parent.parent / "zettelkasten_config.json"
    
    @classmethod
    def load(cls) -> Dict[str, str]:
        """Load saved configuration.
        
        Returns:
            Dictionary containing configuration values, with defaults for missing keys
        """
        config_file = cls.get_config_file()
        config = cls.DEFAULT_CONFIG.copy()
        
        if config_file.exists():
            try:
                saved = json.loads(config_file.read_text(encoding="utf-8"))
                config.update(saved)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Ensure all required keys are present
        for key in cls.DEFAULT_CONFIG:
            if key not in config:
                config[key] = cls.DEFAULT_CONFIG[key]
        
        return config
    
    @classmethod
    def save(
        cls, 
        author: str = "", 
        reference: str = "", 
        chapter: str = "", 
        output_dir: str = ""
    ) -> None:
        """Save configuration to file.
        
        Args:
            author: Author name
            reference: Reference source
            chapter: Chapter information
            output_dir: Output directory path
        """
        config_file = cls.get_config_file()
        config = cls.load()
        
        # Update only provided values that are non-empty
        if author:
            config["author"] = author
        if reference:
            config["reference"] = reference
        if chapter:
            config["chapter"] = chapter
        if output_dir:
            config["output_dir"] = output_dir
        
        try:
            config_file.write_text(
                json.dumps(config, indent=2),
                encoding="utf-8"
            )
        except IOError:
            pass  # Silently fail if we can't write config
    
    @classmethod
    def get_prefilled(cls, key: str) -> str:
        """Get prefilled value for a key.
        
        Args:
            key: Configuration key to retrieve
            
        Returns:
            Value for the key, or empty string if not found
        """
        config = cls.load()
        return config.get(key, "")
