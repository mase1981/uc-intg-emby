"""Emby configuration. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from dataclasses import dataclass, field
from ucapi_framework import BaseConfigManager


@dataclass
class EmbyDeviceConfig:
    """Emby server device configuration."""

    identifier: str
    name: str
    server_url: str
    api_key: str
    user_id: str = ""
    server_version: str = ""
