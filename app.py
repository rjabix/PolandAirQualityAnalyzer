"""
Poland Air Quality Interactive Dashboard
Run:  .venv/bin/python app.py
Open: http://127.0.0.1:8050
"""
from __future__ import annotations

import logging

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from configuration import config
from smogloader import load_snapshot_dir

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Load & index data ─────────────────────────────────────────────────────────
log.info("Loading data (this takes ~10 s on first run)…")
_result = load_snapshot_dir(config.DataFolderPath, dev_mode=config.DevMode)
df = _result.df.dropna(subset=["latitude", "longitude"]).copy()
df["file_timestamp"] = pd.to_datetime(df["file_timestamp"])

TIMESTAMPS: list = sorted(df["file_timestamp"].unique())
N = len(TIMESTAMPS)
# Pre-group for O(1) per-frame lookup — avoids scanning 4.7M rows on every slider drag
_FRAMES: dict = {ts: grp for ts, grp in df.groupby("file_timestamp", sort=False)}
# Pre-group by station for O(1) history lookup in the side panel
_STATIONS: dict = {sid: grp for sid, grp in df.groupby("station_id", sort=False)}
log.info("Ready: %d rows · %d snapshots · %d stations", len(df), N, df["station_id"].nunique())

# ── Metric definitions ────────────────────────────────────────────────────────
METRICS: dict[str, dict] = {
    "pm25_avg": {
        "label": "PM2.5",
        "unit":  "µg/m³",
        "vmin": 0, "vmax": 60,
        "colorscale": [[0, "#4CAF50"], [.2, "#8BC34A"], [.5, "#FFC107"], [.75, "#FF5722"], [1, "#B71C1C"]],
    },
    "pm10_avg": {
        "label": "PM10",
        "unit":  "µg/m³",
        "vmin": 0, "vmax": 100,
        "colorscale": [[0, "#4CAF50"], [.2, "#8BC34A"], [.5, "#FFC107"], [.75, "#FF5722"], [1, "#B71C1C"]],
    },
    "temperature_avg": {
        "label": "Temperature",
        "unit":  "°C",
        "vmin": -10, "vmax": 35,
        "colorscale": [[0, "#1565C0"], [.25, "#42A5F5"], [.5, "#A5D6A7"], [.75, "#FF8F00"], [1, "#B71C1C"]],
    },
    "humidity_avg": {
        "label": "Humidity",
        "unit":  "%",
        "vmin": 0, "vmax": 100,
        "colorscale": [[0, "#B71C1C"], [.3, "#FF8F00"], [.6, "#42A5F5"], [1, "#1565C0"]],
    },
    "pressure_avg": {
        "label": "Pressure",
        "unit":  "hPa",
        "vmin": 970, "vmax": 1030,
        "colorscale": [[0, "#7B1FA2"], [.5, "#CE93D8"], [1, "#E3F2FD"]],
    },
}

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = "#0d1117"
SURFACE = "#161b22"
BORDER  = "#30363d"
FG      = "#e6edf3"
MUTED   = "#8b949e"
ACCENT  = "#58a6ff"


