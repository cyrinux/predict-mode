---

# 🚀 **Cursor Prompt — Home Assistant Learning Integration**

**Project:**
Build a Home Assistant custom integration that **learns** and **recognizes appliance energy-consumption patterns** (dishwasher, washing machine, dryer, etc.).
The integration must automatically detect running cycles, identify which program is in progress, and estimate time remaining based solely on the power-usage curve.

---

## **Core Requirements**

### **1. Integration structure**

Create a complete HA custom component:

```
custom_components/appliance_patterns/
  __init__.py
  manifest.json
  config_flow.py
  sensor.py
  coordinator.py
  ml/
    model.py
    dtw.py
    clustering.py
    feature_extraction.py
  storage/
    db.py
```

- Configurable in UI (Config Flow) and via YAML.
- Allow selecting one or more power sensors as input.
- Local storage using SQLite or HA storage API.

---

## **2. Data collection**

- Continuously record the time-series (W) from selected sensors.
- Downsample (e.g. 1 sample / 5s).
- Store sequences for each detected run.
- Detect run boundaries automatically (on/off threshold, stats, slope).

---

## **3. Machine Learning**

Implement fully local ML, no cloud:

- **Pattern discovery**
  Use clustering on recorded runs (DBSCAN or Agglomerative).
- **Similarity matching**
  Use DTW (Dynamic Time Warping) to compare active sliding window vs learned patterns.
- **Phase detection**
  Segment patterns by derivative/slope change or clustering.
- **Prediction**
  Estimate remaining time:

  ```
  predicted_total_duration - elapsed
  ```

- Maintain:
  - per-appliance pattern templates
  - variance envelope
  - average duration

Models must continually improve over time.

---

## **4. Realtime detection**

- Use a sliding window of recent power samples.
- Compare against all known patterns.
- Pick best match based on DTW distance.
- Expose confidence (0–1).
- Detect transitions between phases.

---

## **5. Exposed Home Assistant entities**

For each appliance:

- `sensor.<name>_program`
- `sensor.<name>_phase`
- `sensor.<name>_time_remaining`
- `sensor.<name>_confidence`
- `sensor.<name>_state` (idle / running)

---

## **6. Services**

Provide HA services:

- `appliance_patterns.reset_patterns`
- `appliance_patterns.export_patterns`
- `appliance_patterns.import_patterns`

---

## **7. Performance**

- Must run on Raspberry Pi 4 with no GPU.
- Keep CPU load low.
- Use incremental models, avoid large matrices.

---

## **8. Documentation**

Generate:

- A full `README.md`
- Installation steps
- Explanation of the ML approach
- Example Lovelace dashboard cards

---

## **9. Testing**

- Unit tests for data collection logic
- Tests for DTW matching
- Tests for pattern clustering
- Tests for time-remaining prediction

---

## **Constraints**

- No placeholder code.
- No comments unless strictly needed.
- Code must be directly runnable in Home Assistant.
- Use modern Python.
- Produce all files automatically.

---

If you want, I can also generate:

✅ a complete **Cursor task plan** (`cursor.json`)
✅ the **initial directory tree with stubs**
✅ the **first working version of the plugin**

Tell me what you want next.
