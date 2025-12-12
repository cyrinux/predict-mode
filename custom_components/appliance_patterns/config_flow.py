from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
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
)


class AppliancePatternsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = slugify(user_input[CONF_NAME])
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_SENSORS): selector.selector(
                    {"entity": {"domain": "sensor", "device_class": "power", "multiple": True}}
                ),
                vol.Optional(CONF_ON_POWER, default=DEFAULT_ON_POWER): vol.Coerce(float),
                vol.Optional(CONF_OFF_POWER, default=DEFAULT_OFF_POWER): vol.Coerce(float),
                vol.Optional(CONF_OFF_DELAY, default=DEFAULT_OFF_DELAY): vol.Coerce(float),
                vol.Optional(CONF_SAMPLE_INTERVAL, default=DEFAULT_SAMPLE_INTERVAL): vol.Coerce(int),
                vol.Optional(CONF_WINDOW_DURATION, default=DEFAULT_WINDOW_DURATION): vol.Coerce(int),
                vol.Optional(CONF_MIN_RUN_DURATION, default=DEFAULT_MIN_RUN_DURATION): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_import(self, user_input: dict) -> FlowResult:
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return AppliancePatternsOptionsFlowHandler(entry)


class AppliancePatternsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = self.entry.options or {}
        data = self.entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_ON_POWER, default=options.get(CONF_ON_POWER, data.get(CONF_ON_POWER, DEFAULT_ON_POWER))): vol.Coerce(float),
                vol.Required(CONF_OFF_POWER, default=options.get(CONF_OFF_POWER, data.get(CONF_OFF_POWER, DEFAULT_OFF_POWER))): vol.Coerce(float),
                vol.Required(CONF_OFF_DELAY, default=options.get(CONF_OFF_DELAY, data.get(CONF_OFF_DELAY, DEFAULT_OFF_DELAY))): vol.Coerce(float),
                vol.Required(
                    CONF_SAMPLE_INTERVAL,
                    default=options.get(CONF_SAMPLE_INTERVAL, data.get(CONF_SAMPLE_INTERVAL, DEFAULT_SAMPLE_INTERVAL)),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_WINDOW_DURATION,
                    default=options.get(CONF_WINDOW_DURATION, data.get(CONF_WINDOW_DURATION, DEFAULT_WINDOW_DURATION)),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_MIN_RUN_DURATION,
                    default=options.get(CONF_MIN_RUN_DURATION, data.get(CONF_MIN_RUN_DURATION, DEFAULT_MIN_RUN_DURATION)),
                ): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="options", data_schema=schema)
