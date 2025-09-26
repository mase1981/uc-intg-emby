"""
Configuration management for Emby integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import json
import logging
import os
from typing import Any

_LOG = logging.getLogger(__name__)


class Config:
    """Configuration management for Emby integration with reboot survival support."""

    def __init__(self, config_dir_path: str = None):
        """Initialize configuration manager."""
        self._config_dir_path = config_dir_path or os.getenv("UC_CONFIG_HOME", ".")
        self._config_file_path = os.path.join(self._config_dir_path, "config.json")
        self._config: dict[str, Any] = {}
        
        # Create config directory if it doesn't exist
        os.makedirs(self._config_dir_path, exist_ok=True)
        
        # Load existing configuration
        self.reload_from_disk()

    def reload_from_disk(self) -> bool:

        try:
            if os.path.exists(self._config_file_path):
                with open(self._config_file_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                    _LOG.info("Configuration reloaded from disk")
                    return True
            else:
                _LOG.info("No existing configuration file found")
                self._config = {}
                return False
        except Exception as e:
            _LOG.error("Failed to reload configuration from disk: %s", e)
            self._config = {}
            return False

    def save_to_disk(self) -> bool:

        try:
            with open(self._config_file_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
            _LOG.info("Configuration saved to disk")
            return True
        except Exception as e:
            _LOG.error("Failed to save configuration to disk: %s", e)
            return False

    def update_config(self, config: dict[str, Any]) -> bool:

        try:
            self._config.update(config)
            return self.save_to_disk()
        except Exception as e:
            _LOG.error("Failed to update configuration: %s", e)
            return False

    def is_configured(self) -> bool:
        """Check if integration is properly configured."""
        return bool(
            self.server_url 
            and self.api_key
            and self.server_url.startswith(("http://", "https://"))
        )

    @property
    def server_url(self) -> str:
        """Get server URL."""
        return self._config.get("server_url", "")

    @property
    def api_key(self) -> str:
        """Get API key."""
        return self._config.get("api_key", "")

    @property
    def user_id(self) -> str:
        """Get user ID (optional)."""
        return self._config.get("user_id", "")

    @property
    def config_dict(self) -> dict[str, Any]:
        """Get complete configuration as dictionary."""
        return self._config.copy()

    def clear_config(self):
        """Clear all configuration."""
        self._config = {}
        try:
            if os.path.exists(self._config_file_path):
                os.remove(self._config_file_path)
                _LOG.info("Configuration file removed")
        except Exception as e:
            _LOG.error("Failed to remove configuration file: %s", e)