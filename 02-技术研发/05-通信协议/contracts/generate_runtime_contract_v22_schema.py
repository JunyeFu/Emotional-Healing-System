from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "runtime-contract-v2.1.schema.json"
TARGET = ROOT / "runtime-contract-v2.2.schema.json"

STEP_PHASES = {
    "storm": {
        "inhale_1": "inhale",
        "hold_1": "hold",
        "exhale_1": "exhale",
        "hold_2": "hold",
    },
    "heat": {"inhale_1": "inhale", "exhale_1": "exhale"},
    "snow": {"inhale_1": "inhale", "exhale_1": "exhale"},
    "fade": {
        "inhale_1": "inhale",
        "inhale_2": "inhale",
        "exhale_1": "exhale",
    },
}


def _step_pair_constraint(prefix: str) -> dict:
    return {
        "oneOf": [
            {
                "properties": {
                    f"{prefix}_cycle_index": {"type": "null"},
                    f"{prefix}_step_id": {"type": "null"},
                    f"{prefix}_phase": {"const": "none"},
                    f"{prefix}_progress": {"const": 0},
                },
                "required": [
                    f"{prefix}_cycle_index",
                    f"{prefix}_step_id",
                    f"{prefix}_phase",
                    f"{prefix}_progress",
                ],
            },
            {
                "properties": {
                    f"{prefix}_cycle_index": {"type": "integer", "minimum": 0},
                    f"{prefix}_step_id": {"type": "string"},
                },
                "required": [f"{prefix}_cycle_index", f"{prefix}_step_id"],
            },
        ]
    }


def build() -> dict:
    schema = deepcopy(json.loads(SOURCE.read_text(encoding="utf-8")))
    schema["$id"] = "https://srp.local/contracts/runtime-contract-v2.2.schema.json"
    schema["title"] = "SRP Runtime Contract v2.2"
    for definition in schema["$defs"].values():
        properties = definition.get("properties", {})
        if "schema_version" in properties:
            properties["schema_version"] = {"const": "2.2"}

    manifest = schema["$defs"]["session_manifest"]
    manifest["required"].extend(
        ["breath_protocol_config_version", "breath_protocol_config_hash"]
    )
    manifest["properties"].update(
        {
            "breath_protocol_config_version": {"type": "string", "minLength": 1},
            "breath_protocol_config_hash": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
        }
    )

    telemetry = schema["$defs"]["telemetry_frame"]
    identity_fields = [
        "target_cycle_index",
        "target_step_id",
        "actual_cycle_index",
        "actual_step_id",
    ]
    telemetry["required"].extend(identity_fields)
    telemetry["properties"]["module_id"] = {"enum": list(STEP_PHASES)}
    for prefix in ("target", "actual"):
        telemetry["properties"][f"{prefix}_cycle_index"] = {
            "type": ["integer", "null"],
            "minimum": 0,
        }
        telemetry["properties"][f"{prefix}_step_id"] = {
            "type": ["string", "null"]
        }
        telemetry["allOf"].append(_step_pair_constraint(prefix))
        for module_id, steps in STEP_PHASES.items():
            telemetry["allOf"].append(
                {
                    "if": {
                        "properties": {"module_id": {"const": module_id}},
                        "required": ["module_id"],
                    },
                    "then": {
                        "properties": {
                            f"{prefix}_step_id": {
                                "type": ["string", "null"],
                                "enum": [None, *steps],
                            }
                        }
                    },
                }
            )
            for step_id, phase in steps.items():
                telemetry["allOf"].append(
                    {
                        "if": {
                            "properties": {
                                "module_id": {"const": module_id},
                                f"{prefix}_step_id": {"const": step_id},
                            },
                            "required": ["module_id", f"{prefix}_step_id"],
                        },
                        "then": {
                            "properties": {f"{prefix}_phase": {"const": phase}}
                        },
                    }
                )
    return schema


if __name__ == "__main__":
    TARGET.write_text(
        json.dumps(build(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
