import argparse
import importlib
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def _module(name: str, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _configuration_module(output_dir: str = "output"):
    config = types.SimpleNamespace(
        DataFolderPath="data",
        DevMode=False,
        OutputDir=output_dir,
    )
    return _module("configuration", Configuration=type("Configuration", (), {}), config=config)


class MainTests(unittest.TestCase):
    def test_run_gifs_generates_all_expected_outputs(self):
        result = types.SimpleNamespace(df=object())
        load_snapshot_dir = Mock(return_value=result)

        pm25 = Mock()
        temp = Mock()
        bar = Mock()
        heatmap = Mock()

        cfg_module = _configuration_module(output_dir="out")
        smogloader = _module("smogloader", load_snapshot_dir=load_snapshot_dir)
        visualizations = _module(
            "visualizations",
            generate_pm25_map=pm25,
            generate_temperature_map=temp,
            generate_bar_race=bar,
            generate_daily_heatmap=heatmap,
        )

        with patch.dict(sys.modules, {"configuration": cfg_module, "smogloader": smogloader, "visualizations": visualizations}):
            sys.modules.pop("main", None)
            main = importlib.import_module("main")
            custom_cfg = types.SimpleNamespace(DataFolderPath="input", DevMode=True, OutputDir="out")
            main.run_gifs(custom_cfg)

        load_snapshot_dir.assert_called_once_with("input", dev_mode=True)
        pm25.assert_called_once_with(result.df, Path("out") / "pm25_map.gif")
        temp.assert_called_once_with(result.df, Path("out") / "temperature_map.gif")
        bar.assert_called_once_with(result.df, Path("out") / "bar_race.gif")
        heatmap.assert_called_once_with(result.df, Path("out") / "daily_heatmap.gif")

    def test_run_dashboard_starts_dash_app_with_expected_arguments(self):
        run = Mock()
        cfg_module = _configuration_module()
        app_module = _module("app", app=types.SimpleNamespace(run=run))

        with patch.dict(sys.modules, {"configuration": cfg_module, "app": app_module}):
            sys.modules.pop("main", None)
            main = importlib.import_module("main")
            main.run_dashboard()

        run.assert_called_once_with(debug=False, host="127.0.0.1", port=8050)

    def test_main_cli_mode_gifs_runs_only_gif_generation(self):
        cfg_module = _configuration_module()
        load_snapshot_dir = Mock(return_value=types.SimpleNamespace(df=object()))
        visualizations = _module(
            "visualizations",
            generate_pm25_map=Mock(),
            generate_temperature_map=Mock(),
            generate_bar_race=Mock(),
            generate_daily_heatmap=Mock(),
        )
        smogloader = _module("smogloader", load_snapshot_dir=load_snapshot_dir)
        app_module = _module("app", app=types.SimpleNamespace(run=Mock()))

        with patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(mode="gifs")):
            with patch.dict(
                sys.modules,
                {"configuration": cfg_module, "smogloader": smogloader, "visualizations": visualizations, "app": app_module},
            ):
                runpy.run_module("main", run_name="__main__")

        load_snapshot_dir.assert_called_once()
        app_module.app.run.assert_not_called()

    def test_main_cli_mode_dashboard_runs_only_dashboard(self):
        cfg_module = _configuration_module()
        load_snapshot_dir = Mock(return_value=types.SimpleNamespace(df=object()))
        smogloader = _module("smogloader", load_snapshot_dir=load_snapshot_dir)
        visualizations = _module(
            "visualizations",
            generate_pm25_map=Mock(),
            generate_temperature_map=Mock(),
            generate_bar_race=Mock(),
            generate_daily_heatmap=Mock(),
        )
        app_module = _module("app", app=types.SimpleNamespace(run=Mock()))

        with patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(mode="dashboard")):
            with patch.dict(
                sys.modules,
                {"configuration": cfg_module, "smogloader": smogloader, "visualizations": visualizations, "app": app_module},
            ):
                runpy.run_module("main", run_name="__main__")

        app_module.app.run.assert_called_once_with(debug=False, host="127.0.0.1", port=8050)
        load_snapshot_dir.assert_not_called()

    def test_main_cli_default_runs_gifs_then_dashboard(self):
        cfg_module = _configuration_module()
        load_snapshot_dir = Mock(return_value=types.SimpleNamespace(df=object()))
        smogloader = _module("smogloader", load_snapshot_dir=load_snapshot_dir)
        visualizations = _module(
            "visualizations",
            generate_pm25_map=Mock(),
            generate_temperature_map=Mock(),
            generate_bar_race=Mock(),
            generate_daily_heatmap=Mock(),
        )
        app_module = _module("app", app=types.SimpleNamespace(run=Mock()))

        with patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(mode="all")):
            with patch.dict(
                sys.modules,
                {"configuration": cfg_module, "smogloader": smogloader, "visualizations": visualizations, "app": app_module},
            ):
                runpy.run_module("main", run_name="__main__")

        load_snapshot_dir.assert_called_once()
        app_module.app.run.assert_called_once_with(debug=False, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    unittest.main()
