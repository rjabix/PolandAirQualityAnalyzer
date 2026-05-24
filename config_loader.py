"""Low-level loader for `appsettings.yml`.

This module only knows how to read the YAML file and convert it into a Python
mapping. The higher-level `configuration.py` module turns that mapping into a
friendly config object.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _yaml = None


class ConfigurationLoader:
    """Load configuration values from `appsettings.yml`."""

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or Path(__file__).with_name("appsettings.yml")

    def load(self) -> dict[str, Any]:
        """Return the parsed YAML mapping."""
        if not self.settings_path.exists():
            raise FileNotFoundError(f"Settings file not found: {self.settings_path}")

        text = self.settings_path.read_text(encoding="utf-8")
        if _yaml is not None:
            data = _yaml.safe_load(text) or {}
        else:
            data = self._parse_simple_yaml_mapping(text)

        if not isinstance(data, dict):
            raise ValueError("appsettings.yml must contain a YAML mapping at the top level")
        return data

    def _parse_simple_yaml_mapping(self, text: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" not in line:
                raise ValueError(f"Unsupported YAML line: {raw_line!r}")

            key, value_text = line.split(":", 1)
            result[key.strip()] = self._parse_scalar(value_text.strip())
        return result

    def _parse_scalar(self, value_text: str) -> Any:
        if value_text == "":
            return ""

        lowered = value_text.lower()
        if lowered in {"null", "~"}:
            return None
        if lowered == "true":
            return True
        if lowered == "false":
            return False

        try:
            return ast.literal_eval(value_text)
        except (ValueError, SyntaxError):
            return value_text
