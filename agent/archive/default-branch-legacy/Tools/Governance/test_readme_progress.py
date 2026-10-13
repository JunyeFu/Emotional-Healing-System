import runpy
from pathlib import Path

render = runpy.run_path(str(Path(__file__).with_name("render_governance_views.py")))["progress_section"]


def test_insert_before_first_section():
    text = render("# SRP\n\nIntro\n\n## Overview\nBody\n", "DONE=20")
    assert text.index("TEAM_PROGRESS_START") < text.index("## Overview")
    assert "DONE=20" in text
    assert text.count("![团队任务进度图]") == 1


def test_refresh_replaces_old_state_and_preserves_prose():
    old = render("# SRP\n\n## Overview\nBody\n", "IN_REVIEW=U12-03")
    new = render(old, "DONE=21")
    assert "IN_REVIEW=U12-03" not in new
    assert new.count("TEAM_PROGRESS_START") == 1
    assert new.endswith("## Overview\nBody\n")
    assert render(new, "DONE=21") == new


def test_document_without_sections():
    assert "TEAM_PROGRESS_END" in render("# SRP\n", "DONE=20")
