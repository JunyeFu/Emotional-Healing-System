from __future__ import annotations

import json
import runpy
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
TOOL = PROJECT_ROOT / "Tools" / "F05" / "f05_evidence.py"
LEAVES = (
    "contract-tests.log",
    "p01-tests.log",
    "p02-tests.log",
    "f05-contract-verifier.log",
    "f05-verification.json",
    "git-diff-check.log",
)


def load_tool():
    return runpy.run_path(str(TOOL))


def write_leaves(directory: Path) -> None:
    directory.mkdir()
    for index, name in enumerate(LEAVES):
        (directory / name).write_bytes(f"leaf {index}\nPASS\n".encode())


def test_canonical_hash_ignores_newlines_and_trailing_whitespace() -> None:
    canonicalize = load_tool()["canonicalize_text"]
    digest = load_tool()["canonical_digest"]
    variants = (b"alpha\nbeta\n", b"alpha  \r\nbeta\t\r\n", b"alpha  \rbeta\t\r")

    assert {canonicalize(value) for value in variants} == {b"alpha\nbeta\n"}
    assert len({digest(value)[0] for value in variants}) == 1
    assert digest(b"alpha\ngamma\n")[0] != digest(variants[0])[0]


def test_seal_is_deterministic_and_detects_all_tampering(tmp_path: Path) -> None:
    tool = load_tool()
    evidence = tmp_path / "evidence"
    write_leaves(evidence)

    tool["seal"](evidence, "abc123")
    first_index = (evidence / "evidence_hashes.sha256").read_bytes()
    first_manifest = (evidence / "evidence_manifest.json").read_bytes()
    tool["verify"](evidence)
    tool["seal"](evidence, "abc123")
    assert (evidence / "evidence_hashes.sha256").read_bytes() == first_index
    assert (evidence / "evidence_manifest.json").read_bytes() == first_manifest

    cases = {
        "missing": lambda: (evidence / LEAVES[0]).unlink(),
        "extra": lambda: (evidence / "extra.log").write_text("x", encoding="utf-8"),
        "index": lambda: (evidence / "evidence_hashes.sha256").write_text("bad\n", encoding="utf-8"),
        "manifest": lambda: (evidence / "evidence_manifest.json").write_text("{}\n", encoding="utf-8"),
    }
    for name, mutate in cases.items():
        case = tmp_path / name
        write_leaves(case)
        tool["seal"](case, "abc123")
        mutate_target = evidence
        evidence = case
        mutate()
        with pytest.raises(ValueError):
            tool["verify"](case)
        evidence = mutate_target

    changed = tmp_path / "changed"
    write_leaves(changed)
    tool["seal"](changed, "abc123")
    (changed / LEAVES[1]).write_text("different\n", encoding="utf-8")
    with pytest.raises(ValueError):
        tool["verify"](changed)


def test_manifest_v2_has_fixed_leaf_set_and_never_hashes_itself(tmp_path: Path) -> None:
    tool = load_tool()
    evidence = tmp_path / "evidence"
    write_leaves(evidence)
    tool["seal"](evidence, "fixed-commit")
    manifest = json.loads((evidence / "evidence_manifest.json").read_text())

    assert manifest["manifest_schema"] == "f05-evidence-manifest-v2"
    assert manifest["tested_git_commit"] == "fixed-commit"
    assert manifest["hash_policy"] == "sha256_lf_no_trailing_ws_text_v1"
    assert tuple(manifest["leaves"]) == LEAVES
    assert manifest["hash_index"]["path"] == "evidence_hashes.sha256"
    assert "evidence_manifest.json" not in json.dumps(manifest)


def test_git_tree_verification_matches_worktree_with_crlf_checkout(tmp_path: Path) -> None:
    tool = load_tool()
    repo = tmp_path / "repo"
    evidence = repo / "03-测试与实验" / "evidence" / "F-05"
    evidence.mkdir(parents=True)
    for index, name in enumerate(LEAVES):
        (evidence / name).write_bytes(f"leaf {index}  \r\nPASS\t\r\n".encode())
    tool["seal"](evidence, "candidate")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "F05 Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "f05@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "evidence"], cwd=repo, check=True)

    tool["verify"](evidence)
    tool["verify"](evidence, git_tree="HEAD", repo_root=repo)
