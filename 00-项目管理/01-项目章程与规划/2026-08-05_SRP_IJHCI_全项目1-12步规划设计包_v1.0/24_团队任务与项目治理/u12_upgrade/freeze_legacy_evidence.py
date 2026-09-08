"""Bind old evidence references to Git objects, preserving unverified byte claims."""
import hashlib
import json
import runpy
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV = HERE.parent
REPO = GOV.parents[3]
COMMIT = "bdda9f955c4de7e96bd07fb03fd6a63c8ef0ac8a"
OUTPUT = HERE / "legacy_evidence_binding.json"


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def historical_bytes(path):
    relative = path.relative_to(REPO).as_posix()
    return subprocess.check_output(["git", "show", COMMIT + ":" + relative], cwd=REPO)


def expected_binding():
    manifest_path = GOV / "audit_upgrade/upgrade_evidence_manifest_v1.0.json"
    original = historical_bytes(manifest_path)
    resolver = runpy.run_path(str(GOV / "audit_upgrade/build_upgrade_evidence_manifest.py"))["resolve_ref"]
    entries = {}
    for task, values in json.loads(original)["entries"].items():
        refs = []
        for item in values:
            path = resolver(item["reference"])
            content = historical_bytes(path)
            declared = item["byte_sha256"]
            variants = {digest(content), digest(content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))}
            refs.append({"reference": item["reference"], "repository_path": path.relative_to(REPO).as_posix(),
                         "git_blob_sha256": digest(content), "original_declared_byte_sha256": declared,
                         "original_byte_identity": "RECONSTRUCTABLE" if declared in variants else "UNRESOLVED_WORKTREE_BYTES"})
        entries[task] = refs
    return {"commit": COMMIT, "original_manifest_git_sha256": digest(original), "entries": entries,
            "scope": "GIT_HISTORY_IDENTITY_ONLY_NOT_RETROACTIVE_ACCEPTANCE"}


def validate():
    expected = expected_binding()
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if actual != expected:
        return ["LEGACY_GIT_BINDING_MISMATCH"]
    # Preserve the original declaration, including unresolved raw-worktree identities.
    original = json.loads(historical_bytes(GOV / "audit_upgrade/upgrade_evidence_manifest_v1.0.json"))
    current = json.loads((GOV / "audit_upgrade/upgrade_evidence_manifest_v1.0.json").read_text(encoding="utf-8"))
    return [] if current == original else ["LEGACY_MANIFEST_REWRITTEN"]


if __name__ == "__main__":
    if OUTPUT.exists():
        raise SystemExit("ALREADY_FROZEN")
    value = expected_binding()
    OUTPUT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    unresolved = sum(r["original_byte_identity"] == "UNRESOLVED_WORKTREE_BYTES" for refs in value["entries"].values() for r in refs)
    print(f"FROZEN: Git evidence identities; unresolved original byte references={unresolved}")
