# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Loads Poland air quality JSON snapshots from a smog API, caches them as Parquet, and renders four animated GIFs: a PM2.5 geographic map, a temperature map, a bar chart race of most-polluted cities, and a daily rhythm heatmap.

## Running the project

```bash
python main.py
```

Outputs four GIFs to `output/` (`pm25_map.gif`, `temperature_map.gif`, `bar_race.gif`, `daily_heatmap.gif`).

**Dev mode** (loads only the 3 most recent days from cache — fast restarts):
```bash
# Either set in appsettings.yml:
#   DevMode: true
# Or via env var:
DEV=true python main.py
```

**Force cache rebuild** (after model or parsing changes):
```python
from smogloader import load_snapshot_dir
result = load_snapshot_dir("../PolandAirQualityData/data/", rebuild_cache=True)
```

## Dependencies

No `requirements.txt` exists. Required packages: `pandas`, `pydantic` (v2), `matplotlib`, `Pillow`, `pyyaml`. Optional speedup: `orjson` (falls back to stdlib `json` if absent).

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

visualizations.py        ← four GIF generator functions; each takes (df, output_path)
main.py                  ← calls load_snapshot_dir then all four generators
```

**Two similarly-named files:**
- `visualization.py` (singular) — legacy exploratory script, hardcoded paths, calls `plt.show()`. Not part of the production pipeline.
- `visualizations.py` (plural) — production module with all four GIF generators.

**`appsettings.py`** is a compatibility shim that re-exports from `configuration.py`. Prefer importing from `configuration` directly in new code.

## Data layout

Raw snapshot files live in a **sibling repository** at `../PolandAirQualityData/data/`, not in this repo. Files are named `smog_api_YYYY-MM-DD-HH-MM-SS-TZ`. The Parquet cache (`.smog_cache.parquet`) is written into that same data directory.

## Adding a new config key

1. Add the key/value to `appsettings.yml`.
2. Add a typed field to the `Configuration` dataclass in `configuration.py` and update `from_mapping()`.
3. Access it anywhere via `configuration.<KeyName>` or `config.<KeyName>`.

## Adding a new visualization

1. Write a `generate_<name>(df: pd.DataFrame, output_path: Path, ...) -> Path` function in `visualizations.py`.
2. Use `_daily_frames()` to get one representative snapshot per calendar day, `_geo_axes()` for map frames, `_save_gif()` to write the output.
3. Import and call it in `main.py`.
