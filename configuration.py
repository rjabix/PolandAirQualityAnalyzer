"""Project configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config_loader import ConfigurationLoader


@dataclass(slots=True)
class Configuration:
    DataFolderPath: str
    DevMode: bool
    OutputDir: str

    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> "Configuration":
        for key in ("DataFolderPath", "DevMode", "OutputDir"):
            if key not in mapping:
                raise KeyError(f"Missing required config key: '{key}'")
        extra = {k: v for k, v in mapping.items() if k not in {"DataFolderPath", "DevMode", "OutputDir"}}
        return cls(
            DataFolderPath=mapping["DataFolderPath"],
            DevMode=mapping["DevMode"],
            OutputDir=mapping["OutputDir"],
            extra=extra,
        )

    def __getattr__(self, name: str) -> Any:
        try:
            return self.extra[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"DataFolderPath": self.DataFolderPath, "DevMode": self.DevMode, "OutputDir": self.OutputDir, **self.extra}


_loader = ConfigurationLoader()
config = Configuration.from_mapping(_loader.load())

DataFolderPath: str = config.DataFolderPath
DevMode: bool = config.DevMode
OutputDir: str = config.OutputDir


def __getattr__(name: str) -> Any:
    return getattr(config, name)

def __dir__() -> list[str]:
    return sorted({*globals().keys(), *config.to_dict().keys()})

__all__ = ["Configuration", "config", "DataFolderPath", "DevMode", "OutputDir"]
