from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .errors import RandomizationError
from .generator import verify_plan
from .models import AllocationRecord, RandomizationPlan


def write_plan(plan: RandomizationPlan, path: Path) -> None:
    verify_plan(plan)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(plan.to_dict(), handle, ensure_ascii=True, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as error:
        raise RandomizationError("LIST_FILE_ALREADY_EXISTS") from error


def load_plan(path: Path) -> RandomizationPlan:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "contracts/randomization-list-v1.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)
        records = tuple(
            AllocationRecord(
                allocation_index=item["allocation_index"],
                stage=item["stage"],
                stratum=item["stratum"],
                block=item["block"],
                arm=item["arm"],
                weather_sequence=(
                    tuple(item["weather_sequence"])
                    if item["weather_sequence"] is not None
                    else None
                ),
                arm_behavior_probability=item["arm_behavior_probability"],
            )
            for item in payload["records"]
        )
        plan = RandomizationPlan(
            schema_version=payload["schema_version"],
            randomization_version=payload["randomization_version"],
            stage=payload["stage"],
            block_size=payload["block_size"],
            seed_commitment=payload["seed_commitment"],
            records=records,
            list_hash=payload["list_hash"],
        )
    except (
        OSError,
        json.JSONDecodeError,
        jsonschema.ValidationError,
        KeyError,
        TypeError,
    ) as error:
        raise RandomizationError("LIST_FILE_INVALID") from error
    verify_plan(plan)
    return plan
