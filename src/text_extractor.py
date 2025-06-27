"""
Text Extractor Module

Handles extraction of visible text content from terminal windows
using UI Automation with optimization and error handling.

Author: dbbuilder
License: MIT
"""

import hashlib
import logging
import time
from typing import Optional, Dict, Any
from pywinauto.application import Application
from pywinauto import findwindows


class TextExtractor:
    """
    Extracts and processes text content from terminal windows.
    
    Provides optimized text extraction with hash-based change detection,
    error handling, and support for different terminal types.
    """

    def __init__(self, operation_timeout: int = 5, hash_optimization: bool = True, 
                 hash_sample_size: int = 1000):
        """
        Initialize the Text Extractor.

        Args:
            operation_timeout: Timeout for UI operations in seconds
            hash_optimization: Enable hash-based text comparison optimization
            hash_sample_size: Size of text sample for hash calculation (0 = full text)
        """
        self.operation_timeout = operation_timeout
        self.hash_optimization = hash_optimization
        self.hash_sample_size = hash_sample_size
        self.logger = logging.getLogger(__name__)
        
        # Cache for UI Automation connections to improve performance
        self._app_cache = {}
        self._cache_timeout = 30  # Seconds before refreshing cached connections
        
        self.logger.info(
            f"Text Extractor initialized - timeout: {operation_timeout}s, "
            f"hash optimization: {hash_optimization}, sample size: {hash_sample_size}"
        )

    def extract_text(self, window_handle: int) -> Optional[str]:
        """
        Extract visible text content from a terminal window.

        Args:
            window_handle: Window handle to extract text from

        Returns:
            Extracted text content or None if extraction fails
        """
        try:
            start_time = time.time()
            
            # Get cached or create new application connection
            app = self._get_application_connection(window_handle)
            if not app:
                return None
            
            # Extract text using the most appropriate method
            text_content = self._extract_text_from_window(app, window_handle)
            
            # Log performance metrics for debugging
            extraction_time = time.time() - start_time
            if extraction_time > 1.0:  # Log slow extractions
                self.logger.debug(
                    f"Slow text extraction: {extraction_time:.2f}s for window {window_handle}"
                )
            
            return text_content
            
        except Exception as e:
            self.logger.debug(f"Text extraction failed for window {window_handle}: {e}")
            # Clean up potentially stale cache entry
            self._invalidate_cache_entry(window_handle)
            return None

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
            
            # Check if we have a valid cached connection
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

    def _extract_text_from_window(self, app: Application, window_handle: int) -> Optional[str]:
        """
        Extract text from a window using the application connection.

        Args:
            app: Application object connected to the window
            window_handle: Window handle for the terminal

        Returns:
            Extracted text content or None if extraction fails
        """
        try:
            window = app.window(handle=window_handle)
            
            # Try multiple extraction methods in order of preference
            extraction_methods = [
                self._extract_from_terminal_control,
                self._extract_from_edit_control,
                self._extract_from_legacy_properties,
                self._extract_from_window_text
            ]
            
            for method in extraction_methods:
                try:
                    text_content = method(window)
                    if text_content is not None and text_content.strip():
                        return self._process_extracted_text(text_content)
                except Exception as e:
                    self.logger.debug(f"Extraction method {method.__name__} failed: {e}")
                    continue
            
            # If all methods fail, log a warning
            self.logger.debug(f"All text extraction methods failed for window {window_handle}")
            return None
            
        except Exception as e:
            self.logger.debug(f"Error in text extraction process: {e}")
            return None

    def _extract_from_terminal_control(self, window) -> Optional[str]:
        """
        Extract text from Windows Terminal specific controls.

        Args:
            window: Window object to extract text from

        Returns:
            Extracted text or None if method fails
        """
        try:
            # Look for Windows Terminal specific controls
            terminal_controls = [
                ("Terminal", "Pane"),
                ("TerminalTabContent", "Pane"),
                ("TermControl", "Pane")
            ]
            
            for title, control_type in terminal_controls:
                try:
                    terminal_control = window.child_window(title=title, control_type=control_type)
                    if terminal_control.exists(timeout=0.5):
                        # Try to get text through legacy properties first
                        properties = terminal_control.legacy_properties()
                        if 'Value' in properties and properties['Value']:
                            return properties['Value']
                        
                        # Fallback to window text
                        text = terminal_control.window_text()
                        if text:
                            return text
                            
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Terminal control extraction failed: {e}")
            return None

    def _extract_from_edit_control(self, window) -> Optional[str]:
        """
        Extract text from edit controls (common in some terminal configurations).

        Args:
            window: Window object to extract text from

        Returns:
            Extracted text or None if method fails
        """
        try:
            # Look for edit controls that might contain terminal content
            edit_controls = window.children(control_type="Edit")
            
            for edit_control in edit_controls:
                try:
                    # Get text from edit control
                    text = edit_control.window_text()
                    if text and len(text.strip()) > 10:  # Minimum content threshold
                        return text
                        
                    # Try legacy properties for edit controls
                    properties = edit_control.legacy_properties()
                    if 'Value' in properties and properties['Value']:
                        return properties['Value']
                        
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Edit control extraction failed: {e}")
            return None

    def _extract_from_legacy_properties(self, window) -> Optional[str]:
        """
        Extract text using legacy window properties.

        Args:
            window: Window object to extract text from

        Returns:
            Extracted text or None if method fails
        """
        try:
            # Try to get legacy properties from the main window
            properties = window.legacy_properties()
            
            # Check various property keys that might contain text content
            text_properties = ['Value', 'Text', 'Name', 'LegacyIAccessible.Value']
            
            for prop_key in text_properties:
                if prop_key in properties and properties[prop_key]:
                    text_content = properties[prop_key]
                    if len(text_content.strip()) > 5:  # Minimum content check
                        return text_content
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Legacy properties extraction failed: {e}")
            return None

    def _extract_from_window_text(self, window) -> Optional[str]:
        """
        Extract text using basic window text method.

        Args:
            window: Window object to extract text from

        Returns:
            Extracted text or None if method fails
        """
        try:
            # Simple window text extraction as final fallback
            text = window.window_text()
            
            # For terminal windows, window text is often just the title
            # but sometimes contains useful content
            if text and len(text.strip()) > 5:
                return text
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Window text extraction failed: {e}")
            return None

    def _process_extracted_text(self, raw_text: str) -> str:
        """
        Process and clean extracted text content.

        Args:
            raw_text: Raw text content from extraction

        Returns:
            Processed text content
        """
        try:
            # Basic text cleaning and normalization
            processed_text = raw_text
            
            # Remove common control characters and normalize whitespace
            processed_text = processed_text.replace('\r\n', '\n')
            processed_text = processed_text.replace('\r', '\n')
            
            # Remove ANSI escape sequences (color codes, cursor movements, etc.)
            processed_text = self._remove_ansi_sequences(processed_text)
            
            # Limit text size for hash optimization if enabled
            if self.hash_optimization and self.hash_sample_size > 0:
                if len(processed_text) > self.hash_sample_size:
                    # Take sample from the end (most recent content)
                    processed_text = processed_text[-self.hash_sample_size:]
            
            return processed_text
            
        except Exception as e:
            self.logger.debug(f"Error processing extracted text: {e}")
            return raw_text  # Return unprocessed text as fallback

    def _remove_ansi_sequences(self, text: str) -> str:
        """
        Remove ANSI escape sequences from text.

        Args:
            text: Text containing potential ANSI sequences

        Returns:
            Text with ANSI sequences removed
        """
        try:
            import re
            
            # Regular expression to match ANSI escape sequences
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            
            # Remove ANSI sequences
            cleaned_text = ansi_escape.sub('', text)
            
            return cleaned_text
            
        except Exception as e:
            self.logger.debug(f"Error removing ANSI sequences: {e}")
            return text  # Return original text if cleaning fails

    def compute_text_hash(self, text: str) -> str:
        """
        Compute a hash of text content for change detection.

        Args:
            text: Text content to hash

        Returns:
            SHA-256 hash of the text content
        """
        try:
            if not text:
                return ""
            
            # Use UTF-8 encoding for consistent hashing
            text_bytes = text.encode('utf-8')
            
            # Compute SHA-256 hash
            hash_object = hashlib.sha256(text_bytes)
            return hash_object.hexdigest()
            
        except Exception as e:
            self.logger.debug(f"Error computing text hash: {e}")
            return ""

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

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current cache state.

        Returns:
            Dictionary containing cache statistics
        """
        try:
            current_time = time.time()
            active_entries = 0
            expired_entries = 0
            
            for cache_entry in self._app_cache.values():
                if current_time - cache_entry['timestamp'] < self._cache_timeout:
                    active_entries += 1
                else:
                    expired_entries += 1
            
            return {
                'total_entries': len(self._app_cache),
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'cache_timeout': self._cache_timeout
            }
            
        except Exception as e:
            self.logger.debug(f"Error getting cache stats: {e}")
            return {}

    def test_extraction(self, window_handle: int) -> Dict[str, Any]:
        """
        Test text extraction for a specific window and return diagnostic information.

        Args:
            window_handle: Window handle to test

        Returns:
            Dictionary containing test results and diagnostic information
        """
        test_results = {
            'window_handle': window_handle,
            'extraction_successful': False,
            'text_length': 0,
            'extraction_time': 0,
            'methods_tried': [],
            'error_messages': []
        }
        
        try:
            start_time = time.time()
            
            # Attempt text extraction
            extracted_text = self.extract_text(window_handle)
            
            test_results['extraction_time'] = time.time() - start_time
            
            if extracted_text is not None:
                test_results['extraction_successful'] = True
                test_results['text_length'] = len(extracted_text)
                test_results['text_hash'] = self.compute_text_hash(extracted_text)
                test_results['text_preview'] = extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text
            
        except Exception as e:
            test_results['error_messages'].append(str(e))
        
        return test_results

    def set_operation_timeout(self, timeout: int) -> None:
        """
        Update the operation timeout for UI operations.

        Args:
            timeout: New timeout value in seconds
        """
        if timeout > 0:
            self.operation_timeout = timeout
            self.logger.info(f"Operation timeout updated to: {timeout}s")
        else:
            self.logger.warning("Invalid timeout value, keeping current setting")

    def set_hash_sample_size(self, sample_size: int) -> None:
        """
        Update the hash sample size for text processing.

        Args:
            sample_size: New sample size (0 for full text)
        """
        if sample_size >= 0:
            self.hash_sample_size = sample_size
            self.logger.info(f"Hash sample size updated to: {sample_size}")
        else:
            self.logger.warning("Invalid sample size, keeping current setting")