def _marks(n: int, max_labels: int = 16) -> dict[int, dict]:
    step = max(1, n // max_labels)
    out: dict[int, dict] = {}
    for i in range(0, n, step):
        out[i] = {"label": pd.Timestamp(TIMESTAMPS[i]).strftime("%-d %b"),
                  "style": {"color": MUTED, "fontSize": "9px"}}
    out[n - 1] = {"label": pd.Timestamp(TIMESTAMPS[-1]).strftime("%-d %b"),
                  "style": {"color": MUTED, "fontSize": "9px"}}
    return out


def _v(val: object, unit: str = "") -> str:
    if pd.isna(val):
        return "—"
    return f"{float(val):.1f}{' ' + unit if unit else ''}"


# ── Layout ────────────────────────────────────────────────────────────────────
app = Dash(__name__, title="Poland Air Quality")

_DARK_CSS = f"""
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: {BG}; overflow: hidden; }}

    /* Dash 4 design-token overrides — themes Dropdown, Slider, etc. */
    :root {{
      --Dash-Fill-Inverse-Strong:     {SURFACE};
      --Dash-Stroke-Strong:           {BORDER};
      --Dash-Fill-Disabled:           {BORDER};
      --Dash-Text-Strong:             {FG};
      --Dash-Text-Weak:               {MUTED};
      --Dash-Text-Disabled:           {MUTED};
      --Dash-Fill-Interactive-Strong: {ACCENT};
      --Dash-Fill-Interactive-Weak:   rgba(88,166,255,0.12);
      --Dash-Shading-Strong:          rgba(0,0,0,0.55);
      --Dash-Shading-Weak:            rgba(0,0,0,0.22);
      --Dash-Spacing:                 4px;
    }}

    /* Dropdown */
    .dash-dropdown {{ color: {FG}; }}
    .dash-dropdown-content {{ background: {SURFACE}; border-color: {BORDER}; }}
    .dash-dropdown-option {{ color: {FG}; }}
    .dash-dropdown-option:hover {{ background: {BORDER}; }}
    .dash-dropdown-search {{ color: {FG}; }}

    /* Slider */
    .dash-slider-track   {{ background: {BORDER}; }}
    .dash-slider-range   {{ background: {ACCENT}; }}
    .dash-slider-tooltip {{ background: {SURFACE}; color: {FG}; border: 1px solid {BORDER}; }}
"""

app.index_string = (
    "<!DOCTYPE html>\n<html>\n<head>\n"
    "  {%metas%}\n  <title>{%title%}</title>\n  {%favicon%}\n  {%css%}\n"
    "  <style>" + _DARK_CSS + "  </style>\n"
    "</head>\n<body>\n  {%app_entry%}\n"
    "  <footer>{%config%}{%scripts%}{%renderer%}</footer>\n"
    "</body>\n</html>"
)

app.layout = html.Div(
    style={
        "backgroundColor": BG, "color": FG, "fontFamily": "system-ui, -apple-system, sans-serif",
        "height": "100vh", "display": "flex", "flexDirection": "column", "overflow": "hidden",
    },
    children=[

        # ── Header ────────────────────────────────────────────────────────────
        html.Div(
            style={
                "padding": "8px 20px", "borderBottom": f"1px solid {BORDER}",
                "backgroundColor": SURFACE, "display": "flex", "alignItems": "center",
                "gap": "16px", "flexShrink": 0, "zIndex": 10,
            },
            children=[
                html.Span(
                    "🇵🇱 Poland Air Quality",
                    style={"fontWeight": 700, "fontSize": "15px", "letterSpacing": "-0.2px", "whiteSpace": "nowrap"},
                ),
                dcc.Dropdown(
                    id="metric-dd", clearable=False, value="pm25_avg",
                    options=[{"label": v["label"], "value": k} for k, v in METRICS.items()],
                    style={"width": "160px", "fontSize": "13px", "flexShrink": 0},
                ),
                html.Div(
                    id="hdr-ts",
                    style={"fontSize": "13px", "color": ACCENT, "marginLeft": "auto",
                           "fontVariantNumeric": "tabular-nums", "whiteSpace": "nowrap"},
                ),
                html.Div(
                    id="hdr-stats",
                    style={"fontSize": "11px", "color": MUTED, "whiteSpace": "nowrap"},
                ),
            ],
        ),

        # ── Map + side panel ──────────────────────────────────────────────────
        html.Div(
            style={"display": "flex", "flex": 1, "overflow": "hidden"},
            children=[
                dcc.Graph(
                    id="map",
                    style={"flex": 1, "minWidth": 0},
                    config={
                        "scrollZoom": True,
                        "modeBarButtonsToRemove": ["toImage", "select2d", "lasso2d"],
                    },
                ),
                html.Div(
                    id="panel",
                    style={
                        "width": "260px", "backgroundColor": SURFACE,
                        "borderLeft": f"1px solid {BORDER}",
                        "padding": "14px 12px", "overflowY": "auto",
                        "flexShrink": 0, "fontSize": "13px",
                    },
                    children=[
                        html.Div(
                            "Click a station dot on the map to see details.",
                            style={"color": MUTED, "marginTop": "60px", "textAlign": "center", "fontSize": "12px"},
                        ),
                    ],
                ),
            ],
        ),

        # ── Timeline ─────────────────────────────────────────────────────────
        html.Div(
            style={
                "padding": "8px 20px 10px", "borderTop": f"1px solid {BORDER}",
                "backgroundColor": SURFACE, "flexShrink": 0,
            },
            children=[
                dcc.Slider(
                    id="slider", min=0, max=N - 1, step=1, value=0,
                    marks=_marks(N),
                    tooltip={"placement": "top", "always_visible": False},
                    updatemode="drag",
                ),
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "10px", "marginTop": "4px"},
                    children=[
                        html.Button(
                            "▶ Play", id="play-btn", n_clicks=0,
                            style={
                                "backgroundColor": ACCENT, "color": BG, "border": "none",
                                "borderRadius": "6px", "padding": "5px 14px",
                                "fontWeight": 700, "cursor": "pointer", "fontSize": "12px",
                                "flexShrink": 0,
                            },
                        ),
                        html.Label("Speed:", style={"fontSize": "11px", "color": MUTED, "flexShrink": 0}),
                        html.Div(
                            dcc.Slider(
                                id="speed", min=1, max=5, step=1, value=3,
                                marks={
                                    1: {"label": "Slow", "style": {"color": MUTED, "fontSize": "9px"}},
                                    3: {"label": "Med",  "style": {"color": MUTED, "fontSize": "9px"}},
                                    5: {"label": "Fast", "style": {"color": MUTED, "fontSize": "9px"}},
                                },
                                tooltip={"always_visible": False},
                            ),
                            style={"width": "120px"},
                        ),
                        html.Div(
                            id="frame-lbl",
                            style={"fontSize": "11px", "color": MUTED, "marginLeft": "auto"},
                        ),
                    ],
                ),
            ],
        ),

        dcc.Interval(id="tick", interval=700, disabled=True),
        dcc.Store(id="playing", data=False),
    ],
)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("playing", "data"),
    Output("play-btn", "children"),
    Output("tick", "disabled"),
    Input("play-btn", "n_clicks"),
    State("playing", "data"),
    prevent_initial_call=True,
)
def toggle_play(_, playing):
    playing = not playing
    return playing, ("⏸ Pause" if playing else "▶ Play"), not playing


