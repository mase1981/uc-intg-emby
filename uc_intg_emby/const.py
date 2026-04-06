"""Emby integration constants. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""

EMBY_POLL_INTERVAL = 5
EMBY_API_TIMEOUT = 10
EMBY_CONNECTION_TIMEOUT = 5
EMBY_TICKS_PER_SECOND = 10_000_000

EMBY_COMMAND_FALLBACKS: dict[str, list[str]] = {
    "PlayPause": ["PlayPause", "Select"],
    "Stop": ["Stop", "Back"],
    "NextTrack": ["NextTrack", "NextLetter"],
    "PreviousTrack": ["PreviousTrack", "PreviousLetter"],
    "FastForward": ["FastForward", "MoveRight"],
    "Rewind": ["Rewind", "MoveLeft"],
}
