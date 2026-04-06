"""Emby setup flow. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
import logging
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from .client import EmbyClient
from .config import EmbyDeviceConfig

_LOG = logging.getLogger(__name__)


class EmbySetupFlow(BaseSetupFlow[EmbyDeviceConfig]):
    """Setup flow for Emby Media Server integration."""

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "Emby Server Configuration"},
            [
                {
                    "id": "server_url",
                    "label": {"en": "Server URL"},
                    "field": {"text": {"value": "http://", "placeholder": "http://192.168.1.100:8096"}},
                },
                {
                    "id": "api_key",
                    "label": {"en": "API Key"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "user_id",
                    "label": {"en": "User ID (optional, auto-detected if empty)"},
                    "field": {"text": {"value": ""}},
                },
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> EmbyDeviceConfig | RequestUserInput:
        server_url = input_values.get("server_url", "").strip().rstrip("/")
        api_key = input_values.get("api_key", "").strip()
        user_id = input_values.get("user_id", "").strip()

        if not server_url or not server_url.startswith(("http://", "https://")):
            raise ValueError("A valid server URL starting with http:// or https:// is required")
        if not api_key:
            raise ValueError("API Key is required")

        client = EmbyClient(server_url, api_key)
        try:
            await client.connect()
            if not await client.test_connection():
                raise ConnectionError(f"Cannot connect to Emby server at {server_url}")

            server_info = await client.get_server_info()
            server_name = "Emby Server"
            server_version = ""
            if server_info:
                server_name = server_info.get("ServerName", "Emby Server")
                server_version = server_info.get("Version", "")

            if not user_id:
                users = await client.get_users()
                if users:
                    admin = next((u for u in users if u.get("Policy", {}).get("IsAdministrator")), None)
                    selected_user = admin or users[0]
                    user_id = selected_user.get("Id", "")
                    _LOG.info("Auto-detected user: %s (%s)", selected_user.get("Name"), user_id)

            host = server_url.replace("http://", "").replace("https://", "").split(":")[0]
            identifier = f"emby_{host.replace('.', '_')}"

            return EmbyDeviceConfig(
                identifier=identifier,
                name=server_name,
                server_url=server_url,
                api_key=api_key,
                user_id=user_id,
                server_version=server_version,
            )
        finally:
            await client.close()