@app.callback(Output("tick", "interval"), Input("speed", "value"))
def set_speed(s):
    return int(1400 - s * 240)  # 1 → 1160 ms … 5 → 200 ms


@app.callback(
    Output("slider", "value"),
    Input("tick", "n_intervals"),
    State("slider", "value"),
    State("playing", "data"),
    prevent_initial_call=True,
)
def advance(_, idx, playing):
    return ((idx + 1) % N) if playing else idx


@app.callback(
    Output("map", "figure"),
    Output("hdr-ts", "children"),
    Output("hdr-stats", "children"),
    Output("frame-lbl", "children"),
    Input("slider", "value"),
    Input("metric-dd", "value"),
)
def render_map(idx: int, metric: str):
    ts    = TIMESTAMPS[idx]
    mc    = METRICS[metric]
    frame = _FRAMES[ts].dropna(subset=[metric, "latitude", "longitude"])

    vals  = frame[metric].clip(mc["vmin"], mc["vmax"])
    sizes = (
        7 + (vals - mc["vmin"]) / max(mc["vmax"] - mc["vmin"], 1) * 22
        if metric in ("pm25_avg", "pm10_avg") else 9
    )

    recs  = frame.to_dict("records")
    hover = [
        f"<b>{r['station_name']}</b><br>"
        f"{r['city']}<br>"
        f"──────────<br>"
        f"PM2.5:    {_v(r['pm25_avg'])} µg/m³<br>"
        f"PM10:     {_v(r['pm10_avg'])} µg/m³<br>"
        f"Temp:     {_v(r['temperature_avg'])} °C<br>"
        f"Humidity: {_v(r['humidity_avg'])} %<br>"
        f"Pressure: {_v(r['pressure_avg'])} hPa"
        for r in recs
    ]

    fig = go.Figure(go.Scattermap(
        lat=frame["latitude"],
        lon=frame["longitude"],
        mode="markers",
        marker=go.scattermap.Marker(
            size=sizes,
            color=vals,
            colorscale=mc["colorscale"],
            cmin=mc["vmin"],
            cmax=mc["vmax"],
            colorbar=dict(
                title=dict(text=f"{mc['label']}<br>({mc['unit']})", font=dict(color=FG, size=10)),
                tickfont=dict(color=FG, size=9),
                bgcolor=SURFACE,
                bordercolor=BORDER,
                thickness=12,
                len=0.65,
            ),
            opacity=0.9,
        ),
        hovertext=hover,
        hoverinfo="text",
        customdata=frame["station_id"].values,
    ))

    fig.update_layout(
        map=dict(
            style="carto-darkmatter",
            center=dict(lat=52.0, lon=19.5),
            zoom=5.5,
        ),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="stable",
        font=dict(color=FG),
        hoverlabel=dict(
            bgcolor=SURFACE,
            bordercolor=BORDER,
            font=dict(color=FG, size=12, family="monospace"),
        ),
    )

    ts_lbl = pd.Timestamp(ts).strftime("%d %b %Y  %H:%M")
    n      = len(frame)
    if n and not frame[metric].isna().all():
        avg   = frame[metric].mean()
        mx    = frame[metric].max()
        worst = frame.loc[frame[metric].idxmax(), "city"] if metric.startswith("pm") else ""
        stats = (f"{n} stations · avg {avg:.1f} · max {mx:.1f} {mc['unit']}"
                 + (f"  ({worst})" if worst else ""))
    else:
        stats = f"{n} stations · no data"

    return fig, ts_lbl, stats, f"Frame {idx + 1} / {N}"


