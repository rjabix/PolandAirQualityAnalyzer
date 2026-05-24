"""
Loader for directories of smog API snapshot files.

Each file is one point-in-time dump from the smog API, named like:
    smog_api_2026-03-18-18-19-34-CET

Typical usage:
    from smog_loader import load_snapshot_dir

    result = load_snapshot_dir("data/snapshots/")
    df = result.df

    # Now you have a tidy DataFrame — one row per station per timestamp:
    # station_id | city | pm25_avg | pm10_avg | timestamp | ...

    # Example: PM2.5 over time for one station
    station_df = df[df["station_id"] == "63-421_ZESPÓŁ SZKÓŁ..."]
    station_df.plot(x="timestamp", y="pm25_avg")
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from models import SmogApiResponse

logger = logging.getLogger(__name__)

# Matches: smog_api_2026-03-18-18-19-34-CET  (timezone suffix optional)
_FILENAME_TIMESTAMP_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})(?:-[A-Z]+)?$"
)


def _parse_timestamp_from_filename(path: Path) -> datetime | None:
    """
    Extract the snapshot datetime from the filename.

    The filename is treated as the authoritative timestamp for the whole file
    because it reflects when the API was called, whereas the per-reading
    timestamps are all identical and may lag slightly.

    Returns None if the filename doesn't match the expected pattern.
    """
    match = _FILENAME_TIMESTAMP_RE.search(path.stem)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        return None


def load_snapshot_file(path: Path | str) -> list[dict]:
    """
    Parse one snapshot file and return its readings as a list of flat dicts.

    The 'file_timestamp' column comes from the filename (preferred) and falls
    back to the per-reading timestamp embedded in the JSON. This lets you
    reconstruct a reliable timeline even if the JSON timestamps drift.

    Raises:
        ValueError / ValidationError  on malformed JSON or failed validation.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    response = SmogApiResponse.model_validate_json(text)
    records = response.to_flat_records()

    # Stamp every row with where it came from
    file_ts = _parse_timestamp_from_filename(path) or response.snapshot_timestamp
    for record in records:
        record["file_timestamp"] = file_ts
        record["source_file"] = path.name

    return records


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
    drop_test_stations: bool = True,
) -> LoadResult:
    """
    Load all snapshot files in a directory into a single tidy DataFrame.

    Parameters
    ----------
    directory:
        Folder containing the snapshot files.
    glob:
        Filename pattern to match. Defaults to 'smog_api_*'.
    workers:
        Number of threads for parallel file I/O. Set to 1 to disable threading.
    drop_test_stations:
        If True (default), filters out rows where the city contains 'TEST',
        matching dummy stations like "TESTCITY" present in the source data.

    Returns
    -------
    LoadResult
        .df             — combined, deduplicated, sorted DataFrame
        .failed_files   — list of (Path, Exception) for files that failed
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = sorted(directory.glob(glob))
    if not files:
        logger.warning("No files matched '%s' in %s", glob, directory)
        return LoadResult(df=_empty_dataframe())

    logger.info("Loading %d snapshot files from %s ...", len(files), directory)

    all_records: list[dict] = []
    failed: list[tuple[Path, Exception]] = []

    def _load(path: Path) -> list[dict] | Exception:
        try:
            return load_snapshot_file(path)
        except Exception as exc:  # noqa: BLE001
            return exc

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_load, f): f for f in files}
        for future in as_completed(futures):
            path = futures[future]
            result = future.result()
            if isinstance(result, Exception):
                logger.warning("Skipping %s: %s", path.name, result)
                failed.append((path, result))
            else:
                all_records.extend(result)

    if not all_records:
        return LoadResult(df=_empty_dataframe(), failed_files=failed)

    df = pd.DataFrame(all_records)

    if drop_test_stations:
        mask = df["city"].str.upper().str.contains("TEST", na=False)
        dropped = mask.sum()
        if dropped:
            logger.info("Dropped %d test-station rows.", dropped)
        df = df[~mask]

    df = (
        df
        # One station can appear in multiple files with the same timestamp
        # (e.g. if the API was polled twice in a short window).
        .drop_duplicates(subset=["station_id", "file_timestamp"])
        .sort_values(["station_id", "file_timestamp"])
        .reset_index(drop=True)
    )

    # Ensure sensible dtypes for downstream analysis
    df["file_timestamp"] = pd.to_datetime(df["file_timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    logger.info(
        "Loaded %d rows | %d snapshots | %d stations | %d failed files",
        len(df),
        df["file_timestamp"].nunique(),
        df["station_id"].nunique(),
        len(failed),
    )

    return LoadResult(df=df, failed_files=failed)


def _empty_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame with the expected column schema."""
    return pd.DataFrame(columns=[
        "station_id", "station_name", "city", "post_code", "street",
        "latitude", "longitude",
        "timestamp", "file_timestamp", "source_file",
        "humidity_avg", "pressure_avg", "temperature_avg",
        "pm10_avg", "pm25_avg", "air_quality_index",
    ])