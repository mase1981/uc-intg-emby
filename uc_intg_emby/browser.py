"""Emby media browser. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ucapi import StatusCodes
from ucapi.api_definitions import Pagination
from ucapi.media_player import (
    BrowseMediaItem,
    BrowseOptions,
    BrowseResults,
    MediaClass,
    MediaContentType,
    SearchOptions,
    SearchResults,
)

if TYPE_CHECKING:
    from uc_intg_emby.device import EmbyServer

_LOG = logging.getLogger(__name__)

EMBY_TYPE_TO_MEDIA_CLASS: dict[str, MediaClass] = {
    "Movie": MediaClass.MOVIE,
    "Series": MediaClass.TV_SHOW,
    "Season": MediaClass.SEASON,
    "Episode": MediaClass.EPISODE,
    "Audio": MediaClass.TRACK,
    "MusicAlbum": MediaClass.ALBUM,
    "MusicArtist": MediaClass.ARTIST,
    "Folder": MediaClass.DIRECTORY,
    "CollectionFolder": MediaClass.DIRECTORY,
    "Playlist": MediaClass.PLAYLIST,
    "BoxSet": MediaClass.DIRECTORY,
    "MusicVideo": MediaClass.VIDEO,
    "Video": MediaClass.VIDEO,
}

PLAYABLE_TYPES = {"Movie", "Episode", "Audio", "MusicVideo", "Video"}
BROWSABLE_TYPES = {"Series", "Season", "MusicAlbum", "MusicArtist", "Folder", "CollectionFolder", "BoxSet", "Playlist"}


async def browse(device: EmbyServer, options: BrowseOptions) -> BrowseResults | StatusCodes:
    if not device.client or not device.user_id:
        return StatusCodes.SERVICE_UNAVAILABLE

    media_id = options.media_id if hasattr(options, "media_id") else None
    media_type = options.media_type if hasattr(options, "media_type") else None

    if not media_id or media_id == "root":
        return await _browse_root(device)

    if media_id.startswith("library_"):
        library_id = media_id[8:]
        return await _browse_library(device, library_id, options)

    if media_id.startswith("folder_"):
        folder_id = media_id[7:]
        return await _browse_folder(device, folder_id, options)

    return StatusCodes.NOT_FOUND


async def search(device: EmbyServer, options: SearchOptions) -> SearchResults | StatusCodes:
    if not device.client or not device.user_id:
        return StatusCodes.SERVICE_UNAVAILABLE

    query = options.query if hasattr(options, "query") else ""
    if not query:
        return SearchResults(media=[], pagination=Pagination(page=1, limit=0, count=0))

    items = await device.client.search_items(device.user_id, query, limit=30)
    results = []
    for item in items:
        media_item = _item_to_browse_item(device, item)
        if media_item:
            results.append(media_item)

    return SearchResults(
        media=results,
        pagination=Pagination(page=1, limit=len(results), count=len(results)),
    )


async def _browse_root(device: EmbyServer) -> BrowseResults:
    libraries = await device.client.get_libraries(device.user_id)

    items = []
    for lib in libraries:
        lib_id = lib.get("Id", "")
        lib_name = lib.get("Name", "Unknown")
        lib_type = lib.get("CollectionType", "")

        media_class = MediaClass.DIRECTORY
        if lib_type == "movies":
            media_class = MediaClass.MOVIE
        elif lib_type == "tvshows":
            media_class = MediaClass.TV_SHOW
        elif lib_type == "music":
            media_class = MediaClass.ALBUM

        thumbnail = device.build_image_url(lib_id) if lib_id else ""

        items.append(BrowseMediaItem(
            title=lib_name,
            media_class=media_class,
            media_type="library",
            media_id=f"library_{lib_id}",
            can_browse=True,
            can_play=False,
            thumbnail=thumbnail,
        ))

    return BrowseResults(
        media=BrowseMediaItem(
            title=device.server_name or "Emby",
            media_class=MediaClass.DIRECTORY,
            media_type="root",
            media_id="root",
            can_browse=True,
            can_search=True,
            items=items,
        ),
        pagination=Pagination(page=1, limit=len(items), count=len(items)),
    )


async def _browse_library(device: EmbyServer, library_id: str, options: BrowseOptions) -> BrowseResults:
    page = options.paging.page if hasattr(options, "paging") and options.paging and hasattr(options.paging, "page") and options.paging.page else 1
    limit = options.paging.limit if hasattr(options, "paging") and options.paging and hasattr(options.paging, "limit") and options.paging.limit else 50

    start_index = (page - 1) * limit
    result = await device.client.get_items(device.user_id, parent_id=library_id, start_index=start_index, limit=limit)

    total = result.get("TotalRecordCount", 0)
    emby_items = result.get("Items", [])

    items = []
    for item in emby_items:
        media_item = _item_to_browse_item(device, item)
        if media_item:
            items.append(media_item)

    return BrowseResults(
        media=BrowseMediaItem(
            title="Library",
            media_class=MediaClass.DIRECTORY,
            media_type="library",
            media_id=f"library_{library_id}",
            can_browse=True,
            can_search=True,
            items=items,
        ),
        pagination=Pagination(page=page, limit=limit, count=total),
    )


async def _browse_folder(device: EmbyServer, folder_id: str, options: BrowseOptions) -> BrowseResults:
    page = options.paging.page if hasattr(options, "paging") and options.paging and hasattr(options.paging, "page") and options.paging.page else 1
    limit = options.paging.limit if hasattr(options, "paging") and options.paging and hasattr(options.paging, "limit") and options.paging.limit else 50

    start_index = (page - 1) * limit
    result = await device.client.get_items(device.user_id, parent_id=folder_id, start_index=start_index, limit=limit)

    total = result.get("TotalRecordCount", 0)
    emby_items = result.get("Items", [])

    items = []
    for item in emby_items:
        media_item = _item_to_browse_item(device, item)
        if media_item:
            items.append(media_item)

    return BrowseResults(
        media=BrowseMediaItem(
            title="Folder",
            media_class=MediaClass.DIRECTORY,
            media_type="folder",
            media_id=f"folder_{folder_id}",
            can_browse=True,
            items=items,
        ),
        pagination=Pagination(page=page, limit=limit, count=total),
    )


def _item_to_browse_item(device: EmbyServer, item: dict) -> BrowseMediaItem | None:
    item_id = item.get("Id", "")
    item_name = item.get("Name", "")
    item_type = item.get("Type", "")

    if not item_id or not item_name:
        return None

    media_class = EMBY_TYPE_TO_MEDIA_CLASS.get(item_type, MediaClass.VIDEO)
    is_playable = item_type in PLAYABLE_TYPES
    is_browsable = item_type in BROWSABLE_TYPES

    if is_playable:
        media_id = f"item_{item_id}"
    elif is_browsable:
        media_id = f"folder_{item_id}"
    else:
        media_id = f"folder_{item_id}"
        is_browsable = True

    thumbnail = ""
    if "Primary" in item.get("ImageTags", {}):
        thumbnail = device.build_image_url(item_id)

    title = item_name
    if item_type == "Episode":
        series = item.get("SeriesName", "")
        season_num = item.get("ParentIndexNumber")
        episode_num = item.get("IndexNumber")
        if series and season_num is not None and episode_num is not None:
            title = f"{series} - S{season_num:02d}E{episode_num:02d} - {item_name}"
    elif item_type == "Movie":
        year = item.get("ProductionYear")
        if year:
            title = f"{item_name} ({year})"

    return BrowseMediaItem(
        title=title,
        media_class=media_class,
        media_type=item_type.lower(),
        media_id=media_id,
        can_browse=is_browsable,
        can_play=is_playable,
        thumbnail=thumbnail,
    )
