from __future__ import annotations

import runpy
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_ROOT = (
    PROJECT_ROOT
    / "00-项目管理"
    / "01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
    / "24_团队任务与项目治理"
)


@pytest.mark.parametrize(
    "script_name",
    ["13_render_ready_task_packages.py", "14_validate_ready_task_packages.py"],
)
def test_hash_policy_normalizes_all_dispatched_text_types(
    script_name: str, tmp_path: Path
) -> None:
    canonical_content = runpy.run_path(str(GOVERNANCE_ROOT / script_name))[
        "canonical_content"
    ]

    for filename in (
        "fixture_hashes.sha256",
        "consumer.ps1",
        ".gitattributes",
        "34_.gitattributes",
    ):
        crlf_dir = tmp_path / f"crlf-{filename.replace('.', '_')}"
        lf_dir = tmp_path / f"lf-{filename.replace('.', '_')}"
        crlf_dir.mkdir()
        lf_dir.mkdir()
        crlf = crlf_dir / filename
        lf = lf_dir / filename
        crlf.write_bytes(b"alpha  \r\nbeta\t\r\n")
        lf.write_bytes(b"alpha\nbeta\n")

        assert canonical_content(crlf) == canonical_content(lf) == b"alpha\nbeta\n"
