import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd
import seaborn as sns
from smogloader import load_snapshot_dir

result = load_snapshot_dir("../PolandAirQualityData/data/")
dataframe = result.df
print(dataframe.info())


def correlation_matrix():
    parameters = dataframe[
        ["humidity_avg", "pressure_avg", "temperature_avg", "pm10_avg", "pm25_avg"]
    ]

    parameters = parameters.sample(frac=0.1)
    corr = parameters.corr()
    print(corr)
    mask = np.triu(np.ones_like(corr, dtype=bool))
    f, ax = plt.subplots(figsize=(11, 9))
    cmap = sns.diverging_palette(346, 230, s=80, l=50, as_cmap=True)
    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.5},
        annot=True,
    )
    plt.suptitle("Correlation Matrix")
    plt.show()


correlation_matrix()
