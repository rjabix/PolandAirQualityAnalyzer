"""
All animated GIF visualizations for Poland air quality data.

Each function accepts the full smog DataFrame (from load_snapshot_dir) and
an output path, and returns the Path it wrote to.

Available generators
--------------------
generate_pm25_map(df, path)
    Geographic dot map coloured by PM2.5. One frame per day.

generate_temperature_map(df, path)
    Same dot map, coloured by temperature. Reveals spring warming March→May.

generate_bar_race(df, path)
    Animated horizontal bar chart — top 15 most polluted cities by daily
    average PM2.5. Bars race up and down as rankings shift over time.

generate_daily_heatmap(df, path)
    Heatmap: X = calendar date, Y = hour of day (0–23),
    colour = national median PM2.5. Shows daily pollution rhythms and
    how they shift across the season.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
_BG = "#0d1117"
_FG = "#e6edf3"
_GRID = "#21262d"

_LAT_MIN, _LAT_MAX = 49.0, 55.0
_LON_MIN, _LON_MAX = 14.0, 24.5

_POLAND_BORDER = [
    (14.12, 51.00), (14.33, 51.84), (14.61, 52.58), (14.13, 52.84),
    (14.20, 53.90), (14.22, 54.15), (16.00, 54.52), (17.30, 54.83),
    (18.33, 55.00), (19.00, 54.46), (19.64, 54.46), (20.52, 54.36),
    (21.27, 54.22), (22.78, 54.36), (22.87, 54.60), (23.48, 54.22),
    (23.53, 53.94), (23.91, 53.16), (23.94, 52.71), (23.68, 52.30),
    (23.60, 51.52), (24.15, 50.86), (24.10, 50.42), (23.43, 50.31),
    (22.65, 49.54), (22.06, 49.00), (21.46, 49.41), (20.62, 49.40),
    (19.82, 49.19), (18.84, 49.51), (18.56, 49.88), (17.88, 49.97),
    (17.14, 50.38), (16.62, 50.16), (16.00, 50.61), (15.33, 50.78),
    (15.03, 51.27), (14.80, 51.06), (14.12, 51.00),
]

_PM25_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "pm25",
    [(0.00, "#4CAF50"), (0.20, "#8BC34A"), (0.50, "#FFC107"),
     (0.75, "#FF5722"), (1.00, "#B71C1C")],
)
_TEMP_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "temp",
    [(0.0, "#1565C0"), (0.25, "#42A5F5"), (0.5, "#A5D6A7"),
     (0.75, "#FF8F00"), (1.0, "#B71C1C")],
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fig_to_pil(fig: plt.Figure) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=fig.get_facecolor(),
                bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).copy()


def _save_gif(images: list[Image.Image], path: Path, fps: int = 4) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure all frames are the same size (bbox_inches="tight" can vary slightly)
    w, h = images[0].size
    images = [img.resize((w, h), Image.LANCZOS) for img in images]
    images[0].save(
        path, save_all=True, append_images=images[1:],
        duration=1000 // fps, loop=0, optimize=False,
    )
    logger.info("Saved → %s  (%d frames)", path, len(images))
    return path


def _daily_frames(df: pd.DataFrame, metric: str) -> list[tuple[str, pd.DataFrame]]:
    """One representative snapshot per calendar day, nearest to 14:00."""
    df = df.dropna(subset=[metric]).copy()
    df["_date"] = df["file_timestamp"].dt.date
    df["_hdiff"] = (df["file_timestamp"].dt.hour - 14).abs()
    frames = []
    for day, grp in df.groupby("_date"):
        best_ts = grp.loc[grp["_hdiff"].idxmin(), "file_timestamp"]
        frame = grp[grp["file_timestamp"] == best_ts]
        frames.append((pd.Timestamp(day).strftime("%-d %b %Y"), frame))
    return sorted(frames, key=lambda x: x[1]["file_timestamp"].iloc[0])


def _geo_axes(fig: plt.Figure) -> plt.Axes:
    ax = fig.add_subplot(111)
    ax.set_facecolor(_BG)
    border = np.array(_POLAND_BORDER)
    ax.plot(border[:, 0], border[:, 1], color="#ffffff22", linewidth=0.8, zorder=1)
    ax.set_xlim(_LON_MIN, _LON_MAX)
    ax.set_ylim(_LAT_MIN, _LAT_MAX)
    ax.set_aspect("equal")
    for spine in ax.spines.values():
        spine.set_color(_GRID)
    ax.tick_params(colors="#ffffff44", labelsize=6)
    return ax


def _add_colorbar(fig, ax, sm, label):
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label(label, color=_FG, fontsize=8)
    cbar.ax.yaxis.set_tick_params(color=_FG, labelsize=7)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=_FG)
    for s in cbar.ax.spines.values():
        s.set_color(_GRID)


# ---------------------------------------------------------------------------
# 1. PM2.5 geographic map
# ---------------------------------------------------------------------------

def generate_pm25_map(
    df: pd.DataFrame,
    output_path: str | Path = "output/pm25_map.gif",
    fps: int = 4,
) -> Path:
    """Animated geographic dot map coloured by PM2.5. One frame per day."""
    output_path = Path(output_path)
    norm = mcolors.Normalize(vmin=0, vmax=50)
    frames_data = _daily_frames(df, "pm25_avg")
    logger.info("pm25_map: rendering %d frames", len(frames_data))

    images = []
    for label, frame in frames_data:
        fig = plt.figure(figsize=(7, 7), facecolor=_BG)
        ax = _geo_axes(fig)

        valid = frame.dropna(subset=["longitude", "latitude", "pm25_avg"])
        pm25 = valid["pm25_avg"].clip(0, 50)
        sizes = 6 + (pm25 / 50) * 60
        ax.scatter(valid["longitude"], valid["latitude"],
                   s=sizes, c=_PM25_CMAP(norm(pm25)), alpha=0.85,
                   linewidths=0, zorder=2)

        if not valid.empty:
            avg = valid["pm25_avg"].mean()
            worst = valid.nlargest(1, "pm25_avg").iloc[0]
            ax.text(0.02, 0.04,
                    f"Avg: {avg:.1f} µg/m³\nWorst: {worst['city']}  {worst['pm25_avg']:.0f}",
                    transform=ax.transAxes, color="#ffffffcc", fontsize=7.5,
                    va="bottom", fontfamily="monospace",
                    bbox=dict(facecolor="#00000055", edgecolor="none", pad=3))

        ax.text(0.98, 0.97, label, transform=ax.transAxes,
                color=_FG, fontsize=12, fontweight="bold", va="top", ha="right")
        ax.set_title("PM2.5 (µg/m³)", color=_FG, fontsize=10, pad=6)

        sm = plt.cm.ScalarMappable(cmap=_PM25_CMAP, norm=norm)
        sm.set_array([])
        _add_colorbar(fig, ax, sm, "PM2.5 µg/m³")
        images.append(_fig_to_pil(fig))

    return _save_gif(images, output_path, fps)


# ---------------------------------------------------------------------------
# 2. Temperature geographic map
# ---------------------------------------------------------------------------

def generate_temperature_map(
    df: pd.DataFrame,
    output_path: str | Path = "output/temperature_map.gif",
    fps: int = 4,
) -> Path:
    """
    Animated geographic dot map coloured by temperature.
    Spring warming from cold blue (March) to warm orange/red (May) is
    clearly visible as the season progresses.
    """
    output_path = Path(output_path)
    frames_data = _daily_frames(df, "temperature_avg")

    all_temps = df["temperature_avg"].dropna()
    t_min = float(np.percentile(all_temps, 2))
    t_max = float(np.percentile(all_temps, 98))
    norm = mcolors.Normalize(vmin=t_min, vmax=t_max)

    logger.info("temperature_map: rendering %d frames  (%.0f°C – %.0f°C)",
                len(frames_data), t_min, t_max)

    images = []
    for label, frame in frames_data:
        fig = plt.figure(figsize=(7, 7), facecolor=_BG)
        ax = _geo_axes(fig)

        valid = frame.dropna(subset=["longitude", "latitude", "temperature_avg"])
        temp = valid["temperature_avg"]
        ax.scatter(valid["longitude"], valid["latitude"],
                   s=18, c=_TEMP_CMAP(norm(temp)), alpha=0.85,
                   linewidths=0, zorder=2)

        if not valid.empty:
            ax.text(0.02, 0.04, f"National avg: {temp.mean():.1f} °C",
                    transform=ax.transAxes, color="#ffffffcc", fontsize=8,
                    va="bottom", fontfamily="monospace",
                    bbox=dict(facecolor="#00000055", edgecolor="none", pad=3))

        ax.text(0.98, 0.97, label, transform=ax.transAxes,
                color=_FG, fontsize=12, fontweight="bold", va="top", ha="right")
        ax.set_title("Temperature (°C) — Spring 2026", color=_FG, fontsize=10, pad=6)

        sm = plt.cm.ScalarMappable(cmap=_TEMP_CMAP, norm=norm)
        sm.set_array([])
        _add_colorbar(fig, ax, sm, "°C")
        images.append(_fig_to_pil(fig))

    return _save_gif(images, output_path, fps)


# ---------------------------------------------------------------------------
# 3. Bar chart race — top 15 most polluted cities
# ---------------------------------------------------------------------------

def generate_bar_race(
    df: pd.DataFrame,
    output_path: str | Path = "output/bar_race.gif",
    fps: int = 3,
    top_n: int = 15,
    max_label_len: int = 18,
) -> Path:
    """
    Animated horizontal bar chart — top N cities by daily average PM2.5.
    Bars grow/shrink and rows reorder as the pollution rankings shift day to day.
    """
    output_path = Path(output_path)

    daily = (
        df.dropna(subset=["pm25_avg", "city"])
          .groupby(["city", df["file_timestamp"].dt.date.rename("date")])["pm25_avg"]
          .mean()
          .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    # Truncate long city names so they fit comfortably on the Y axis
    daily["city_label"] = daily["city"].str[:max_label_len].str.title()

    dates = sorted(daily["date"].unique())
    palette = {c: plt.cm.tab20(i % 20) for i, c in enumerate(daily["city"].unique())}
    x_max = float(daily["pm25_avg"].quantile(0.99)) * 1.15

    logger.info("bar_race: rendering %d frames, top %d cities", len(dates), top_n)

    images = []
    for date in dates:
        day_data = (
            daily[daily["date"] == date]
            .nlargest(top_n, "pm25_avg")
            .sort_values("pm25_avg")
        )

        fig, ax = plt.subplots(figsize=(10, 6), facecolor=_BG)
        ax.set_facecolor(_BG)

        bars = ax.barh(
            day_data["city_label"],
            day_data["pm25_avg"],
            color=[palette[c] for c in day_data["city"]],
            edgecolor="none",
            height=0.72,
        )

        for bar, val in zip(bars, day_data["pm25_avg"]):
            ax.text(val + x_max * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", ha="left", color=_FG, fontsize=8)

        ax.axvline(25, color="#FFC107", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.text(25.5, -0.7, "WHO limit", color="#FFC107", fontsize=6.5, va="top")

        ax.set_xlim(0, x_max)
        ax.set_xlabel("Daily avg PM2.5 (µg/m³)", color=_FG, fontsize=9)
        ax.set_title(
            f"Top {top_n} most polluted cities — {pd.Timestamp(date).strftime('%-d %b %Y')}",
            color=_FG, fontsize=11, pad=8,
        )
        ax.tick_params(axis="y", colors=_FG, labelsize=8.5, pad=4)
        ax.tick_params(axis="x", colors=_FG, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(_GRID)
        ax.xaxis.grid(True, color=_GRID, linewidth=0.5)
        ax.set_axisbelow(True)

        # Use subplots_adjust for explicit left margin — avoids the tight_layout warning
        fig.subplots_adjust(left=0.26, right=0.97, top=0.91, bottom=0.10)
        images.append(_fig_to_pil(fig))

    return _save_gif(images, output_path, fps)


# ---------------------------------------------------------------------------
# 4. Daily rhythm heatmap — hour × date
# ---------------------------------------------------------------------------

def generate_daily_heatmap(
    df: pd.DataFrame,
    output_path: str | Path = "output/daily_heatmap.gif",
    fps: int = 6,
) -> Path:
    """
    Heatmap: X = calendar date, Y = hour of day (0–23),
    colour = national median PM2.5.

    Rendered as an animated "reveal" — columns appear one day at a time so
    you can watch the pattern build up left to right.
    """
    output_path = Path(output_path)

    pivot = (
        df.dropna(subset=["pm25_avg"])
          .assign(
              date=df["file_timestamp"].dt.date,
              hour=df["file_timestamp"].dt.hour,
          )
          .groupby(["date", "hour"])["pm25_avg"]
          .median()
          .unstack("date")
          .sort_index()
    )
    pivot.index = pivot.index.astype(int)
    pivot = pivot.reindex(range(24)).interpolate(axis=0, limit_direction="both")

    dates = list(pivot.columns)
    n_dates = len(dates)

    vmin = float(pivot.stack().quantile(0.02))
    vmax = float(pivot.stack().quantile(0.98))
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "rhythm",
        [(0.0, "#1A237E"), (0.3, "#1565C0"), (0.55, "#FDD835"),
         (0.75, "#F57F17"), (1.0, "#B71C1C")],
    )

    month_ticks = [i for i, d in enumerate(dates)
                   if pd.Timestamp(d).day == 1 or i == 0]
    month_labels = [pd.Timestamp(dates[i]).strftime("%b") for i in month_ticks]

    logger.info("daily_heatmap: rendering %d frames (one per day)", n_dates)

    images = []
    for reveal_idx in range(1, n_dates + 1):
        full_canvas = np.full((24, n_dates), np.nan)
        full_canvas[:, :reveal_idx] = pivot.iloc[:, :reveal_idx].values

        fig, ax = plt.subplots(figsize=(11, 5), facecolor=_BG)
        ax.set_facecolor(_BG)

        im = ax.imshow(full_canvas, aspect="auto", origin="lower",
                       cmap=cmap, norm=norm, interpolation="nearest")
        ax.axvline(reveal_idx - 1, color="white", linewidth=1.2, alpha=0.7)

        ax.set_yticks(range(0, 24, 3))
        ax.set_yticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], color=_FG, fontsize=7)
        ax.set_xticks(month_ticks)
        ax.set_xticklabels(month_labels, color=_FG, fontsize=8)
        ax.set_ylabel("Hour of day", color=_FG, fontsize=9)
        ax.set_xlim(-0.5, n_dates - 0.5)

        current_label = pd.Timestamp(dates[reveal_idx - 1]).strftime("%-d %b %Y")
        ax.set_title(f"Poland PM2.5 daily rhythm — {current_label}",
                     color=_FG, fontsize=10, pad=6)
        for spine in ax.spines.values():
            spine.set_color(_GRID)

        cbar = fig.colorbar(im, ax=ax, fraction=0.015, pad=0.01)
        cbar.set_label("Median PM2.5 (µg/m³)", color=_FG, fontsize=8)
        cbar.ax.yaxis.set_tick_params(color=_FG, labelsize=7)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=_FG)
        for s in cbar.ax.spines.values():
            s.set_color(_GRID)

        fig.subplots_adjust(left=0.07, right=0.97, top=0.91, bottom=0.08)
        images.append(_fig_to_pil(fig))

    return _save_gif(images, output_path, fps)
