"""
Emby Media Server API client.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""
import asyncio
import logging
import ssl
from typing import Any, Optional
from urllib.parse import quote, urljoin

import aiohttp
import async_timeout

_LOG = logging.getLogger(__name__)


class EmbyClient:
    """Emby Media Server API client."""

    def __init__(self, server_url: str, api_key: str, user_id: str = ""):
        self._server_url = server_url.rstrip('/')
        self._api_key = api_key
        self._user_id = user_id
        self._session: Optional[aiohttp.ClientSession] = None
        self._server_info: Optional[dict[str, Any]] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            ssl_context = None
            if self._server_url.startswith('https://'):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "UC-Emby-Integration/1.0.0"},
                connector=aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_url(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> str:
        url = urljoin(self._server_url, endpoint)
        
        final_params = params.copy() if params else {}
        final_params['api_key'] = self._api_key
        
        query_parts = [f"{key}={quote(str(value))}" for key, value in final_params.items() if value]
        if query_parts:
            url += "?" + "&".join(query_parts)
        return url

    async def test_connection(self) -> tuple[bool, str]:
        try:
            session = await self._get_session()
            url = self._build_url("/System/Info")
            async with async_timeout.timeout(5):
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._server_info = data
                        return True, f"Connected to {data.get('ServerName')} v{data.get('Version')}"
                    return False, f"Connection failed with status: {response.status}"
        except Exception as e:
            _LOG.error(f"Connection error: {e}", exc_info=True)
            return False, f"Connection error: {e}"

    async def get_sessions(self) -> list[dict[str, Any]]:
        try:
            session = await self._get_session()
            params = {'ControllableByUserId': self._user_id} if self._user_id else {}
            url = self._build_url("/Sessions", params)
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    _LOG.error(f"Failed to get sessions: HTTP {response.status}")
                    return []
        except Exception as e:
            _LOG.error(f"Error getting sessions: {e}", exc_info=True)
            return []

    async def send_command(self, session_id: str, command: str, arguments: Optional[dict[str, Any]] = None) -> bool:
        """
        Send a command to a specific session, using the correct endpoint.
        """
        try:
            session = await self._get_session()
            url: str
            post_data: Optional[dict] = None

            if not arguments:
                url = self._build_url(f"/Sessions/{session_id}/Command/{command}")
                post_data = None # Send empty POST
            else:
                url = self._build_url(f"/Sessions/{session_id}/Command")
                post_data = {"Name": command, "Arguments": arguments}

            _LOG.debug(f"Sending command '{command}' to URL: {url} with data: {post_data}")
            
            async with async_timeout.timeout(5):
                async with session.post(url, json=post_data) as response:
                    await response.text()  # Consume response
                    success = response.status in (200, 204) # 204 No Content is a success
                    if not success:
                        _LOG.warning(f"Command '{command}' failed: HTTP {response.status}")
                    return success
                    
        except Exception as e:
            _LOG.error(f"Error sending command '{command}': {e}", exc_info=True)
            return False

    async def get_session_by_id(self, session_id: str) -> Optional[dict[str, Any]]:
        sessions = await self.get_sessions()
        return next((s for s in sessions if s.get('Id') == session_id), None)

    @property
    def is_configured(self) -> bool:
        return bool(self._server_url and self._api_key)