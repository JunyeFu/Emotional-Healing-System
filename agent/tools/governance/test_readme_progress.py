import runpy
from pathlib import Path

render = runpy.run_path(str(Path(__file__).with_name("render_governance_views.py")))["progress_section"]


def test_insert_before_first_section():
    text = render("# SRP\n\nIntro\n\n## Overview\nBody\n", "DONE=20")
    assert text.index("TEAM_PROGRESS_START") < text.index("## Overview")
    assert "DONE=20" in text
    assert text.count("![团队任务进度图]") == 1
    assert '(human/assets/readme/team-task-progress.svg)' in text


def test_refresh_replaces_old_state_and_preserves_prose():
    old = render("# SRP\n\n## Overview\nBody\n", "IN_REVIEW=U12-03")
    new = render(old, "DONE=21")
    assert "IN_REVIEW=U12-03" not in new
    assert new.count("TEAM_PROGRESS_START") == 1
    assert new.endswith("## Overview\nBody\n")
    assert render(new, "DONE=21") == new


def test_document_without_sections():
    assert "TEAM_PROGRESS_END" in render("# SRP\n", "DONE=20")


def test_renderer_root_and_current_media_target():
    namespace = runpy.run_path(str(Path(__file__).with_name("render_governance_views.py")))
    root = Path(__file__).resolve().parents[3]
    assert namespace['ROOT'] == root
    assert namespace['GOV'].is_dir()
    assert (root / 'human/assets/readme/team-task-progress.svg').is_file()
    assert not (root / 'Tools').exists()
    assert not (root / 'assets').exists()
    assert not (root / '04-成果与交付').exists()
    source = (root / 'agent/tools/governance/render_governance_views.py').read_text(encoding='utf-8')
    assert '"agent/delivery/briefs/02_固定任务概要.md"' in source
    assert 'destination = ROOT / "human/assets/diagrams"' in source


def test_delivery_builder_does_not_skip_chinese_source_in_windows_powershell():
    root = Path(__file__).resolve().parents[3]
    source = (root / 'agent/delivery/briefs/build_briefs.ps1').read_text(encoding='utf-8')
    assert "-Filter '02_*.md'" in source
    assert '$sources.Count -ne 1' in source
    assert "'..\\..\\..'" in source
