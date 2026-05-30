import argparse
import logging
from pathlib import Path

from configuration import Configuration, config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def run_dashboard():
    import app as _app
    _app.app.run(debug=False, host="127.0.0.1", port=8050)


def run_gifs(configuration: Configuration = config):
    from smogloader import load_snapshot_dir
    from visualizations import (
        generate_pm25_map,
        generate_temperature_map,
        generate_bar_race,
        generate_daily_heatmap,
    )

    result = load_snapshot_dir(configuration.DataFolderPath, dev_mode=configuration.DevMode)
    df = result.df
    out = Path(configuration.OutputDir)

    generate_pm25_map(df,          out / "pm25_map.gif")
    generate_temperature_map(df,   out / "temperature_map.gif")
    generate_bar_race(df,          out / "bar_race.gif")
    generate_daily_heatmap(df,     out / "daily_heatmap.gif")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poland Air Quality Analyzer")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["all", "dashboard", "gifs"],
        help="all (default): generate GIFs then launch dashboard  |  dashboard: dashboard only  |  gifs: GIFs only",
    )
    args = parser.parse_args()

    if args.mode == "gifs":
        run_gifs()
    elif args.mode == "dashboard":
        run_dashboard()
    else:
        run_gifs()
        run_dashboard()