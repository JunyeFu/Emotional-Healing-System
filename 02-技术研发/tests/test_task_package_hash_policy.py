from __future__ import annotations

import runpy
import csv
import json
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


def test_in_review_human_signoff_remains_open() -> None:
    renderer = runpy.run_path(str(GOVERNANCE_ROOT / "13_render_ready_task_packages.py"))
    with (GOVERNANCE_ROOT / "05_可领取任务包.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        row = next(item for item in csv.DictReader(handle) if item["task_id"] == "F-05")
    row["status"] = "IN_REVIEW"
    mapping = json.loads(
        (GOVERNANCE_ROOT / "12_独立任务包文件映射_v1.0.json").read_text(
            encoding="utf-8-sig"
        )
    )
    task_map = {
        "source_files": [],
        "working_paths": [],
        "implementation_commit": "candidate",
        "model_review_status": "PENDING_REAUDIT",
    }
    handbook = runpy.run_path(str(GOVERNANCE_ROOT / "10_render_task_handbook.py"))
    rendered = renderer["task_markdown"](
        row, handbook["parse_resources"](), handbook["PROCESS_PROFILES"], task_map
    )

    assert "- [ ] 第二人签收报告" in rendered
    assert "傅钧烨签收仍开放" in rendered
