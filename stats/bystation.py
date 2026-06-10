import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print(dataframe.info())
print("Dataframe start date: ", dataframe[["timestamp"]]["timestamp"].min())
print("Datafram end date: ", dataframe[["timestamp"]]["timestamp"].max())


def single_station_statistics(date1, date2, station_id=None):
    df = dataframe
    if station_id is None:
        station_id = df["station_id"].iloc[0]

    date1 = pd.Timestamp(date1)
    date2 = pd.Timestamp(date2)

    station_df = df[
        (df["station_id"] == station_id)
        & (df["file_timestamp"] >= date1)
        & (df["file_timestamp"] <= date2)
    ].sort_values("file_timestamp")

    if len(station_df) == 0:
        print(
            f"No data found for station {station_id} in date range {date1} to {date2}"
        )
        return

    station_name = station_df["station_name"].iloc[0]

    x = station_df["file_timestamp"].values
    y1 = station_df["pm10_avg"].values
    y2 = station_df["pm25_avg"].values

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.scatter(x, y1, color="skyblue", alpha=0.6, label="PM10")
    ax.scatter(x, y2, color="#982CDE", alpha=0.6, label="PM2.5")
    ax.set_ylabel("concentration (PM10)")
    ax.set_xlabel("timestamp")
    fig.suptitle(f"PM10 over time: {station_name}")
    fig.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


date1 = datetime.datetime(2026, 4, 6, 3)
date2 = datetime.datetime(2026, 4, 30, 4)

single_station_statistics(date1, date2)