@app.callback(
    Output("panel", "children"),
    Input("map", "clickData"),
    Input("slider", "value"),
    prevent_initial_call=True,
)
def station_detail(click, idx):
    if not click:
        return _empty_panel()

    sid   = click["points"][0]["customdata"]
    ts    = TIMESTAMPS[idx]
    frame = _FRAMES[ts]

    row = frame[frame["station_id"] == sid]
    if row.empty:
        # Station absent from current frame — fall back to its most recent snapshot
        station_rows = _STATIONS.get(sid)
        if station_rows is None or station_rows.empty:
            return html.Div("Station not found.", style={"color": MUTED})
        row = station_rows.sort_values("file_timestamp", ascending=False)
    row = row.iloc[0]

    # History up to the current slider position (last 96 snapshots)
    station_df = _STATIONS.get(sid, frame.iloc[:0])
    hist = (
        station_df[station_df["file_timestamp"] <= ts]
        .sort_values("file_timestamp")
        .tail(96)
    )

    AQI_C = {"Good": "#4CAF50", "Moderate": "#FFC107", "Unhealthy": "#FF5722", "Hazardous": "#B71C1C"}
    aqi_raw = row["air_quality_index"]
    aqi     = str(aqi_raw) if pd.notna(aqi_raw) else None
    ac      = AQI_C.get(aqi, MUTED)

    street = str(row["street"]) if pd.notna(row.get("street")) else ""

    def drow(label: str, val: object, unit: str = "") -> html.Div:
        return html.Div(
            style={
                "display": "flex", "justifyContent": "space-between",
                "padding": "4px 0", "borderBottom": f"1px solid {BORDER}44",
            },
            children=[
                html.Span(label, style={"color": MUTED}),
                html.Span(_v(val, unit), style={"fontWeight": 500}),
            ],
        )

    return [
        html.Div(
            str(row["station_name"]),
            style={"fontWeight": 700, "fontSize": "14px", "marginBottom": "2px"},
        ),
        html.Div(
            f"{row['city']} · {row['post_code']}",
            style={"color": MUTED, "fontSize": "11px"},
        ),
        html.Div(street, style={"color": MUTED, "fontSize": "11px", "marginBottom": "10px"}),

        html.Span(
            aqi or "No AQI",
            style={
                "backgroundColor": ac + "33", "color": ac,
                "border": f"1px solid {ac}55",
                "borderRadius": "4px", "padding": "2px 8px",
                "fontSize": "11px", "fontWeight": 600,
                "display": "inline-block", "marginBottom": "10px",
            },
        ),

        drow("PM2.5",       row["pm25_avg"],       "µg/m³"),
        drow("PM10",        row["pm10_avg"],        "µg/m³"),
        drow("Temperature", row["temperature_avg"], "°C"),
        drow("Humidity",    row["humidity_avg"],    "%"),
        drow("Pressure",    row["pressure_avg"],    "hPa"),

        html.Div(
            "History — last 96 snapshots up to this moment",
            style={"color": MUTED, "fontSize": "11px", "marginTop": "12px", "marginBottom": "6px"},
        ),
        *[_metric_sparkline(hist, m) for m in METRICS],

        html.Div(
            f"📍 {float(row['latitude']):.4f}°N, {float(row['longitude']):.4f}°E",
            style={"color": MUTED, "fontSize": "11px", "marginTop": "6px"},
        ),
    ]


