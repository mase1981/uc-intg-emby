"""Emby Media Server API client. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
import logging
import ssl
from typing import Any

import aiohttp
import certifi

from uc_intg_emby.const import EMBY_API_TIMEOUT, EMBY_CONNECTION_TIMEOUT

_LOG = logging.getLogger(__name__)


class EmbyClient:
    """Emby Media Server REST API client."""

    def __init__(self, server_url: str, api_key: str) -> None:
        self._server_url = server_url.rstrip("/")
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> None:
        if self._session and not self._session.closed:
            return
        ssl_context: ssl.SSLContext | bool | None = None
        if self._server_url.startswith("https://"):
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=EMBY_API_TIMEOUT),
            connector=connector,
        )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _url(self, endpoint: str) -> str:
        sep = "&" if "?" in endpoint else "?"
        return f"{self._server_url}{endpoint}{sep}api_key={self._api_key}"

    async def _get(self, endpoint: str) -> dict | list | None:
        if not self._session:
            return None
        try:
            async with self._session.get(self._url(endpoint), timeout=aiohttp.ClientTimeout(total=EMBY_API_TIMEOUT)) as resp:
                if resp.status == 200:
                    return await resp.json()
                _LOG.warning("GET %s returned %d", endpoint, resp.status)
        except Exception as err:
            _LOG.debug("GET %s failed: %s", endpoint, err)
        return None

    async def _post(self, endpoint: str, data: dict | None = None) -> bool:
        if not self._session:
            return False
        try:
            async with self._session.post(self._url(endpoint), json=data, timeout=aiohttp.ClientTimeout(total=EMBY_API_TIMEOUT)) as resp:
                return resp.status in (200, 204)
        except Exception as err:
            _LOG.debug("POST %s failed: %s", endpoint, err)
        return False

    async def test_connection(self) -> bool:
        if not self._session:
            await self.connect()
        try:
            async with self._session.get(
                self._url("/System/Info"),
                timeout=aiohttp.ClientTimeout(total=EMBY_CONNECTION_TIMEOUT),
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def get_server_info(self) -> dict | None:
        return await self._get("/System/Info")

    async def get_sessions(self, user_id: str = "") -> list[dict[str, Any]]:
        endpoint = "/Sessions"
        if user_id:
            endpoint += f"?ControllableByUserId={user_id}"
        result = await self._get(endpoint)
        return result if isinstance(result, list) else []

    async def send_playstate_command(self, session_id: str, command: str, seek_ticks: int | None = None) -> bool:
        endpoint = f"/Sessions/{session_id}/Playing/{command}"
        if seek_ticks is not None:
            endpoint += f"?SeekPositionTicks={seek_ticks}"
        return await self._post(endpoint)

    async def send_command(self, session_id: str, command: str, arguments: dict[str, Any] | None = None) -> bool:
        if not arguments:
            return await self._post(f"/Sessions/{session_id}/Command/{command}")
        return await self._post(f"/Sessions/{session_id}/Command", {"Name": command, "Arguments": arguments})

    async def play_items(self, session_id: str, item_ids: list[str], start_index: int = 0) -> bool:
        return await self._post(
            f"/Sessions/{session_id}/Playing",
            {"ItemIds": item_ids, "StartIndex": start_index, "PlayCommand": "PlayNow"},
        )

    async def get_libraries(self, user_id: str) -> list[dict[str, Any]]:
        result = await self._get(f"/Users/{user_id}/Views")
        if isinstance(result, dict):
            return result.get("Items", [])
        return []

    async def get_items(
        self, user_id: str, parent_id: str = "", item_type: str = "",
        start_index: int = 0, limit: int = 50, sort_by: str = "SortName",
    ) -> dict[str, Any]:
        endpoint = f"/Users/{user_id}/Items?StartIndex={start_index}&Limit={limit}&SortBy={sort_by}&SortOrder=Ascending"
        if parent_id:
            endpoint += f"&ParentId={parent_id}"
        if item_type:
            endpoint += f"&IncludeItemTypes={item_type}"
        endpoint += "&Fields=PrimaryImageAspectRatio,Overview&ImageTypeLimit=1"
        result = await self._get(endpoint)
        if isinstance(result, dict):
            return result
        return {"Items": [], "TotalRecordCount": 0}

    async def search_items(self, user_id: str, search_term: str, limit: int = 30) -> list[dict[str, Any]]:
        endpoint = f"/Users/{user_id}/Items?SearchTerm={search_term}&Limit={limit}&Recursive=true"
        endpoint += "&Fields=PrimaryImageAspectRatio&ImageTypeLimit=1"
        result = await self._get(endpoint)
        if isinstance(result, dict):
            return result.get("Items", [])
        return []

    async def get_users(self) -> list[dict[str, Any]]:
        result = await self._get("/Users")
        return result if isinstance(result, list) else []

    def image_url(self, item_id: str, max_height: int = 300) -> str:
        return f"{self._server_url}/Items/{item_id}/Images/Primary?maxHeight={max_height}&api_key={self._api_key}"

    @property
    def server_url(self) -> str:
        return self._server_url
