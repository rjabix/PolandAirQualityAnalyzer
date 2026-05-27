import logging
from pathlib import Path
from configuration import Configuration, config
from smogloader import load_snapshot_dir
from visualizations import (
    generate_pm25_map,
    generate_temperature_map,
    generate_bar_race,
    generate_daily_heatmap,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main(configuration: Configuration = config):
    result = load_snapshot_dir(configuration.DataFolderPath, dev_mode=configuration.DevMode)
    df = result.df

    out = Path(configuration.OutputDir)

    generate_pm25_map(df,          out / "pm25_map.gif")
    generate_temperature_map(df,   out / "temperature_map.gif")
    generate_bar_race(df,          out / "bar_race.gif")
    generate_daily_heatmap(df,     out / "daily_heatmap.gif")


if __name__ == '__main__':
    main()
