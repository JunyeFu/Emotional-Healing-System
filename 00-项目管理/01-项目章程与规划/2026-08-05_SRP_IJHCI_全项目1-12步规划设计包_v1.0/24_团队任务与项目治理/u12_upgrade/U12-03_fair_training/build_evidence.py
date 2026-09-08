"""Create reproducible text identities for the teaching design candidate."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
PLAN = HERE.parents[2]


def text_hash(path):
    text = path.read_text(encoding="utf-8-sig")
    normalized = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sources = [
        PLAN / "00_总控/protocol_authority_v1.2.json",
        PLAN / "20_产品与场景设计/R-01_四层表示方案/R-01_四层候选语法与完整表示方案_v0.9-candidate.md",
        ROOT / "02-技术研发/srp_session_core/config/breath_protocol_config_v2.2.json",
        ROOT / "02-技术研发/srp_step_measurement/README.md",
        ROOT / "02-技术研发/srp_step_measurement/annotation_plan.md",
        ROOT / "01-需求与设计/情绪天气方案/四种天气设计.md",
    ]
    outputs = [HERE / f for f in ("README.md", "contract.json", "teaching.md",
               "formative.md", "observation.template.json", "sources.md", "validate.py",
               "test_contract.py", "build_evidence.py")]
    manifest = json.loads((HERE.parents[1] / "当前解锁独立任务包/U12-03/package_manifest.json").read_text(encoding="utf-8"))
    data = {
        "evidence_class": "DESIGN_AND_SYNTHETIC_ONLY",
        "hash_policy": "UTF8_LF_TRAILING_WHITESPACE_REMOVED_FINAL_LF",
        "input_snapshot_id": manifest["input_snapshot_id"],
        "sources": {str(p.relative_to(ROOT)).replace("\\", "/"): text_hash(p) for p in sources},
        "outputs": {p.name: text_hash(p) for p in outputs},
        "real_clips": "PENDING", "participant_observations": "PENDING",
        "research_freeze": "PENDING",
    }
    path = HERE / "evidence.json"
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text(encoding="utf-8") != content:
            raise SystemExit("EVIDENCE_HASH_MISMATCH")
        print("PASS: source and deliverable identities")
    else:
        path.write_text(content, encoding="utf-8")
        print("WROTE: evidence.json")


if __name__ == "__main__":
    main()
