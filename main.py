from configuration import Configuration, config
from smogloader import load_snapshot_dir


def main(configuration: Configuration = config):
    result = load_snapshot_dir(configuration.DataFolderPath)
    df = result.df


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
