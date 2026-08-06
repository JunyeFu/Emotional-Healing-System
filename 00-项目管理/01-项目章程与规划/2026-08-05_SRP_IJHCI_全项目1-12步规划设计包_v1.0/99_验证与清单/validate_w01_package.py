"""Validate the W-01 closest-work and one-paper candidate package."""

from __future__ import annotations

import csv
import pathlib
import re
import sys


HERE = pathlib.Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
DELIVERY_DIR = next(PACKAGE_ROOT.glob("25_*"))
W01_DIR = next(DELIVERY_DIR.glob("W-01_*"))
TASK_DIR = next(PACKAGE_ROOT.glob("24_*"))
REGISTRY = next(TASK_DIR.glob("05_*.csv"))

REPORT = next(W01_DIR.glob("W-01_2015-2026*_v0.9-candidate.md"))
ACCEPTANCE = next(W01_DIR.glob("W-01_*验收记录.md"))
BIBLIOGRAPHY = W01_DIR / "w01-references.bib"
CSV_EXPECTATIONS = {
    "w01-search-log.csv": 13,
    "w01-core-evidence-matrix.csv": 15,
    "w01-claims-evidence.csv": 6,
    "w01-doi-audit.csv": 15,
}

EXPECTED_DOIS = {
    "10.1145/2851581.2859027",
    "10.1145/3173574.3174219",
    "10.3389/fpsyg.2019.02172",
    "10.1145/3369835",
    "10.1145/3365107",
    "10.1080/10447318.2021.1898827",
    "10.1145/3500868.3559708",
    "10.1145/3544549.3585589",
    "10.48550/arxiv.2310.14343",
    "10.1016/j.ijhcs.2024.103275",
    "10.1080/10447318.2025.2504201",
    "10.1145/3715668.3736338",
    "10.1080/10447318.2026.2669040",
    "10.1080/10447318.2026.2672591",
    "10.1145/3772363.3798443",
}

REQUIRED_REPORT_MARKERS = (
    "REVISE_REQUIRED",
    "PLANNED_NOT_OBSERVED",
    "ACM Digital Library",
    "Scopus",
    "Web of Science",
    "International Journal of Human-Computer Interaction",
    "International Journal of Human-Computer Studies",
    "场景融合",
    "四层信息 T/A/C/D",
    "呼吸结构",
    "比较条件",
    "状态编排",
    "测量方法",
    "设计知识",
    "完整提示表示方案",
    "条件式部署扩展",
    "### 结果占位",
    "数据库原生去重",
    "双人题名摘要筛选",
)

FORBIDDEN_TERMS = ("诊断", "治疗", "疾病", "患者", "医疗设备", "临床")


def normalize_doi(value: str) -> str:
    return value.strip().rstrip("},").lower()


def load_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    errors: list[str] = []

    required_files = [REPORT, ACCEPTANCE, BIBLIOGRAPHY]
    required_files.extend(W01_DIR / name for name in CSV_EXPECTATIONS)
    for path in required_files:
        if not path.is_file():
            errors.append(f"missing file: {path.name}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    report_text = REPORT.read_text(encoding="utf-8-sig")
    acceptance_text = ACCEPTANCE.read_text(encoding="utf-8-sig")
    package_text = report_text + "\n" + acceptance_text

    for marker in REQUIRED_REPORT_MARKERS:
        if marker not in report_text:
            errors.append(f"report missing marker: {marker}")

    if re.search(r"(?:file)?cite[^]+", package_text):
        errors.append("unusable GPT internal citation remains")

    for term in FORBIDDEN_TERMS:
        if term in package_text:
            errors.append(f"forbidden terminology remains: {term}")

    stale_markers = (
        "2026-12-31",
        "America/Los_Angeles",
        "Rook, Chris and others",
        "2015 publication status",
        "Adaptive Biofeedback 2015／2016 年份表示需统一",
        "Heart Garden 完整作者列表需由出版引用导出替换",
    )
    for marker in stale_markers:
        if marker in report_text:
            errors.append(f"stale import marker remains: {marker}")

    bib_text = BIBLIOGRAPHY.read_text(encoding="utf-8-sig")
    bib_entries = re.findall(r"^@", bib_text, flags=re.MULTILINE)
    if len(bib_entries) != 15:
        errors.append(f"expected 15 BibTeX entries, found {len(bib_entries)}")

    bib_dois = {
        normalize_doi(value)
        for value in re.findall(r"^\s*doi\s*=\s*\{([^}]+)\}", bib_text, flags=re.MULTILINE)
    }
    if bib_dois != EXPECTED_DOIS:
        errors.append(
            f"BibTeX DOI set mismatch: missing={sorted(EXPECTED_DOIS - bib_dois)}, "
            f"extra={sorted(bib_dois - EXPECTED_DOIS)}"
        )

    for name, expected_rows in CSV_EXPECTATIONS.items():
        rows = load_csv(W01_DIR / name)
        if len(rows) != expected_rows:
            errors.append(f"{name}: expected {expected_rows} rows, found {len(rows)}")

    doi_rows = load_csv(W01_DIR / "w01-doi-audit.csv")
    audited_dois = {normalize_doi(row["doi"]) for row in doi_rows}
    if audited_dois != EXPECTED_DOIS:
        errors.append("DOI audit set does not match the 15-source core set")
    if any(row.get("status") != "VERIFIED_IDENTITY" for row in doi_rows):
        errors.append("DOI audit contains an unverified identity row")

    registry_rows = load_csv(REGISTRY)
    rows_by_id = {row["task_id"]: row for row in registry_rows}
    if rows_by_id.get("W-01", {}).get("status") != "DONE":
        errors.append("W-01 must be DONE at candidate-package scope")
    if rows_by_id.get("W-02", {}).get("status") != "WAIT_DEP":
        errors.append("W-02 must remain WAIT_DEP because A-04 is incomplete")
    if "REVISE_REQUIRED" not in rows_by_id.get("W-01", {}).get("completion_condition", ""):
        errors.append("W-01 completion condition must preserve REVISE_REQUIRED")

    required_acceptance_markers = (
        "PASS_FOR_CANDIDATE_PACKAGE",
        "W-01=DONE",
        "REVISE_REQUIRED",
        "W-02仍同时依赖A-04",
        "5856C9C848E13285A42CFDCD212595D53DDAFA0B37B3F69CA028AF143018CD7E",
    )
    for marker in required_acceptance_markers:
        if marker not in acceptance_text:
            errors.append(f"acceptance record missing marker: {marker}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        "PASS: W-01 candidate package; "
        "search_rows=13; core_sources=15; claims=6; bib_entries=15; "
        "novelty=REVISE_REQUIRED; W-02=WAIT_DEP"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
