from configuration import Configuration, config
from smogloader import load_snapshot_dir


def main(configuration: Configuration = config):
    result = load_snapshot_dir(configuration.DataFolderPath, dev_mode=configuration.DevMode)
    df = result.df
    df[df["city"] == "PSZCZYNA"].plot(x="file_timestamp", y="pm25_avg")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
