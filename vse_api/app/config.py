from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
API_ROOT = APP_DIR.parent
PROJECT_ROOT = API_ROOT.parent
CONFIG_PATH = API_ROOT / "config.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 8010,
    },
    "storage": {
        "data_root": r"D:\short\vse-data",
    },
}


def _load_raw_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        loaded = json.load(f)

    merged = {
        "server": dict(DEFAULT_CONFIG["server"]),
        "storage": dict(DEFAULT_CONFIG["storage"]),
    }
    merged["server"].update(loaded.get("server", {}))
    merged["storage"].update(loaded.get("storage", {}))
    return merged


RAW_CONFIG = _load_raw_config()

SERVER_HOST = str(RAW_CONFIG["server"]["host"])
SERVER_PORT = int(RAW_CONFIG["server"]["port"])
DATA_ROOT = Path(
    os.getenv("VSE_API_DATA_ROOT", str(RAW_CONFIG["storage"]["data_root"]))
).resolve()
JOBS_ROOT = DATA_ROOT / "jobs"
DB_PATH = DATA_ROOT / "app.db"


def ensure_data_dirs() -> None:
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)


def write_default_config() -> None:
    if CONFIG_PATH.exists():
        return
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        f.write("\n")
