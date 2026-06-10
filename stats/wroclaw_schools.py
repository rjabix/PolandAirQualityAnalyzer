import numpy as np
import matplotlib.pyplot as plt
import datetime
import seaborn as sns
import pandas as pd
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print(dataframe.info())


def bycity(date1 = None, date2 = None):
    df = dataframe
    # df = df.sample(frac=0.1)

    if date1:
        date1 = pd.Timestamp(date1)
        df = df[df["file_timestamp"] >= date1]
    if date2:
        date2 = pd.Timestamp(date2)
        df = df[df["file_timestamp"] <= date2]

    top_n = 50


    # wroclaw_stats = df[
    #     (df["station_name"] == "EUROPEJSKIE LICEUM SŁUŻB MUNDUROWYCH WE WROCŁAWIU") |
    #     (df["station_name"] == "SZKOŁA PODSTAWOWA EKOLA WROCŁAW") |
    #     (df["station_name"] == "LICEUM OGÓLNOKSZTAŁCĄCE Z ODDZIAŁAMI INTEGRACYJNYMI NR XXX WE WROCŁAWIU") |
    #     (df["station_name"] == "TECHNIKUM AKADEMICKIE PRZY MIĘDZYNARODOWEJ WYŻSZEJ SZKOLE LOGISTYKI I TRANSPORTU WE WROCŁAWIU")
    #     ]

    wroclaw_stats = df[(df["station_name"] == "EUROPEJSKIE LICEUM SŁUŻB MUNDUROWYCH WE WROCŁAWIU")]


    week_starts = pd.date_range(
        start=wroclaw_stats["timestamp"].min(),
        end=wroclaw_stats["timestamp"].max(),
        freq="W-MON"
    )
    day_starts = pd.date_range(
        start=wroclaw_stats["timestamp"].min(),
        end=wroclaw_stats["timestamp"].max(),
        freq="D"
    )


    sns.lineplot(
        data=wroclaw_stats, x="timestamp", y="pm10_avg", units="city",
        estimator=None, color=".7", linewidth=1, hue="city", palette="pastel",
    )
    ax = plt.gca()
    for date in week_starts:
        ax.axvline(x=date, color="blue", linestyle="--", linewidth=4, alpha=0.3)
    for date in day_starts:
        ax.axvline(x=date, color="teal", linestyle="--", linewidth=2, alpha=0.3)

    import matplotlib.patches as mpatches
    week = mpatches.Patch(color='blue', alpha=0.3, linestyle="--", linewidth=0.3, label='Weekends')
    day = mpatches.Patch(color='teal', alpha=0.3, linestyle="--", linewidth=0.3, label='Day ends')

    handles, labels = ax.get_legend_handles_labels()
    handles.append(week)
    handles.append(day)

    plt.legend(handles=handles)
    plt.suptitle("Wrocław Schools PM10 by time")
    # plt.legend()
    plt.show()




date1 = datetime.datetime(2026, 5, 1, 0)
date2 = datetime.datetime(2026, 4, 30, 4)

bycity(date1)


