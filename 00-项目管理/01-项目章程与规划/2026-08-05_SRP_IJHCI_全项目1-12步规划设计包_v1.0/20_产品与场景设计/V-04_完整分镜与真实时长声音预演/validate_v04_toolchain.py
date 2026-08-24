from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import PIL
import numpy


HERE = Path(__file__).resolve().parent
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
PROBE_PATH = HERE / "V-04_toolchain-probe_v1.0.json"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*args: str) -> str:
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        fail(f"command failed ({completed.returncode}): {' '.join(args)}")
    return completed.stdout


def find_repo_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / ".git").exists():
            return candidate
    fail("repository root not found")
    raise AssertionError


def verify_hash(path_value: str, expected: str, label: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute() or not path.is_file():
        fail(f"{label} path is not an existing absolute file")
    actual = sha256(path)
    if actual != expected.lower():
        fail(f"{label} sha256 mismatch")
    return path


def main() -> None:
    repo = find_repo_root()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))

    if lock["task_id"] != "V-04" or lock["invocation_policy"] != "ABSOLUTE_PATH_ONLY":
        fail("lock identity or invocation policy mismatch")
    if sys.version.split()[0] != lock["python"]["version"]:
        fail("Python version mismatch")
    if PIL.__version__ != lock["pillow"]["version"]:
        fail("Pillow version mismatch")
    if numpy.__version__ != lock["numpy"]["version"]:
        fail("NumPy version mismatch")

    verify_hash(
        lock["python"]["executable"],
        lock["python"]["executable_sha256"],
        "python",
    )
    ffmpeg = verify_hash(
        lock["ffmpeg"]["ffmpeg_executable"],
        lock["ffmpeg"]["ffmpeg_executable_sha256"],
        "ffmpeg",
    )
    ffprobe = verify_hash(
        lock["ffmpeg"]["ffprobe_executable"],
        lock["ffmpeg"]["ffprobe_executable_sha256"],
        "ffprobe",
    )
    verify_hash(
        lock["ffmpeg"]["ffplay_executable"],
        lock["ffmpeg"]["ffplay_executable_sha256"],
        "ffplay",
    )
    archive = verify_hash(
        lock["ffmpeg"]["archive_path"],
        lock["ffmpeg"]["archive_sha256"],
        "archive",
    )
    if archive.stat().st_size != lock["ffmpeg"]["archive_size_bytes"]:
        fail("archive size mismatch")

    tool_root = (repo / ".tools" / "ffmpeg" / "9.0.1").resolve()
    if not ffmpeg.resolve().is_relative_to(tool_root):
        fail("ffmpeg is outside the frozen project-local tool root")
    version_output = run(str(ffmpeg), "-version")
    if not version_output.startswith(lock["ffmpeg"]["version_banner"]):
        fail("ffmpeg version banner mismatch")
    for flag in lock["ffmpeg"]["build_flags_required"]:
        if flag not in version_output:
            fail(f"required FFmpeg build flag missing: {flag}")
    if not run(str(ffprobe), "-version").startswith("ffprobe version 9.0.1"):
        fail("ffprobe version mismatch")

    for ignored_path in (".tools/ffmpeg/9.0.1", ".artifacts-local/V-04"):
        completed = subprocess.run(
            ("git", "check-ignore", "-q", ignored_path), cwd=repo, check=False
        )
        if completed.returncode != 0:
            fail(f"path is not ignored: {ignored_path}")
    if run("git", "ls-files", ".tools").strip():
        fail("project-local tool binary is tracked by Git")

    ledger_path = repo / "02-技术研发/07-数据治理/config/development_tool_license_ledger_v1.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    matching = [
        item
        for item in ledger["entries"]
        if item["entry_id"] == "TOOL-V04-FFMPEG-9.0.1-GYAN-ESSENTIALS"
    ]
    if len(matching) != 1:
        fail("G-02 development tool ledger entry missing or duplicated")
    entry = matching[0]
    if entry["archive_sha256"] != lock["ffmpeg"]["archive_sha256"]:
        fail("G-02 ledger archive hash mismatch")
    if entry["included_in_unity_build"] or entry["redistribution_allowed_by_project"]:
        fail("FFmpeg redistribution boundary is not fail-closed")

    smoke = Path(probe["smoke_test"]["artifact"])
    if not smoke.is_file():
        fail("FFmpeg smoke artifact missing")
    media = json.loads(
        run(
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,codec_type,width,height,pix_fmt,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(smoke),
        )
    )
    streams = {stream["codec_type"]: stream for stream in media["streams"]}
    video = streams.get("video", {})
    audio = streams.get("audio", {})
    if (
        video.get("codec_name") != "h264"
        or video.get("width") != 1920
        or video.get("height") != 1080
        or video.get("pix_fmt") != "yuv420p"
        or video.get("r_frame_rate") != "30/1"
    ):
        fail("video smoke contract mismatch")
    if (
        audio.get("codec_name") != "aac"
        or audio.get("sample_rate") != "48000"
        or audio.get("channels") != 2
    ):
        fail("audio smoke contract mismatch")

    print(
        "PASS: V-04 toolchain locked; Python/Pillow/NumPy exact; "
        "FFmpeg 9.0.1 hashes and build flags exact; smoke media valid; "
        "G-02 tool license entry present"
    )


if __name__ == "__main__":
    main()
