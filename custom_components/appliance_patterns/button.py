from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .coordinator import ApplianceRuntimeManager


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    manager: ApplianceRuntimeManager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutoTuneButton(manager, entry)])


class AutoTuneButton(ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, manager: ApplianceRuntimeManager, entry) -> None:
        self._manager = manager
        self._attr_name = f"{entry.title} Auto-calibrage"
        self._attr_unique_id = f"{entry.entry_id}_auto_tune"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Appliance Patterns",
        }

    async def async_press(self) -> None:
        try:
            updates = await self._manager.async_auto_tune()
        except HomeAssistantError as err:
            self.hass.components.persistent_notification.async_create(
                f"Auto-calibrage impossible : {err}", title="Appliance Patterns"
            )
            raise
        self.hass.bus.async_fire(
            f"{DOMAIN}_auto_tuned",
            {
                "entry_id": self._manager.entry.entry_id,
                "settings": updates,
            },
        )
