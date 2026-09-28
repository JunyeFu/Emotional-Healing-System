"""Regression cases for the two independently reproduced verification gaps."""
from hashlib import sha256
import pytest

from verify import compare_core_files, git_artifact_policy


@pytest.mark.parametrize('policy', ['raw', 'text', 'lfs'])
def test_valid_git_artifact_policies(policy):
    content = b'artifact\n'
    original = content
    if policy == 'text':
        content = b'artifact\r\n'
    elif policy == 'lfs':
        original = f'version https://git-lfs.github.com/spec/v1\noid sha256:{sha256(content).hexdigest()}\nsize {len(content)}\n'.encode()
    assert git_artifact_policy(original, content) == {
        'raw': 'raw_bytes', 'text': 'git_normalized_text_vs_signed_checkout_bytes',
        'lfs': 'lfs_pointer_vs_materialized_artifact'}[policy]


@pytest.mark.parametrize('wrong', ['oid', 'size'])
def test_lfs_pointer_wrong_identity_rejected(wrong):
    content = b'artifact'
    oid = '0' * 64 if wrong == 'oid' else sha256(content).hexdigest()
    size = 999999 if wrong == 'size' else len(content)
    pointer = f'version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {size}\n'.encode()
    with pytest.raises(ValueError, match='LFS_POINTER_IDENTITY_MISMATCH'):
        git_artifact_policy(pointer, content)


@pytest.mark.parametrize('change', ['added', 'deleted', 'functional', 'layout'])
def test_core_comparison_covers_both_sets_and_content(tmp_path, change):
    old, new = tmp_path / 'old', tmp_path / 'new'
    path = 'project1/T01_TelemetryPanel/Runtime/tick.n'
    for folder in (old, new):
        (folder / path).parent.mkdir(parents=True)
        (folder / path).write_text('DAT:execute\ntile 0 0 130 90\nflags =  parlanguage 0\nend\n', encoding='utf-8')
    old_entries, new_entries = [path], [path]
    if change == 'added':
        new_entries.append('project1/T01_TelemetryPanel/Runtime/unverified_send.text')
    elif change == 'deleted':
        new_entries.clear()
    elif change == 'functional':
        (new / path).write_text('DAT:udpin\nend\n', encoding='utf-8')
    else:
        (new / path).write_text('DAT:execute\nv 1 2 3\ntile 50 20 130 90\nflags =  current on parlanguage 0\nend\n', encoding='utf-8')
    count, differences, layout = compare_core_files(old, old_entries, new, new_entries)
    assert count == 1
    if change == 'layout':
        assert differences == [] and layout == [path]
    else:
        assert len(differences) == 1 and layout == []
