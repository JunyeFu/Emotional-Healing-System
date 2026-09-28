from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


HASH_POLICY = "sha256_lf_no_trailing_ws_text_v1"
LEAF_FILES = (
    "contract-tests.log",
    "p01-tests.log",
    "p02-tests.log",
    "f05-contract-verifier.log",
    "f05-verification.json",
    "git-diff-check.log",
)
INDEX_FILE = "evidence_hashes.sha256"
MANIFEST_FILE = "evidence_manifest.json"
EXPECTED_FILES = frozenset((*LEAF_FILES, INDEX_FILE, MANIFEST_FILE))


def canonicalize_text(content: bytes) -> bytes:
    normalized = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return b"\n".join(line.rstrip(b" \t") for line in normalized.split(b"\n"))


def canonical_digest(content: bytes) -> tuple[str, int]:
    canonical = canonicalize_text(content)
    return hashlib.sha256(canonical).hexdigest(), len(canonical)


def _record(content: bytes) -> dict[str, object]:
    digest, size = canonical_digest(content)
    return {"sha256": digest, "canonical_size_bytes": size}


def _index_content(records: dict[str, dict[str, object]]) -> bytes:
    return "".join(f"{records[name]['sha256']}  {name}\n" for name in LEAF_FILES).encode()


def seal(evidence_dir: Path, tested_git_commit: str) -> None:
    evidence_dir = Path(evidence_dir)
    missing = [name for name in LEAF_FILES if not (evidence_dir / name).is_file()]
    if missing:
        raise ValueError(f"missing evidence files: {','.join(missing)}")
    unexpected = {path.name for path in evidence_dir.iterdir() if path.is_file()} - EXPECTED_FILES
    if unexpected:
        raise ValueError(f"unexpected evidence files: {','.join(sorted(unexpected))}")
    leaves = {name: _record((evidence_dir / name).read_bytes()) for name in LEAF_FILES}
    index_content = _index_content(leaves)
    (evidence_dir / INDEX_FILE).write_bytes(index_content)
    manifest = {
        "manifest_schema": "f05-evidence-manifest-v2",
        "tested_git_commit": tested_git_commit,
        "hash_policy": HASH_POLICY,
        "leaves": leaves,
        "hash_index": {"path": INDEX_FILE, **_record(index_content)},
    }
    (evidence_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _git_blob(repo_root: Path, tree: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{tree}:{relative}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise ValueError(f"missing git blob: {relative}")
    return result.stdout


def verify(evidence_dir: Path, *, git_tree: str | None = None, repo_root: Path | None = None) -> None:
    evidence_dir = Path(evidence_dir)
    if git_tree:
        if repo_root is None:
            raise ValueError("repo_root is required for git-tree verification")
        relative_dir = evidence_dir.resolve().relative_to(Path(repo_root).resolve()).as_posix()
        read = lambda name: _git_blob(Path(repo_root), git_tree, f"{relative_dir}/{name}")
        output = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "-z", git_tree, "--", relative_dir],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
        names = {line[len(relative_dir) + 1 :] for line in output.split("\0") if line.startswith(relative_dir + "/")}
    else:
        if not evidence_dir.is_dir():
            raise ValueError("evidence directory missing")
        names = {path.name for path in evidence_dir.iterdir() if path.is_file()}
        read = lambda name: (evidence_dir / name).read_bytes()
    if names != EXPECTED_FILES:
        raise ValueError(f"evidence file set mismatch: {sorted(names)}")
    try:
        manifest = json.loads(read(MANIFEST_FILE).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid evidence manifest") from error
    if manifest.get("manifest_schema") != "f05-evidence-manifest-v2":
        raise ValueError("manifest schema mismatch")
    if manifest.get("hash_policy") != HASH_POLICY:
        raise ValueError("hash policy mismatch")
    expected_leaves = {name: _record(read(name)) for name in LEAF_FILES}
    if manifest.get("leaves") != expected_leaves:
        raise ValueError("leaf hash mismatch")
    expected_index = _index_content(expected_leaves)
    if read(INDEX_FILE) != expected_index:
        raise ValueError("hash index mismatch")
    if manifest.get("hash_index") != {"path": INDEX_FILE, **_record(expected_index)}:
        raise ValueError("hash index record mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    seal_parser = subparsers.add_parser("seal")
    seal_parser.add_argument("--evidence-dir", type=Path, required=True)
    seal_parser.add_argument("--tested-git-commit", required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--evidence-dir", type=Path, required=True)
    verify_parser.add_argument("--git-tree")
    verify_parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args()
    if args.action == "seal":
        seal(args.evidence_dir, args.tested_git_commit)
    else:
        verify(args.evidence_dir, git_tree=args.git_tree, repo_root=args.repo_root)
    print("PASS: F-05 evidence seal is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
