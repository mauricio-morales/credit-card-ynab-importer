from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class BudgetConfig:
    budget_name: str
    loan_account_id: str


@dataclass
class Config:
    api_key: str = ""
    budgets: dict[str, BudgetConfig] = field(default_factory=dict)


_CONFIG_PATH = Path.home() / ".config" / "credit-card-ynab-importer" / "config.json"


def _config_path() -> Path:
    return _CONFIG_PATH


def load_config() -> Config:
    path = _config_path()
    if not path.exists():
        return Config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        budgets = {
            k: BudgetConfig(**v)
            for k, v in data.get("budgets", {}).items()
        }
        return Config(api_key=data.get("api_key", ""), budgets=budgets)
    except (json.JSONDecodeError, KeyError, TypeError):
        return Config()


def save_config(config: Config) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "api_key": config.api_key,
        "budgets": {
            k: asdict(v) for k, v in config.budgets.items()
        },
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)
