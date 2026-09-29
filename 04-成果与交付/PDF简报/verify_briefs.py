from __future__ import annotations

import hashlib
import csv
from collections import Counter
from pathlib import Path
import re

import pdfplumber
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "human/deliverables/pdf"

EXPECTED = {
    "02_固定任务概要.pdf": (
        "固定任务概要",
        "任务分解问题",
        "固定任务的统一过程与验收",
    ),
}

FORBIDDEN_TERMS = ("\u8bca\u65ad", "\u6cbb\u7597", "\u75be\u75c5", "\u60a3\u8005", "\u533b\u7597\u8bbe\u5907", "\u4e34\u5e8a")
UNRESOLVED_MARKERS = ("??", "\\ref", "\\label")
A4_WIDTH = 595.28
A4_HEIGHT = 841.89
PAGE_TOLERANCE = 1.0


def verify_pdf(path: Path, markers: tuple[str, ...]) -> tuple[int, str]:
    if not path.is_file():
        raise AssertionError(f"missing output: {path}")

    reader = PdfReader(path)
    if reader.is_encrypted:
        raise AssertionError(f"encrypted output: {path.name}")

    page_texts: list[str] = []
    with pdfplumber.open(path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            if abs(page.width - A4_WIDTH) > PAGE_TOLERANCE:
                raise AssertionError(f"{path.name} page {page_number}: width is not A4")
            if abs(page.height - A4_HEIGHT) > PAGE_TOLERANCE:
                raise AssertionError(f"{path.name} page {page_number}: height is not A4")

            text = page.extract_text() or ""
            if len(text.strip()) < 80:
                raise AssertionError(f"{path.name} page {page_number}: page is blank or too sparse")
            page_texts.append(text)

    full_text = "\n".join(page_texts)
    for marker in markers:
        if marker not in full_text:
            raise AssertionError(f"{path.name}: missing marker {marker}")
    for term in FORBIDDEN_TERMS:
        if term in full_text:
            raise AssertionError(f"{path.name}: restricted term found")
    for marker in UNRESOLVED_MARKERS:
        if marker in full_text:
            raise AssertionError(f"{path.name}: unresolved marker {marker}")

    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return len(reader.pages), digest


def main() -> None:
    for filename, markers in EXPECTED.items():
        pages, digest = verify_pdf(OUTPUT_DIR / filename, markers)
        text = ''.join(page.extract_text() for page in PdfReader(OUTPUT_DIR / filename).pages)
        normalized = re.sub(r'\s+', '', text)
        registry = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/05_可领取任务包.csv'
        with registry.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        counts = Counter(row['status'] for row in rows)
        if f"DONE={counts['DONE']}项" not in normalized:
            raise AssertionError('PDF status count differs from current registry')
        for row in rows:
            if row['task_id'] not in normalized:
                raise AssertionError(f"PDF task missing: {row['task_id']}")
        for status in ('READY', 'IN_PROGRESS', 'IN_REVIEW'):
            values = [row['task_id'] for row in rows if row['status'] == status]
            match = re.search(rf'{status}=([^；;]+)', normalized)
            if match is None or set(match.group(1).split('/')) != set(values):
                raise AssertionError(f'PDF {status} tasks differ from registry')
        print(f"PASS {filename} pages={pages} sha256={digest}")


if __name__ == "__main__":
    main()
