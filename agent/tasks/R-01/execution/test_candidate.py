"""Exercise the candidate schema, not a replacement runtime protocol."""
import copy

import pytest
from jsonschema import Draft202012Validator

from validate_candidate import FIXTURES, SCHEMA, load_json


@pytest.fixture
def validator():
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.mark.parametrize('name', ['scene-native', 'abstract-pacer'])
def test_valid_condition(validator, name):
    validator.validate(load_json(FIXTURES / f'valid-storm-{name}.json'))


@pytest.mark.parametrize(('name', 'path'), [
    ('missing-fallback', ['layers']),
    ('coupled-actual', ['layers', 'actual', 'source']),
    ('unusable-behavior', ['fallback_contract', 'UNUSABLE']),
    ('confound-budget', ['confound_budget', 'motion_energy_relative_difference']),
])
def test_targeted_negative(validator, name, path):
    errors = list(validator.iter_errors(load_json(FIXTURES / f'invalid-{name}.json')))
    assert any(list(error.path) == path for error in errors)


@pytest.mark.parametrize(('path', 'value'), [
    (['cue_mode'], 'hidden'),
    (['timing', 'demo_seconds'], 23),
    (['timing', 'closed_loop_seconds'], 161),
    (['timing', 'lock_transition_seconds'], 31),
    (['schema_version'], '2.2'),
    (['layers', 'target', 'source'], 'python.interaction_state_estimate'),
])
def test_other_invalid_fields(validator, path, value):
    candidate = copy.deepcopy(load_json(FIXTURES / 'valid-storm-scene-native.json'))
    parent = candidate
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    assert list(validator.iter_errors(candidate))


def test_condition_invariants():
    native = load_json(FIXTURES / 'valid-storm-scene-native.json')
    abstract = load_json(FIXTURES / 'valid-storm-abstract-pacer.json')
    for key in ('timing', 'layers', 'fallback_contract', 'confound_budget'):
        assert native[key] == abstract[key]
    assert native['mapping'] != abstract['mapping']
