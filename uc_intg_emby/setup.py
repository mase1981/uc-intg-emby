"""
Setup flow handler for Emby integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

import ucapi
from uc_intg_emby.client import EmbyClient
from uc_intg_emby.config import Config

_LOG = logging.getLogger(__name__)


class EmbySetupHandler:
    """Handles the setup flow for Emby integration."""

    def __init__(self, config: Config):
        """Initialize setup handler."""
        self._config = config

    async def handle_setup(self, msg: ucapi.SetupDriver) -> ucapi.SetupAction:

        _LOG.info(f"Handling setup message: {type(msg)}")
        
        if isinstance(msg, ucapi.DriverSetupRequest):
            return await self._handle_driver_setup_request(msg)
        elif isinstance(msg, ucapi.UserDataResponse):
            return await self._handle_user_data_response(msg)
        elif isinstance(msg, ucapi.AbortDriverSetup):
            return await self._handle_setup_abort(msg)
        else:
            _LOG.warning(f"Unknown setup message type: {type(msg)}")
            return ucapi.SetupError()

    async def _handle_driver_setup_request(self, msg: ucapi.DriverSetupRequest) -> ucapi.SetupAction:
        """Handle initial setup request."""
        _LOG.info("Starting Emby integration setup")
        
        # Check if this is a reconfiguration with existing data
        if hasattr(msg, 'setup_data') and msg.setup_data:
            _LOG.info("Setup data provided directly, processing...")
            return await self._process_setup_data(msg.setup_data)
        
        # Check if this is a reconfiguration
        if msg.reconfigure and self._config.is_configured():
            _LOG.info("Reconfiguring existing Emby integration")
        
        # Request user input for Emby server details
        return ucapi.RequestUserInput(
            title={"en": "Emby Server Configuration"},
            settings=[
                {
                    "id": "server_url",
                    "label": {"en": "Server URL"},
                    "field": {
                        "text": {
                            "value": self._config.server_url or "http://",
                            "regex": r"^https?://.*",
                            "placeholder": "http://192.168.1.100:8096"
                        }
                    }
                },
                {
                    "id": "api_key", 
                    "label": {"en": "API Key"},
                    "field": {
                        "text": {
                            "value": self._config.api_key or "",
                            "regex": r"^[a-fA-F0-9]{32}$"
                        }
                    }
                },
                {
                    "id": "user_id",
                    "label": {"en": "User ID (optional)"},
                    "field": {
                        "text": {
                            "value": self._config.user_id or ""
                        }
                    }
                }
            ]
        )

    async def _handle_user_data_response(self, msg: ucapi.UserDataResponse) -> ucapi.SetupAction:
        """Handle user input response."""
        _LOG.info("Processing user configuration input")
        return await self._process_setup_data(msg.input_values)

    async def _process_setup_data(self, input_values: dict[str, Any]) -> ucapi.SetupAction:
        """Process setup data from user input or direct setup."""
        _LOG.info(f"Processing setup data: {list(input_values.keys())}")
        
        # Extract configuration values
        server_url = input_values.get("server_url", "").strip()
        api_key = input_values.get("api_key", "").strip()
        user_id = input_values.get("user_id", "").strip()

        # Validate input
        if not server_url or not server_url.startswith(("http://", "https://")):
            _LOG.error(f"Invalid server URL: {server_url}")
            return ucapi.SetupError(ucapi.IntegrationSetupError.CONNECTION_REFUSED)

        if not api_key:
            _LOG.error("API Key is required")
            return ucapi.SetupError(ucapi.IntegrationSetupError.AUTHORIZATION_ERROR)

        # Test connection to Emby server
        _LOG.info(f"Testing connection to Emby server: {server_url}")
        
        try:
            client = EmbyClient(server_url, api_key, user_id)
            success, message = await client.test_connection()
            await client.close()
            
            if success:
                # Connection successful - save configuration
                config_data = {
                    "server_url": server_url,
                    "api_key": api_key,
                    "user_id": user_id
                }
                
                if self._config.update_config(config_data):
                    _LOG.info(f"Emby integration setup completed: {message}")
                    return ucapi.SetupComplete()
                else:
                    _LOG.error("Failed to save configuration")
                    return ucapi.SetupError(ucapi.IntegrationSetupError.OTHER)
            else:
                # Connection failed - show error
                _LOG.warning(f"Connection test failed: {message}")
                if "Authentication failed" in message:
                    return ucapi.SetupError(ucapi.IntegrationSetupError.AUTHORIZATION_ERROR)
                elif "timeout" in message.lower():
                    return ucapi.SetupError(ucapi.IntegrationSetupError.CONNECTION_REFUSED)
                else:
                    return ucapi.SetupError(ucapi.IntegrationSetupError.OTHER)
                
        except Exception as e:
            _LOG.error(f"Setup error: {e}")
            return ucapi.SetupError(ucapi.IntegrationSetupError.OTHER)

    async def _handle_setup_abort(self, msg: ucapi.AbortDriverSetup) -> ucapi.SetupAction:
        """Handle setup abort."""
        _LOG.info(f"Setup aborted: {msg.error}")
        return ucapi.SetupError(msg.error)

    async def discover_emby_servers(self, timeout: int = 5) -> list[dict[str, str]]:

        servers = []
        
        try:
            # Try UDP broadcast discovery on port 7359 (standard Emby discovery)
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Send discovery message
            message = "who is EmbyServer?"
            sock.sendto(message.encode(), ('<broadcast>', 7359))
            
            # Listen for responses
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode()
                    
                    # Parse response (simplified - actual format may vary)
                    if "EmbyServer" in response:
                        server_url = f"http://{addr[0]}:8096"  # Default Emby port
                        servers.append({
                            "name": f"Emby Server ({addr[0]})",
                            "url": server_url
                        })
                        _LOG.info(f"Discovered Emby server at {server_url}")
                        
                except socket.timeout:
                    break
                except Exception as e:
                    _LOG.debug(f"Discovery error: {e}")
                    break
            
            sock.close()
            
        except Exception as e:
            _LOG.debug(f"Server discovery failed: {e}")
        
        return servers