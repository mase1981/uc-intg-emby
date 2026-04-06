"""Emby media player entity. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from ucapi import media_player, StatusCodes
from ucapi.api_definitions import BrowseOptions, BrowseResults, SearchOptions, SearchResults
from ucapi_framework import MediaPlayerEntity

from . import browser
from .config import EmbyDeviceConfig
from .const import EMBY_TICKS_PER_SECOND
from .device import EmbyServer, sanitize_id

_LOG = logging.getLogger(__name__)

BASE_FEATURES = [
    media_player.Features.PLAY_PAUSE,
    media_player.Features.STOP,
    media_player.Features.NEXT,
    media_player.Features.PREVIOUS,
    media_player.Features.FAST_FORWARD,
    media_player.Features.REWIND,
    media_player.Features.SEEK,
    media_player.Features.MEDIA_DURATION,
    media_player.Features.MEDIA_POSITION,
    media_player.Features.MEDIA_TITLE,
    media_player.Features.MEDIA_ARTIST,
    media_player.Features.MEDIA_ALBUM,
    media_player.Features.MEDIA_IMAGE_URL,
    media_player.Features.MEDIA_TYPE,
    media_player.Features.DPAD,
    media_player.Features.HOME,
    media_player.Features.MENU,
    media_player.Features.CONTEXT_MENU,
    media_player.Features.PLAY_MEDIA,
    media_player.Features.BROWSE_MEDIA,
    media_player.Features.SEARCH_MEDIA,
]

VOLUME_FEATURES = [
    media_player.Features.VOLUME,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
]


class EmbyMediaPlayer(MediaPlayerEntity):
    """Media player entity for an active Emby session."""

    def __init__(
        self,
        device_config: EmbyDeviceConfig,
        device: EmbyServer,
        session_data: dict[str, Any],
    ) -> None:
        self._device = device
        self._emby_device_id = session_data.get("DeviceId", "")
        self._supported_commands: list[str] = session_data.get("SupportedCommands", [])

        device_name = session_data.get("DeviceName", "Unknown")
        client_name = session_data.get("Client", "Unknown")
        if device_name and device_name != client_name:
            entity_name = f"{client_name} ({device_name})"
        else:
            entity_name = client_name

        features = list(BASE_FEATURES)
        if "VolumeUp" in self._supported_commands:
            features.extend(VOLUME_FEATURES)

        safe_id = sanitize_id(self._emby_device_id)
        entity_id = f"media_player.{device_config.identifier}.{safe_id}"

        super().__init__(
            entity_id,
            entity_name,
            features=features,
            attributes={
                media_player.Attributes.STATE: media_player.States.UNAVAILABLE,
                media_player.Attributes.VOLUME: 0,
                media_player.Attributes.MUTED: False,
                media_player.Attributes.MEDIA_TITLE: "",
                media_player.Attributes.MEDIA_ARTIST: "",
                media_player.Attributes.MEDIA_ALBUM: "",
                media_player.Attributes.MEDIA_IMAGE_URL: "",
                media_player.Attributes.MEDIA_TYPE: "",
                media_player.Attributes.MEDIA_DURATION: 0,
                media_player.Attributes.MEDIA_POSITION: 0,
            },
            device_class=media_player.DeviceClasses.STREAMING_BOX,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        session = self._device.get_session(self._emby_device_id)
        if not session or self._device.state == "UNAVAILABLE":
            self.update({
                media_player.Attributes.STATE: media_player.States.STANDBY,
                media_player.Attributes.MEDIA_TITLE: "",
                media_player.Attributes.MEDIA_ARTIST: "",
                media_player.Attributes.MEDIA_ALBUM: "",
                media_player.Attributes.MEDIA_IMAGE_URL: "",
                media_player.Attributes.MEDIA_TYPE: "",
                media_player.Attributes.MEDIA_DURATION: 0,
                media_player.Attributes.MEDIA_POSITION: 0,
            })
            return

        self._supported_commands = session.get("SupportedCommands", [])
        attrs = self._build_attributes(session)
        self.update(attrs)

    def _build_attributes(self, session: dict[str, Any]) -> dict:
        attrs: dict[str, Any] = {}
        now_playing = session.get("NowPlayingItem")
        play_state = session.get("PlayState", {})

        if now_playing:
            is_paused = play_state.get("IsPaused", False)
            attrs[media_player.Attributes.STATE] = (
                media_player.States.PAUSED if is_paused else media_player.States.PLAYING
            )
            self._set_media_metadata(attrs, now_playing)

            if now_playing.get("RunTimeTicks"):
                attrs[media_player.Attributes.MEDIA_DURATION] = now_playing["RunTimeTicks"] // EMBY_TICKS_PER_SECOND
            else:
                attrs[media_player.Attributes.MEDIA_DURATION] = 0

            attrs[media_player.Attributes.MEDIA_POSITION] = (
                play_state.get("PositionTicks", 0) // EMBY_TICKS_PER_SECOND
            )

            attrs[media_player.Attributes.MEDIA_IMAGE_URL] = self._resolve_image_url(now_playing)
        else:
            attrs[media_player.Attributes.STATE] = media_player.States.ON
            attrs[media_player.Attributes.MEDIA_TITLE] = ""
            attrs[media_player.Attributes.MEDIA_ARTIST] = ""
            attrs[media_player.Attributes.MEDIA_ALBUM] = ""
            attrs[media_player.Attributes.MEDIA_IMAGE_URL] = ""
            attrs[media_player.Attributes.MEDIA_TYPE] = ""
            attrs[media_player.Attributes.MEDIA_DURATION] = 0
            attrs[media_player.Attributes.MEDIA_POSITION] = 0

        if play_state.get("VolumeLevel") is not None:
            attrs[media_player.Attributes.VOLUME] = play_state["VolumeLevel"]
        attrs[media_player.Attributes.MUTED] = play_state.get("IsMuted", False)

        return attrs

    def _set_media_metadata(self, attrs: dict, now_playing: dict) -> None:
        media_type = now_playing.get("Type", "")

        if media_type == "Episode":
            attrs[media_player.Attributes.MEDIA_TYPE] = media_player.MediaType.TVSHOW
            attrs[media_player.Attributes.MEDIA_TITLE] = now_playing.get("Name", "")
            series = now_playing.get("SeriesName", "")
            season_num = now_playing.get("ParentIndexNumber")
            episode_num = now_playing.get("IndexNumber")
            if series and season_num is not None and episode_num is not None:
                attrs[media_player.Attributes.MEDIA_ARTIST] = f"{series} - S{season_num:02d}E{episode_num:02d}"
            else:
                attrs[media_player.Attributes.MEDIA_ARTIST] = series
            attrs[media_player.Attributes.MEDIA_ALBUM] = now_playing.get("SeasonName", "")

        elif media_type == "Movie":
            attrs[media_player.Attributes.MEDIA_TYPE] = media_player.MediaType.MOVIE
            name = now_playing.get("Name", "")
            year = now_playing.get("ProductionYear")
            attrs[media_player.Attributes.MEDIA_TITLE] = f"{name} ({year})" if year else name
            attrs[media_player.Attributes.MEDIA_ARTIST] = ""
            attrs[media_player.Attributes.MEDIA_ALBUM] = ""

        elif media_type in ("Audio", "MusicAlbum"):
            attrs[media_player.Attributes.MEDIA_TYPE] = media_player.MediaType.MUSIC
            attrs[media_player.Attributes.MEDIA_TITLE] = now_playing.get("Name", "")
            attrs[media_player.Attributes.MEDIA_ARTIST] = ", ".join(now_playing.get("Artists", []))
            attrs[media_player.Attributes.MEDIA_ALBUM] = now_playing.get("Album", "")

        else:
            attrs[media_player.Attributes.MEDIA_TYPE] = media_player.MediaType.VIDEO
            attrs[media_player.Attributes.MEDIA_TITLE] = now_playing.get("Name", "")
            attrs[media_player.Attributes.MEDIA_ARTIST] = ""
            attrs[media_player.Attributes.MEDIA_ALBUM] = ""

    def _resolve_image_url(self, now_playing: dict) -> str:
        item_id = now_playing.get("Id", "")
        if item_id and "Primary" in now_playing.get("ImageTags", {}):
            return self._device.build_image_url(item_id)
        series_id = now_playing.get("SeriesId", "")
        if series_id and now_playing.get("SeriesPrimaryImageTag"):
            return self._device.build_image_url(series_id)
        album_id = now_playing.get("AlbumId", "")
        if album_id and now_playing.get("AlbumPrimaryImageTag"):
            return self._device.build_image_url(album_id)
        parent_id = now_playing.get("ParentId", "")
        if parent_id and now_playing.get("ParentPrimaryImageTag"):
            return self._device.build_image_url(parent_id)
        if item_id:
            return self._device.build_image_url(item_id)
        return ""

    async def browse(self, options: BrowseOptions) -> BrowseResults | StatusCodes:
        return await browser.browse(self._device, options)

    async def search(self, options: SearchOptions) -> SearchResults | StatusCodes:
        return await browser.search(self._device, options)

    async def _handle_command(
        self, entity: media_player.MediaPlayer, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        session_id = self._device.get_session_id_for_device(self._emby_device_id)
        if not session_id:
            _LOG.warning("[%s] No active session for command %s", self.id, cmd_id)
            return StatusCodes.SERVICE_UNAVAILABLE

        try:
            success = await self._dispatch_command(session_id, cmd_id, params)
            return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
        except Exception as err:
            _LOG.error("[%s] Command %s failed: %s", self.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _dispatch_command(
        self, session_id: str, cmd_id: str, params: dict[str, Any] | None
    ) -> bool:
        if cmd_id == media_player.Commands.PLAY_PAUSE:
            return await self._device.send_playstate_command(session_id, "PlayPause")
        if cmd_id == media_player.Commands.STOP:
            return await self._device.send_playstate_command(session_id, "Stop")
        if cmd_id == media_player.Commands.NEXT:
            return await self._device.send_playstate_command(session_id, "NextTrack")
        if cmd_id == media_player.Commands.PREVIOUS:
            return await self._device.send_playstate_command(session_id, "PreviousTrack")
        if cmd_id == media_player.Commands.FAST_FORWARD:
            return await self._device.send_playstate_command(session_id, "FastForward")
        if cmd_id == media_player.Commands.REWIND:
            return await self._device.send_playstate_command(session_id, "Rewind")
        if cmd_id == media_player.Commands.VOLUME_UP:
            return await self._device.send_command(session_id, "VolumeUp")
        if cmd_id == media_player.Commands.VOLUME_DOWN:
            return await self._device.send_command(session_id, "VolumeDown")
        if cmd_id == media_player.Commands.MUTE_TOGGLE:
            return await self._device.send_command(session_id, "ToggleMute")
        if cmd_id == media_player.Commands.VOLUME and params:
            return await self._device.send_command(
                session_id, "SetVolume", {"Volume": str(params.get("volume", 0))}
            )
        if cmd_id == media_player.Commands.SEEK and params:
            position_ticks = int(params.get("media_position", 0)) * EMBY_TICKS_PER_SECOND
            return await self._device.send_playstate_command(session_id, "Seek", position_ticks)
        if cmd_id == media_player.Commands.CURSOR_UP:
            return await self._device.send_command(session_id, "MoveUp")
        if cmd_id == media_player.Commands.CURSOR_DOWN:
            return await self._device.send_command(session_id, "MoveDown")
        if cmd_id == media_player.Commands.CURSOR_LEFT:
            return await self._device.send_command(session_id, "MoveLeft")
        if cmd_id == media_player.Commands.CURSOR_RIGHT:
            return await self._device.send_command(session_id, "MoveRight")
        if cmd_id == media_player.Commands.CURSOR_ENTER:
            return await self._device.send_command(session_id, "Select")
        if cmd_id == media_player.Commands.BACK:
            return await self._device.send_command(session_id, "Back")
        if cmd_id == media_player.Commands.HOME:
            return await self._device.send_command(session_id, "GoHome")
        if cmd_id == media_player.Commands.MENU:
            return await self._device.send_command(session_id, "ContextMenu")
        if cmd_id == media_player.Commands.CONTEXT_MENU:
            return await self._device.send_command(session_id, "ContextMenu")
        if cmd_id == media_player.Commands.PLAY_MEDIA:
            return await self._handle_play_media(session_id, params)

        _LOG.warning("[%s] Unhandled command: %s", self.id, cmd_id)
        return False

    async def _handle_play_media(self, session_id: str, params: dict[str, Any] | None) -> bool:
        if not params:
            return False
        media_id = params.get("media_id", "")
        if not media_id:
            return False
        if media_id.startswith("item_"):
            item_id = media_id[5:]
            return await self._device.play_items(session_id, [item_id])
        _LOG.warning("[%s] Unknown media_id format: %s", self.id, media_id)
        return False
