from __future__ import annotations

import json
from pathlib import Path

from .canonical import domain_hash
from .errors import StoreError
from .models import StoreConfig


def load_store_config(path: Path | None = None) -> StoreConfig:
    config_path = path or Path(__file__).with_name("config") / "session_store_config_v1.json"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StoreError("STORE_CONFIG_UNAVAILABLE") from error
    required = {
        "storage_schema_version",
        "max_record_bytes",
        "l0_flush_interval_ms",
        "l0_flush_bytes",
        "checkpoint_interval_ms",
        "segment_max_bytes",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise StoreError("STORE_CONFIG_INVALID")
    if payload["storage_schema_version"] != "1.0":
        raise StoreError("STORE_CONFIG_INVALID")
    numeric = required - {"storage_schema_version"}
    if any(
        isinstance(payload[name], bool)
        or not isinstance(payload[name], int)
        or payload[name] <= 0
        for name in numeric
    ):
        raise StoreError("STORE_CONFIG_INVALID")
    return StoreConfig(
        **payload,
        config_hash=domain_hash(b"srp:p02:store-config:v1\0", payload),
    )
