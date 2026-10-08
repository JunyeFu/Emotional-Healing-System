"""Development-only TD bridge to P-01/P-02; Unity acknowledgements are simulated."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
import uuid

MODULES = Path(__file__).resolve().parents[3] / 'modules'
sys.path.insert(0, str(MODULES))
from srp_session_core import (AssignmentBundle, OperatorRequest, RuntimeDependencies,
                              SessionCore, load_breath_protocol_config)
from srp_session_store import (DurableManifestStore, RecordingSessionCore, RawPacket,
                               ReplayReader, SessionReplayer)


class DevelopmentBackend:
    def __init__(self, root, session_id, condition='A'):
        if condition != 'A':
            raise ValueError('ADAPTIVE_B_NOT_IMPLEMENTED')
        self.root, self.session_id = Path(root), session_id
        self.store = DurableManifestStore.development(self.root)
        dependencies = RuntimeDependencies.development()
        dependencies.manifest_store = self.store
        self.core = RecordingSessionCore(SessionCore(dependencies=dependencies), self.store)
        self.now = 0
        self.frame = 0
        self.sealed = False

    def observation(self, event, **fields):
        return dict(message_type='session_observation', version='1.0',
                    source_mode='dev_mock', authority='python_session_core',
                    session_id=self.session_id, event_id=str(uuid.uuid4()), event=event,
                    **fields)

    def _deliver(self, update, now):
        # This endpoint acknowledges Python controls, not real rendered Unity frames.
        for control in update.control_events:
            self.frame += 1
            ack = dict(schema_version='2.2', message_type='ack', session_id=self.session_id,
                       event_id=control['event_id'], received_monotonic_ns=now,
                       applied_monotonic_ns=now, unity_frame=self.frame,
                       result='applied', error_code=None)
            result = self.core.confirm_delivery(ack, now)
            if any(a.result == 'rejected' for a in result.audit_records):
                raise RuntimeError('SIMULATED_ACK_REJECTED')
        self.now = now
        return update

    def request(self, request, now):
        if request['session_id'] != self.session_id or request['source_mode'] != 'dev_mock':
            raise ValueError('DEVELOPMENT_REQUEST_IDENTITY')
        action = request['action']
        if action == 'prepare':
            if self.core.snapshot().status.value != 'CREATED':
                return self.observation('request_rejected', request_id=request['request_id'])
            trace = json.loads((MODULES / 'srp_session_core/fixtures/golden/four-module-trace-v1.json').read_text(encoding='utf-8'))
            manifest = deepcopy(trace['manifest'])
            config = load_breath_protocol_config()
            manifest.update(session_id=self.session_id, schema_version='2.2',
                            cue_mode='abstract_pacer', assignment_arm='abstract_pacer',
                            breath_protocol_config_version=config.breath_protocol_config_version,
                            breath_protocol_config_hash=config.config_hash,
                            python_commit='TD-DEVELOPMENT-BACKEND',
                            unity_build_hash='sha256:simulated-unity-not-a-build')
            decisions = tuple(dict(p, session_id=self.session_id, schema_version='2.2')
                              for p in trace['policy_decisions'])
            assignment = AssignmentBundle(manifest['allocation_index'],
                manifest['randomization_list_hash'], tuple(manifest['weather_sequence']), decisions)
            update = self.core.prepare(manifest, assignment, now)
            event, expected = 'prepared', 'PREPARED'
        elif action in ('pause', 'resume', 'abort', 'cancel_prepare'):
            update = self.core.apply_operator_request(OperatorRequest(request['request_id'],
                'start' if action == 'resume' else 'abort' if action == 'cancel_prepare' else action), now)
            event, expected = {'pause': ('paused','PAUSED'), 'resume': ('resumed','RUNNING'),
                'abort': ('aborted','ABORTED'), 'cancel_prepare': ('cancelled','ABORTED')}[action]
        else:
            raise ValueError('UNSUPPORTED_REQUEST')
        self._deliver(update, now)
        rejected = any(a.result == 'rejected' for a in update.audit_records)
        if rejected or self.core.snapshot().status.value != expected:
            event = 'request_rejected'
        return self.observation(event, request_id=request['request_id'])

    def start_from_simulated_unity(self, now):
        update = self.core.apply_operator_request(OperatorRequest('SIMULATED-UNITY-START', 'start'), now)
        self._deliver(update, now)
        if self.core.snapshot().status.value != 'RUNNING' or any(a.result == 'rejected' for a in update.audit_records):
            raise RuntimeError(('CORE_START_REJECTED', update.snapshot.status.value,
                                [a.to_dict() for a in update.audit_records]))
        return self.observation('started', unity_start_confirmed=True)

    def advance(self, now):
        self._deliver(self.core.advance(now), now)
        return self.core.snapshot()

    def append_packet(self, packet, now):
        if packet['session_id'] != self.session_id or packet['source_mode'] != 'dev_mock':
            raise ValueError('DEVELOPMENT_PACKET_IDENTITY')
        if self.core.snapshot().status.value not in ('RUNNING','PAUSED'):
            raise ValueError('NOT_RECORDING')
        # Preserve the synthetic sensor-domain JSON exactly; it is not a vendor notification.
        payload = json.dumps(packet, ensure_ascii=False, allow_nan=False).encode('utf-8')
        raw = RawPacket(packet['source_id'], 'replay', packet['packet_seq'], None, now,
                        packet['clock_domain_id'], len(packet['samples']), payload)
        return self.store.archive.append_raw_packet(raw)

    def completed(self):
        if self.core.snapshot().status.value != 'COMPLETED':
            raise ValueError('CORE_NOT_COMPLETED')
        return self.observation('completed')

    def seal(self):
        status = self.core.snapshot().status.value
        if status not in ('COMPLETED','ABORTED') or self.sealed:
            raise ValueError('SEAL_STATE')
        summary = self.core.finish(status, self.now)
        self.store.archive.seal(summary, self.now)
        path = self.store.archive.path
        self.store.archive.close()
        reader = ReplayReader.open(self.root, self.session_id)
        integrity = reader.verify()
        replay = SessionReplayer(reader).replay_core()
        if not integrity.valid or not replay.valid:
            raise RuntimeError('P02_VERIFICATION_FAILED')
        self.sealed = True
        return dict(session_id=self.session_id, archive=str(path), summary=summary.to_dict(),
                    integrity=asdict(integrity), replay=asdict(replay),
                    formal_capable=False, unity_endpoint='simulated',
                    l0_encoding='synthetic sensor-domain JSON, not vendor BLE bytes')

    def close(self):
        if self.store.archive is not None:
            self.store.archive.close()
