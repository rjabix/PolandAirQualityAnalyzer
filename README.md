# PolandAirQualityAnalyzer Config Guide

## How configuration works

- `appsettings.yml` stores the actual values.
- `config_loader.py` reads that YAML file.
- `configuration.py` turns the loaded mapping into a `Configuration` object.
- `main.py` uses `configuration.config` by default, so you can also pass a custom config in tests.

## Plan for adding a new config variable

1. Open `appsettings.yml`.
2. Add a new top-level key/value pair.
3. Use it from `configuration` as an attribute.
4. If you want the field to be explicitly typed and visible in code completion, add it to the `Configuration` dataclass in `configuration.py`.

## Example

### 1) Add it in `appsettings.yml`

```yaml
DataFolderPath: "../PolandAirQualityData/data/"
DevMode: true
CacheEnabled: true
MaxRetries: 3
```

### 2) Use it in Python

```python
import configuration

print(configuration.DataFolderPath)
print(configuration.DevMode)
print(configuration.CacheEnabled)
print(configuration.MaxRetries)
```

### 3) Make it explicit in the config class

If you want the new setting to be part of the main config object, add a field in `configuration.py`:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class Configuration:
    DataFolderPath: str
    DevMode: bool
    CacheEnabled: bool = False
    MaxRetries: int = 3
    extra: dict[str, Any] = field(default_factory=dict, repr=False)
```

Then update `from_mapping()` so it pulls those values out of the YAML mapping.

## Recommended workflow

- For quick settings: add the key to `appsettings.yml` and read it through `configuration.<Name>`.
- For important settings: add a typed field to `Configuration` so the setting is explicit and easier to maintain.
- Keep loader logic in `config_loader.py`; keep app-facing config access in `configuration.py`.

