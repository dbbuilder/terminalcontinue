"""
Configuration Manager Module

Handles loading, validation, and management of application configuration
from YAML files with support for defaults and validation.

Author: dbbuilder
License: MIT
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class ConfigurationManager:
    """
    Manages application configuration loading, validation, and access.
    
    Provides centralized configuration management with support for
    default values, validation, and environment variable overrides.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to configuration file (defaults to config.yaml)
        """
        self.config_path = Path(config_path) if config_path else Path("config.yaml")
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        # Load configuration with fallback to defaults
        self._load_configuration()
        self._validate_configuration()
        self._apply_environment_overrides()

    def _load_configuration(self) -> None:
        """
        Load configuration from file with fallback to defaults.
        
        Raises:
            FileNotFoundError: If configuration file is required but not found
            yaml.YAMLError: If configuration file has invalid YAML syntax
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as config_file:
                    self.config = yaml.safe_load(config_file) or {}
                self.logger.info(f"Configuration loaded from: {self.config_path}")
            else:
                # Check if example configuration exists
                example_path = Path("config.example.yaml")
                if example_path.exists():
                    self.logger.warning(
                        f"Configuration file {self.config_path} not found. "
                        f"Copy {example_path} to {self.config_path} and modify as needed."
                    )
                else:
                    self.logger.warning(f"Configuration file {self.config_path} not found.")
                
                # Use default configuration
                self.config = self._get_default_configuration()
                self.logger.info("Using default configuration")
        
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in configuration file {self.config_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration from {self.config_path}: {e}")
            # Fall back to defaults for robustness
            self.config = self._get_default_configuration()
            self.logger.warning("Using default configuration due to loading error")

    def _get_default_configuration(self) -> Dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Dictionary containing default configuration settings
        """
        return {
            'target_processes': [
                'cmd.exe',
                'powershell.exe',
                'WindowsTerminal.exe'
            ],
            'inactivity_threshold_seconds': 30,
            'keys_to_send': 'continue{ENTER}',
            'polling_interval_seconds': 5,
            'logging': {
                'level': 'INFO',
                'file': {
                    'enabled': True,
                    'path': 'logs/terminal_monitor.log',
                    'max_size_mb': 10,
                    'backup_count': 5
                },
                'console': {
                    'enabled': True,
                    'colored': True
                }
            },
            'advanced': {
                'max_windows': 50,
                'window_operation_timeout': 5,
                'retry_attempts': 3,
                'retry_delay': 1,
                'use_hash_optimization': True,
                'hash_sample_size': 1000
            },
            'process_overrides': {},
            'exclusions': {
                'window_titles': [],
                'command_lines': []
            },
            'notifications': {
                'desktop_notifications': False,
                'email_notifications': False,
                'smtp': {
                    'server': '',
                    'port': 587,
                    'username': '',
                    'password': '',
                    'from_address': '',
                    'to_addresses': []
                }
            },
            'performance': {
                'enabled': True,
                'metrics_interval': 300,
                'cpu_warning_threshold': 10,
                'memory_warning_threshold': 100
            }
        }

    def _validate_configuration(self) -> None:
        """
        Validate configuration values and apply corrections where possible.
        
        Raises:
            ValueError: If critical configuration values are invalid
        """
        try:
            # Validate target processes
            if not isinstance(self.config.get('target_processes'), list):
                self.logger.error("target_processes must be a list")
                raise ValueError("Invalid target_processes configuration")
            
            if not self.config.get('target_processes'):
                self.logger.warning("No target processes specified, using defaults")
                self.config['target_processes'] = self._get_default_configuration()['target_processes']
            
            # Validate timing values
            inactivity_threshold = self.config.get('inactivity_threshold_seconds', 30)
            if not isinstance(inactivity_threshold, (int, float)) or inactivity_threshold <= 0:
                self.logger.warning("Invalid inactivity_threshold_seconds, using default (30)")
                self.config['inactivity_threshold_seconds'] = 30
            
            polling_interval = self.config.get('polling_interval_seconds', 5)
            if not isinstance(polling_interval, (int, float)) or polling_interval <= 0:
                self.logger.warning("Invalid polling_interval_seconds, using default (5)")
                self.config['polling_interval_seconds'] = 5
            
            # Validate keys to send
            if not isinstance(self.config.get('keys_to_send'), str):
                self.logger.warning("Invalid keys_to_send, using default")
                self.config['keys_to_send'] = 'continue{ENTER}'
            
            # Validate advanced settings
            advanced = self.config.setdefault('advanced', {})
            self._validate_advanced_settings(advanced)
            
            # Validate logging configuration
            logging_config = self.config.setdefault('logging', {})
            self._validate_logging_configuration(logging_config)
            
            self.logger.info("Configuration validation completed")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise

    def _validate_advanced_settings(self, advanced: Dict[str, Any]) -> None:
        """
        Validate advanced configuration settings.

        Args:
            advanced: Advanced configuration dictionary to validate
        """
        defaults = self._get_default_configuration()['advanced']
        
        # Validate max_windows
        max_windows = advanced.get('max_windows', defaults['max_windows'])
        if not isinstance(max_windows, int) or max_windows <= 0:
            self.logger.warning("Invalid max_windows, using default")
            advanced['max_windows'] = defaults['max_windows']
        
        # Validate timeouts and attempts
        for key in ['window_operation_timeout', 'retry_attempts', 'retry_delay']:
            value = advanced.get(key, defaults[key])
            if not isinstance(value, (int, float)) or value < 0:
                self.logger.warning(f"Invalid {key}, using default")
                advanced[key] = defaults[key]
        
        # Validate hash settings
        if not isinstance(advanced.get('use_hash_optimization'), bool):
            advanced['use_hash_optimization'] = defaults['use_hash_optimization']
        
        hash_sample_size = advanced.get('hash_sample_size', defaults['hash_sample_size'])
        if not isinstance(hash_sample_size, int) or hash_sample_size < 0:
            advanced['hash_sample_size'] = defaults['hash_sample_size']

    def _validate_logging_configuration(self, logging_config: Dict[str, Any]) -> None:
        """
        Validate logging configuration settings.

        Args:
            logging_config: Logging configuration dictionary to validate
        """
        defaults = self._get_default_configuration()['logging']
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if logging_config.get('level', '').upper() not in valid_levels:
            logging_config['level'] = defaults['level']
        
        # Validate file logging configuration
        file_config = logging_config.setdefault('file', defaults['file'])
        if not isinstance(file_config.get('enabled'), bool):
            file_config['enabled'] = defaults['file']['enabled']
        
        if not isinstance(file_config.get('path'), str):
            file_config['path'] = defaults['file']['path']
        
        # Validate console logging configuration
        console_config = logging_config.setdefault('console', defaults['console'])
        if not isinstance(console_config.get('enabled'), bool):
            console_config['enabled'] = defaults['console']['enabled']
        
        if not isinstance(console_config.get('colored'), bool):
            console_config['colored'] = defaults['console']['colored']

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        try:
            # Check for common environment variable overrides
            env_overrides = {
                'TERMINAL_MONITOR_LOG_LEVEL': ['logging', 'level'],
                'TERMINAL_MONITOR_POLLING_INTERVAL': ['polling_interval_seconds'],
                'TERMINAL_MONITOR_INACTIVITY_THRESHOLD': ['inactivity_threshold_seconds']
            }
            
            for env_var, config_path in env_overrides.items():
                env_value = os.environ.get(env_var)
                if env_value:
                    try:
                        # Attempt to convert to appropriate type
                        if config_path[-1] in ['polling_interval_seconds', 'inactivity_threshold_seconds']:
                            env_value = float(env_value)
                        
                        # Apply override
                        if len(config_path) == 1:
                            self.config[config_path[0]] = env_value
                        else:
                            self.config.setdefault(config_path[0], {})[config_path[1]] = env_value
                        
                        self.logger.info(f"Applied environment override: {env_var}={env_value}")
                        
                    except ValueError:
                        self.logger.warning(f"Invalid environment variable value: {env_var}={env_value}")
        
        except Exception as e:
            self.logger.warning(f"Error applying environment overrides: {e}")

    def get_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()

    def get_target_processes(self) -> List[str]:
        """
        Get the list of target process names to monitor.

        Returns:
            List of executable names to monitor
        """
        return self.config.get('target_processes', [])

    def get_inactivity_threshold(self, process_name: str = None) -> float:
        """
        Get inactivity threshold for a specific process or default.

        Args:
            process_name: Optional process name for override lookup

        Returns:
            Inactivity threshold in seconds
        """
        if process_name:
            overrides = self.config.get('process_overrides', {})
            if process_name in overrides:
                return overrides[process_name].get(
                    'inactivity_threshold_seconds',
                    self.config.get('inactivity_threshold_seconds', 30)
                )
        
        return self.config.get('inactivity_threshold_seconds', 30)

    def get_keys_to_send(self, process_name: str = None) -> str:
        """
        Get keystroke sequence for a specific process or default.

        Args:
            process_name: Optional process name for override lookup

        Returns:
            Keystroke sequence string
        """
        if process_name:
            overrides = self.config.get('process_overrides', {})
            if process_name in overrides:
                return overrides[process_name].get(
                    'keys_to_send',
                    self.config.get('keys_to_send', 'continue{ENTER}')
                )
        
        return self.config.get('keys_to_send', 'continue{ENTER}')

    def get_polling_interval(self) -> float:
        """
        Get polling interval in seconds.

        Returns:
            Polling interval in seconds
        """
        return self.config.get('polling_interval_seconds', 5)

    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.

        Returns:
            Logging configuration dictionary
        """
        return self.config.get('logging', {})

    def get_advanced_config(self) -> Dict[str, Any]:
        """
        Get advanced configuration settings.

        Returns:
            Advanced configuration dictionary
        """
        return self.config.get('advanced', {})

    def get_exclusions(self) -> Dict[str, List[str]]:
        """
        Get exclusion rules for window monitoring.

        Returns:
            Dictionary containing exclusion rules
        """
        return self.config.get('exclusions', {})

    def reload_configuration(self) -> bool:
        """
        Reload configuration from file.

        Returns:
            True if configuration was successfully reloaded, False otherwise
        """
        try:
            old_config = self.config.copy()
            self._load_configuration()
            self._validate_configuration()
            self._apply_environment_overrides()
            
            self.logger.info("Configuration reloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            self.config = old_config  # Restore previous configuration
            return False

    def save_configuration(self, new_config_path: Optional[str] = None) -> bool:
        """
        Save current configuration to file.

        Args:
            new_config_path: Optional path for saving configuration

        Returns:
            True if configuration was successfully saved, False otherwise
        """
        try:
            save_path = Path(new_config_path) if new_config_path else self.config_path
            
            with open(save_path, 'w', encoding='utf-8') as config_file:
                yaml.dump(self.config, config_file, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False

    def update_configuration(self, updates: Dict[str, Any]) -> bool:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary containing configuration updates

        Returns:
            True if configuration was successfully updated, False otherwise
        """
        try:
            # Create a deep copy for validation
            test_config = self.config.copy()
            test_config.update(updates)
            
            # Temporarily update configuration for validation
            old_config = self.config
            self.config = test_config
            
            try:
                self._validate_configuration()
                self.logger.info("Configuration updated successfully")
                return True
            except Exception as e:
                self.config = old_config  # Restore on validation failure
                self.logger.error(f"Configuration update failed validation: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
