"""Collect this migration batch's verified results without claiming goal completion."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'agent/evidence'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    report_path = EVIDENCE / 'root-migration-local.json'
    report = read(report_path)
    packages = read(EVIDENCE / 'root-migration-local-package-tests.json')
    root = read(EVIDENCE / 'root-migration-check.json')
    probe = read(EVIDENCE / 'root-migration-local-td/probe_report.json')
    reopen = read(EVIDENCE / 'root-migration-local-td/touchdesigner/reopen_report.json')
    media = read(ROOT / 'agent/tasks/V-04/evidence/verification.json')
    assert report['verified'] and len(packages) == 60
    assert all(item['exit_code'] == 0 for item in packages)
    assert len(root['migrated_roots']) == 19 and not root['pending_roots']
    assert not root['root_entries_still_to_classify']
    assert root['task_packages_checked'] == 71 and root['word_source_links_checked'] == 330
    assert probe['pass'] and reopen['pass']
    assert all(item['exit_code'] == 0 for item in media['checks'])
    report['verification'] = {
        'root_pytest_observed': '635 passed in 46.68s',
        'task_packages_with_tests': len(packages),
        'failed_task_packages': 0,
        'word_source_links': root['word_source_links_checked'],
        'task_packages_checked': root['task_packages_checked'],
        'physical_root_moves': len(root['migrated_roots']),
        'v04_historical_media_gates': 8,
        'v04_current_tests': 8,
        'source_json_bytes_preserved': True,
        'td_reopen_checks': len(reopen['checks']),
        'td_udp_checks': len(probe['checks']),
        'dispatch_packages': 5,
        'frozen_snapshots': 61,
        'real_devices_or_formal_admission': 'NOT_RUN',
    }
    report['remaining_goal_work'] = [
        'Refresh historical progress statements in current Agent task summaries and current task documents',
        'Regenerate affected task Word summaries and inspect changed rendered pages',
        'Requirement-by-requirement goal completion audit',
    ]
    report['human_review'] += (
        'V-04八项媒体门及800秒深度解码通过，根Python635项、60包专项通过；'
        'TD隔离重开12项和UDP恢复8项通过，五分发包61快照保持。'
        '根目录19/19已实际迁移，当前单包历史进度表述待从Agent源刷新；整体目标暂不标完成。'
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS local migration evidence; goal remains active for current Word refresh and final audit')


if __name__ == '__main__':
    main()
