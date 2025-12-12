from __future__ import annotations

from collections.abc import Mapping

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ENTRY_ID,
    ATTR_PAYLOAD,
    CONF_APPLIANCES,
    CONF_MIN_RUN_DURATION,
    CONF_NAME,
    CONF_OFF_DELAY,
    CONF_OFF_POWER,
    CONF_ON_POWER,
    CONF_SAMPLE_INTERVAL,
    CONF_SENSORS,
    CONF_WINDOW_DURATION,
    DEFAULT_MIN_RUN_DURATION,
    DEFAULT_OFF_DELAY,
    DEFAULT_OFF_POWER,
    DEFAULT_ON_POWER,
    DEFAULT_SAMPLE_INTERVAL,
    DEFAULT_WINDOW_DURATION,
    DOMAIN,
    PLATFORMS,
    SERVICE_EXPORT,
    SERVICE_IMPORT,
    SERVICE_RESET,
)
from .coordinator import ApplianceRuntimeManager

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_APPLIANCES): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required(CONF_NAME): cv.string,
                                vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [cv.entity_id]),
                                vol.Optional(CONF_ON_POWER, default=DEFAULT_ON_POWER): vol.Coerce(float),
                                vol.Optional(CONF_OFF_POWER, default=DEFAULT_OFF_POWER): vol.Coerce(float),
                                vol.Optional(CONF_OFF_DELAY, default=DEFAULT_OFF_DELAY): vol.Coerce(float),
                                vol.Optional(CONF_SAMPLE_INTERVAL, default=DEFAULT_SAMPLE_INTERVAL): cv.positive_int,
                                vol.Optional(CONF_WINDOW_DURATION, default=DEFAULT_WINDOW_DURATION): cv.positive_int,
                                vol.Optional(CONF_MIN_RUN_DURATION, default=DEFAULT_MIN_RUN_DURATION): cv.positive_int,
                            }
                        )
                    ],
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_ENTRY_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string})
SERVICE_IMPORT_SCHEMA = SERVICE_ENTRY_SCHEMA.extend({vol.Required(ATTR_PAYLOAD): dict})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("services_registered", False)
    yaml_config = config.get(DOMAIN)
    if yaml_config:
        for appliance in yaml_config.get(CONF_APPLIANCES, []):
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_IMPORT},
                    data=appliance,
                )
            )
    if not hass.data[DOMAIN]["services_registered"]:
        _register_services(hass)
        hass.data[DOMAIN]["services_registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = _entry_config(entry)
    manager = ApplianceRuntimeManager(hass, entry, config)
    await manager.async_setup()
    hass.data[DOMAIN][entry.entry_id] = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager: ApplianceRuntimeManager | None = hass.data[DOMAIN].get(entry.entry_id)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if manager:
        await manager.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


def _entry_config(entry: ConfigEntry) -> dict:
    base: Mapping = entry.data
    options: Mapping = entry.options
    config = {
        CONF_NAME: base.get(CONF_NAME, entry.title),
        CONF_SENSORS: base.get(CONF_SENSORS, []),
        CONF_ON_POWER: options.get(CONF_ON_POWER, base.get(CONF_ON_POWER, DEFAULT_ON_POWER)),
        CONF_OFF_POWER: options.get(CONF_OFF_POWER, base.get(CONF_OFF_POWER, DEFAULT_OFF_POWER)),
        CONF_OFF_DELAY: options.get(CONF_OFF_DELAY, base.get(CONF_OFF_DELAY, DEFAULT_OFF_DELAY)),
        CONF_SAMPLE_INTERVAL: options.get(CONF_SAMPLE_INTERVAL, base.get(CONF_SAMPLE_INTERVAL, DEFAULT_SAMPLE_INTERVAL)),
        CONF_WINDOW_DURATION: options.get(CONF_WINDOW_DURATION, base.get(CONF_WINDOW_DURATION, DEFAULT_WINDOW_DURATION)),
        CONF_MIN_RUN_DURATION: options.get(
            CONF_MIN_RUN_DURATION, base.get(CONF_MIN_RUN_DURATION, DEFAULT_MIN_RUN_DURATION)
        ),
    }
    config["power_sensors"] = config[CONF_SENSORS]
    config["on_power"] = config[CONF_ON_POWER]
    config["off_power"] = config[CONF_OFF_POWER]
    config["off_delay"] = config[CONF_OFF_DELAY]
    config["sample_interval"] = config[CONF_SAMPLE_INTERVAL]
    config["window_duration"] = config[CONF_WINDOW_DURATION]
    config["min_run_duration"] = config[CONF_MIN_RUN_DURATION]
    return config


def _register_services(hass: HomeAssistant) -> None:
    async def _async_require_manager(call: ServiceCall) -> ApplianceRuntimeManager:
        entry_id = call.data[ATTR_ENTRY_ID]
        manager = hass.data[DOMAIN].get(entry_id)
        if not manager:
            raise ValueError(f"Integration entry {entry_id} introuvable")
        return manager

    async def _async_reset(call: ServiceCall) -> None:
        manager = await _async_require_manager(call)
        await manager.async_reset_patterns()

    async def _async_export(call: ServiceCall) -> None:
        manager = await _async_require_manager(call)
        payload = manager.export()
        hass.bus.async_fire(
            f"{DOMAIN}_exported",
            {
                ATTR_ENTRY_ID: call.data[ATTR_ENTRY_ID],
                ATTR_PAYLOAD: payload,
            },
        )

    async def _async_import(call: ServiceCall) -> None:
        manager = await _async_require_manager(call)
        await manager.async_import(call.data[ATTR_PAYLOAD])

    hass.services.async_register(DOMAIN, SERVICE_RESET, _async_reset, schema=SERVICE_ENTRY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT, _async_export, schema=SERVICE_ENTRY_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_IMPORT, _async_import, schema=SERVICE_IMPORT_SCHEMA)
