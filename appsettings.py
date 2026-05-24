"""Compatibility wrapper for older imports.

Prefer `configuration.py` for new code.
"""

from configuration import Configuration, DataFolderPath, config


def __getattr__(name):
    return getattr(config, name)


__all__ = ["Configuration", "config", "DataFolderPath"]
