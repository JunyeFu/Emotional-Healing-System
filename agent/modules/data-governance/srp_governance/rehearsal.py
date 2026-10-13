from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile

from .backup import backup_registry, restore_registry
from .registry import DedupRegistry, Stage


def _synthetic_phone(index: int) -> str:
    return f"+86139{index:08d}"


def run_synthetic_rehearsal() -> dict:
    key = b"G" * 32
    actor = "synthetic-data-admin"
    stages = tuple(Stage)
    with tempfile.TemporaryDirectory(prefix="srp-g02-rehearsal-") as temporary:
        root = Path(temporary)
        registry = DedupRegistry(
            database_path=root / "governance" / "dedup" / "dedup_registry.sqlite",
            key_provider=lambda: key,
            allowed_actors={actor},
        )

        active_results: list[bool] = []
        exposed_results: list[bool] = []
        index = 0
        for first_stage in stages:
            for next_stage in stages:
                phone = _synthetic_phone(index)
                index += 1
                first = registry.check_and_reserve(phone, first_stage, actor)
                blocked = registry.check_and_reserve(phone, next_stage, actor)
                active_results.append(
                    first.allowed
                    and not blocked.allowed
                    and blocked.reason_code == "ACTIVE_RESERVATION"
                )

                phone = _synthetic_phone(index)
                index += 1
                first = registry.check_and_reserve(phone, first_stage, actor)
                registry.mark_exposed(first.reservation_id, actor)
                blocked = registry.check_and_reserve(phone, next_stage, actor)
                exposed_results.append(
                    not blocked.allowed and blocked.reason_code == "PRIOR_EXPOSURE"
                )

        release_phone = _synthetic_phone(index)
        index += 1
        released = registry.check_and_reserve(release_phone, Stage.LEVEL_B, actor)
        registry.release_before_exposure(
            released.reservation_id, "SYNTHETIC_CANCEL", actor
        )
        reentry = registry.check_and_reserve(release_phone, Stage.STAGE_3, actor)

        completed_phone = _synthetic_phone(index)
        index += 1
        completed = registry.check_and_reserve(completed_phone, Stage.LEVEL_C, actor)
        registry.mark_exposed(completed.reservation_id, actor)
        registry.mark_completed(completed.reservation_id, actor)
        completed_block = registry.check_and_reserve(
            completed_phone, Stage.STAGE_1, actor
        )

        withdrawn_phone = _synthetic_phone(index)
        index += 1
        withdrawn = registry.check_and_reserve(withdrawn_phone, Stage.STAGE_1, actor)
        registry.mark_exposed(withdrawn.reservation_id, actor)
        registry.mark_withdrawn_after_exposure(withdrawn.reservation_id, actor)
        withdrawn_block = registry.check_and_reserve(
            withdrawn_phone, Stage.STAGE_3, actor
        )

        concurrent_phone = _synthetic_phone(index)
        index += 1
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent = list(
                pool.map(
                    lambda _: registry.check_and_reserve(
                        concurrent_phone, Stage.STAGE_1, actor
                    ),
                    range(2),
                )
            )

        bundle = root / "backup"
        backup_registry(registry, bundle, actor)
        restored = restore_registry(
            bundle,
            root / "restored",
            key_provider=lambda: key,
            allowed_actors={actor},
            actor_id=actor,
        )
        restored_registry = DedupRegistry(
            database_path=restored.database_path,
            key_provider=lambda: key,
            allowed_actors={actor},
        )
        cross_stage = restored_registry.audit_cross_stage()

        return {
            "active_cross_stage_cases": len(active_results),
            "active_cross_stage_passed": all(active_results),
            "audit_chain_valid": restored_registry.verify_audit_chain().valid,
            "backup_restore_valid": restored.valid,
            "completed_blocks_reentry": (
                not completed_block.allowed
                and completed_block.reason_code == "PRIOR_EXPOSURE"
            ),
            "concurrent_active_reservation_count": sum(
                item.reason_code == "ACTIVE_RESERVATION" for item in concurrent
            ),
            "concurrent_new_count": sum(item.reason_code == "NEW" for item in concurrent),
            "cross_stage_audit_valid": cross_stage.valid,
            "prior_exposure_cases": len(exposed_results),
            "prior_exposure_passed": all(exposed_results),
            "release_before_exposure_allows_reentry": reentry.allowed,
            "schema_version": 1,
            "synthetic_only": True,
            "withdrawn_after_exposure_blocks_reentry": (
                not withdrawn_block.allowed
                and withdrawn_block.reason_code == "PRIOR_EXPOSURE"
            ),
        }
