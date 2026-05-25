import numpy as np
import matplotlib.pyplot as plt
import datetime
import os
import pathlib
import json


working_directory_path = "../PolandAirQualityData/data/"

working_directory = pathlib.Path(working_directory_path)



def choose_date(date1, date2, directory=working_directory):
    chosen_files = []
    for file in sorted(working_directory.iterdir()):
        prefix = "smog_api_"
        filename = file.name
        if filename[:len(prefix)] == prefix:
            date_string = filename[len(prefix):]
            # date_format = "%F-%H-%M-%S-%Z"
            date_format = "%Y-%m-%d-%H-%M-%S-%Z"
            # 2026-03-30-04-01-01-CEST 
            file_date = datetime.datetime.strptime(date_string, date_format)
            if file_date > date1 and file_date < date2:
                chosen_files.append(file)
    return chosen_files


def single_file_statistics():
    example_file = "smog_api_2026-03-18-18-36-01-CET"
    file = pathlib.Path(working_directory_path + example_file)
    with file.open() as f:
        filedata = json.load(f)
        # print(json.dumps(filedata, indent=4)[:2000])
        pm_10 = np.zeros(len(filedata["smog_data"]))
        pm_25 = np.zeros(len(filedata["smog_data"]))
        for i, school in enumerate(filedata["smog_data"]):
            parameters = school["data"]
            pm_10[i] = parameters["pm10_avg"]
            pm_25[i] = parameters["pm25_avg"]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        fig.suptitle("Data for " + example_file)
        ax1.hist(pm_10, bins=60, color="skyblue")
        ax1.set_title("pm10")
        ax1.set_ylabel("frequency")
        ax1.set_xlabel("concentration (PM10)")
        ax1.grid()
        ax2.hist(pm_25, bins=60, color="skyblue")
        ax2.set_title("pm25")
        ax2.set_xlabel("concentration (PM10)")
        ax2.set_ylabel("frequency")
        ax2.grid()
        plt.show()


def single_school_statistics(date1, date2, school_index=0):
    files = choose_date(date1, date2)
    parameters = np.zeros(len(files))
    school_name = ""
    with files[0].open() as f:
        filedata = json.load(f)
        # print(json.dumps(filedata, indent=4)[:2000])
        school_name = filedata["smog_data"][school_index]["school"]["name"]
    for i, file in enumerate(files):
        try:
            with file.open() as f:
                school_data = json.load(f)["smog_data"][school_index]["data"]
                parameters[i] = school_data["pm10_avg"]
        except json.JSONDecodeError:
            parameters[i] = 0
            print("Corrupted File:", file)
        except IndexError:
            parameters[i] = 0
            print("Corrupted File:", file)

    prefix = "smog_api_"
    x = np.array([path.name[len(prefix):len(prefix) + 13] for path in files])
    y = parameters

    fig, ax = plt.subplots()
    ax.scatter(x, y, color="skyblue")
    ticks = np.where(np.arange(len(x)) % (len(x) // 10) == 0, x, np.full((len(x)), ""))
    ax.xaxis.set_ticks(ticks)
    fig.suptitle("Data for " + school_name)
    ax.xaxis.set_tick_params(rotation=60)
    ax.set_ylabel("concentration (PM10)")
    plt.show()


date1 = datetime.datetime(2026, 4, 6, 3)
date2 = datetime.datetime(2026, 4, 30, 4)

single_file_statistics()
single_school_statistics(date1, date2)







