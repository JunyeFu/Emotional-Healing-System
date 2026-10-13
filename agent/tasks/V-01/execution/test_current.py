import copy

import pytest

from validate_current import inputs, validate


def test_current_design():
    assert validate(*inputs()) == []


@pytest.mark.parametrize(('key', 'value'), [
    ('formal_collection_allowed', True),
    ('unity_reads_questionnaires', True),
    ('sequence_authority', 'unity_random'),
    ('td_role', 'session_authority'),
    ('runtime_schema_version', '2.1'),
    ('native_is_hidden', True),
    ('training_budget_seconds', 180),
    ('training_counts_in_core_seconds', True),
    ('core_demo_replaces_training', True),
    ('exposure_boundary', 'before_core_start_only'),
    ('exposure_receipt_required_before_training', False),
    ('report_affect_if_functional_guard_fails', False),
    ('stage_3_required_for_core_paper', True),
    ('camera', 'scrolling'),
    ('fade_fullscreen_color_source', 'recovery_value'),
])
def test_invalid_current_rule(key, value):
    view, protocol, training = inputs()
    view[key] = value
    assert validate(view, protocol, training)


@pytest.mark.parametrize('mutation', ['pre_training', 'post_measures', 'missing_training', 'core_input', 'duplicate_id', 'unknown_boundary'])
def test_invalid_journey(mutation):
    view, protocol, training = inputs()
    nodes = copy.deepcopy(view['journey'])
    if mutation == 'pre_training':
        nodes[2], nodes[3] = nodes[3], nodes[2]
    elif mutation == 'post_measures':
        nodes[11], nodes[12] = nodes[12], nodes[11]
    elif mutation == 'missing_training':
        nodes.pop(3)
    elif mutation == 'core_input':
        nodes[6]['participant_action'] = 'click'
    elif mutation == 'unknown_boundary':
        nodes[5]['id'] = 'J-UNKNOWN'
    else:
        nodes[3]['id'] = nodes[2]['id']
    view['journey'] = nodes
    assert validate(view, protocol, training)
