"""Project configuration.

Use this module as:

    import configuration
    print(configuration.DataFolderPath)

The actual file-loading logic lives in `config_loader.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config_loader import ConfigurationLoader


@dataclass(slots=True)
class Configuration:
    """Structured configuration values loaded from `appsettings.yml`."""

    DataFolderPath: str
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> "Configuration":
        if "DataFolderPath" not in mapping:
            raise KeyError("Missing required config key: 'DataFolderPath'")

        extra = {key: value for key, value in mapping.items() if key != "DataFolderPath"}
        return cls(DataFolderPath=mapping["DataFolderPath"], extra=extra)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.extra[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"DataFolderPath": self.DataFolderPath, **self.extra}


_loader = ConfigurationLoader()
config = Configuration.from_mapping(_loader.load())

# Explicit attribute for the common setting, so code completion and static
# analysis understand `configuration.DataFolderPath`.
DataFolderPath: str = config.DataFolderPath


def __getattr__(name: str) -> Any:
    return getattr(config, name)


def __dir__() -> list[str]:
    return sorted({*globals().keys(), *config.to_dict().keys()})


__all__ = ["Configuration", "config", "DataFolderPath"]
