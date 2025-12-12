from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, STATE_IDLE
from .coordinator import ApplianceRuntimeManager, ApplianceRuntimeState


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    manager: ApplianceRuntimeManager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ApplianceStateSensor(manager, entry),
        ApplianceProgramSensor(manager, entry),
        AppliancePhaseSensor(manager, entry),
        ApplianceTimeRemainingSensor(manager, entry),
        ApplianceConfidenceSensor(manager, entry),
    ]
    async_add_entities(entities)


class AppliancePatternsEntity(SensorEntity):
    _attr_should_poll = False

    def __init__(self, manager: ApplianceRuntimeManager, entry, name_suffix: str, unique_suffix: str) -> None:
        self._manager = manager
        self._attr_name = f"{entry.title} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Patterns",
        )
        self._unsubscribe = None

    async def async_added_to_hass(self) -> None:
        self._unsubscribe = self._manager.coordinator.async_add_listener(self._handle_coordinator_update)
        self.async_on_remove(self._unsubscribe)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def coordinator_state(self) -> ApplianceRuntimeState:
        return self._manager.coordinator.data


class ApplianceStateSensor(AppliancePatternsEntity):
    def __init__(self, manager: ApplianceRuntimeManager, entry) -> None:
        super().__init__(manager, entry, "Etat", "state")

    @property
    def native_value(self) -> str:
        return self.coordinator_state.state or STATE_IDLE


class ApplianceProgramSensor(AppliancePatternsEntity):
    def __init__(self, manager: ApplianceRuntimeManager, entry) -> None:
        super().__init__(manager, entry, "Programme", "program")

    @property
    def native_value(self) -> str | None:
        return self.coordinator_state.program


class AppliancePhaseSensor(AppliancePatternsEntity):
    def __init__(self, manager: ApplianceRuntimeManager, entry) -> None:
        super().__init__(manager, entry, "Phase", "phase")

    @property
    def native_value(self) -> str | None:
        return self.coordinator_state.phase


class ApplianceTimeRemainingSensor(AppliancePatternsEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, manager: ApplianceRuntimeManager, entry) -> None:
        super().__init__(manager, entry, "Temps restant", "time_remaining")

    @property
    def native_value(self) -> float | None:
        remaining = self.coordinator_state.time_remaining
        if remaining is None:
            return None
        return round(remaining / 60, 1)


class ApplianceConfidenceSensor(AppliancePatternsEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, manager: ApplianceRuntimeManager, entry) -> None:
        super().__init__(manager, entry, "Confiance", "confidence")

    @property
    def native_value(self) -> float:
        return round(self.coordinator_state.confidence * 100, 1)
