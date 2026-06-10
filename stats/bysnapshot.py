import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print("Dataframe start date: ", dataframe[["timestamp"]]["timestamp"].min())
print("Datafram end date: ", dataframe[["timestamp"]]["timestamp"].max())


def single_snapshot_statistics(target_date=None):
    df = dataframe
    if target_date is None:
        target_date = df["file_timestamp"].max()
    else:
        target_date = pd.Timestamp(target_date)

    snapshot_df = df[df["file_timestamp"] == target_date]

    if len(snapshot_df) == 0:
        print(f"No data found for {target_date}")
        return

    pm_10_95q = snapshot_df.pm10_avg.quantile(0.95)
    pm_25_95q = snapshot_df.pm25_avg.quantile(0.95)

    set_bounds = True

    if set_bounds:
        snapshot_df = snapshot_df[
            (snapshot_df.pm10_avg <= pm_10_95q) & (snapshot_df.pm25_avg <= pm_25_95q)
        ]

    pm_10 = snapshot_df["pm10_avg"].values
    pm_10_median = snapshot_df["pm10_avg"].median()
    pm_10_mean = snapshot_df["pm10_avg"].mean()
    pm_10_max = snapshot_df["pm10_avg"].max()

    pm_25 = snapshot_df["pm25_avg"].values
    pm_25_median = snapshot_df["pm25_avg"].median()
    pm_25_mean = snapshot_df["pm25_avg"].mean()
    pm_25_max = snapshot_df["pm25_avg"].max()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    fig.suptitle(f"Data for {target_date.strftime('%Y-%m-%d %H:%M:%S')}")

    nbins = 200
    ax1.hist(pm_10, bins=nbins, color="skyblue")
    ax1.set_title("PM10")
    ax1.set_ylabel("frequency")
    ax1.set_xlabel("concentration")
    ax1.grid()
    ax1.axvline(
        x=pm_10_mean,
        linestyle="--",
        color="#2C94D4",
        label=f"mean: PM10 = {pm_10_mean:.2f}",
    )
    ax1.axvline(
        x=pm_10_median,
        linestyle="--",
        color="#2761C2",
        label=f"median: PM10 = {pm_10_median:.2f}",
    )
    ax1.axvline(
        x=pm_10_max, linestyle="--", color="red", label=f"max: PM10 = {pm_10_max:.2f}"
    )
    ax1.legend()

    ax2.hist(pm_25, bins=nbins, color="skyblue")
    ax2.set_title("PM2.5")
    ax2.set_xlabel("concentration")
    ax2.set_ylabel("frequency")
    ax2.grid()
    ax2.axvline(
        x=pm_25_mean,
        linestyle="--",
        color="#2C94D4",
        label=f"mean: PM25 = {pm_25_mean:.2f}",
    )
    ax2.axvline(
        x=pm_25_median,
        linestyle="--",
        color="#2761C2",
        label=f"median: PM25 = {pm_25_median:.2f}",
    )
    ax2.axvline(
        x=pm_25_max, linestyle="--", color="red", label=f"max: PM25 = {pm_25_max:.2f}"
    )
    ax2.legend()

    plt.tight_layout()
    plt.show()


single_snapshot_statistics()
