"""
Emby Media Player entity for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, List, Optional

import ucapi
from uc_intg_emby.client import EmbyClient

_LOG = logging.getLogger(__name__)


class EmbyMediaPlayer(ucapi.MediaPlayer):
    """Emby Media Player entity implementation."""

    def __init__(self, client: EmbyClient, session_data: dict[str, Any], api: ucapi.IntegrationAPI):
        self._client = client
        self._session_data = session_data
        self._api = api
        self._update_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        
        # Store the list of supported commands for this specific session
        self.supported_commands: List[str] = session_data.get('SupportedCommands', [])

        session_id = session_data.get('Id', '')
        device_name = session_data.get('DeviceName', 'Unknown Device')
        client_name = session_data.get('Client', 'Unknown Client')
        
        entity_id = f"emby_{session_id}"
        
        if device_name and device_name != client_name:
            entity_name = f"{client_name} ({device_name})"
        else:
            entity_name = client_name
        
        features = [
            ucapi.media_player.Features.PLAY_PAUSE, ucapi.media_player.Features.STOP,
            ucapi.media_player.Features.NEXT, ucapi.media_player.Features.PREVIOUS,
            ucapi.media_player.Features.SEEK, ucapi.media_player.Features.MEDIA_DURATION,
            ucapi.media_player.Features.MEDIA_POSITION, ucapi.media_player.Features.MEDIA_TITLE,
            ucapi.media_player.Features.MEDIA_ARTIST, ucapi.media_player.Features.MEDIA_ALBUM,
            ucapi.media_player.Features.MEDIA_IMAGE_URL, ucapi.media_player.Features.MEDIA_TYPE,
            ucapi.media_player.Features.FAST_FORWARD, ucapi.media_player.Features.REWIND,
        ]
        
        if 'VolumeUp' in self.supported_commands:
            features.extend([
                ucapi.media_player.Features.VOLUME,
                ucapi.media_player.Features.VOLUME_UP_DOWN,
                ucapi.media_player.Features.MUTE_TOGGLE
            ])
        
        attributes = self._build_attributes()
        
        super().__init__(
            identifier=entity_id, name=entity_name, features=features,
            attributes=attributes, device_class=ucapi.media_player.DeviceClasses.STREAMING_BOX,
            cmd_handler=self.command_handler
        )

    def _build_attributes(self) -> dict[str, Any]:
        attributes = {}
        now_playing = self._session_data.get('NowPlayingItem')
        play_state = self._session_data.get('PlayState', {})
        
        if now_playing:
            is_paused = play_state.get('IsPaused', False)
            attributes[ucapi.media_player.Attributes.STATE] = ucapi.media_player.States.PAUSED if is_paused else ucapi.media_player.States.PLAYING
            
            media_type = now_playing.get('Type', '')
            if media_type == 'Episode':
                attributes[ucapi.media_player.Attributes.MEDIA_TYPE] = ucapi.media_player.MediaType.TVSHOW
                attributes[ucapi.media_player.Attributes.MEDIA_TITLE] = now_playing.get('Name', '')
                series_name = now_playing.get('SeriesName', '')
                season_num = now_playing.get('ParentIndexNumber')
                episode_num = now_playing.get('IndexNumber')
                if series_name and season_num is not None and episode_num is not None:
                    attributes[ucapi.media_player.Attributes.MEDIA_ARTIST] = f"{series_name} - S{season_num:02d}E{episode_num:02d}"
                else:
                    attributes[ucapi.media_player.Attributes.MEDIA_ARTIST] = series_name or "TV Show"
                attributes[ucapi.media_player.Attributes.MEDIA_ALBUM] = now_playing.get('SeasonName', '')
            elif media_type == 'Movie':
                attributes[ucapi.media_player.Attributes.MEDIA_TYPE] = ucapi.media_player.MediaType.MOVIE
                movie_name = now_playing.get('Name', '')
                year = now_playing.get('ProductionYear')
                attributes[ucapi.media_player.Attributes.MEDIA_TITLE] = f"{movie_name} ({year})" if year else movie_name
            elif media_type in ['Audio', 'MusicAlbum']:
                attributes[ucapi.media_player.Attributes.MEDIA_TYPE] = ucapi.media_player.MediaType.MUSIC
                attributes[ucapi.media_player.Attributes.MEDIA_TITLE] = now_playing.get('Name', '')
                attributes[ucapi.media_player.Attributes.MEDIA_ARTIST] = ', '.join(now_playing.get('Artists', []))
                attributes[ucapi.media_player.Attributes.MEDIA_ALBUM] = now_playing.get('Album', '')
            else:
                attributes[ucapi.media_player.Attributes.MEDIA_TYPE] = ucapi.media_player.MediaType.VIDEO
                attributes[ucapi.media_player.Attributes.MEDIA_TITLE] = now_playing.get('Name', '')

            if now_playing.get('RunTimeTicks'):
                attributes[ucapi.media_player.Attributes.MEDIA_DURATION] = now_playing['RunTimeTicks'] // 10000000
            if play_state.get('PositionTicks'):
                attributes[ucapi.media_player.Attributes.MEDIA_POSITION] = play_state['PositionTicks'] // 10000000

            if 'Primary' in now_playing.get('ImageTags', {}):
                image_tag = now_playing['ImageTags']['Primary']
                item_id = now_playing['Id']
                image_url = f"{self._client._server_url}/Items/{item_id}/Images/Primary?tag={image_tag}&api_key={self._client._api_key}"
                attributes[ucapi.media_player.Attributes.MEDIA_IMAGE_URL] = image_url
        else:
            attributes[ucapi.media_player.Attributes.STATE] = ucapi.media_player.States.STANDBY

        if play_state.get('VolumeLevel') is not None:
            attributes[ucapi.media_player.Attributes.VOLUME] = play_state['VolumeLevel']
        attributes[ucapi.media_player.Attributes.MUTED] = play_state.get('IsMuted', False)
        
        return attributes

    async def _send_prioritized_command(self, session_id: str, commands: List[str]) -> bool:
        """Try to send commands from a prioritized list."""
        for command in commands:
            if command in self.supported_commands:
                _LOG.info(f"Client supports '{command}', sending it.")
                return await self._client.send_command(session_id, command)
        _LOG.warning(f"Client does not support any of the priority commands: {commands}")
        return False

    async def command_handler(self, entity: ucapi.Entity, cmd_id: str, params: dict[str, Any] | None = None) -> ucapi.StatusCodes:
        session_id = self._session_data.get('Id')
        _LOG.info(f"COMMAND RECEIVED: '{cmd_id}' for session '{session_id}'")
        
        if not session_id:
            _LOG.error("Command failed: No session ID found.")
            return ucapi.StatusCodes.SERVER_ERROR

        try:
            success = False
            
            # THIS IS THE FINAL FIX: Dynamically send the correct command based on what the client supports.
            if cmd_id == ucapi.media_player.Commands.PLAY_PAUSE:
                success = await self._send_prioritized_command(session_id, ["PlayPause", "Select"])
            elif cmd_id == ucapi.media_player.Commands.STOP:
                success = await self._send_prioritized_command(session_id, ["Stop", "Back"])
            elif cmd_id == ucapi.media_player.Commands.NEXT:
                success = await self._send_prioritized_command(session_id, ["NextTrack", "NextLetter"])
            elif cmd_id == ucapi.media_player.Commands.PREVIOUS:
                success = await self._send_prioritized_command(session_id, ["PreviousTrack", "PreviousLetter"])
            elif cmd_id == ucapi.media_player.Commands.FAST_FORWARD:
                success = await self._send_prioritized_command(session_id, ["FastForward", "MoveRight"])
            elif cmd_id == ucapi.media_player.Commands.REWIND:
                success = await self._send_prioritized_command(session_id, ["Rewind", "MoveLeft"])
            elif cmd_id == ucapi.media_player.Commands.VOLUME_UP:
                success = await self._client.send_command(session_id, "VolumeUp")
            elif cmd_id == ucapi.media_player.Commands.VOLUME_DOWN:
                success = await self._client.send_command(session_id, "VolumeDown")
            elif cmd_id == ucapi.media_player.Commands.MUTE_TOGGLE:
                success = await self._client.send_command(session_id, "ToggleMute")
            elif cmd_id == ucapi.media_player.Commands.VOLUME and params:
                success = await self._client.send_command(session_id, "SetVolume", {"Volume": params.get('volume')})
            elif cmd_id == ucapi.media_player.Commands.SEEK and params:
                position_ticks = int(params.get('media_position', 0) * 10000000)
                success = await self._client.send_command(session_id, "Seek", {"SeekPositionTicks": position_ticks})
            else:
                _LOG.warning(f"Unsupported command received: {cmd_id}")
                return ucapi.StatusCodes.NOT_IMPLEMENTED

            _LOG.info(f"Command '{cmd_id}' execution result: {'Success' if success else 'Failed'}")
            
            if success:
                await asyncio.sleep(0.5)
                await self.push_update()
            
            return ucapi.StatusCodes.OK if success else ucapi.StatusCodes.SERVER_ERROR
            
        except Exception as e:
            _LOG.error(f"Command execution failed with exception: {e}", exc_info=True)
            return ucapi.StatusCodes.SERVER_ERROR

    async def update_from_session(self, session_data: dict[str, Any]):
        self._session_data = session_data
        # Update our knowledge of supported commands in case they change
        self.supported_commands = session_data.get('SupportedCommands', [])
        new_attributes = self._build_attributes()
        
        if new_attributes != self.attributes:
            self.attributes.update(new_attributes)
            if self._api:
                self._api.configured_entities.update_attributes(self.id, new_attributes)

    async def push_update(self):
        session_id = self._session_data.get('Id')
        if not session_id: return
        
        try:
            updated_session = await self._client.get_session_by_id(session_id)
            if updated_session:
                await self.update_from_session(updated_session)
            else:
                _LOG.info(f"Session {session_id} appears to have ended.")
                self.stop_monitoring()
                if self._api:
                    self._api.available_entities.remove(self.id)
        except Exception as e:
            _LOG.error(f"Error during push_update for {self.id}: {e}", exc_info=True)

    async def _periodic_update(self):
        while self._is_monitoring:
            try:
                await self.push_update()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOG.error(f"Periodic update failed for {self.id}: {e}", exc_info=True)
                await asyncio.sleep(15)

    async def start_monitoring(self):
        if not self._is_monitoring:
            _LOG.info(f"Starting monitoring for {self.id}")
            self._is_monitoring = True
            self._update_task = asyncio.create_task(self._periodic_update())

    def stop_monitoring(self):
        if self._is_monitoring:
            _LOG.info(f"Stopping monitoring for {self.id}")
            self._is_monitoring = False
            if self._update_task:
                self._update_task.cancel()
                self._update_task = None