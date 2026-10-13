"""Render refreshed summaries and compare every page with this batch's baseline."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'agent/local/artifacts/summary-refresh'
SKILL = Path('C:/Users/fujunye/.codex/plugins/cache/openai-primary-runtime/documents/26.905.11957/skills/documents')
REPORT = ROOT / 'agent/evidence/normalization-summary-render.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-baselines', action='store_true')
    parser.add_argument('--version', default='current')
    args = parser.parse_args()
    refresh = json.loads((ROOT / 'agent/evidence/normalization-summary-refresh.json').read_text(encoding='utf-8'))
    results = []
    for entry in refresh['summaries']:
        task = entry['task_id']
        word = ROOT / f'human/tasks/{task}/summary.docx'
        original = QA / task / 'baseline/summary.docx'
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(subprocess.check_output(['git', 'show', refresh['baseline_commit'] + ':' + word.relative_to(ROOT).as_posix()], cwd=ROOT))
        directories = []
        for label, source in (('baseline', original), (args.version, word)):
            output = QA / task / label
            command = [sys.executable, str(SKILL / 'render_docx.py'), str(source), '--output_dir', str(output), '--emit_pdf']
            if not (label == 'baseline' and args.reuse_baselines and (output / 'summary.pdf').is_file()
                    and list(output.glob('page-*.png'))):
                result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                (output / 'render.log').write_bytes(result.stdout)
                if result.returncode:
                    raise RuntimeError(f'{task} {label}: ' + result.stdout.decode('utf-8', 'replace'))
            directories.append(output)
        before = {p.name: sha(p) for p in directories[0].glob('page-*.png')}
        after = {p.name: sha(p) for p in directories[1].glob('page-*.png')}
        unchanged = [name for name in after if before.get(name) == after[name]]
        changed = [name for name in after if name not in unchanged]
        results.append({'task_id': task, 'word_sha256': sha(word),
                        'baseline_pages': len(before), 'current_pages': len(after),
                        'unchanged_pages': unchanged, 'changed_pages': changed,
                        'changed_pages_visually_checked': [],
                        'qa_path': directories[1].relative_to(ROOT).as_posix()})
        REPORT.write_text(json.dumps({'scope': 'Rendered page comparisons; changed pages still require visual inspection',
                                      'tasks': results}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'{task}: pages={len(after)}, unchanged={len(unchanged)}, inspect={len(changed)}', flush=True)
    print('Rendered all 71 summaries; visual inspection remains explicitly pending', flush=True)


if __name__ == '__main__':
    main()
