# PolandAirQualityAnalyzer

## Running

```bash
# Default: generate GIFs then launch the dashboard
.venv/bin/python main.py

# Dashboard only
.venv/bin/python main.py dashboard

# GIF export only
.venv/bin/python main.py gifs
```

Open **http://127.0.0.1:8050** after the dashboard starts.

First startup parses new JSON files (~10 s); subsequent runs load instantly from the Parquet cache.
Use `DevMode: true` in `appsettings.yml` (or `DEV=true` env var) for a fast 3-day slice during development.

---

## Interactive Dashboard

### Map
- Station dots colored by the selected metric (PM2.5, PM10, Temperature, Humidity, Pressure)
- Each metric has its own color scale (green → yellow → red for pollutants, blue → red for temperature, etc.)
- Hover a dot for a full readings tooltip

### Timeline
- Slider across all snapshots — drag or hit **▶ Play** to animate
- Adjustable playback speed (Slow / Med / Fast)

### Station side panel
Click any dot to open the side panel:
- Station name, city, postcode, street address
- AQI badge (Good / Moderate / Unhealthy / Hazardous)
- Current readings for all five metrics
- **Sparkline charts** (last 96 snapshots up to the current slider position) for every metric, with value-coloured markers matching the map colorscale
- Panel updates live as the slider moves or animation plays

### Full-history modal
The **⤢** button (top-right of the side panel, lights up once a station is selected) opens a full-screen overlay with the **complete station history** for all five metrics:
- Drag left/right to pan through the full timeline
- Use the range-slider bar at the bottom of each chart to jump anywhere
- Scroll to zoom in/out
- Default view shows the last 4 days; scrub left for older data

---

## Animated GIFs

`python main.py gifs` exports four files to `output/`:

| File                   | Contents                             |
|------------------------|--------------------------------------|
| `pm25_map.gif`         | PM2.5 levels animated across Poland  |
| `temperature_map.gif`  | Temperature map animation            |
| `bar_race.gif`         | Bar-chart race of top stations       |
| `daily_heatmap.gif`    | Daily rhythm heatmap                 |

---

## Config Guide

## How configuration works

- `appsettings.yml` stores the actual values.
- `config_loader.py` reads that YAML file.
- `configuration.py` turns the loaded mapping into a `Configuration` object.
- `main.py` uses `configuration.config` by default, so you can also pass a custom config in tests.

## Plan for adding a new config variable

1. Open `appsettings.yml`.
2. Add a new top-level key/value pair.
3. Use it from `configuration` as an attribute.
4. If you want the field to be explicitly typed and visible in code completion, add it to the `Configuration` dataclass in `configuration.py`.

## Example

### 1) Add it in `appsettings.yml`

```yaml
DataFolderPath: "../PolandAirQualityData/data/"
DevMode: true
CacheEnabled: true
MaxRetries: 3
```

### 2) Use it in Python

```python
import configuration

print(configuration.DataFolderPath)
print(configuration.DevMode)
print(configuration.CacheEnabled)
print(configuration.MaxRetries)
```

### 3) Make it explicit in the config class

If you want the new setting to be part of the main config object, add a field in `configuration.py`:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class Configuration:
    DataFolderPath: str
    DevMode: bool
    CacheEnabled: bool = False
    MaxRetries: int = 3
    extra: dict[str, Any] = field(default_factory=dict, repr=False)
```

Then update `from_mapping()` so it pulls those values out of the YAML mapping.

## Recommended workflow

- For quick settings: add the key to `appsettings.yml` and read it through `configuration.<Name>`.
- For important settings: add a typed field to `Configuration` so the setting is explicit and easier to maintain.
- Keep loader logic in `config_loader.py`; keep app-facing config access in `configuration.py`.

