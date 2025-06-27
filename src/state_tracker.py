"""
State Tracker Module

Manages window state tracking, inactivity detection, and timing
for terminal monitoring operations.

Author: dbbuilder
License: MIT
"""

import time
import hashlib
import logging
from typing import Dict, Any, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class WindowState:
    """Data class representing the state of a monitored window."""
    window_handle: int
    process_name: str
    text_hash: str
    last_change_time: float
    creation_time: float
    inactivity_threshold: float
    change_count: int = 0
    last_action_time: Optional[float] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateTracker:
    """
    Tracks state and activity for monitored terminal windows.
    
    Manages window state information, detects inactivity periods,
    and provides timing and activity analysis functionality.
    """

    def __init__(self, inactivity_threshold: float = 30, 
                 process_overrides: Dict[str, Any] = None, 
                 max_windows: int = 50):
        """
        Initialize the State Tracker.

        Args:
            inactivity_threshold: Default inactivity threshold in seconds
            process_overrides: Process-specific configuration overrides
            max_windows: Maximum number of windows to track
        """
        self.default_inactivity_threshold = inactivity_threshold
        self.process_overrides = process_overrides or {}
        self.max_windows = max_windows
        self.logger = logging.getLogger(__name__)
        
        # Window state storage
        self.window_states: Dict[int, WindowState] = {}
        
        # Statistics and metrics
        self.statistics = {
            'total_windows_tracked': 0,
            'total_state_updates': 0,
            'total_inactivity_events': 0,
            'average_activity_duration': 0.0,
            'startup_time': time.time()
        }
        
        # Performance monitoring
        self._performance_metrics = defaultdict(list)
        
        self.logger.info(
            f"State Tracker initialized - default threshold: {inactivity_threshold}s, "
            f"max windows: {max_windows}"
        )

    def update_window_state(self, window_handle: int, text_content: str, 
                          process_name: str) -> Dict[str, Any]:
        """
        Update the state for a window based on new text content.

        Args:
            window_handle: Window handle identifier
            text_content: Current text content from the window
            process_name: Name of the process (executable)

        Returns:
            Dictionary containing update results and activity status
        """
        try:
            current_time = time.time()
            text_hash = self._compute_text_hash(text_content)
            
            # Initialize tracking for new windows
            if window_handle not in self.window_states:
                return self._initialize_new_window(
                    window_handle, text_hash, process_name, current_time
                )
            
            # Update existing window state
            return self._update_existing_window(
                window_handle, text_hash, current_time
            )
            
        except Exception as e:
            self.logger.error(f"Error updating window state for {window_handle}: {e}")
            return {
                'is_new_window': False,
                'text_changed': False,
                'is_inactive': False,
                'inactivity_duration': 0,
                'error': str(e)
            }

    def _initialize_new_window(self, window_handle: int, text_hash: str, 
                             process_name: str, current_time: float) -> Dict[str, Any]:
        """
        Initialize state tracking for a new window.

        Args:
            window_handle: Window handle identifier
            text_hash: Hash of initial text content
            process_name: Name of the process
            current_time: Current timestamp

        Returns:
            Dictionary containing initialization results
        """
        try:
            # Check if we've reached the maximum window limit
            if len(self.window_states) >= self.max_windows:
                self.logger.warning(
                    f"Maximum window limit ({self.max_windows}) reached. "
                    f"Cannot track new window {window_handle}"
                )
                return {
                    'is_new_window': False,
                    'text_changed': False,
                    'is_inactive': False,
                    'inactivity_duration': 0,
                    'error': 'Maximum window limit reached'
                }
            
            # Get process-specific inactivity threshold
            inactivity_threshold = self._get_inactivity_threshold(process_name)
            
            # Create new window state
            window_state = WindowState(
                window_handle=window_handle,
                process_name=process_name,
                text_hash=text_hash,
                last_change_time=current_time,
                creation_time=current_time,
                inactivity_threshold=inactivity_threshold,
                change_count=1
            )
            
            # Store the state
            self.window_states[window_handle] = window_state
            
            # Update statistics
            self.statistics['total_windows_tracked'] += 1
            self.statistics['total_state_updates'] += 1
            
            self.logger.info(
                f"New window tracking initialized: {process_name} "
                f"(HWND: {window_handle}, threshold: {inactivity_threshold}s)"
            )
            
            return {
                'is_new_window': True,
                'text_changed': True,
                'is_inactive': False,
                'inactivity_duration': 0,
                'window_state': window_state
            }
            
        except Exception as e:
            self.logger.error(f"Error initializing new window {window_handle}: {e}")
            return {
                'is_new_window': False,
                'text_changed': False,
                'is_inactive': False,
                'inactivity_duration': 0,
                'error': str(e)
            }

    def _update_existing_window(self, window_handle: int, text_hash: str, 
                              current_time: float) -> Dict[str, Any]:
        """
        Update state for an existing window.

        Args:
            window_handle: Window handle identifier
            text_hash: Hash of current text content
            current_time: Current timestamp

        Returns:
            Dictionary containing update results
        """
        try:
            window_state = self.window_states[window_handle]
            text_changed = text_hash != window_state.text_hash
            
            # Update state based on text changes
            if text_changed:
                # Text has changed - reset activity timer
                window_state.text_hash = text_hash
                window_state.last_change_time = current_time
                window_state.change_count += 1
                window_state.is_active = True
                
                self.logger.debug(
                    f"Activity detected in {window_state.process_name} "
                    f"(HWND: {window_handle})"
                )
            
            # Calculate inactivity duration
            inactivity_duration = current_time - window_state.last_change_time
            is_inactive = inactivity_duration >= window_state.inactivity_threshold
            
            # Update statistics
            self.statistics['total_state_updates'] += 1
            
            # Log inactivity detection
            if is_inactive and window_state.is_active:
                self.statistics['total_inactivity_events'] += 1
                self.logger.debug(
                    f"Inactivity detected: {window_state.process_name} "
                    f"(HWND: {window_handle}) idle for {inactivity_duration:.1f}s"
                )
            
            return {
                'is_new_window': False,
                'text_changed': text_changed,
                'is_inactive': is_inactive,
                'inactivity_duration': inactivity_duration,
                'window_state': window_state
            }
            
        except Exception as e:
            self.logger.error(f"Error updating existing window {window_handle}: {e}")
            return {
                'is_new_window': False,
                'text_changed': False,
                'is_inactive': False,
                'inactivity_duration': 0,
                'error': str(e)
            }

    def _compute_text_hash(self, text_content: str) -> str:
        """
        Compute SHA-256 hash of text content for efficient comparison.

        Args:
            text_content: Text content to hash

        Returns:
            SHA-256 hash as hexadecimal string
        """
        try:
            if not text_content:
                return ""
            
            # Use UTF-8 encoding for consistent hashing
            text_bytes = text_content.encode('utf-8')
            hash_object = hashlib.sha256(text_bytes)
            return hash_object.hexdigest()
            
        except Exception as e:
            self.logger.debug(f"Error computing text hash: {e}")
            return ""

    def _get_inactivity_threshold(self, process_name: str) -> float:
        """
        Get inactivity threshold for a specific process.

        Args:
            process_name: Name of the process

        Returns:
            Inactivity threshold in seconds
        """
        try:
            # Check for process-specific override
            if process_name in self.process_overrides:
                override_threshold = self.process_overrides[process_name].get(
                    'inactivity_threshold_seconds'
                )
                if override_threshold is not None:
                    return float(override_threshold)
            
            # Return default threshold
            return self.default_inactivity_threshold
            
        except Exception as e:
            self.logger.debug(f"Error getting inactivity threshold for {process_name}: {e}")
            return self.default_inactivity_threshold

    def reset_window_timer(self, window_handle: int) -> bool:
        """
        Reset the inactivity timer for a specific window.

        Args:
            window_handle: Window handle to reset

        Returns:
            True if timer was reset successfully, False otherwise
        """
        try:
            if window_handle in self.window_states:
                current_time = time.time()
                window_state = self.window_states[window_handle]
                
                # Reset timing information
                window_state.last_change_time = current_time
                window_state.last_action_time = current_time
                window_state.is_active = True
                
                self.logger.debug(
                    f"Reset inactivity timer for {window_state.process_name} "
                    f"(HWND: {window_handle})"
                )
                
                return True
            else:
                self.logger.warning(f"Cannot reset timer - window {window_handle} not tracked")
                return False
                
        except Exception as e:
            self.logger.error(f"Error resetting timer for window {window_handle}: {e}")
            return False

    def cleanup_closed_windows(self, active_window_handles: Set[int]) -> int:
        """
        Remove tracking for windows that are no longer active.

        Args:
            active_window_handles: Set of currently active window handles

        Returns:
            Number of windows cleaned up
        """
        try:
            # Find windows that are no longer active
            tracked_handles = set(self.window_states.keys())
            closed_handles = tracked_handles - active_window_handles
            
            cleanup_count = 0
            for handle in closed_handles:
                try:
                    window_state = self.window_states[handle]
                    
                    # Log cleanup with duration information
                    duration = time.time() - window_state.creation_time
                    self.logger.info(
                        f"Cleaning up closed window: {window_state.process_name} "
                        f"(HWND: {handle}) - tracked for {duration:.1f}s, "
                        f"{window_state.change_count} changes detected"
                    )
                    
                    # Update average activity duration statistic
                    self._update_activity_duration_statistic(duration)
                    
                    # Remove from tracking
                    del self.window_states[handle]
                    cleanup_count += 1
                    
                except Exception as e:
                    self.logger.debug(f"Error cleaning up window {handle}: {e}")
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} closed windows")
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"Error during window cleanup: {e}")
            return 0

    def _update_activity_duration_statistic(self, duration: float) -> None:
        """
        Update the average activity duration statistic.

        Args:
            duration: Duration of window activity in seconds
        """
        try:
            current_avg = self.statistics['average_activity_duration']
            total_windows = self.statistics['total_windows_tracked']
            
            if total_windows > 1:
                # Calculate running average
                new_avg = ((current_avg * (total_windows - 1)) + duration) / total_windows
                self.statistics['average_activity_duration'] = new_avg
            else:
                self.statistics['average_activity_duration'] = duration
                
        except Exception as e:
            self.logger.debug(f"Error updating activity duration statistic: {e}")

    def get_window_count(self) -> int:
        """
        Get the current number of tracked windows.

        Returns:
            Number of windows currently being tracked
        """
        return len(self.window_states)

    def get_window_state(self, window_handle: int) -> Optional[WindowState]:
        """
        Get the state object for a specific window.

        Args:
            window_handle: Window handle to query

        Returns:
            WindowState object or None if not tracked
        """
        return self.window_states.get(window_handle)

    def get_inactive_windows(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all windows that are currently inactive.

        Returns:
            Dictionary mapping window handles to inactivity information
        """
        inactive_windows = {}
        current_time = time.time()
        
        try:
            for handle, state in self.window_states.items():
                inactivity_duration = current_time - state.last_change_time
                
                if inactivity_duration >= state.inactivity_threshold:
                    inactive_windows[handle] = {
                        'process_name': state.process_name,
                        'inactivity_duration': inactivity_duration,
                        'threshold': state.inactivity_threshold,
                        'change_count': state.change_count,
                        'creation_time': state.creation_time
                    }
            
            return inactive_windows
            
        except Exception as e:
            self.logger.error(f"Error getting inactive windows: {e}")
            return {}

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about state tracking.

        Returns:
            Dictionary containing various statistics
        """
        try:
            current_time = time.time()
            uptime = current_time - self.statistics['startup_time']
            
            # Calculate additional statistics
            active_windows = len(self.window_states)
            inactive_windows = len(self.get_inactive_windows())
            
            # Performance metrics
            avg_update_rate = self.statistics['total_state_updates'] / max(uptime, 1)
            
            return {
                'uptime_seconds': uptime,
                'active_windows': active_windows,
                'inactive_windows': inactive_windows,
                'total_windows_tracked': self.statistics['total_windows_tracked'],
                'total_state_updates': self.statistics['total_state_updates'],
                'total_inactivity_events': self.statistics['total_inactivity_events'],
                'average_activity_duration': self.statistics['average_activity_duration'],
                'average_update_rate': avg_update_rate,
                'default_inactivity_threshold': self.default_inactivity_threshold,
                'max_windows_limit': self.max_windows
            }
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}

    def get_window_details(self) -> Dict[int, Dict[str, Any]]:
        """
        Get detailed information about all tracked windows.

        Returns:
            Dictionary mapping window handles to detailed state information
        """
        window_details = {}
        current_time = time.time()
        
        try:
            for handle, state in self.window_states.items():
                inactivity_duration = current_time - state.last_change_time
                
                window_details[handle] = {
                    'process_name': state.process_name,
                    'creation_time': state.creation_time,
                    'last_change_time': state.last_change_time,
                    'last_action_time': state.last_action_time,
                    'inactivity_duration': inactivity_duration,
                    'inactivity_threshold': state.inactivity_threshold,
                    'change_count': state.change_count,
                    'is_active': state.is_active,
                    'is_currently_inactive': inactivity_duration >= state.inactivity_threshold,
                    'text_hash': state.text_hash[:16] + "..." if state.text_hash else "",
                    'metadata': state.metadata.copy()
                }
            
            return window_details
            
        except Exception as e:
            self.logger.error(f"Error getting window details: {e}")
            return {}

    def update_window_metadata(self, window_handle: int, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a specific window.

        Args:
            window_handle: Window handle to update
            metadata: Metadata dictionary to merge

        Returns:
            True if metadata was updated successfully, False otherwise
        """
        try:
            if window_handle in self.window_states:
                self.window_states[window_handle].metadata.update(metadata)
                return True
            else:
                self.logger.warning(f"Cannot update metadata - window {window_handle} not tracked")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating metadata for window {window_handle}: {e}")
            return False

    def set_window_threshold(self, window_handle: int, threshold: float) -> bool:
        """
        Set a custom inactivity threshold for a specific window.

        Args:
            window_handle: Window handle to update
            threshold: New inactivity threshold in seconds

        Returns:
            True if threshold was updated successfully, False otherwise
        """
        try:
            if window_handle in self.window_states and threshold > 0:
                old_threshold = self.window_states[window_handle].inactivity_threshold
                self.window_states[window_handle].inactivity_threshold = threshold
                
                self.logger.info(
                    f"Updated inactivity threshold for window {window_handle}: "
                    f"{old_threshold}s -> {threshold}s"
                )
                return True
            else:
                self.logger.warning(
                    f"Cannot update threshold - window {window_handle} not tracked "
                    f"or invalid threshold {threshold}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating threshold for window {window_handle}: {e}")
            return False

    def cleanup(self) -> None:
        """Perform cleanup operations for the State Tracker."""
        try:
            # Log final statistics
            final_stats = self.get_statistics()
            self.logger.info(f"State Tracker cleanup - Final statistics: {final_stats}")
            
            # Clear all tracked windows
            self.window_states.clear()
            
            # Reset statistics
            self.statistics = {
                'total_windows_tracked': 0,
                'total_state_updates': 0,
                'total_inactivity_events': 0,
                'average_activity_duration': 0.0,
                'startup_time': time.time()
            }
            
            self.logger.info("State Tracker cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during State Tracker cleanup: {e}")

    def export_state_data(self) -> Dict[str, Any]:
        """
        Export complete state data for backup or analysis.

        Returns:
            Dictionary containing all state data
        """
        try:
            export_data = {
                'export_time': time.time(),
                'statistics': self.statistics.copy(),
                'configuration': {
                    'default_inactivity_threshold': self.default_inactivity_threshold,
                    'max_windows': self.max_windows,
                    'process_overrides': self.process_overrides.copy()
                },
                'window_states': {}
            }
            
            # Export window state data
            for handle, state in self.window_states.items():
                export_data['window_states'][handle] = {
                    'process_name': state.process_name,
                    'creation_time': state.creation_time,
                    'last_change_time': state.last_change_time,
                    'last_action_time': state.last_action_time,
                    'inactivity_threshold': state.inactivity_threshold,
                    'change_count': state.change_count,
                    'is_active': state.is_active,
                    'metadata': state.metadata.copy()
                }
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting state data: {e}")
            return {}
