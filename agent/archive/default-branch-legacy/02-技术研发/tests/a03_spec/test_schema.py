from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest


PACKAGE = Path(__file__).parents[3] / "02-技术研发" / "02-信号处理" / "a03_gate2_spec"


def _documents():
    spec = json.loads((PACKAGE / "gate2_spec_v1.0.json").read_text(encoding="utf-8"))
    schema = json.loads((PACKAGE / "gate2_spec_v1.0.schema.json").read_text(encoding="utf-8"))
    return spec, schema


def test_gate2_spec_validates_against_strict_schema():
    spec, schema = _documents()
    jsonschema.Draft202012Validator(schema).validate(spec)


@pytest.mark.parametrize(
    "path",
    [
        ("constructs", "panas"),
        ("constructs", "scci"),
        ("constructs", "comprehension"),
        ("constructs", "mental_effort"),
        ("constructs", "stage_error"),
        ("models",),
        ("ordered_gate",),
    ],
)
def test_null_core_sections_are_rejected(path):
    spec, schema = _documents()
    malformed = copy.deepcopy(spec)
    target = malformed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = None
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(malformed)


def test_unknown_top_level_and_nested_fields_are_rejected():
    spec, schema = _documents()
    top = copy.deepcopy(spec)
    top["unexpected"] = True
    nested = copy.deepcopy(spec)
    nested["constructs"]["scci"]["unexpected"] = True
    validator = jsonschema.Draft202012Validator(schema)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(top)
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(nested)
