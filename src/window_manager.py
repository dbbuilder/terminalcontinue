"""
Window Manager Module

Handles detection, enumeration, and management of terminal windows
using Windows API and UI Automation.

Author: dbbuilder
License: MIT
"""

import logging
import win32process
import win32gui
import win32api
from typing import Dict, Set, List, Any, Optional
from pywinauto.findwindows import find_windows


class WindowManager:
    """
    Manages detection and tracking of terminal windows.
    
    Provides functionality to discover terminal windows, validate their
    accessibility, and manage the lifecycle of window monitoring.
    """

    def __init__(self, target_processes: List[str], advanced_config: Dict[str, Any], 
                 exclusions: Dict[str, List[str]]):
        """
        Initialize the Window Manager.

        Args:
            target_processes: List of executable names to monitor
            advanced_config: Advanced configuration settings
            exclusions: Exclusion rules for filtering windows
        """
        self.target_processes = set(target_processes)
        self.max_windows = advanced_config.get('max_windows', 50)
        self.operation_timeout = advanced_config.get('window_operation_timeout', 5)
        self.exclusions = exclusions
        self.logger = logging.getLogger(__name__)
        
        # Cache for window information to improve performance
        self._window_cache = {}
        self._last_discovery_time = 0
        
        self.logger.info(f"Window Manager initialized for processes: {', '.join(self.target_processes)}")

    def discover_windows(self) -> Dict[int, Dict[str, Any]]:
        """
        Discover all visible terminal windows matching target processes.

        Returns:
            Dictionary mapping window handles to window information
        """
        discovered_windows = {}
        
        try:
            # Find all top-level, visible windows
            all_window_handles = find_windows(top_level_only=True, visible=True)
            
            # Filter and process windows
            for window_handle in all_window_handles:
                try:
                    window_info = self._get_window_info(window_handle)
                    
                    if window_info and self._should_monitor_window(window_info):
                        discovered_windows[window_handle] = window_info
                        
                        # Respect maximum window limit
                        if len(discovered_windows) >= self.max_windows:
                            self.logger.warning(
                                f"Maximum window limit ({self.max_windows}) reached. "
                                f"Some windows may not be monitored."
                            )
                            break
                            
                except Exception as e:
                    self.logger.debug(f"Error processing window {window_handle}: {e}")
                    continue
            
            # Log discovery results
            if discovered_windows:
                process_counts = {}
                for window_info in discovered_windows.values():
                    process_name = window_info.get('process_name', 'unknown')
                    process_counts[process_name] = process_counts.get(process_name, 0) + 1
                
                self.logger.debug(
                    f"Discovered {len(discovered_windows)} windows: "
                    f"{', '.join(f'{name}({count})' for name, count in process_counts.items())}"
                )
            
            return discovered_windows
            
        except Exception as e:
            self.logger.error(f"Error during window discovery: {e}")
            return {}

    def _get_window_info(self, window_handle: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a window.

        Args:
            window_handle: Window handle to query

        Returns:
            Dictionary containing window information or None if unavailable
        """
        try:
            # Get process information
            process_name = self._get_process_name(window_handle)
            if not process_name:
                return None
            
            # Get window title and basic properties
            window_title = win32gui.GetWindowText(window_handle)
            window_rect = win32gui.GetWindowRect(window_handle)
            
            # Get additional window properties
            window_info = {
                'handle': window_handle,
                'process_name': process_name,
                'window_title': window_title,
                'window_rect': window_rect,
                'is_visible': win32gui.IsWindowVisible(window_handle),
                'is_enabled': win32gui.IsWindowEnabled(window_handle),
                'window_class': win32gui.GetClassName(window_handle)
            }
            
            # Get process ID and command line if possible
            try:
                _, process_id = win32process.GetWindowThreadProcessId(window_handle)
                window_info['process_id'] = process_id
                
                # Attempt to get command line (may require elevated permissions)
                command_line = self._get_process_command_line(process_id)
                if command_line:
                    window_info['command_line'] = command_line
                    
            except Exception as e:
                self.logger.debug(f"Could not get extended process info for window {window_handle}: {e}")
            
            return window_info
            
        except Exception as e:
            self.logger.debug(f"Error getting window info for {window_handle}: {e}")
            return None

    def _get_process_name(self, window_handle: int) -> Optional[str]:
        """
        Get the executable name for a window.

        Args:
            window_handle: Window handle to query

        Returns:
            Executable name or None if unavailable
        """
        try:
            _, process_id = win32process.GetWindowThreadProcessId(window_handle)
            process_handle = win32api.OpenProcess(
                win32process.PROCESS_QUERY_INFORMATION | win32process.PROCESS_VM_READ,
                False,
                process_id
            )
            
            try:
                executable_path = win32process.GetModuleFileNameEx(process_handle, 0)
                return executable_path.split('\\')[-1]  # Extract filename only
            finally:
                win32api.CloseHandle(process_handle)
                
        except Exception as e:
            self.logger.debug(f"Could not get process name for window {window_handle}: {e}")
            return None

    def _get_process_command_line(self, process_id: int) -> Optional[str]:
        """
        Get the command line for a process.

        Args:
            process_id: Process ID to query

        Returns:
            Command line string or None if unavailable
        """
        try:
            import wmi
            
            # Use WMI to get command line (requires elevated permissions for some processes)
            wmi_connection = wmi.WMI()
            processes = wmi_connection.Win32_Process(ProcessId=process_id)
            
            if processes:
                return processes[0].CommandLine
            
        except ImportError:
            # WMI not available, skip command line detection
            pass
        except Exception as e:
            self.logger.debug(f"Could not get command line for process {process_id}: {e}")
        
        return None

    def _should_monitor_window(self, window_info: Dict[str, Any]) -> bool:
        """
        Determine if a window should be monitored based on configuration.

        Args:
            window_info: Window information dictionary

        Returns:
            True if window should be monitored, False otherwise
        """
        try:
            process_name = window_info.get('process_name', '')
            window_title = window_info.get('window_title', '')
            command_line = window_info.get('command_line', '')
            
            # Check if process is in target list
            if process_name not in self.target_processes:
                return False
            
            # Check window visibility and enablement
            if not window_info.get('is_visible', False) or not window_info.get('is_enabled', False):
                self.logger.debug(f"Skipping invisible/disabled window: {process_name}")
                return False
            
            # Apply exclusion rules
            if self._is_excluded_by_title(window_title):
                self.logger.debug(f"Window excluded by title rule: {window_title}")
                return False
            
            if self._is_excluded_by_command_line(command_line):
                self.logger.debug(f"Window excluded by command line rule: {command_line}")
                return False
            
            # Additional validation for specific window types
            if not self._is_valid_terminal_window(window_info):
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error evaluating window monitoring criteria: {e}")
            return False

    def _is_excluded_by_title(self, window_title: str) -> bool:
        """
        Check if window title matches exclusion rules.

        Args:
            window_title: Window title to check

        Returns:
            True if window should be excluded, False otherwise
        """
        excluded_titles = self.exclusions.get('window_titles', [])
        
        for excluded_title in excluded_titles:
            if excluded_title.lower() in window_title.lower():
                return True
        
        return False

    def _is_excluded_by_command_line(self, command_line: str) -> bool:
        """
        Check if command line matches exclusion rules.

        Args:
            command_line: Command line to check

        Returns:
            True if window should be excluded, False otherwise
        """
        if not command_line:
            return False
        
        excluded_commands = self.exclusions.get('command_lines', [])
        
        for excluded_command in excluded_commands:
            if excluded_command.lower() in command_line.lower():
                return True
        
        return False

    def _is_valid_terminal_window(self, window_info: Dict[str, Any]) -> bool:
        """
        Perform additional validation for terminal windows.

        Args:
            window_info: Window information dictionary

        Returns:
            True if window is a valid terminal window, False otherwise
        """
        try:
            window_handle = window_info.get('handle')
            process_name = window_info.get('process_name', '')
            window_class = window_info.get('window_class', '')
            
            # Validate window dimensions (too small windows are likely not terminals)
            window_rect = window_info.get('window_rect', (0, 0, 0, 0))
            width = window_rect[2] - window_rect[0]
            height = window_rect[3] - window_rect[1]
            
            if width < 100 or height < 50:
                self.logger.debug(f"Window too small to be a terminal: {width}x{height}")
                return False
            
            # Process-specific validation
            if process_name == 'WindowsTerminal.exe':
                # Windows Terminal specific validation
                return self._validate_windows_terminal(window_info)
            elif process_name in ['cmd.exe', 'powershell.exe']:
                # Legacy console validation
                return self._validate_legacy_console(window_info)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error validating terminal window: {e}")
            return False

    def _validate_windows_terminal(self, window_info: Dict[str, Any]) -> bool:
        """
        Validate Windows Terminal specific windows.

        Args:
            window_info: Window information dictionary

        Returns:
            True if valid Windows Terminal window, False otherwise
        """
        try:
            # Windows Terminal usually has specific window classes
            window_class = window_info.get('window_class', '')
            valid_classes = ['CASCADIA_HOSTING_WINDOW_CLASS', 'ConsoleWindowClass']
            
            if window_class not in valid_classes:
                self.logger.debug(f"Invalid Windows Terminal window class: {window_class}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error validating Windows Terminal window: {e}")
            return False

    def _validate_legacy_console(self, window_info: Dict[str, Any]) -> bool:
        """
        Validate legacy console windows (cmd.exe, powershell.exe).

        Args:
            window_info: Window information dictionary

        Returns:
            True if valid console window, False otherwise
        """
        try:
            # Legacy consoles typically have ConsoleWindowClass
            window_class = window_info.get('window_class', '')
            
            if window_class != 'ConsoleWindowClass':
                self.logger.debug(f"Invalid console window class: {window_class}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Error validating legacy console window: {e}")
            return False

    def is_window_accessible(self, window_handle: int) -> bool:
        """
        Check if a window is still accessible and valid.

        Args:
            window_handle: Window handle to check

        Returns:
            True if window is accessible, False otherwise
        """
        try:
            # Check if window still exists and is visible
            if not win32gui.IsWindow(window_handle):
                return False
            
            if not win32gui.IsWindowVisible(window_handle):
                return False
            
            # Try to get window text as a basic accessibility test
            try:
                win32gui.GetWindowText(window_handle)
                return True
            except:
                return False
                
        except Exception as e:
            self.logger.debug(f"Error checking window accessibility for {window_handle}: {e}")
            return False

    def get_window_process_name(self, window_handle: int) -> Optional[str]:
        """
        Get the process name for a specific window handle.

        Args:
            window_handle: Window handle to query

        Returns:
            Process name or None if unavailable
        """
        return self._get_process_name(window_handle)

    def get_active_windows_count(self) -> int:
        """
        Get count of currently active monitored windows.

        Returns:
            Number of active windows being monitored
        """
        try:
            current_windows = self.discover_windows()
            return len(current_windows)
        except Exception as e:
            self.logger.error(f"Error getting active windows count: {e}")
            return 0

    def cleanup(self) -> None:
        """Perform cleanup operations for the Window Manager."""
        try:
            # Clear any cached data
            self._window_cache.clear()
            
            self.logger.info("Window Manager cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during Window Manager cleanup: {e}")

    def get_window_details(self, window_handle: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific window.

        Args:
            window_handle: Window handle to query

        Returns:
            Detailed window information dictionary or None
        """
        return self._get_window_info(window_handle)

    def refresh_window_cache(self) -> None:
        """Force refresh of internal window cache."""
        self._window_cache.clear()
        self.logger.debug("Window cache refreshed")

    def set_max_windows(self, max_windows: int) -> None:
        """
        Update the maximum number of windows to monitor.

        Args:
            max_windows: New maximum window count
        """
        if max_windows > 0:
            self.max_windows = max_windows
            self.logger.info(f"Maximum window limit updated to: {max_windows}")
        else:
            self.logger.warning("Invalid max_windows value, keeping current setting")

    def add_target_process(self, process_name: str) -> None:
        """
        Add a new target process to monitor.

        Args:
            process_name: Process executable name to add
        """
        if process_name not in self.target_processes:
            self.target_processes.add(process_name)
            self.logger.info(f"Added target process: {process_name}")
        else:
            self.logger.debug(f"Process already monitored: {process_name}")

    def remove_target_process(self, process_name: str) -> None:
        """
        Remove a target process from monitoring.

        Args:
            process_name: Process executable name to remove
        """
        if process_name in self.target_processes:
            self.target_processes.remove(process_name)
            self.logger.info(f"Removed target process: {process_name}")
        else:
            self.logger.debug(f"Process not in target list: {process_name}")

    def get_target_processes(self) -> Set[str]:
        """
        Get the current set of target processes.

        Returns:
            Set of target process names
        """
        return self.target_processes.copy()
