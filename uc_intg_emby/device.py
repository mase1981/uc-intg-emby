"""Emby server device. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from __future__ import annotations

import logging
import re
from typing import Any

from ucapi_framework import DeviceEvents, PollingDevice

from uc_intg_emby.client import EmbyClient
from uc_intg_emby.config import EmbyDeviceConfig
from uc_intg_emby.const import EMBY_POLL_INTERVAL, EMBY_TICKS_PER_SECOND

_LOG = logging.getLogger(__name__)


def sanitize_id(value: str) -> str:
    """Sanitize a string for use in entity IDs (alphanumeric and underscores only)."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", value).lower()


class EmbyServer(PollingDevice):
    """Emby Media Server device using polling for session discovery and state updates."""

    def __init__(self, device_config: EmbyDeviceConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=EMBY_POLL_INTERVAL, **kwargs)
        self._device_config: EmbyDeviceConfig = device_config
        self._client: EmbyClient | None = None
        self._state: str = "UNAVAILABLE"

        self._server_name: str = ""
        self._server_version: str = ""
        self._server_os: str = ""
        self._sessions: dict[str, dict[str, Any]] = {}
        self._known_device_ids: set[str] = set()

    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.server_url

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def server_name(self) -> str:
        return self._server_name

    @property
    def server_version(self) -> str:
        return self._server_version

    @property
    def server_os(self) -> str:
        return self._server_os

    @property
    def sessions(self) -> dict[str, dict[str, Any]]:
        return self._sessions

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    @property
    def user_id(self) -> str:
        return self._device_config.user_id

    @property
    def client(self) -> EmbyClient | None:
        return self._client

    def get_session(self, device_id: str) -> dict[str, Any] | None:
        return self._sessions.get(device_id)

    def get_session_id_for_device(self, device_id: str) -> str | None:
        session = self._sessions.get(device_id)
        return session.get("Id") if session else None

    async def establish_connection(self) -> EmbyClient:
        if self._client:
            await self._client.close()
        self._client = EmbyClient(self._device_config.server_url, self._device_config.api_key)
        await self._client.connect()

        if not await self._client.test_connection():
            await self._client.close()
            self._client = None
            raise ConnectionError(f"Cannot reach Emby server at {self._device_config.server_url}")

        server_info = await self._client.get_server_info()
        if server_info:
            self._server_name = server_info.get("ServerName", "Emby Server")
            self._server_version = server_info.get("Version", "Unknown")
            self._server_os = server_info.get("OperatingSystemDisplayName", "") or server_info.get("OperatingSystem", "Unknown")
            _LOG.info("[%s] Connected to %s v%s (%s)", self.log_id, self._server_name, self._server_version, self._server_os)

        try:
            await self._update_state()
        except ConnectionError:
            _LOG.warning("[%s] Initial session query failed, continuing with defaults", self.log_id)

        self._state = "ON"
        return self._client

    async def poll_device(self) -> None:
        if not self._client:
            return
        try:
            await self._update_state()
            self._create_dynamic_entities()
            self.push_update()
        except Exception as err:
            _LOG.debug("[%s] Poll error: %s", self.log_id, err)
            if self._state != "UNAVAILABLE":
                self._state = "UNAVAILABLE"
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        self._sessions.clear()
        self._state = "UNAVAILABLE"
        await super().disconnect()

    async def _update_state(self) -> None:
        sessions_list = await self._client.get_sessions(self._device_config.user_id)
        if sessions_list is None:
            raise ConnectionError("Failed to fetch sessions")

        current_device_ids: set[str] = set()
        for session in sessions_list:
            device_id = session.get("DeviceId")
            if not device_id:
                continue
            current_device_ids.add(device_id)
            self._sessions[device_id] = session

        ended = set(self._sessions.keys()) - current_device_ids
        for device_id in ended:
            del self._sessions[device_id]

    def _create_dynamic_entities(self) -> None:
        if not self.driver:
            return

        new_device_ids = set(self._sessions.keys()) - self._known_device_ids
        if not new_device_ids:
            return

        from uc_intg_emby.media_player import EmbyMediaPlayer
        from uc_intg_emby.remote import EmbyRemote

        new_entities = []
        for device_id in new_device_ids:
            session = self._sessions[device_id]
            try:
                new_entities.append(EmbyMediaPlayer(self._device_config, self, session))
                new_entities.append(EmbyRemote(self._device_config, self, session))
                self._known_device_ids.add(device_id)
                _LOG.info(
                    "[%s] New session: %s (%s)",
                    self.log_id,
                    session.get("Client", "Unknown"),
                    session.get("DeviceName", "Unknown"),
                )
            except Exception as err:
                _LOG.error("[%s] Failed to create entity for %s: %s", self.log_id, device_id, err)

        if new_entities:
            self.driver.add_entities(new_entities)

    async def send_playstate_command(self, session_id: str, command: str, seek_ticks: int | None = None) -> bool:
        if not self._client:
            return False
        return await self._client.send_playstate_command(session_id, command, seek_ticks)

    async def send_command(self, session_id: str, command: str, arguments: dict[str, Any] | None = None) -> bool:
        if not self._client:
            return False
        return await self._client.send_command(session_id, command, arguments)

    async def play_items(self, session_id: str, item_ids: list[str]) -> bool:
        if not self._client:
            return False
        return await self._client.play_items(session_id, item_ids)

    def build_image_url(self, item_id: str, max_height: int = 300) -> str:
        if not self._client:
            return ""
        return self._client.image_url(item_id, max_height)
