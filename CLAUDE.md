# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Loads Poland air quality JSON snapshots from a smog API, caches them as Parquet, and provides:
- **Interactive dashboard** (`app.py`) — a Dash web app with a map, timeline slider, play/pause animation, and clickable station dots
- **Animated GIFs** (`main.py`) — four exported GIFs: PM2.5 map, temperature map, bar chart race, daily rhythm heatmap

## Running the project

**Interactive dashboard (main entry point):**
```bash
.venv/bin/python app.py
# Open http://127.0.0.1:8050
```

**GIF export:**
```bash
.venv/bin/python main.py
```
Outputs `output/pm25_map.gif`, `temperature_map.gif`, `bar_race.gif`, `daily_heatmap.gif`.

**Dev mode** (loads only the 3 most recent days from cache — fast restarts):
```bash
# Either set in appsettings.yml:
#   DevMode: true
# Or via env var:
DEV=true .venv/bin/python app.py
```

**Force cache rebuild** (after model or parsing changes):
```python
from smogloader import load_snapshot_dir
result = load_snapshot_dir("../PolandAirQualityData/data/", rebuild_cache=True)
```

## Dependencies

```bash
pip install -r requirements.txt
```

Key packages: `dash>=4.1` (includes Plotly 6), `pandas>=3.0`, `pyarrow` (Parquet), `pydantic` v2, `matplotlib`, `Pillow`, `PyYAML`. Optional speedup: `orjson` (faster JSON parsing; falls back to stdlib if absent).

## Architecture

```
appsettings.yml          ← config values
config_loader.py         ← reads YAML → dict
configuration.py         ← dict → Configuration dataclass; module-level `config` singleton
                           also re-exports DataFolderPath, DevMode, OutputDir as module attrs

models.py                ← Pydantic v2 models (SmogApiResponse, StationReading, etc.)
                           used for validation; NOT used in the hot loading path
smogloader.py            ← bulk loader: raw JSON → flat dicts → DataFrame → Parquet cache
                           bypasses Pydantic intentionally for performance
                           public API: load_snapshot_dir() → LoadResult(df, failed_files)

app.py                   ← interactive Dash dashboard (main entry point)
                           pre-groups data into _FRAMES (by timestamp) and _STATIONS (by station_id)
                           for O(1) per-frame and per-station lookups at runtime

visualizations.py        ← four GIF generator functions; each takes (df, output_path)
main.py                  ← calls load_snapshot_dir then all four GIF generators
```

**Two similarly-named files:**
- `visualization.py` (singular) — legacy exploratory script, hardcoded paths, calls `plt.show()`. Not part of any pipeline.
- `visualizations.py` (plural) — production module with all four GIF generators.

**`appsettings.py`** is a compatibility shim that re-exports from `configuration.py`. Prefer importing from `configuration` directly in new code.

## Data layout

Raw snapshot files live in a **sibling repository** at `../PolandAirQualityData/data/`, not in this repo. Files are named `smog_api_YYYY-MM-DD-HH-MM-SS-TZ`. The Parquet cache (`.smog_cache.parquet`) is written into that same data directory.

## app.py internals

`app.py` loads the full dataset on startup, then pre-builds two dicts:
- `_FRAMES[timestamp]` → DataFrame of all stations for that snapshot (used by `render_map`)
- `_STATIONS[station_id]` → DataFrame of all snapshots for that station (used by `station_detail` sparkline)

The Dash callbacks are:
- `render_map(idx, metric)` — triggered by slider or metric dropdown; returns a `go.Scattermap` figure
- `station_detail(clickData, idx)` — triggered by clicking a dot; returns the side-panel content
- `toggle_play`, `advance`, `set_speed` — control playback animation

Dark theme is applied via Dash 4's CSS custom properties (`--Dash-Fill-Inverse-Strong` etc.) injected through `app.index_string`.

## Adding a new config key

1. Add the key/value to `appsettings.yml`.
2. Add a typed field to the `Configuration` dataclass in `configuration.py` and update `from_mapping()`.
3. Access it anywhere via `configuration.<KeyName>` or `config.<KeyName>`.

## Adding a new visualization

**GIF:** write a `generate_<name>(df, output_path) -> Path` in `visualizations.py`, using `_daily_frames()`, `_geo_axes()`, and `_save_gif()`. Call it in `main.py`.

**Dashboard metric:** add an entry to the `METRICS` dict in `app.py` with `label`, `unit`, `vmin`, `vmax`, and `colorscale`. It will appear automatically in the dropdown.
