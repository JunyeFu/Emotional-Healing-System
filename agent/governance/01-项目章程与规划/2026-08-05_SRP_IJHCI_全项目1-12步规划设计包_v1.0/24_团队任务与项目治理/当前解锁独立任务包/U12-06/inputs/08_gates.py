from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Protocol

from .errors import SessionCoreError
from .models import AssignmentBundle, GateReceipt


class PreparationGate(Protocol):
    formal_capable: bool

    def check(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        config_hash: str,
    ) -> GateReceipt: ...


class ManifestStore(Protocol):
    formal_capable: bool

    def append_manifest(
        self, manifest: Mapping[str, Any], config_hash: str
    ) -> GateReceipt: ...


class ExposureGate(Protocol):
    formal_capable: bool

    def mark_exposed(
        self, manifest: Mapping[str, Any], assignment: AssignmentBundle
    ) -> GateReceipt: ...


@dataclass
class CallableGate:
    name: str
    checker: Callable[[Mapping[str, Any], AssignmentBundle, str], str | None]
    formal_capable: bool = False

    def check(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        config_hash: str,
    ) -> GateReceipt:
        try:
            evidence_id = self.checker(manifest, assignment, config_hash) or f"{self.name}:PASS"
        except SessionCoreError:
            raise
        except Exception as error:
            code = str(getattr(error, "code", "GATE_FAILED"))
            path = str(getattr(error, "path", ""))
            raise SessionCoreError(f"{self.name.upper()}_{code}", path) from error
        return GateReceipt(self.name, evidence_id, self.formal_capable)


@dataclass
class InMemoryManifestStore:
    formal_capable: bool = False
    records: list[dict[str, Any]] = field(default_factory=list)

    def append_manifest(
        self, manifest: Mapping[str, Any], config_hash: str
    ) -> GateReceipt:
        self.records.append({"manifest": dict(manifest), "config_hash": config_hash})
        return GateReceipt("manifest_store", f"memory:{len(self.records)}", self.formal_capable)


@dataclass
class CallableExposureGate:
    marker: Callable[[Mapping[str, Any], AssignmentBundle], str | None]
    formal_capable: bool = False

    def mark_exposed(
        self, manifest: Mapping[str, Any], assignment: AssignmentBundle
    ) -> GateReceipt:
        evidence_id = self.marker(manifest, assignment) or "exposure:PASS"
        return GateReceipt("exposure", evidence_id, self.formal_capable)


@dataclass
class G02PrivacyGate:
    checker: Callable[[dict[str, Any]], None]
    formal_capable: bool = True

    def check(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        config_hash: str,
    ) -> GateReceipt:
        del assignment, config_hash
        try:
            self.checker(dict(manifest))
        except Exception as error:
            code = str(getattr(error, "code", "GATE_FAILED"))
            path = str(getattr(error, "path", ""))
            raise SessionCoreError(f"PRIVACY_{code}", path) from error
        return GateReceipt("privacy", "g02:privacy-lint:PASS", self.formal_capable)


def load_g02_privacy_gate(repo_root: Path | None = None) -> G02PrivacyGate:
    root = repo_root or Path(__file__).resolve().parents[2]
    module_root = root / "02-技术研发" / "07-数据治理"
    if not module_root.is_dir():
        raise SessionCoreError("G02_PRIVACY_GATE_UNAVAILABLE", str(module_root))
    module_path = str(module_root)
    if module_path not in sys.path:
        sys.path.insert(0, module_path)
    try:
        from srp_governance import privacy_lint_manifest
    except ImportError as error:
        raise SessionCoreError("G02_PRIVACY_GATE_UNAVAILABLE") from error
    return G02PrivacyGate(privacy_lint_manifest)


def _synthetic_gate(
    manifest: Mapping[str, Any], assignment: AssignmentBundle, config_hash: str
) -> str:
    del manifest, assignment, config_hash
    return "synthetic:PASS"


def _synthetic_exposure(
    manifest: Mapping[str, Any], assignment: AssignmentBundle
) -> str:
    del manifest, assignment
    return "synthetic-exposure:PASS"


@dataclass
class RuntimeDependencies:
    privacy_gate: PreparationGate
    assignment_gate: PreparationGate
    formal_readiness_gate: PreparationGate
    manifest_store: ManifestStore
    exposure_gate: ExposureGate

    @classmethod
    def development(cls) -> "RuntimeDependencies":
        return cls(
            privacy_gate=load_g02_privacy_gate(),
            assignment_gate=CallableGate("assignment", _synthetic_gate),
            formal_readiness_gate=CallableGate("formal_readiness", _synthetic_gate),
            manifest_store=InMemoryManifestStore(),
            exposure_gate=CallableExposureGate(_synthetic_exposure),
        )

    def _require_capability(self, adapter: Any, manifest: Mapping[str, Any], name: str) -> None:
        if str(manifest["runtime_mode"]).startswith("formal_") and not adapter.formal_capable:
            raise SessionCoreError("FORMAL_GATE_UNAVAILABLE", name)

    def privacy_receipt(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        config_hash: str,
    ) -> GateReceipt:
        self._require_capability(self.privacy_gate, manifest, "privacy_gate")
        return self.privacy_gate.check(manifest, assignment, config_hash)

    def assignment_receipt(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        config_hash: str,
    ) -> GateReceipt:
        self._require_capability(self.assignment_gate, manifest, "assignment_gate")
        return self.assignment_gate.check(manifest, assignment, config_hash)

    def store_receipt(
        self, manifest: Mapping[str, Any], config_hash: str
    ) -> GateReceipt:
        self._require_capability(self.manifest_store, manifest, "manifest_store")
        return self.manifest_store.append_manifest(manifest, config_hash)

    def readiness_receipt(
        self,
        manifest: Mapping[str, Any],
        assignment: AssignmentBundle,
        config_hash: str,
    ) -> GateReceipt:
        self._require_capability(
            self.formal_readiness_gate, manifest, "formal_readiness_gate"
        )
        self._require_capability(self.exposure_gate, manifest, "exposure_gate")
        return self.formal_readiness_gate.check(manifest, assignment, config_hash)

    def mark_exposed(
        self, manifest: Mapping[str, Any], assignment: AssignmentBundle
    ) -> GateReceipt:
        try:
            return self.exposure_gate.mark_exposed(manifest, assignment)
        except SessionCoreError:
            raise
        except Exception as error:
            raise SessionCoreError("EXPOSURE_GATE_FAILED", type(error).__name__) from error
