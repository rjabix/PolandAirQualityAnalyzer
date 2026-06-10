import numpy as np
import numpy as np
import matplotlib.pyplot as plt
import datetime
import seaborn as sns
import pandas as pd
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print(dataframe.info())


def bycity(date1=None, date2=None):
    df = dataframe

    pm_10_end = df.pm10_avg.quantile(0.90)
    pm_10_start = df.pm10_avg.quantile(0.02)
    temp_end = df.temperature_avg.quantile(0.98)
    temp_start = df.temperature_avg.quantile(0.02)

    df = df.sample(frac=0.001)
    df = df[
        (df["pressure_avg"] > temp_start) &
        (df["pressure_avg"] < temp_end) &
        (df["pm10_avg"] > pm_10_start) &
        (df["pm10_avg"] < pm_10_end)
    ]

    if date1:
        date1 = pd.Timestamp(date1)
        df = df[df["file_timestamp"] >= date1]
    if date2:
        date2 = pd.Timestamp(date2)
        df = df[df["file_timestamp"] <= date2]

    g = sns.JointGrid(data=df, x="pressure_avg", y="pm10_avg", space=0)
    g.plot_joint(sns.kdeplot, fill=True, thresh=0, levels=100, cmap="rocket")
    g.plot_marginals(sns.kdeplot, color="#582766", fill=True, alpha=1)
    g.set_axis_labels("Presure (Pa)", "PM 10")
    plt.show()


date1 = datetime.datetime(2026, 5, 1, 0)
date2 = datetime.datetime(2026, 4, 30, 4)

bycity(date1)

