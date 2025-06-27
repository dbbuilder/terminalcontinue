"""
Terminal Continue Monitor Package

A Python package for monitoring Windows terminal applications and automatically
sending keystrokes to maintain session activity.

Author: dbbuilder
License: MIT
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "dbbuilder"
__license__ = "MIT"
__description__ = "Automated terminal session activity monitor for Windows"

# Package imports for easier access
from .terminal_monitor import TerminalMonitor
from .configuration_manager import ConfigurationManager
from .window_manager import WindowManager
from .text_extractor import TextExtractor
from .state_tracker import StateTracker
from .keystroke_sender import KeystrokeSender

__all__ = [
    'TerminalMonitor',
    'ConfigurationManager', 
    'WindowManager',
    'TextExtractor',
    'StateTracker',
    'KeystrokeSender'
]
