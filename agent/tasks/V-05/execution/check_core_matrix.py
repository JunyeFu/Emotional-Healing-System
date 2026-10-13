"""Replay the core only; this does not run Unity or the external journey."""
from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/V-05'
sys.path.insert(0, str(ROOT / 'agent/modules'))
from srp_session_core import AssignmentBundle, OperatorRequest, SessionCore, load_breath_protocol_config


def build_core_matrix():
    golden = json.loads((ROOT / 'agent/modules/srp_session_core/fixtures/golden/four-module-trace-v1.json').read_text(encoding='utf-8'))
    current = json.loads((TASK / 'outputs/current-graybox.json').read_text(encoding='utf-8'))
    breath = load_breath_protocol_config()
    cases = []
    for sequence in permutations(current['module_ids']):
        for cue in current['conditions']:
            manifest = deepcopy(golden['manifest'])
            manifest.update(schema_version='2.2', cue_mode=cue, assignment_arm=cue,
                            session_id=f'S-V05-DEV-{len(cases):02d}', weather_sequence=list(sequence),
                            breath_protocol_config_version=breath.breath_protocol_config_version,
                            breath_protocol_config_hash=breath.config_hash)
            decisions = deepcopy(golden['policy_decisions'])
            for position, decision in enumerate(decisions):
                decision.update(schema_version='2.2', session_id=manifest['session_id'],
                                candidate_actions=list(sequence[position:]), selected_action=sequence[position],
                                behavior_probability=1 / (4 - position))
            assignment = AssignmentBundle(
                allocation_index=manifest['allocation_index'], randomization_list_hash=manifest['randomization_list_hash'],
                weather_sequence=sequence, policy_decisions=tuple(decisions),
                permit_id='V05-DEV-PERMIT', reservation_id='V05-DEV-RESERVATION')
            core = SessionCore()
            controls = []
            segments = []
            ack_count = 0

            def consume(update, now):
                nonlocal ack_count
                for event in update.control_events:
                    controls.append(event['event_type'])
                    if event['event_type'] == 'segment':
                        segments.append({'module_id': event['payload']['module_id'],
                                         'segment': event['payload']['segment'], 'at_ns': now})
                    core.confirm_delivery({
                        'schema_version': '2.2', 'message_type': 'ack',
                        'session_id': event['session_id'], 'event_id': event['event_id'],
                        'received_monotonic_ns': now, 'applied_monotonic_ns': now,
                        'unity_frame': len(controls), 'result': 'applied', 'error_code': None,
                    }, now)
                    ack_count += 1

            consume(core.prepare(manifest, assignment, 0), 0)
            consume(core.apply_operator_request(OperatorRequest('V05-DEV-START', 'start'), 0), 0)
            now = 0
            for _ in range(4):
                for segment in current['core_segments']:
                    now += manifest['module_durations'][segment] * 1_000_000_000
                    consume(core.advance(now), now)
            summary = core.finish('COMPLETED', now).to_dict()
            assert summary['status'] == 'COMPLETED'
            assert tuple(summary['completed_modules']) == sequence
            assert summary['session_elapsed_ns'] == 800_000_000_000
            assert controls.count('module') == 4 and controls.count('segment') == 12
            assert len(controls) == ack_count == 19
            assert len(segments) == 12
            cases.append({'weather_sequence': list(sequence), 'cue_mode': cue,
                          'schema_version': manifest['schema_version'], 'runtime_mode': manifest['runtime_mode'],
                          'source_policy': manifest['source_policy'], 'completed_modules': summary['completed_modules'],
                          'status': summary['status'], 'core_elapsed_ns': summary['session_elapsed_ns'],
                          'control_events': len(controls), 'synthetic_acks': ack_count, 'segment_trace': segments})
    for first, second in zip(cases[::2], cases[1::2]):
        assert first['segment_trace'] == second['segment_trace']
    return {'task_id': 'V-05', 'scope': 'HOST_CORE_ONLY_NOT_UNITY', 'cases': cases,
            'case_count': len(cases), 'sequence_count': len(cases) // 2,
            'acks': 'SYNTHETIC_HOST_FIXTURE', 'unity_render_receipts': 'NOT_RUN',
            'external_journey_runtime': 'NOT_RUN', 'human_formative_review': 'NOT_RUN'}


if __name__ == '__main__':
    output = TASK / 'evidence/runtime/core-matrix.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_core_matrix(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS 24 sequences x 2 conditions in Python SessionCore; Unity NOT_RUN')
