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

result = load_snapshot_dir(config.DataFolderPath, dev_mode=config.DevMode)

df = result.df

print(df.head())
print(df.info())
print(df["city"].nunique())
wroclawdf = df[df["city"] == "WROCŁAW"]
print(len(wroclawdf.index))
print(wroclawdf["station_name"].nunique())
