from __future__ import annotations

import hashlib
from pathlib import Path

import pdfplumber
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "pdf"

EXPECTED = {
    "01_项目目标介绍与可行性论证.pdf": (
        "项目目标介绍与可行性论证",
        "可行性论证",
        "结论",
    ),
    "02_固定任务概要.pdf": (
        "固定任务概要",
        "任务分解问题",
        "固定任务的统一过程与验收",
    ),
    "03_项目设计简述与实验流程.pdf": (
        "项目设计简述与实验流程",
        "单次体验流程",
        "三阶段研究设计",
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
        print(f"PASS {filename} pages={pages} sha256={digest}")


if __name__ == "__main__":
    main()
