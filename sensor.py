"""Sensor definitions for Cudy Router."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation, UnitOfTime, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN, MODULE_BANDWIDTH, MODULE_LAN, MODULE_SYSTEM, MODULE_DEVICES,
    MODULE_SYSTEM_STATUS, MODULE_WAN, MODULE_WIRELESS,
)

@dataclass
class CudySensorEntityDescription(SensorEntityDescription):
    module: str = None
    value_fn: Callable[[dict], Any] = None

SENSOR_TYPES: tuple[CudySensorEntityDescription, ...] = (
    CudySensorEntityDescription(
        key="eth0_download_speed", name="Download Speed", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:download-network", value_fn=lambda data: data.get("download_mbps"),
    ),
    CudySensorEntityDescription(
        key="eth0_upload_speed", name="Upload Speed", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:upload-network", value_fn=lambda data: data.get("upload_mbps"),
    ),
    CudySensorEntityDescription(
        key="eth0_download_total", name="Download Total", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:download-circle", value_fn=lambda data: data.get("download_total_gb"),
    ),
    CudySensorEntityDescription(
        key="eth0_upload_total", name="Upload Total", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:upload-circle", value_fn=lambda data: data.get("upload_total_gb"),
    ),
    CudySensorEntityDescription(
        key="firmware_version", name="Firmware Version", module=MODULE_SYSTEM,
        icon="mdi:chip", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("firmware"),
    ),
    CudySensorEntityDescription(
        key="hardware_version", name="Hardware Version", module=MODULE_SYSTEM,
        icon="mdi:server", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("hardware"),
    ),
    CudySensorEntityDescription(
        key="lan_ip", name="LAN IP Address", module=MODULE_LAN,
        icon="mdi:ip-network", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("ip_address"),
    ),
    CudySensorEntityDescription(
        key="lan_uptime", name="Connected Time", module=MODULE_LAN,
        icon="mdi:clock-check", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("connected_time"),
    ),
    CudySensorEntityDescription(
        key="device_count", name="Total Devices Connected", module=MODULE_DEVICES,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:devices",
        value_fn=lambda data: data.get("device_count", {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="wifi_device_count", name="WiFi Devices Connected", module=MODULE_DEVICES,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:wifi",
        value_fn=lambda data: data.get("wifi_device_count", {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="eth_device_count", name="Ethernet Devices Connected", module=MODULE_DEVICES,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:lan",
        value_fn=lambda data: data.get("eth_device_count", {}).get("value"),
    ),
    # System status
    CudySensorEntityDescription(
        key="uptime", name="Uptime", module=MODULE_SYSTEM_STATUS,
        icon="mdi:timer-outline", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("uptime"),
    ),
    CudySensorEntityDescription(
        key="uptime_seconds", name="Uptime Seconds", module=MODULE_SYSTEM_STATUS,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:timer", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("uptime_seconds"),
    ),
    # WAN
    CudySensorEntityDescription(
        key="wan_status", name="WAN Status", module=MODULE_WAN,
        icon="mdi:wan", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("wan_status"),
    ),
    CudySensorEntityDescription(
        key="wan_ip", name="WAN IP Address", module=MODULE_WAN,
        icon="mdi:ip-network-outline", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("wan_ip"),
    ),
    CudySensorEntityDescription(
        key="wan_protocol", name="WAN Protocol", module=MODULE_WAN,
        icon="mdi:protocol", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("wan_protocol"),
    ),
    # Wireless 2.4G
    CudySensorEntityDescription(
        key="wifi_24g_ssid", name="WiFi 2.4G SSID", module=MODULE_WIRELESS,
        icon="mdi:wifi", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("ssid_24g"),
    ),
    CudySensorEntityDescription(
        key="wifi_24g_channel", name="WiFi 2.4G Channel", module=MODULE_WIRELESS,
        icon="mdi:access-point", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("channel_24g"),
    ),
    CudySensorEntityDescription(
        key="wifi_24g_status", name="WiFi 2.4G Status", module=MODULE_WIRELESS,
        icon="mdi:wifi-check", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status_24g"),
    ),
    # Wireless 5G
    CudySensorEntityDescription(
        key="wifi_5g_ssid", name="WiFi 5G SSID", module=MODULE_WIRELESS,
        icon="mdi:wifi", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("ssid_5g"),
    ),
    CudySensorEntityDescription(
        key="wifi_5g_channel", name="WiFi 5G Channel", module=MODULE_WIRELESS,
        icon="mdi:access-point", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("channel_5g"),
    ),
    CudySensorEntityDescription(
        key="wifi_5g_status", name="WiFi 5G Status", module=MODULE_WIRELESS,
        icon="mdi:wifi-check", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status_5g"),
    ),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [CudyGenericSensor(coordinator, desc) for desc in SENSOR_TYPES]
    sensors.append(CudyConnectedDevicesSensor(coordinator))
    async_add_entities(sensors)

class CudyGenericSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"cudy_{coordinator.host}_{description.key}"
        self._attr_name = f"Cudy {coordinator.host} {description.name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Cudy Router {coordinator.host}",
            "manufacturer": "Cudy",
        }

    @property
    def native_value(self):
        module_data = self.coordinator.data.get(self.entity_description.module)
        return self.entity_description.value_fn(module_data) if module_data else None

class CudyConnectedDevicesSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"cudy_{coordinator.host}_connected_devices"
        self._attr_name = f"Cudy {coordinator.host} Connected Devices List"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.host)}}

    @property
    def native_value(self):
        return self.coordinator.data.get(MODULE_DEVICES, {}).get("connected_devices", {}).get("value")

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get(MODULE_DEVICES, {}).get("connected_devices", {}).get("attributes", {})
