"""
Keystroke Sender Module

Handles automated keystroke injection to terminal windows
with retry logic, error handling, and process-specific customization.

Author: dbbuilder
License: MIT
"""

import time
import logging
from typing import Dict, Any, Optional, List
from pywinauto.application import Application
from pywinauto import keyboard


class KeystrokeSender:
    """
    Manages automated keystroke sending to terminal windows.
    
    Provides reliable keystroke injection with retry mechanisms,
    process-specific customization, and comprehensive error handling.
    """

    def __init__(self, default_keys: str = "continue{ENTER}", 
                 process_overrides: Dict[str, Any] = None, 
                 retry_config: Dict[str, Any] = None):
        """
        Initialize the Keystroke Sender.

        Args:
            default_keys: Default keystroke sequence to send
            process_overrides: Process-specific keystroke configurations
            retry_config: Configuration for retry behavior
        """
        self.default_keys = default_keys
        self.process_overrides = process_overrides or {}
        self.logger = logging.getLogger(__name__)
        
        # Configure retry behavior
        retry_config = retry_config or {}
        self.retry_attempts = retry_config.get('retry_attempts', 3)
        self.retry_delay = retry_config.get('retry_delay', 1)
        self.operation_timeout = retry_config.get('window_operation_timeout', 5)
        
        # Statistics tracking
        self.statistics = {
            'total_attempts': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'retry_count': 0,
            'average_send_time': 0.0
        }
        
        # Cache for application connections
        self._app_cache = {}
        self._cache_timeout = 30  # Seconds
        
        self.logger.info(
            f"Keystroke Sender initialized - default keys: '{default_keys}', "
            f"retry attempts: {self.retry_attempts}, timeout: {self.operation_timeout}s"
        )

    def send_keystrokes(self, window_handle: int, process_name: str = None) -> bool:
        """
        Send keystrokes to a specific terminal window.

        Args:
            window_handle: Window handle to send keystrokes to
            process_name: Optional process name for customization

        Returns:
            True if keystrokes were sent successfully, False otherwise
        """
        try:
            start_time = time.time()
            self.statistics['total_attempts'] += 1
            
            # Get keystroke sequence for this process
            keystroke_sequence = self._get_keystroke_sequence(process_name)
            
            # Attempt to send keystrokes with retry logic
            success = self._send_with_retry(window_handle, keystroke_sequence, process_name)
            
            # Update statistics
            send_time = time.time() - start_time
            self._update_send_statistics(success, send_time)
            
            if success:
                self.logger.debug(
                    f"Successfully sent '{keystroke_sequence}' to {process_name or 'unknown'} "
                    f"(HWND: {window_handle}) in {send_time:.2f}s"
                )
            else:
                self.logger.warning(
                    f"Failed to send keystrokes to {process_name or 'unknown'} "
                    f"(HWND: {window_handle}) after {self.retry_attempts + 1} attempts"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending keystrokes to window {window_handle}: {e}")
            self.statistics['failed_sends'] += 1
            return False

    def _get_keystroke_sequence(self, process_name: str = None) -> str:
        """
        Get the appropriate keystroke sequence for a process.

        Args:
            process_name: Optional process name for override lookup

        Returns:
            Keystroke sequence string
        """
        try:
            # Check for process-specific override
            if process_name and process_name in self.process_overrides:
                override_keys = self.process_overrides[process_name].get('keys_to_send')
                if override_keys:
                    return override_keys
            
            # Return default keystroke sequence
            return self.default_keys
            
        except Exception as e:
            self.logger.debug(f"Error getting keystroke sequence for {process_name}: {e}")
            return self.default_keys

    def _send_with_retry(self, window_handle: int, keystroke_sequence: str, 
                        process_name: str = None) -> bool:
        """
        Send keystrokes with retry logic for improved reliability.

        Args:
            window_handle: Window handle to send keystrokes to
            keystroke_sequence: Keystroke sequence to send
            process_name: Optional process name for logging

        Returns:
            True if keystrokes were sent successfully, False otherwise
        """
        last_exception = None
        
        for attempt in range(self.retry_attempts + 1):
            try:
                if attempt > 0:
                    self.statistics['retry_count'] += 1
                    self.logger.debug(
                        f"Retry attempt {attempt} for window {window_handle}"
                    )
                    # Wait before retry
                    time.sleep(self.retry_delay)
                
                # Attempt to send keystrokes
                if self._send_keystrokes_direct(window_handle, keystroke_sequence):
                    return True
                    
            except Exception as e:
                last_exception = e
                self.logger.debug(
                    f"Keystroke send attempt {attempt + 1} failed for window {window_handle}: {e}"
                )
                
                # Clean up potentially stale cache entry
                self._invalidate_cache_entry(window_handle)
        
        # All attempts failed
        if last_exception:
            self.logger.debug(f"All keystroke attempts failed: {last_exception}")
        
        return False

    def _send_keystrokes_direct(self, window_handle: int, keystroke_sequence: str) -> bool:
        """
        Send keystrokes directly to a window using UI Automation.

        Args:
            window_handle: Window handle to send keystrokes to
            keystroke_sequence: Keystroke sequence to send

        Returns:
            True if keystrokes were sent successfully, False otherwise
        """
        try:
            # Get or create application connection
            app = self._get_application_connection(window_handle)
            if not app:
                return False
            
            # Get the window object
            window = app.window(handle=window_handle)
            
            # Verify window is accessible
            if not window.exists(timeout=1):
                self.logger.debug(f"Window {window_handle} no longer exists")
                return False
            
            # Focus the window before sending keystrokes
            try:
                window.set_focus()
                time.sleep(0.1)  # Brief delay for focus to take effect
            except Exception as e:
                self.logger.debug(f"Could not focus window {window_handle}: {e}")
                # Continue anyway - focus may not be critical
            
            # Send the keystroke sequence
            window.type_keys(keystroke_sequence, with_spaces=True)
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Direct keystroke send failed for window {window_handle}: {e}")
            return False

    def _get_application_connection(self, window_handle: int) -> Optional[Application]:
        """
        Get or create a cached application connection for a window.

        Args:
            window_handle: Window handle to connect to

        Returns:
            Application object or None if connection fails
        """
        try:
            current_time = time.time()
            
            # Check for valid cached connection
            if window_handle in self._app_cache:
                cache_entry = self._app_cache[window_handle]
                
                # Validate cache entry age
                if current_time - cache_entry['timestamp'] < self._cache_timeout:
                    try:
                        # Test if connection is still valid
                        app = cache_entry['app']
                        app.window(handle=window_handle).exists(timeout=0.1)
                        return app
                    except:
                        # Connection is stale, remove from cache
                        del self._app_cache[window_handle]
            
            # Create new connection
            app = Application(backend="uia").connect(
                handle=window_handle, 
                timeout=self.operation_timeout
            )
            
            # Cache the connection
            self._app_cache[window_handle] = {
                'app': app,
                'timestamp': current_time
            }
            
            return app
            
        except Exception as e:
            self.logger.debug(f"Failed to connect to window {window_handle}: {e}")
            return None

    def _update_send_statistics(self, success: bool, send_time: float) -> None:
        """
        Update keystroke sending statistics.

        Args:
            success: Whether the send operation was successful
            send_time: Time taken for the send operation
        """
        try:
            if success:
                self.statistics['successful_sends'] += 1
            else:
                self.statistics['failed_sends'] += 1
            
            # Update average send time
            total_attempts = self.statistics['total_attempts']
            current_avg = self.statistics['average_send_time']
            
            if total_attempts > 1:
                new_avg = ((current_avg * (total_attempts - 1)) + send_time) / total_attempts
                self.statistics['average_send_time'] = new_avg
            else:
                self.statistics['average_send_time'] = send_time
                
        except Exception as e:
            self.logger.debug(f"Error updating send statistics: {e}")

    def _invalidate_cache_entry(self, window_handle: int) -> None:
        """
        Remove a specific window handle from the application cache.

        Args:
            window_handle: Window handle to remove from cache
        """
        try:
            if window_handle in self._app_cache:
                del self._app_cache[window_handle]
                self.logger.debug(f"Invalidated cache entry for window {window_handle}")
        except Exception as e:
            self.logger.debug(f"Error invalidating cache entry: {e}")

    def test_keystroke_send(self, window_handle: int, test_sequence: str = None) -> Dict[str, Any]:
        """
        Test keystroke sending to a specific window with diagnostic information.

        Args:
            window_handle: Window handle to test
            test_sequence: Optional test keystroke sequence (defaults to configured sequence)

        Returns:
            Dictionary containing test results and diagnostic information
        """
        test_results = {
            'window_handle': window_handle,
            'test_sequence': test_sequence or self.default_keys,
            'success': False,
            'send_time': 0,
            'attempts_made': 0,
            'error_messages': [],
            'connection_successful': False,
            'window_accessible': False
        }
        
        try:
            start_time = time.time()
            keystroke_sequence = test_sequence or self.default_keys
            
            # Test application connection
            app = self._get_application_connection(window_handle)
            test_results['connection_successful'] = app is not None
            
            if app:
                # Test window accessibility
                try:
                    window = app.window(handle=window_handle)
                    test_results['window_accessible'] = window.exists(timeout=1)
                except Exception as e:
                    test_results['error_messages'].append(f"Window access error: {e}")
            
            # Attempt keystroke send
            if test_results['connection_successful'] and test_results['window_accessible']:
                test_results['success'] = self._send_keystrokes_direct(window_handle, keystroke_sequence)
                test_results['attempts_made'] = 1
            
            test_results['send_time'] = time.time() - start_time
            
        except Exception as e:
            test_results['error_messages'].append(f"Test error: {e}")
        
        return test_results

    def send_custom_keystrokes(self, window_handle: int, custom_sequence: str) -> bool:
        """
        Send a custom keystroke sequence to a window.

        Args:
            window_handle: Window handle to send keystrokes to
            custom_sequence: Custom keystroke sequence to send

        Returns:
            True if keystrokes were sent successfully, False otherwise
        """
        try:
            self.logger.info(
                f"Sending custom keystrokes '{custom_sequence}' to window {window_handle}"
            )
            
            # Use the retry mechanism with the custom sequence
            success = self._send_with_retry(window_handle, custom_sequence)
            
            if success:
                self.logger.info(f"Custom keystrokes sent successfully to window {window_handle}")
            else:
                self.logger.warning(f"Failed to send custom keystrokes to window {window_handle}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending custom keystrokes: {e}")
            return False

    def validate_keystroke_sequence(self, keystroke_sequence: str) -> Dict[str, Any]:
        """
        Validate a keystroke sequence format.

        Args:
            keystroke_sequence: Keystroke sequence to validate

        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'parsed_keys': []
        }
        
        try:
            if not keystroke_sequence:
                validation_result['is_valid'] = False
                validation_result['errors'].append("Empty keystroke sequence")
                return validation_result
            
            # Check for common special key patterns
            special_keys = [
                '{ENTER}', '{TAB}', '{SPACE}', '{BACKSPACE}', '{DELETE}',
                '{HOME}', '{END}', '{UP}', '{DOWN}', '{LEFT}', '{RIGHT}',
                '{CTRL}', '{ALT}', '{SHIFT}', '{ESC}', '{F1}', '{F2}', '{F3}',
                '{F4}', '{F5}', '{F6}', '{F7}', '{F8}', '{F9}', '{F10}',
                '{F11}', '{F12}'
            ]
            
            # Parse the sequence
            parts = []
            current_part = ""
            in_special_key = False
            
            for char in keystroke_sequence:
                if char == '{':
                    if in_special_key:
                        validation_result['warnings'].append("Nested braces detected")
                    if current_part:
                        parts.append(current_part)
                        current_part = ""
                    current_part = char
                    in_special_key = True
                elif char == '}' and in_special_key:
                    current_part += char
                    parts.append(current_part)
                    current_part = ""
                    in_special_key = False
                else:
                    current_part += char
            
            if current_part:
                parts.append(current_part)
            
            if in_special_key:
                validation_result['warnings'].append("Unclosed special key sequence")
            
            validation_result['parsed_keys'] = parts
            
            # Check for recognized special keys
            for part in parts:
                if part.startswith('{') and part.endswith('}'):
                    if part.upper() not in special_keys:
                        validation_result['warnings'].append(f"Unrecognized special key: {part}")
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {e}")
        
        return validation_result

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get keystroke sending statistics.

        Returns:
            Dictionary containing statistics
        """
        try:
            total_attempts = self.statistics['total_attempts']
            success_rate = 0.0
            
            if total_attempts > 0:
                success_rate = (self.statistics['successful_sends'] / total_attempts) * 100
            
            return {
                'total_attempts': total_attempts,
                'successful_sends': self.statistics['successful_sends'],
                'failed_sends': self.statistics['failed_sends'],
                'retry_count': self.statistics['retry_count'],
                'success_rate_percent': success_rate,
                'average_send_time_seconds': self.statistics['average_send_time'],
                'cache_entries': len(self._app_cache),
                'retry_attempts_configured': self.retry_attempts,
                'retry_delay_seconds': self.retry_delay,
                'operation_timeout_seconds': self.operation_timeout
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}

    def cleanup_cache(self) -> None:
        """Clean up expired cache entries and release resources."""
        try:
            current_time = time.time()
            expired_handles = []
            
            # Find expired cache entries
            for window_handle, cache_entry in self._app_cache.items():
                if current_time - cache_entry['timestamp'] > self._cache_timeout:
                    expired_handles.append(window_handle)
            
            # Remove expired entries
            for handle in expired_handles:
                try:
                    del self._app_cache[handle]
                except KeyError:
                    pass  # Entry already removed
            
            if expired_handles:
                self.logger.debug(f"Cleaned up {len(expired_handles)} expired cache entries")
                
        except Exception as e:
            self.logger.debug(f"Error during cache cleanup: {e}")

    def clear_cache(self) -> None:
        """Clear all cached application connections."""
        try:
            cache_count = len(self._app_cache)
            self._app_cache.clear()
            
            if cache_count > 0:
                self.logger.debug(f"Cleared {cache_count} cached application connections")
                
        except Exception as e:
            self.logger.debug(f"Error clearing cache: {e}")

    def update_configuration(self, new_config: Dict[str, Any]) -> None:
        """
        Update keystroke sender configuration.

        Args:
            new_config: Dictionary containing configuration updates
        """
        try:
            # Update default keys if provided
            if 'default_keys' in new_config:
                self.default_keys = new_config['default_keys']
                self.logger.info(f"Updated default keys: '{self.default_keys}'")
            
            # Update process overrides if provided
            if 'process_overrides' in new_config:
                self.process_overrides.update(new_config['process_overrides'])
                self.logger.info("Updated process overrides")
            
            # Update retry configuration if provided
            retry_config = new_config.get('retry_config', {})
            if 'retry_attempts' in retry_config:
                self.retry_attempts = retry_config['retry_attempts']
                self.logger.info(f"Updated retry attempts: {self.retry_attempts}")
            
            if 'retry_delay' in retry_config:
                self.retry_delay = retry_config['retry_delay']
                self.logger.info(f"Updated retry delay: {self.retry_delay}s")
            
            if 'window_operation_timeout' in retry_config:
                self.operation_timeout = retry_config['window_operation_timeout']
                self.logger.info(f"Updated operation timeout: {self.operation_timeout}s")
                
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")

    def get_process_keystrokes(self, process_name: str) -> str:
        """
        Get the keystroke sequence configured for a specific process.

        Args:
            process_name: Process name to query

        Returns:
            Keystroke sequence for the process
        """
        return self._get_keystroke_sequence(process_name)

    def set_process_keystrokes(self, process_name: str, keystroke_sequence: str) -> bool:
        """
        Set a custom keystroke sequence for a specific process.

        Args:
            process_name: Process name to configure
            keystroke_sequence: Keystroke sequence to set

        Returns:
            True if configuration was updated successfully, False otherwise
        """
        try:
            # Validate the keystroke sequence
            validation = self.validate_keystroke_sequence(keystroke_sequence)
            if not validation['is_valid']:
                self.logger.error(f"Invalid keystroke sequence for {process_name}: {validation['errors']}")
                return False
            
            # Log any warnings
            for warning in validation['warnings']:
                self.logger.warning(f"Keystroke sequence warning for {process_name}: {warning}")
            
            # Update process override
            if process_name not in self.process_overrides:
                self.process_overrides[process_name] = {}
            
            self.process_overrides[process_name]['keys_to_send'] = keystroke_sequence
            
            self.logger.info(f"Set keystroke sequence for {process_name}: '{keystroke_sequence}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting keystroke sequence for {process_name}: {e}")
            return False

    def cleanup(self) -> None:
        """Perform cleanup operations for the Keystroke Sender."""
        try:
            # Log final statistics
            final_stats = self.get_statistics()
            self.logger.info(f"Keystroke Sender cleanup - Final statistics: {final_stats}")
            
            # Clear application cache
            self.clear_cache()
            
            self.logger.info("Keystroke Sender cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during Keystroke Sender cleanup: {e}")
