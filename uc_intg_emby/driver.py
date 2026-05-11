"""Emby integration driver. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
from ucapi_framework import BaseIntegrationDriver

from uc_intg_emby.config import EmbyDeviceConfig
from uc_intg_emby.device import EmbyServer
from uc_intg_emby.sensor import (
    EmbyActiveSessionsSensor,
    EmbyServerNameSensor,
    EmbyServerOSSensor,
    EmbyServerURLSensor,
    EmbyServerVersionSensor,
)


class EmbyDriver(BaseIntegrationDriver[EmbyServer, EmbyDeviceConfig]):
    """Emby Media Server integration driver."""

    def __init__(self) -> None:
        super().__init__(
            device_class=EmbyServer,
            entity_classes=[
                EmbyServerNameSensor,
                EmbyServerVersionSensor,
                EmbyActiveSessionsSensor,
                EmbyServerURLSensor,
                EmbyServerOSSensor,
            ],
            driver_id="uc-intg-emby",
            require_connection_before_registry=True,
        )
