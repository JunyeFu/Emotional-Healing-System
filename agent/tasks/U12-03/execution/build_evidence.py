"""Current teaching identities, separate from the archived candidate."""
import argparse
import hashlib
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'


def text_hash(path):
    text = path.read_text(encoding="utf-8-sig")
    normalized = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate():
    sources = [
        PLAN / "00_总控/protocol_authority_v1.2.json",
        ROOT / "agent/tasks/R-01/outputs/current-representation.md",
        ROOT / "agent/modules/srp_session_core/config/breath_protocol_config_v2.2.json",
        ROOT / "agent/tasks/U12-02/outputs/current-measurement.md",
        ROOT / "agent/tasks/U12-02/outputs/annotation-plan.md",
    ]
    outputs = [TASK / ("outputs/" + f) for f in
               ("contract.json", "teaching.md", "formative.md", "observation.template.json", "current-training.md", "current-training.json")]
    outputs += [TASK / ("execution/" + f) for f in ("validate.py", "test_contract.py", "build_evidence.py")]
    manifest = json.loads((GOV / "当前解锁独立任务包/U12-03/package_manifest.json").read_text(encoding="utf-8"))
    return {
        "evidence_class": "DESIGN_AND_SYNTHETIC_ONLY",
        "hash_policy": "UTF8_LF_TRAILING_WHITESPACE_REMOVED_FINAL_LF",
        "input_snapshot_id": manifest["input_snapshot_id"],
        "historical_candidate": manifest["candidate_identity"],
        "sources": {str(p.relative_to(ROOT)).replace("\\", "/"): text_hash(p) for p in sources},
        "outputs": {str(p.relative_to(TASK)).replace("\\", "/"): text_hash(p) for p in outputs},
        "real_clips": "PENDING", "participant_observations": "PENDING",
        "research_freeze": "PENDING",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = TASK / "evidence/current-design.json"
    content = json.dumps(generate(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text(encoding="utf-8") != content:
            raise SystemExit("EVIDENCE_HASH_MISMATCH")
        print("PASS: current identities; archived evidence unchanged")
    else:
        path.write_text(content, encoding="utf-8")
        print("WROTE: evidence/current-design.json")


if __name__ == "__main__":
    main()
