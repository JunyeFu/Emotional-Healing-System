from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Iterable


DANGEROUS_SUFFIXES = {
    ".db",
    ".key",
    ".p12",
    ".pfx",
    ".sealed",
    ".sqlite",
    ".sqlite3",
}
ARTIFACT_ROOTS = (
    PurePosixPath("02-技术研发/07-数据治理/evidence"),
    PurePosixPath(
        "02-技术研发/04-Unity视觉/SRP-Weather-Visual/Governance"
    ),
)
TEXT_SUFFIXES = {".json", ".log", ".md", ".txt"}
FORBIDDEN_JSON_KEYS = {
    "contact",
    "contacthash",
    "deduptoken",
    "email",
    "mobile",
    "name",
    "phone",
    "phonehash",
    "subjecttoken",
    "wechat",
}
EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])"
)
MAINLAND_PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Fa-f])(?:\+86|0086|86)?1[3-9][0-9]{9}(?![0-9A-Fa-f])"
)
E164_PATTERN = re.compile(r"(?<![0-9])\+[1-9][0-9]{7,14}(?![0-9])")
SECRET_PATTERN = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")


def _tracked_paths(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return [
        value.decode("utf-8")
        for value in result.stdout.split(b"\0")
        if value
    ]


def _under_artifact_root(path: PurePosixPath) -> bool:
    return any(path == root or root in path.parents for root in ARTIFACT_ROOTS)


def _normalize_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _json_key_violations(value: object, path: str = "$") -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if _normalize_key(key) in FORBIDDEN_JSON_KEYS:
                violations.append(
                    {"code": "FORBIDDEN_IDENTITY_FIELD", "json_path": nested_path}
                )
            violations.extend(_json_key_violations(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            violations.extend(_json_key_violations(nested, f"{path}[{index}]"))
    return violations


def find_privacy_violations(
    repo_root: Path,
    tracked_paths: Iterable[str] | None = None,
) -> list[dict[str, str]]:
    repo_root = repo_root.resolve()
    tracked = list(tracked_paths) if tracked_paths is not None else _tracked_paths(repo_root)
    violations: list[dict[str, str]] = []

    for relative in tracked:
        normalized = relative.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        suffix = posix_path.suffix.lower()
        if suffix in DANGEROUS_SUFFIXES:
            violations.append({"code": "FORBIDDEN_TRACKED_FILE", "path": normalized})

        if not _under_artifact_root(posix_path) or suffix not in TEXT_SUFFIXES:
            continue
        full_path = repo_root / Path(*posix_path.parts)
        if not full_path.is_file():
            continue
        text = full_path.read_text(encoding="utf-8", errors="replace")
        checks = (
            ("PHONE_VALUE", MAINLAND_PHONE_PATTERN),
            ("E164_VALUE", E164_PATTERN),
            ("EMAIL_VALUE", EMAIL_PATTERN),
            ("SECRET_MATERIAL", SECRET_PATTERN),
        )
        for code, pattern in checks:
            if pattern.search(text):
                violations.append({"code": code, "path": normalized})

        if suffix == ".json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                violations.append({"code": "INVALID_JSON_ARTIFACT", "path": normalized})
            else:
                for violation in _json_key_violations(payload):
                    violation["path"] = normalized
                    violations.append(violation)

    return sorted(
        violations,
        key=lambda item: (item["path"], item["code"], item.get("json_path", "")),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check tracked G-02 release artifacts")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    violations = find_privacy_violations(arguments.repo_root)
    report = {
        "schema_version": 1,
        "passed": not violations,
        "violations": violations,
    }
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        f"G02_REPOSITORY_PRIVACY_{'PASS' if not violations else 'BLOCKED'} "
        f"violations={len(violations)}"
    )
    return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
