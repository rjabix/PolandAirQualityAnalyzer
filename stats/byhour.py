import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd
import seaborn as sns
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print(dataframe.info())
print("Dataframe start date: ", dataframe[["timestamp"]]["timestamp"].min())
print("Datafram end date: ", dataframe[["timestamp"]]["timestamp"].max())


def weekday_statistics(date1=None, date2=None, pm_type="pm10_avg"):
    sns.set_theme(style="white", rc={"axes.facecolor": (0, 0, 0, 0)})
    pal = sns.cubehelix_palette(7, rot=-0.25, light=0.7)
    df = dataframe

    if date1:
        date1 = pd.Timestamp(date1)
        df = df[df["file_timestamp"] >= date1]
    if date2:
        date2 = pd.Timestamp(date2)
        df = df[df["file_timestamp"] <= date2]

    df = df.sample(frac=0.001)
    df = df[df[pm_type] < 100]
    df["hour"] = df["file_timestamp"].dt.hour

    print(len(df.index))


    g = sns.FacetGrid(
        df,
        row="hour",
        hue="hour",
        aspect=15,
        height=0.5,
        palette=pal,
    )
    g.map(
        sns.kdeplot,
        pm_type,
        bw_adjust=0.1,
        clip_on=False,
        fill=True,
        alpha=0.8,
        linewidth=1.5,
    )

    def label(x, color, label):
        ax = plt.gca()
        ax.text(0.95, .2, label, color=color,
                ha="left", va="center", transform=ax.transAxes)
    # hour_order = [str(h).zfill(2) + ":00" for h in range(24)]
    # df["hour_label"] = df["hour"].apply(lambda h: str(h) + ":00")
    # df["hour_label"] = df["hour"]
    # df["hour_label"] = pd.Categorical(df["hour_label"], categories=hour_order, ordered=True)
    g.map(label, "hour")
    g.refline(y=0, linewidth=2, linestyle="-", color=None, clip_on=False)
    g.figure.subplots_adjust(hspace=-0.5)
    g.set_titles("")
    g.set(yticks=[], ylabel="")
    g.despine(bottom=True, left=True)
    g.figure.subplots_adjust(hspace=-0.5, left=0.04)
    if pm_type == "pm10_avg":
        g.axes[-1, 0].set_xlabel("PM10")
    if pm_type == "pm25_avg":
        g.axes[-1, 0].set_xlabel("PM2.5")
    g.figure.text(0.02, 0.5, "Density", rotation=90, va="center")
    if pm_type == "pm10_avg":
        plt.suptitle("PM10 density aggregated by hour")
    if pm_type == "pm25_avg":
        plt.suptitle("PM2.5 density aggregated by hour")

    plt.show()


date1 = datetime.datetime(2026, 4, 10, 0)
date2 = datetime.datetime(2026, 4, 30, 0)

# weekday_statistics(date1, date2)
weekday_statistics(pm_type="pm10_avg")
