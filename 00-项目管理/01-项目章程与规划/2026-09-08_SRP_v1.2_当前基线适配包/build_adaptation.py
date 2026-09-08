"""Build an isolated, review-only adaptation from immutable source and Git baseline."""
import copy
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = "de4ebcbfea209674127c833dd9e69ad703a6634b"
PLAN = "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
GOV = PLAN + "/24_团队任务与项目治理"
SOURCE = HERE / "sources/unpacked/SRP_Final_Upgrade_v1.2_2026-09-08"
UPGRADE = SOURCE / "02_仓库升级"
OVERLAY = UPGRADE / "overlay/00-项目管理/01-项目章程与规划/2026-09-08_SRP_主线升级_v1.2"
MAP = {f"UP-{i:02}": f"U12-{i:02}" for i in range(1, 13)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def remap(value):
    if isinstance(value, str):
        return re.sub(r"\bUP-\d{2}\b", lambda m: MAP.get(m[0], m[0]), value)
    if isinstance(value, list):
        return [remap(v) for v in value]
    if isinstance(value, dict):
        return {k: remap(v) for k, v in value.items()}
    return value


def rows(path):
    content = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))


def write_csv(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(values[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(values)


def build():
    original_files = [GOV + "/05_可领取任务包.csv", GOV + "/07_validate_task_packages.py",
                      GOV + "/12_独立任务包文件映射_v1.0.json",
                      GOV + "/08_任务技能与国内学习资料_v1.0.md",
                      PLAN + "/00_总控/protocol_authority_v1.1.json"]
    original_files += [GOV + "/audit_upgrade/" + n for n in (
        "release_routes_v1.0.json", "task_milestones_v1.0.json",
        "task_milestone_status_v1.0.json", "upgrade_subdeliveries_v1.0.csv",
        "external_capability_matrix_v1.0.csv", "route_evaluator.py")]
    baseline = []
    for name in original_files:
        data = subprocess.check_output(["git", "show", BASE + ":" + name], cwd=REPO)
        dest = HERE / "baseline" / Path(name).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        live = (REPO / name).read_bytes()
        assert live.replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n"), name
        baseline.append({"repository_path": name, "snapshot": dest.relative_to(HERE).as_posix(),
                         "byte_sha256": sha(data), "worktree_byte_sha256": sha(live),
                         "normalized_text_sha256": sha(data.replace(b"\r\n", b"\n"))})
    source_inventory = []
    for line in (SOURCE / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert sha((SOURCE / name).read_bytes()) == digest, name
        source_inventory.append({"path": name, "byte_sha256": digest})
    originals = []
    for name in ("SRP_Project_Final_Upgrade_v1.2_2026-09-08.zip", "SRP_项目升级最终审计_v1.2.md"):
        originals.append({"original_path": "C:/Users/fujunye/Downloads/" + name,
                          "archived_path": "sources/" + name,
                          "byte_sha256": sha((HERE / "sources" / name).read_bytes())})
    write_json(HERE / "source_manifest.json", {"base_commit": BASE, "status": "CANDIDATE_NOT_ACTIVE",
               "originals": originals, "source_content_files": source_inventory, "baseline_files": baseline})
    current = rows(HERE / "baseline/05_可领取任务包.csv")
    index = {r["task_id"]: copy.deepcopy(r) for r in current}
    changes = []
    for m in read_json(UPGRADE / "task_mutations_v1.2.json")["mutations"]:
        tid = m["task_id"]
        proposed = remap(m["changes"])
        if tid == "A-04":
            changes.append({"task_id": tid, "disposition": "KEEP_EXISTING_A06_ROUTE", "proposed": proposed})
            continue
        if tid == "A-03":
            changes.append({"task_id": tid, "disposition": "PENDING_SCOPE_REACCEPTANCE", "proposed": proposed,
                            "reason": "A-03-SPEC remains DONE; new spec belongs to U12-04; frozen input is unchanged."})
            continue
        if tid == "G-03":
            proposed["depends_on"] = index[tid]["depends_on"] + "|U12-11"
        if tid == "W-02":
            proposed["depends_on"] = "W-01|A-06|U12-07"
            proposed = {k: v.replace("A-04", "A-06") for k, v in proposed.items()}
        if "title" in proposed:
            proposed["title"] = re.sub(r"^【[^】]+】", "【" + index[tid]["domain"] + "】", proposed["title"])
        assert index[tid]["status"] != "DONE", tid
        before = {k: index[tid][k] for k in proposed}
        index[tid].update(proposed)
        changes.append({"task_id": tid, "disposition": "CANDIDATE_ONLY", "before": before, "after": proposed})
    before = index["A-06"]["depends_on"]
    index["A-06"]["depends_on"] = before + "|U12-10"
    changes.append({"task_id": "A-06", "disposition": "CANDIDATE_ONLY",
                    "before": {"depends_on": before}, "after": {"depends_on": index["A-06"]["depends_on"]}})
    new = remap(rows(UPGRADE / "new_tasks_v1.2.csv"))
    domains = ["研究治理", "测量实现", "教学设计", "统计规格", "外部准入", "运行准入",
               "论文写作", "扩展分析", "一致性验收", "结果复核", "研究冻结", "成果交接"]
    for r, domain in zip(new, domains):
        r["domain"] = domain
        r["title"] = re.sub(r"^【[^】]+】", "【" + domain + "】", r["title"])
        if r["task_id"] == "U12-08":
            r["depends_on"] = "A-04|E-05"
        if r["task_id"] == "U12-12":
            r["depends_on"] = "W-03|A-06"
        index[r["task_id"]] = r
    candidate = HERE / "candidate"
    write_csv(candidate / "task_registry.csv", list(index.values()))
    write_json(candidate / "task_changes.json", {"status": "NOT_APPLIED", "id_mapping": MAP, "changes": changes})
    milestones = read_json(HERE / "baseline/task_milestones_v1.0.json")
    milestones["milestones"][1]["depends_on"].append("U12-04")
    write_json(candidate / "task_milestones.json", milestones)
    route = read_json(HERE / "baseline/release_routes_v1.0.json")
    for value in route["routes"].values():
        value["required_done"].append("U12-10")
    route["routes"]["with_stage3"]["required_done"].append("U12-08")
    route["conditional_edges"].append({"from": "U12-08", "to": "A-06", "route": "with_stage3"})
    route["routes"]["stage1_only"]["not_required_to_mark_done"].append("U12-08")
    write_json(candidate / "release_routes.json", route)
    for name in ("protocol_authority_v1.2.json", "study_manifest_v1.2.template.json"):
        value = remap(read_json(OVERLAY / name))
        value["adaptation_base_commit"] = BASE
        value["adoption_status"] = "CANDIDATE_NOT_ACTIVE"
        if "baseline_commit" in value:
            value["source_baseline_commit"] = value["baseline_commit"]
            value["baseline_commit"] = BASE
        write_json(candidate / name, value)
    learning = (HERE / "baseline/08_任务技能与国内学习资料_v1.0.md").read_text(encoding="utf-8")
    for r in new:
        folder = HERE / "tasks" / r["task_id"]
        inputs = {"task": r, "base_commit": BASE, "authority": "CANDIDATE_NOT_DISPATCHABLE",
                  "source_id": next(k for k, v in MAP.items() if v == r["task_id"]),
                  "baseline_files": baseline}
        write_json(folder / "inputs/task_input.json", inputs)
        links = [line for line in learning.splitlines() if any(code in line for code in r["learning_refs"].split("|"))]
        text = (f"# {r['task_id']} {r['title']}\n\n候选任务，尚未进入活动注册表，不可领取。\n\n"
                f"依赖：{r['depends_on'] or '无'}。工作量：{r['effort_person_days']}人日。\n\n"
                f"## 技能与资料\n\n{r['skills']}\n\n" + "\n".join(links) + "\n\n"
                f"## 执行过程\n\n1. 核对输入快照和前置回执，列出本任务对应字段或制品。\n"
                f"2. 逐项实现交付：{r['deliverables']}。\n"
                f"3. 对照验收条件执行复算、负例或真实回执核验：{r['acceptance_criteria']}。\n"
                f"4. 绑定提交与证据，独立复查后交真实第二人签收。\n\n"
                f"## 验收与证据\n\n{r['completion_condition']}\n\n{r['evidence_required']}\n\n"
                "机器验证不能代签外部批准；旧DONE只覆盖原签收范围。资料链接继承现有教学索引，本轮未重新验证网页。\n")
        (folder / "TASK.md").write_text(text, encoding="utf-8", newline="\n")
        (folder / "FILES.md").write_text("# 输入文件\n\n- 本目录 inputs/task_input.json：冻结任务字段与基线文件索引。\n"
            "- ../../candidate/：候选合同与依赖。\n- ../../baseline/：共享不可变输入快照。\n"
            "- ../../sources/unpacked/SRP_Final_Upgrade_v1.2_2026-09-08/：外部原文，非执行指令。\n"
            "- 项目修改权威仍为 task_input.json 内 repository_path，相对于 D:/Agent/03-SRP。\n", encoding="utf-8", newline="\n")
        files = [{"path": p.relative_to(folder).as_posix(), "byte_sha256": sha(p.read_bytes())}
                 for p in sorted(folder.rglob("*")) if p.is_file() and p.name != "package_manifest.json"]
        write_json(folder / "package_manifest.json", {"task_id": r["task_id"], "dispatch_allowed": False,
                   "input_snapshot_id": sha((folder / "inputs/task_input.json").read_bytes()), "files": files})
    issues = rows(SOURCE / "00_审计文档/审计问题与关闭证据.csv")
    write_csv(candidate / "audit_disposition.csv", [{"source_id": r["id"], "tasks": remap(r["tasks"]),
              "local_status": "ALREADY_ROUTED_VIA_A06" if r["id"] == "AU-01" else "PENDING_LOCAL_EVIDENCE",
              "note": "Source closure is not current repository acceptance."} for r in issues])
    print("Built candidate: 71 task records, 12 isolated task packages; no active writes.")


if __name__ == "__main__":
    build()