def _empty_panel() -> html.Div:
    return html.Div(
        "Click a station dot on the map to see details.",
        style={"color": MUTED, "marginTop": "60px", "textAlign": "center", "fontSize": "12px"},
    )


def _metric_sparkline(hist: "pd.DataFrame", metric: str) -> "dcc.Graph":
    mc  = METRICS[metric]
    col = hist.dropna(subset=[metric])
    vals = col[metric].clip(mc["vmin"], mc["vmax"]) if len(col) else pd.Series([], dtype=float)

    fig = go.Figure(go.Scatter(
        x=col["file_timestamp"] if len(col) else [],
        y=col[metric] if len(col) else [],
        mode="lines+markers",
        line=dict(color=BORDER, width=0.8),
        marker=dict(
            color=vals,
            colorscale=mc["colorscale"],
            cmin=mc["vmin"],
            cmax=mc["vmax"],
            size=5,
            line=dict(width=0),
        ),
        hovertemplate=f"%{{x|%d %b %H:%M}}<br>{mc['label']}: %{{y:.1f}} {mc['unit']}<extra></extra>",
    ))
    fig.update_layout(
        height=90,
        margin=dict(l=40, r=6, t=18, b=32),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        title=dict(
            text=f"{mc['label']} ({mc['unit']})",
            font=dict(color=MUTED, size=9),
            x=0, xanchor="left",
            pad=dict(l=0, t=0),
        ),
        xaxis=dict(
            color=MUTED,
            tickfont=dict(color=MUTED, size=7),
            tickformat="%d %b %H:%M",
            nticks=4,
            gridcolor=BORDER,
            showgrid=True,
            linecolor=BORDER,
            tickangle=-30,
        ),
        yaxis=dict(
            color=MUTED,
            tickfont=dict(color=MUTED, size=7),
            gridcolor=BORDER,
            showgrid=True,
            nticks=3,
            linecolor=BORDER,
        ),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=SURFACE,
            bordercolor=BORDER,
            font=dict(color=FG, size=11, family="monospace"),
        ),
    )
    return dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"marginBottom": "2px"},
    )


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
