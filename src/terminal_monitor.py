#!/usr/bin/env python3
"""
Terminal Continue Monitor - Main Application

A robust terminal monitoring application that detects inactive terminal windows
and automatically sends configured keystrokes to maintain session activity.

Author: dbbuilder
License: MIT
Version: 1.0.0
"""

import sys
import time
import signal
import argparse
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Any
import yaml

from src.configuration_manager import ConfigurationManager
from src.window_manager import WindowManager
from src.state_tracker import StateTracker
from src.keystroke_sender import KeystrokeSender
from src.text_extractor import TextExtractor


class TerminalMonitor:
    """
    Main application class for monitoring terminal windows and managing
    automatic keystroke injection for inactive sessions.
    """

    def __init__(self, config_path: Optional[str] = None, log_level: Optional[str] = None):
        """
        Initialize the Terminal Monitor application.

        Args:
            config_path: Path to configuration file (defaults to config.yaml)
            log_level: Override log level from configuration
        """
        self.running = False
        self.config_manager = None
        self.window_manager = None
        self.state_tracker = None
        self.keystroke_sender = None
        self.text_extractor = None
        self.logger = None

        try:
            # Initialize configuration management
            self.config_manager = ConfigurationManager(config_path)
            
            # Setup logging with configuration
            self._setup_logging(log_level)
            
            # Initialize component modules
            self._initialize_components()
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.logger.info("Terminal Monitor initialized successfully")
            
        except Exception as e:
            # Fallback logging if main logging setup fails
            logging.basicConfig(level=logging.ERROR)
            logging.error(f"Failed to initialize Terminal Monitor: {e}")
            raise

    def _setup_logging(self, log_level_override: Optional[str] = None) -> None:
        """
        Configure logging based on configuration settings.

        Args:
            log_level_override: Override the configured log level
        """
        try:
            log_config = self.config_manager.get_logging_config()
            
            # Determine effective log level
            effective_level = log_level_override or log_config.get('level', 'INFO')
            
            # Configure root logger
            logging.basicConfig(
                level=getattr(logging, effective_level.upper()),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            self.logger = logging.getLogger(__name__)
            
            # Setup file logging if enabled
            if log_config.get('file', {}).get('enabled', False):
                self._setup_file_logging(log_config['file'])
            
            # Setup console logging configuration
            if log_config.get('console', {}).get('colored', False):
                self._setup_colored_logging()
                
            self.logger.info(f"Logging configured with level: {effective_level}")
            
        except Exception as e:
            # Fallback to basic logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Failed to setup advanced logging: {e}")

    def _setup_file_logging(self, file_config: Dict[str, Any]) -> None:
        """
        Setup file-based logging with rotation.

        Args:
            file_config: File logging configuration dictionary
        """
        try:
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(file_config.get('path', 'logs/terminal_monitor.log'))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            max_bytes = file_config.get('max_size_mb', 10) * 1024 * 1024
            backup_count = file_config.get('backup_count', 5)
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            # Add handler to root logger
            logging.getLogger().addHandler(file_handler)
            
            self.logger.info(f"File logging enabled: {log_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to setup file logging: {e}")

    def _setup_colored_logging(self) -> None:
        """Setup colored console logging if colorlog is available."""
        try:
            import colorlog
            
            colored_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            
            # Find console handler and update formatter
            for handler in logging.getLogger().handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setFormatter(colored_formatter)
                    break
                    
        except ImportError:
            self.logger.debug("Colored logging not available (colorlog not installed)")

    def _initialize_components(self) -> None:
        """Initialize all component modules with configuration."""
        try:
            config = self.config_manager.get_config()
            
            # Initialize window manager for detecting and managing terminal windows
            self.window_manager = WindowManager(
                target_processes=config.get('target_processes', []),
                advanced_config=config.get('advanced', {}),
                exclusions=config.get('exclusions', {})
            )
            
            # Initialize text extractor for reading terminal content
            self.text_extractor = TextExtractor(
                operation_timeout=config.get('advanced', {}).get('window_operation_timeout', 5),
                hash_optimization=config.get('advanced', {}).get('use_hash_optimization', True),
                hash_sample_size=config.get('advanced', {}).get('hash_sample_size', 1000)
            )
            
            # Initialize state tracker for monitoring window states
            self.state_tracker = StateTracker(
                inactivity_threshold=config.get('inactivity_threshold_seconds', 30),
                process_overrides=config.get('process_overrides', {}),
                max_windows=config.get('advanced', {}).get('max_windows', 50)
            )
            
            # Initialize keystroke sender for automation
            self.keystroke_sender = KeystrokeSender(
                default_keys=config.get('keys_to_send', 'continue{ENTER}'),
                process_overrides=config.get('process_overrides', {}),
                retry_config=config.get('advanced', {})
            )
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows-specific signal handling
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, signal_handler)

    def start(self) -> None:
        """
        Start the terminal monitoring process.
        
        This method begins the main monitoring loop that continuously
        scans for terminal windows, tracks their activity, and sends
        keystrokes to inactive windows.
        """
        if self.running:
            self.logger.warning("Monitor is already running")
            return
        
        self.running = True
        config = self.config_manager.get_config()
        polling_interval = config.get('polling_interval_seconds', 5)
        
        self.logger.info("🚀 Starting Terminal Continue Monitor")
        self.logger.info(f"Target processes: {', '.join(config.get('target_processes', []))}")
        self.logger.info(f"Inactivity threshold: {config.get('inactivity_threshold_seconds', 30)} seconds")
        self.logger.info(f"Polling interval: {polling_interval} seconds")
        self.logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            self._run_monitoring_loop(polling_interval)
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"Monitoring loop failed: {e}")
            raise
        finally:
            self.running = False
            self.logger.info("Terminal monitoring stopped")

    def _run_monitoring_loop(self, polling_interval: int) -> None:
        """
        Execute the main monitoring loop.

        Args:
            polling_interval: Seconds to wait between monitoring cycles
        """
        last_performance_log = time.time()
        performance_config = self.config_manager.get_config().get('performance', {})
        performance_enabled = performance_config.get('enabled', True)
        metrics_interval = performance_config.get('metrics_interval', 300)
        
        while self.running:
            loop_start_time = time.time()
            
            try:
                # Discover and manage terminal windows
                windows = self.window_manager.discover_windows()
                current_window_handles = set(windows.keys())
                
                # Process each discovered window
                for window_handle, window_info in windows.items():
                    self._process_window(window_handle, window_info)
                
                # Clean up tracking for closed windows
                self.state_tracker.cleanup_closed_windows(current_window_handles)
                
                # Log performance metrics periodically
                if performance_enabled and (time.time() - last_performance_log) >= metrics_interval:
                    self._log_performance_metrics()
                    last_performance_log = time.time()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.logger.info("Continuing monitoring after error...")
            
            # Calculate sleep time to maintain consistent polling interval
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0, polling_interval - loop_duration)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif loop_duration > polling_interval * 2:
                self.logger.warning(f"Monitoring loop took {loop_duration:.2f}s (target: {polling_interval}s)")

    def _process_window(self, window_handle: int, window_info: Dict[str, Any]) -> None:
        """
        Process a single terminal window for activity detection and response.

        Args:
            window_handle: Windows handle identifier for the terminal window
            window_info: Dictionary containing window metadata
        """
        try:
            process_name = window_info.get('process_name', 'unknown')
            
            # Extract current text content from the window
            current_text = self.text_extractor.extract_text(window_handle)
            if current_text is None:
                return
            
            # Update state tracking with current text
            activity_result = self.state_tracker.update_window_state(
                window_handle, current_text, process_name
            )
            
            # Handle new window detection
            if activity_result['is_new_window']:
                self.logger.info(f"New terminal window detected: {process_name} (HWND: {window_handle})")
            
            # Handle inactivity detection and response
            if activity_result['is_inactive']:
                inactivity_duration = activity_result['inactivity_duration']
                self.logger.info(
                    f"✅ ACTION: Sending keystrokes to {process_name} "
                    f"(HWND: {window_handle}) after {inactivity_duration:.1f}s of inactivity"
                )
                
                # Send configured keystrokes to the inactive window
                success = self.keystroke_sender.send_keystrokes(window_handle, process_name)
                
                if success:
                    # Reset the inactivity timer on successful keystroke injection
                    self.state_tracker.reset_window_timer(window_handle)
                else:
                    self.logger.warning(f"Failed to send keystrokes to {process_name} (HWND: {window_handle})")
            
        except Exception as e:
            self.logger.error(f"Error processing window {window_handle}: {e}")

    def _log_performance_metrics(self) -> None:
        """Log current performance metrics."""
        try:
            import psutil
            process = psutil.Process()
            
            cpu_percent = process.cpu_percent()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            tracked_windows = self.state_tracker.get_window_count()
            
            self.logger.info(
                f"Performance: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB, "
                f"Windows {tracked_windows}"
            )
            
            # Check against configured warning thresholds
            performance_config = self.config_manager.get_config().get('performance', {})
            cpu_threshold = performance_config.get('cpu_warning_threshold', 10)
            memory_threshold = performance_config.get('memory_warning_threshold', 100)
            
            if cpu_percent > cpu_threshold:
                self.logger.warning(f"High CPU usage: {cpu_percent:.1f}% (threshold: {cpu_threshold}%)")
            
            if memory_mb > memory_threshold:
                self.logger.warning(f"High memory usage: {memory_mb:.1f}MB (threshold: {memory_threshold}MB)")
                
        except ImportError:
            self.logger.debug("Performance monitoring requires psutil package")
        except Exception as e:
            self.logger.debug(f"Performance monitoring error: {e}")

    def stop(self) -> None:
        """Stop the terminal monitoring process gracefully."""
        if not self.running:
            return
        
        self.logger.info("Stopping terminal monitoring...")
        self.running = False
        
        # Perform cleanup operations
        if self.state_tracker:
            self.state_tracker.cleanup()
        
        if self.window_manager:
            self.window_manager.cleanup()
        
        self.logger.info("Terminal monitoring stopped successfully")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status information about the monitor.

        Returns:
            Dictionary containing current operational status
        """
        status = {
            'running': self.running,
            'tracked_windows': 0,
            'configuration_loaded': self.config_manager is not None,
            'components_initialized': all([
                self.window_manager,
                self.state_tracker,
                self.keystroke_sender,
                self.text_extractor
            ])
        }
        
        if self.state_tracker:
            status['tracked_windows'] = self.state_tracker.get_window_count()
        
        return status


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Monitor terminal windows for inactivity and send automated keystrokes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python terminal_monitor.py                    # Use default config.yaml
  python terminal_monitor.py --config custom.yaml --log-level DEBUG
  python terminal_monitor.py --log-level WARNING
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Override log level from configuration'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Terminal Continue Monitor 1.0.0'
    )
    
    return parser


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code: 0 for success, 1 for error
    """
    try:
        # Parse command-line arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Create and initialize the monitor
        monitor = TerminalMonitor(
            config_path=args.config,
            log_level=args.log_level
        )
        
        # Start monitoring
        monitor.start()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        return 0
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e}")
        return 1
    except yaml.YAMLError as e:
        print(f"Configuration file error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
