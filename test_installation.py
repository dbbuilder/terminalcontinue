#!/usr/bin/env python3
"""
Terminal Continue Monitor - Installation Test Script

Tests the installation and basic functionality of the Terminal Continue Monitor
to ensure all components are working properly.

Author: dbbuilder
License: MIT
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing module imports...")
    
    try:
        # Test individual module imports
        from configuration_manager import ConfigurationManager
        from window_manager import WindowManager
        from text_extractor import TextExtractor
        from state_tracker import StateTracker
        from keystroke_sender import KeystrokeSender
        from terminal_monitor import TerminalMonitor
        
        print("✓ All modules imported successfully")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during import: {e}")
        return False

def test_configuration():
    """Test configuration loading and validation."""
    print("Testing configuration management...")
    
    try:
        # Test with default configuration
        config_manager = ConfigurationManager()
        config = config_manager.get_config()
        
        # Validate essential configuration keys
        required_keys = [
            'target_processes',
            'inactivity_threshold_seconds',
            'keys_to_send',
            'polling_interval_seconds'
        ]
        
        for key in required_keys:
            if key not in config:
                print(f"✗ Missing required configuration key: {key}")
                return False
        
        print("✓ Configuration loaded and validated successfully")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_window_manager():
    """Test window management functionality."""
    print("Testing window manager...")
    
    try:
        from window_manager import WindowManager
        
        # Create window manager with test configuration
        window_manager = WindowManager(
            target_processes=['cmd.exe', 'powershell.exe'],
            advanced_config={'max_windows': 10, 'window_operation_timeout': 5},
            exclusions={'window_titles': [], 'command_lines': []}
        )
        
        # Test window discovery (should not fail even if no windows found)
        windows = window_manager.discover_windows()
        
        print(f"✓ Window manager functional - discovered {len(windows)} terminal windows")
        return True
        
    except Exception as e:
        print(f"✗ Window manager test failed: {e}")
        return False

def test_text_extractor():
    """Test text extraction functionality."""
    print("Testing text extractor...")
    
    try:
        from text_extractor import TextExtractor
        
        # Create text extractor
        text_extractor = TextExtractor(
            operation_timeout=5,
            hash_optimization=True,
            hash_sample_size=1000
        )
        
        # Test hash computation
        test_text = "This is a test string for hash computation."
        hash_result = text_extractor.compute_text_hash(test_text)
        
        if not hash_result or len(hash_result) != 64:  # SHA-256 produces 64-char hex
            print("✗ Hash computation failed")
            return False
        
        print("✓ Text extractor functional")
        return True
        
    except Exception as e:
        print(f"✗ Text extractor test failed: {e}")
        return False

def test_state_tracker():
    """Test state tracking functionality."""
    print("Testing state tracker...")
    
    try:
        from state_tracker import StateTracker
        
        # Create state tracker
        state_tracker = StateTracker(
            inactivity_threshold=30,
            process_overrides={},
            max_windows=50
        )
        
        # Test window state management
        test_handle = 12345
        test_text = "Test terminal content"
        test_process = "cmd.exe"
        
        # Simulate window state update
        result = state_tracker.update_window_state(test_handle, test_text, test_process)
        
        if not result.get('is_new_window'):
            print("✗ State tracker did not recognize new window")
            return False
        
        # Test cleanup
        state_tracker.cleanup_closed_windows(set())
        
        print("✓ State tracker functional")
        return True
        
    except Exception as e:
        print(f"✗ State tracker test failed: {e}")
        return False

def test_keystroke_sender():
    """Test keystroke sender functionality."""
    print("Testing keystroke sender...")
    
    try:
        from keystroke_sender import KeystrokeSender
        
        # Create keystroke sender
        keystroke_sender = KeystrokeSender(
            default_keys="test{ENTER}",
            process_overrides={},
            retry_config={'retry_attempts': 1, 'retry_delay': 1}
        )
        
        # Test keystroke sequence validation
        validation = keystroke_sender.validate_keystroke_sequence("test{ENTER}")
        
        if not validation.get('is_valid'):
            print("✗ Keystroke validation failed")
            return False
        
        print("✓ Keystroke sender functional")
        return True
        
    except Exception as e:
        print(f"✗ Keystroke sender test failed: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are available."""
    print("Testing dependencies...")
    
    required_modules = [
        'yaml',
        'pywinauto',
        'win32process',
        'win32gui',
        'win32api'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"✗ Missing required modules: {', '.join(missing_modules)}")
        print("  Please run: pip install -r requirements.txt")
        return False
    
    print("✓ All required dependencies available")
    return True

def test_file_permissions():
    """Test file and directory permissions."""
    print("Testing file permissions...")
    
    try:
        # Test logs directory
        logs_dir = Path("logs")
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Test writing to logs directory
        test_log_file = logs_dir / "test.log"
        try:
            with open(test_log_file, 'w') as f:
                f.write("Test log entry")
            test_log_file.unlink()  # Clean up
        except PermissionError:
            print("✗ Cannot write to logs directory")
            return False
        
        # Test configuration file access
        config_files = ["config.yaml", "config.example.yaml"]
        for config_file in config_files:
            if Path(config_file).exists():
                try:
                    with open(config_file, 'r') as f:
                        f.read(100)  # Read first 100 chars
                except PermissionError:
                    print(f"✗ Cannot read {config_file}")
                    return False
        
        print("✓ File permissions adequate")
        return True
        
    except Exception as e:
        print(f"✗ File permission test failed: {e}")
        return False

def main():
    """Run all installation tests."""
    print("="*60)
    print("Terminal Continue Monitor - Installation Test")
    print("="*60)
    print()
    
    # Configure logging to reduce noise during testing
    logging.getLogger().setLevel(logging.WARNING)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("File Permissions", test_file_permissions),
        ("Window Manager", test_window_manager),
        ("Text Extractor", test_text_extractor),
        ("State Tracker", test_state_tracker),
        ("Keystroke Sender", test_keystroke_sender),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 All tests passed! Installation appears to be successful.")
        print("\nYou can now start the Terminal Continue Monitor using:")
        print("  python src/terminal_monitor.py")
        print("  or")
        print("  ./start_monitor.bat")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
        print("\nCommon solutions:")
        print("- Ensure all dependencies are installed: pip install -r requirements.txt")
        print("- Check that you're running on a supported Windows version")
        print("- Verify Python version is 3.8 or higher")
        print("- Run as administrator if permission errors occur")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    # Pause for interactive execution
    if sys.stdout.isatty():
        print("\nPress Enter to exit...")
        input()
    
    sys.exit(exit_code)
