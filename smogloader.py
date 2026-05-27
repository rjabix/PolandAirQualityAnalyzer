"""
Loader for directories of smog API snapshot files.

Each file is one point-in-time dump from the smog API, named like:
    smog_api_2026-03-18-18-19-34-CET

HOW SPEED WORKS
---------------
First run (cold):
    JSON files → fast-path parser (orjson, no Pydantic overhead) → Parquet cache
    Slow, but only happens once per file.

Subsequent runs (warm):
    Parquet cache → DataFrame in milliseconds.
    Only files added since the last run go through the slow path.

Typical usage:
    from smog_loader import load_snapshot_dir

    result = load_snapshot_dir("data/snapshots/")
    df = result.df

    # Force a full rebuild (e.g. after a model change):
    result = load_snapshot_dir("data/snapshots/", rebuild_cache=True)
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Cache filename written next to the snapshot directory
_CACHE_FILENAME = ".smog_cache.parquet"

# Matches: smog_api_2026-03-18-18-19-34-CET  (timezone suffix optional)
_FILENAME_TIMESTAMP_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})(?:-[A-Z]+)?$"
)

# ---------------------------------------------------------------------------
# Fast-path parser — bypasses Pydantic entirely for bulk loading.
# Pydantic is great for validation; for trusted local files it's unnecessary
# overhead.  We use orjson (if available) or stdlib json as fallback.
# ---------------------------------------------------------------------------
try:
    import orjson as _json_lib
    def _loads(text: str | bytes) -> dict:
        return _json_lib.loads(text)
    logger.debug("Using orjson for JSON parsing.")
except ImportError:
    import json as _json_lib  # type: ignore[no-redef]
    def _loads(text: str | bytes) -> dict:
        return _json_lib.loads(text)
    logger.debug("orjson not installed; using stdlib json. pip install orjson for a speedup.")


def _parse_timestamp_from_filename(path: Path) -> datetime | None:
    match = _FILENAME_TIMESTAMP_RE.search(path.stem)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        return None


def _file_to_records(path: Path) -> list[dict]:
    """
    Parse one snapshot file into a list of flat dicts.
    Fast path: orjson + manual field extraction, no Pydantic instantiation.
    """
    text = path.read_bytes()
    if not text.strip():
        logger.debug("Empty file, skipping: %s", path.name)
        return []

    payload = _loads(text)
    file_ts = _parse_timestamp_from_filename(path)

    records = []
    for entry in payload.get("smog_data", []):
        school = entry.get("school", {})
        data   = entry.get("data", {})

        # Skip test stations inline — faster than a post-hoc DataFrame filter
        city = (school.get("city") or "")
        if "TEST" in city.upper():
            continue

        # Coordinates are strings in the source JSON
        try:
            lat = float(school.get("latitude") or 0)
            lon = float(school.get("longitude") or 0)
        except (TypeError, ValueError):
            lat = lon = None

        street = school.get("street") or None
        if street is not None and street.strip() == "":
            street = None

        post_code   = school.get("post_code", "")
        name        = school.get("name", "")
        station_id  = f"{post_code}_{name}"

        pm25 = data.get("pm25_avg")
        if pm25 is None:
            aqi = None
        elif pm25 < 10:
            aqi = "Good"
        elif pm25 < 25:
            aqi = "Moderate"
        elif pm25 < 50:
            aqi = "Unhealthy"
        else:
            aqi = "Hazardous"

        # Timestamp: prefer filename, fall back to the value in JSON
        raw_ts = entry.get("timestamp")
        if file_ts is not None:
            ts = file_ts
        elif raw_ts:
            try:
                ts = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts = None
        else:
            ts = None

        records.append({
            "station_id":       station_id,
            "station_name":     name,
            "city":             city,
            "post_code":        post_code,
            "street":           street,
            "latitude":         lat,
            "longitude":        lon,
            "timestamp":        raw_ts,
            "file_timestamp":   ts,
            "source_file":      path.name,
            "humidity_avg":     data.get("humidity_avg"),
            "pressure_avg":     data.get("pressure_avg"),
            "temperature_avg":  data.get("temperature_avg"),
            "pm10_avg":         data.get("pm10_avg"),
            "pm25_avg":         pm25,
            "air_quality_index": aqi,
        })

    return records


def _load_fresh(files: list[Path], workers: int) -> tuple[pd.DataFrame, list[tuple[Path, Exception]]]:
    """Parse a list of raw JSON snapshot files in parallel."""
    all_records: list[dict] = []
    failed: list[tuple[Path, Exception]] = []

    def _safe_load(p: Path) -> list[dict] | Exception:
        try:
            return _file_to_records(p)
        except Exception as exc:  # noqa: BLE001
            return exc

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_safe_load, f): f for f in files}
        for future in as_completed(futures):
            path = futures[future]
            result = future.result()
            if isinstance(result, Exception):
                logger.warning("Skipping %s: %s", path.name, result)
                failed.append((path, result))
            else:
                all_records.extend(result)

    if not all_records:
        return _empty_dataframe(), failed

    df = pd.DataFrame(all_records)
    df["file_timestamp"] = pd.to_datetime(df["file_timestamp"])
    df["timestamp"]      = pd.to_datetime(df["timestamp"])
    return df, failed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class LoadResult:
    """Outcome of loading a directory of snapshot files."""

    df: pd.DataFrame
    """Tidy DataFrame: one row per station per snapshot, sorted by time."""

    failed_files: list[tuple[Path, Exception]] = field(default_factory=list)
    """Files that could not be parsed, with their exceptions."""

    @property
    def ok(self) -> bool:
        return len(self.failed_files) == 0

    def __repr__(self) -> str:
        return (
            f"LoadResult("
            f"snapshots={self.df['file_timestamp'].nunique()}, "
            f"stations={self.df['station_id'].nunique()}, "
            f"rows={len(self.df)}, "
            f"failed={len(self.failed_files)})"
        )


def load_snapshot_dir(
    directory: Path | str,
    *,
    glob: str = "smog_api_*",
    workers: int = 8,
    rebuild_cache: bool = False,
    last_days: int | None = None,
    dev_mode: bool = False,
) -> LoadResult:
    """
    Load all snapshot files in a directory into a single tidy DataFrame.

    On the first call this parses every JSON file and writes a Parquet cache
    alongside the data directory.  On subsequent calls only new files (not
    yet in the cache) are parsed; the rest are read from Parquet instantly.

    Parameters
    ----------
    directory:
        Folder containing the snapshot files.
    glob:
        Filename pattern to match. Defaults to 'smog_api_*'.
    workers:
        Number of threads for parallel file I/O.
    rebuild_cache:
        If True, ignore the existing cache and reparse everything.
        Use this after upgrading the models or fixing a parsing bug.
    last_days:
        If set, only return rows from the most recent N days of available
        data (anchored to the latest timestamp in the cache, not the clock).
    dev_mode:
        Shortcut for fast iteration during development.
        Loads only the 3 most recent days of available data and skips
        parsing any new files (cache must already exist).
        Overrides last_days if both are set.
        Set DEV=true in your environment to enable automatically.
    """
    import os
    if not dev_mode and os.environ.get("DEV", "").lower() in ("1", "true", "yes"):
        dev_mode = True
    if dev_mode:
        last_days = 3

    directory  = Path(directory)
    cache_path = directory / _CACHE_FILENAME

    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    all_files = sorted(directory.glob(glob))
    if not all_files:
        logger.warning("No files matched '%s' in %s", glob, directory)
        return LoadResult(df=_empty_dataframe())

    failed: list[tuple[Path, Exception]] = []

    # -----------------------------------------------------------------------
    # Determine which files still need parsing
    # -----------------------------------------------------------------------
    if not rebuild_cache and cache_path.exists():
        try:
            if dev_mode:
                # In dev mode we never parse new files — just slice the cache.
                # This makes restarts nearly instant even with 5M+ total rows.
                logger.info("dev_mode: reading slice from cache, skipping new-file check.")
                df = _read_parquet_slice(cache_path, last_days=last_days)
                return LoadResult(df=df)
            else:
                # Read only the source_file column to find what's cached —
                # avoids pulling all 5M rows just to check which files are new.
                cached_sources = set(
                    pd.read_parquet(cache_path, columns=["source_file"])["source_file"].unique()
                )
                new_files = [f for f in all_files if f.name not in cached_sources]
                logger.info(
                    "Cache hit: %d source files already cached. %d new file(s) to parse.",
                    len(cached_sources), len(new_files),
                )
        except Exception as exc:
            logger.warning("Cache unreadable (%s), rebuilding from scratch.", exc)
            new_files = all_files
    else:
        new_files = all_files
        if rebuild_cache:
            logger.info("rebuild_cache=True — reparsing all %d files.", len(all_files))

    # -----------------------------------------------------------------------
    # Parse only the new files
    # -----------------------------------------------------------------------
    if new_files:
        logger.info("Parsing %d file(s)...", len(new_files))
        fresh_df, failed = _load_fresh(new_files, workers)

        if len(fresh_df):
            # Append fresh rows to the Parquet cache directly — no need to
            # read all 5M existing rows into memory first.
            if cache_path.exists() and not rebuild_cache:
                existing = pd.read_parquet(cache_path)
                combined = pd.concat([existing, fresh_df], ignore_index=True)
            else:
                combined = fresh_df

            combined = (
                combined
                .drop_duplicates(subset=["station_id", "file_timestamp"])
                .sort_values(["station_id", "file_timestamp"])
                .reset_index(drop=True)
            )

            try:
                combined.to_parquet(cache_path, index=False)
                logger.info("Cache updated → %s (%d total rows)", cache_path, len(combined))
            except Exception as exc:
                logger.warning("Could not write cache: %s", exc)

    df = _read_parquet_slice(cache_path, last_days=last_days)

    logger.info(
        "Ready: %d rows | %d snapshots | %d stations | %d failed",
        len(df),
        df["file_timestamp"].nunique(),
        df["station_id"].nunique(),
        len(failed),
    )

    return LoadResult(df=df, failed_files=failed)


def _read_parquet_slice(cache_path: Path, last_days: int | None) -> pd.DataFrame:
    """
    Read the Parquet cache, optionally returning only the last N days
    of *available data* — anchored to the latest timestamp in the file,
    not to the current clock. This means dev_mode always returns real rows
    even when the data collection has been paused for several days.
    """
    if not cache_path.exists():
        return _empty_dataframe()

    if last_days is None:
        return pd.read_parquet(cache_path)

    # Find the latest timestamp in the cache cheaply (one column, no full read).
    ts_series = pd.read_parquet(cache_path, columns=["file_timestamp"])["file_timestamp"]
    data_max = pd.to_datetime(ts_series).max()
    cutoff = data_max - pd.Timedelta(days=last_days)

    df = pd.read_parquet(cache_path)
    df["file_timestamp"] = pd.to_datetime(df["file_timestamp"])
    result = df[df["file_timestamp"] >= cutoff].reset_index(drop=True)

    logger.info(
        "Sliced to last %d days of data (since %s): %d rows",
        last_days, cutoff.strftime("%Y-%m-%d %H:%M"), len(result),
    )
    return result


def _empty_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "station_id", "station_name", "city", "post_code", "street",
        "latitude", "longitude",
        "timestamp", "file_timestamp", "source_file",
        "humidity_avg", "pressure_avg", "temperature_avg",
        "pm10_avg", "pm25_avg", "air_quality_index",
    ])
