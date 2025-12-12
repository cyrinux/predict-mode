# Appliance Patterns

Home Assistant custom integration that learns local energy-usage patterns for appliances such as dishwashers, washing machines, or dryers. It records power time series, segments runs automatically, clusters recurring programs, and exposes in real time the detected program, phase, remaining time, and confidence.

## Installation

1. Copy `custom_components/appliance_patterns` into Home Assistant’s `config/custom_components` directory.
2. Restart Home Assistant.
3. Go to *Settings → Devices & Services → Add Integration*, search for **Appliance Patterns**, and follow the wizard.

## Configuration

Each config entry represents one appliance:

| Option | Description |
| --- | --- |
| `name` | Friendly name used for entity labels |
| `power_sensors` | List of power sensors (W) feeding this appliance |
| `on_power` | Power threshold that marks the beginning of a run |
| `off_power` | Threshold below which the appliance is considered idle |
| `off_delay` | Seconds spent under `off_power` before closing a run |
| `sample_interval` | Down-sampling interval in seconds |
| `window_duration` | Detection window (seconds) used for matching |
| `min_run_duration` | Minimum run length (seconds) kept in storage |

Optional YAML example:

```yaml
appliance_patterns:
  appliances:
    - name: dishwasher
      power_sensors:
        - sensor.dishwasher_power
      on_power: 20
      off_power: 5
      off_delay: 120
      sample_interval: 5
      window_duration: 1800
      min_run_duration: 600
```

### Tuning cheat sheet

- `on_power` (W): set it slightly above standby draw (10–20 W for most dishwashers).
- `off_power` (W): keep it just above background noise (3–5 W) and bump it up if runs never end.
- `off_delay` (s): duration the appliance must stay below `off_power` before finishing the run. 60–180 s avoids breaking on short pauses.
- `sample_interval` (s): 5 s balances accuracy and CPU, but can go down to 2–3 s for fast detection.
- `window_duration` (s): longer than your longest program (e.g., 1 800 s for a 30 min run).
- `min_run_duration` (s): filters out spikes (300–600 s works for most appliances).

### Fast recognition tips

- **Immediate reaction**: keep `on_power` low and `off_delay` short (60–90 s) to confirm runs during the first minutes.
- **Compact window**: for 30 min express programs, set `window_duration` to ~900–1 200 s and `sample_interval` to 2–3 s so the sliding window captures the signature quickly.
- **Targeted learning**: run each program at least twice so the model stores clean templates. As soon as the current window looks like a known template, `sensor.<name>_program` publishes the right label and the remaining time becomes reliable.

## Machine-learning pipeline

- **Collection**: sliding window (default 30 min) driven by the selected sensors, with automatic start/stop detection based on thresholds.
- **Pre-processing**: each run is down-sampled, normalized, and stored locally through Home Assistant Storage (no cloud).
- **Pattern discovery**: runs are clustered (DTW distance) and averaged into templates that keep duration, variance envelope, and phase segments.
- **Real-time detection**: the live window is compared to templates via DTW; the best score yields program label, phase, confidence, and `predicted_duration - elapsed`.

## Entities

For an appliance named `dishwasher`:

- `sensor.dishwasher_state`
- `sensor.dishwasher_program`
- `sensor.dishwasher_phase`
- `sensor.dishwasher_time_remaining`
- `sensor.dishwasher_confidence`
- `button.dishwasher_auto_tune` (runs automatic calibration)

## Services

| Service | Description |
| --- | --- |
| `appliance_patterns.reset_patterns` | Clears learned runs/templates for an `entry_id`. |
| `appliance_patterns.export_patterns` | Fires `appliance_patterns_exported` with stored runs/templates. |
| `appliance_patterns.import_patterns` | Imports patterns for an `entry_id` using a payload dict. |
| `appliance_patterns.auto_tune` | Analyses up to five recent runs and recalibrates `on/off_power`, `off_delay`, `sample_interval`, `window_duration`, `min_run_duration`. |

### Auto-calibration flow

- Use the `button.<name>_auto_tune` entity or call `appliance_patterns.auto_tune` with the integration `entry_id`.
- Trigger it right after a full cycle: it computes standby vs active power percentiles, longest pauses, average duration, and updates the config entry options.
- An event `appliance_patterns_auto_tuned` is emitted with the derived settings so you can log or display them (and Home Assistant shows a popup if not enough data is available).

## Lovelace example

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Dishwasher
    entities:
      - sensor.dishwasher_state
      - sensor.dishwasher_program
      - sensor.dishwasher_phase
      - button.dishwasher_auto_tune
  - type: gauge
    name: Confidence
    entity: sensor.dishwasher_confidence
    min: 0
    max: 100
  - type: sensor
    entity: sensor.dishwasher_time_remaining
    graph: line
    detail: 2
```

## Tests

Four test modules cover:

1. Run tracking and start/stop detection (`RunTracker` logic).
2. DTW distance computation.
3. Clustering behavior.
4. Remaining-time prediction.

From the repo root:

```bash
pytest
```

## Authors

- Integration originally developed by @cursor-project.
- Product guidance and contributions by @cyrinux.
