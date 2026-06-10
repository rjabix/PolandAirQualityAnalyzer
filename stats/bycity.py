import numpy as np
import matplotlib.pyplot as plt
import datetime
import seaborn as sns
import pandas as pd
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print(dataframe.info())
print("Dataframe start date: ", dataframe[["timestamp"]]["timestamp"].min())
print("Datafram end date: ", dataframe[["timestamp"]]["timestamp"].max())


def bycity(date1 = None, date2 = None):
    df = dataframe

    if date1:
        date1 = pd.Timestamp(date1)
        df = df[df["file_timestamp"] >= date1]
    if date2:
        date2 = pd.Timestamp(date2)
        df = df[df["file_timestamp"] <= date2]

    top_n = 50

    # city_stats = (
    #     df.groupby("city")[["pm10_avg", "pm25_avg"]]
    #     .mean()
    #     .sort_values("pm25_avg", ascending=False)
    #     .head(top_n)
    #     .reset_index()
    # )

    df["pm_sum"] = df["pm10_avg"] + df["pm25_avg"]
    df["pm_diff"] = df["pm10_avg"] - df["pm25_avg"]

    city_stats = (
        df.groupby("city")[["pm10_avg", "pm25_avg", "pm_sum", "pm_diff"]]
        .mean()
        .sort_values("pm_diff", ascending=False)
        .head(top_n)
        .reset_index()
    )

    f, ax = plt.subplots(figsize=(8, top_n * 0.4))


    # sns.set_color_codes("pastel")
    # sns.barplot(x="pm_diff", y="city", data=city_stats, label="PM10 - PM2.5", color="b")


    sns.set_color_codes("pastel")
    sns.barplot(x="pm10_avg", y="city", data=city_stats, label="PM10 - PM2.5", color="b")

    sns.set_color_codes("muted")
    sns.barplot(x="pm25_avg", y="city", data=city_stats, label="PM2.5", color="b")

    # sns.set_color_codes("deep")
    # sns.barplot(x="pm_diff", y="city", data=city_stats, label="PM2.5 diff", color="b")



    # sns.set_color_codes("muted")
    # sns.barplot(x="pm25_avg", y="city", data=city_stats, label="PM2.5", color="b")

    ax.legend(ncol=2, loc="lower right", frameon=True)
    ax.set(ylabel="", xlabel="Mean PM concentration")
    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    plt.show()


date1 = datetime.datetime(2026, 4, 6, 3)
date2 = datetime.datetime(2026, 4, 30, 4)

bycity()

