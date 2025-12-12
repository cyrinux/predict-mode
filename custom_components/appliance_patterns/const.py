from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "appliance_patterns"
PLATFORMS: list[Platform] = [Platform.SENSOR]
CONF_APPLIANCES = "appliances"
CONF_SENSORS = "power_sensors"
CONF_ON_POWER = "on_power"
CONF_OFF_POWER = "off_power"
CONF_SAMPLE_INTERVAL = "sample_interval"
CONF_WINDOW_DURATION = "window_duration"
CONF_MIN_RUN_DURATION = "min_run_duration"
CONF_NAME = "name"
CONF_OFF_DELAY = "off_delay"
CONF_PHASE_METHOD = "phase_method"
DEFAULT_ON_POWER = 15.0
DEFAULT_OFF_POWER = 5.0
DEFAULT_SAMPLE_INTERVAL = 5
DEFAULT_WINDOW_DURATION = 1800
DEFAULT_MIN_RUN_DURATION = 300
DEFAULT_OFF_DELAY = 90
DEFAULT_PHASE_METHOD = "slope"
SERVICE_RESET = "reset_patterns"
SERVICE_EXPORT = "export_patterns"
SERVICE_IMPORT = "import_patterns"
ATTR_ENTRY_ID = "entry_id"
ATTR_PAYLOAD = "payload"
ATTR_APPLIANCE = "appliance"
STATE_IDLE = "idle"
STATE_RUNNING = "running"
