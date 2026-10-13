from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
FILES = (
    ROOT / "04-成果与交付/项目流程图/SRP_任务状态与门禁解释清单_v1.0.svg",
    ROOT / "04-成果与交付/项目流程图/SRP_项目任务关联与门禁流程_v1.0.svg",
)


def test_both_svg_views_show_three_phase_regions_and_two_gates() -> None:
    for path in FILES:
        root = ElementTree.parse(path).getroot()
        ids = {element.attrib.get("id") for element in root.iter()}
        assert {"phase-preparation", "phase-experiment", "phase-writing"} <= ids
        assert {"gate-experiment-start", "gate-experiment-complete"} <= ids
        text = "".join(root.itertext())
        assert "实验开始门" in text
        assert "实验完成门" in text
        assert "G-03 DONE" in text
        assert "A-06 DONE" in text
