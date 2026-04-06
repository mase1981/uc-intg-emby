"""Emby integration driver. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from ucapi_framework import BaseIntegrationDriver

from .config import EmbyDeviceConfig
from .device import EmbyServer
from .sensor import EmbyActiveSessionsSensor, EmbyServerNameSensor, EmbyServerVersionSensor


class EmbyDriver(BaseIntegrationDriver[EmbyServer, EmbyDeviceConfig]):
    """Emby Media Server integration driver."""

    def __init__(self) -> None:
        super().__init__(
            device_class=EmbyServer,
            entity_classes=[
                EmbyServerNameSensor,
                EmbyServerVersionSensor,
                EmbyActiveSessionsSensor,
            ],
            driver_id="uc-intg-emby",
            require_connection_before_registry=True,
        )
