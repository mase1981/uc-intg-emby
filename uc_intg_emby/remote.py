"""Emby remote entity. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from ucapi import remote, StatusCodes
from ucapi.ui import (
    Buttons,
    Size,
    UiPage,
    create_btn_mapping,
    create_ui_icon,
    create_ui_text,
)
from ucapi_framework import RemoteEntity

from uc_intg_emby.const import SIMPLE_COMMANDS

if TYPE_CHECKING:
    from uc_intg_emby.config import EmbyDeviceConfig
    from uc_intg_emby.device import EmbyServer

_LOG = logging.getLogger(__name__)


def _create_button_mapping() -> list:
    return [
        create_btn_mapping(Buttons.DPAD_UP, short="MOVE_UP"),
        create_btn_mapping(Buttons.DPAD_DOWN, short="MOVE_DOWN"),
        create_btn_mapping(Buttons.DPAD_LEFT, short="MOVE_LEFT"),
        create_btn_mapping(Buttons.DPAD_RIGHT, short="MOVE_RIGHT"),
        create_btn_mapping(Buttons.DPAD_MIDDLE, short="SELECT"),
        create_btn_mapping(Buttons.BACK, short="BACK"),
        create_btn_mapping(Buttons.HOME, short="GO_HOME"),
        create_btn_mapping(Buttons.MENU, short="TOGGLE_CONTEXT_MENU"),
        create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
        create_btn_mapping(Buttons.PREV, short="PREVIOUS_TRACK"),
        create_btn_mapping(Buttons.NEXT, short="NEXT_TRACK"),
        create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
        create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
        create_btn_mapping(Buttons.MUTE, short="MUTE_TOGGLE"),
        create_btn_mapping(Buttons.POWER, short="STOP"),
        create_btn_mapping(Buttons.STOP, short="STOP"),
        create_btn_mapping(Buttons.CHANNEL_UP, short="PAGE_UP"),
        create_btn_mapping(Buttons.CHANNEL_DOWN, short="PAGE_DOWN"),
    ]


def _create_ui_pages() -> list[UiPage]:
    nav_page = UiPage("nav", "Navigation", grid=Size(4, 6), items=[
        create_ui_icon("uc:home", 0, 0, cmd="GO_HOME"),
        create_ui_icon("uc:up-arrow", 1, 0, cmd="MOVE_UP"),
        create_ui_text("Menu", 2, 0, cmd="TOGGLE_CONTEXT_MENU"),
        create_ui_text("OSD", 3, 0, cmd="TOGGLE_OSD"),
        create_ui_icon("uc:left-arrow", 0, 1, cmd="MOVE_LEFT"),
        create_ui_text("OK", 1, 1, cmd="SELECT"),
        create_ui_icon("uc:right-arrow", 2, 1, cmd="MOVE_RIGHT"),
        create_ui_text("Back", 3, 1, cmd="BACK"),
        create_ui_icon("uc:down-arrow", 1, 2, cmd="MOVE_DOWN"),
        create_ui_icon("uc:search", 0, 3, cmd="GO_TO_SEARCH"),
        create_ui_icon("uc:menu", 1, 3, cmd="GO_TO_SETTINGS"),
        create_ui_text("PgUp", 2, 3, cmd="PAGE_UP"),
        create_ui_text("PgDn", 3, 3, cmd="PAGE_DOWN"),
    ])

    playback_page = UiPage("playback", "Playback", grid=Size(4, 6), items=[
        create_ui_icon("uc:prev", 0, 0, cmd="PREVIOUS_TRACK"),
        create_ui_icon("uc:play", 1, 0, cmd="PLAY_PAUSE"),
        create_ui_icon("uc:stop", 2, 0, cmd="STOP"),
        create_ui_icon("uc:next", 3, 0, cmd="NEXT_TRACK"),
        create_ui_text("A<<", 0, 1, cmd="PREVIOUS_LETTER"),
        create_ui_text(">>A", 3, 1, cmd="NEXT_LETTER"),
    ])

    volume_page = UiPage("volume", "Volume", grid=Size(4, 6), items=[
        create_ui_icon("uc:vol-up", 0, 0, cmd="VOLUME_UP"),
        create_ui_icon("uc:vol-down", 1, 0, cmd="VOLUME_DOWN"),
        create_ui_icon("uc:mute", 2, 0, cmd="MUTE_TOGGLE"),
        create_ui_text("Full", 3, 0, cmd="TOGGLE_FULLSCREEN"),
    ])

    return [nav_page, playback_page, volume_page]


EMBY_COMMAND_MAP = {
    "MOVE_UP": ("command", "MoveUp"),
    "MOVE_DOWN": ("command", "MoveDown"),
    "MOVE_LEFT": ("command", "MoveLeft"),
    "MOVE_RIGHT": ("command", "MoveRight"),
    "SELECT": ("command", "Select"),
    "BACK": ("command", "Back"),
    "GO_HOME": ("command", "GoHome"),
    "GO_TO_SETTINGS": ("command", "GoToSettings"),
    "GO_TO_SEARCH": ("command", "GoToSearch"),
    "PAGE_UP": ("command", "PageUp"),
    "PAGE_DOWN": ("command", "PageDown"),
    "NEXT_LETTER": ("command", "NextLetter"),
    "PREVIOUS_LETTER": ("command", "PreviousLetter"),
    "TOGGLE_OSD": ("command", "ToggleOsdMenu"),
    "TOGGLE_CONTEXT_MENU": ("command", "ToggleContextMenu"),
    "TOGGLE_FULLSCREEN": ("command", "ToggleFullscreen"),
    "VOLUME_UP": ("command", "VolumeUp"),
    "VOLUME_DOWN": ("command", "VolumeDown"),
    "MUTE_TOGGLE": ("command", "ToggleMute"),
    "PLAY_PAUSE": ("playstate", "PlayPause"),
    "STOP": ("playstate", "Stop"),
    "NEXT_TRACK": ("playstate", "NextTrack"),
    "PREVIOUS_TRACK": ("playstate", "PreviousTrack"),
}


class EmbyRemote(RemoteEntity):
    """Remote entity for an active Emby session."""

    def __init__(
        self,
        device_config: EmbyDeviceConfig,
        device: EmbyServer,
        session_data: dict[str, Any],
    ) -> None:
        self._device = device
        self._emby_device_id = session_data.get("DeviceId", "")

        device_name = session_data.get("DeviceName", "Unknown")
        client_name = session_data.get("Client", "Unknown")
        if device_name and device_name != client_name:
            entity_name = f"{client_name} ({device_name}) Remote"
        else:
            entity_name = f"{client_name} Remote"

        from uc_intg_emby.device import sanitize_id
        safe_id = sanitize_id(self._emby_device_id)
        entity_id = f"remote.{device_config.identifier}.{safe_id}"

        super().__init__(
            entity_id,
            entity_name,
            [remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=SIMPLE_COMMANDS,
            button_mapping=_create_button_mapping(),
            ui_pages=_create_ui_pages(),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        session = self._device.get_session(self._emby_device_id)
        if not session or self._device.state == "UNAVAILABLE":
            self.set_state(remote.States.UNAVAILABLE, update=True)
            return
        self.set_state(remote.States.ON, update=True)

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        if cmd_id == remote.Commands.SEND_CMD:
            command = params.get("command", "") if params else ""
            if not command:
                return StatusCodes.BAD_REQUEST
            return await self._dispatch_command(command)

        if cmd_id == remote.Commands.SEND_CMD_SEQUENCE:
            for command in (params.get("sequence", []) if params else []):
                result = await self._dispatch_command(command)
                if result != StatusCodes.OK:
                    return result
            return StatusCodes.OK

        return StatusCodes.NOT_IMPLEMENTED

    async def _dispatch_command(self, command: str) -> StatusCodes:
        session_id = self._device.get_session_id_for_device(self._emby_device_id)
        if not session_id:
            _LOG.warning("[%s] No active session for command %s", self.id, command)
            return StatusCodes.SERVICE_UNAVAILABLE

        mapping = EMBY_COMMAND_MAP.get(command)
        if not mapping:
            _LOG.warning("[%s] Unknown command: %s", self.id, command)
            return StatusCodes.BAD_REQUEST

        cmd_type, emby_cmd = mapping
        try:
            if cmd_type == "playstate":
                success = await self._device.send_playstate_command(session_id, emby_cmd)
            else:
                success = await self._device.send_command(session_id, emby_cmd)
            return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
        except Exception as err:
            _LOG.error("[%s] Command %s failed: %s", self.id, command, err)
            return StatusCodes.SERVER_ERROR
