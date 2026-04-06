"""Emby sensor entities. :copyright: (c) 2026 by Meir Miyara. :license: MPL-2.0"""
import logging

from ucapi import sensor
from ucapi_framework import SensorEntity

from .config import EmbyDeviceConfig
from .device import EmbyServer

_LOG = logging.getLogger(__name__)


class EmbyServerNameSensor(SensorEntity):
    """Sensor showing the Emby server name."""

    def __init__(self, device_config: EmbyDeviceConfig, device: EmbyServer) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.server_name"
        super().__init__(
            entity_id,
            f"{device_config.name} Server Name",
            features=[],
            attributes={
                sensor.Attributes.STATE: sensor.States.UNKNOWN,
                sensor.Attributes.VALUE: "",
            },
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._device.server_name or "Unknown",
        })


class EmbyServerVersionSensor(SensorEntity):
    """Sensor showing the Emby server version."""

    def __init__(self, device_config: EmbyDeviceConfig, device: EmbyServer) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.server_version"
        super().__init__(
            entity_id,
            f"{device_config.name} Server Version",
            features=[],
            attributes={
                sensor.Attributes.STATE: sensor.States.UNKNOWN,
                sensor.Attributes.VALUE: "",
            },
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._device.server_version or "Unknown",
        })


class EmbyActiveSessionsSensor(SensorEntity):
    """Sensor showing the number of active Emby sessions."""

    def __init__(self, device_config: EmbyDeviceConfig, device: EmbyServer) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.active_sessions"
        super().__init__(
            entity_id,
            f"{device_config.name} Active Sessions",
            features=[],
            attributes={
                sensor.Attributes.STATE: sensor.States.UNKNOWN,
                sensor.Attributes.VALUE: "",
            },
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: "sessions"},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: str(self._device.active_session_count),
        })
