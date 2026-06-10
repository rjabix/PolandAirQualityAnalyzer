#
# Execute this file from the root project directory with
#
# python3 -m stats.test
#
# or else it will have issues with imports
#

import argparse
import logging
from pathlib import Path

from configuration import Configuration, config

from smogloader import load_snapshot_dir

result = load_snapshot_dir(config.DataFolderPath)

df = result.df

print(df.head())
print(df.info())
print("Shape:", df.shape)
print("Numebr of cities:", df["city"].nunique())
print("Start date: ", df[["timestamp"]]["timestamp"].min())
print("End date: ", df[["timestamp"]]["timestamp"].max())
wroclawdf = df[df["city"] == "WROCŁAW"]
print(len(wroclawdf.index))
print(wroclawdf["station_name"].nunique())


wroclaw_stats = df[df["city"].str.contains("WROCŁAW")]
print(wroclaw_stats[["city"]]["city"].unique())


