"""Offline, pinned, opt-in documentation/task migration. Does not change runtime code.

Default --check is read-only. --apply requires a NEW external backup directory.
No commit/push/reset/clean, network, experiments, or implicit protocol approvals.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

PACKAGE=Path(__file__).resolve().parents[1]
NEW_PREFIX='00-项目管理/01-项目章程与规划/2026-09-08_SRP_主线升级_v1.2/'

class MigrationError(RuntimeError): pass

def sha256(data: bytes) -> str:return hashlib.sha256(data).hexdigest()
def git_blob(data: bytes) -> str:return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def _load(path: Path) -> Any:return json.loads(path.read_text(encoding='utf-8-sig'))
def _inside(child: Path,parent: Path) -> bool:
    try:child.relative_to(parent);return True
    except ValueError:return False

def safe_target(root: Path, relative: str) -> Path:
    # Windows and POSIX independent; reject drive/UNC/relative traversal and metadata writes.
    p=PurePosixPath(relative)
    if not relative or '\\' in relative or ':' in relative or p.is_absolute() or any(x in {'.','..','.git'} for x in p.parts):
        raise MigrationError(f'Unsafe path: {relative}')
    target=root.joinpath(*p.parts)
    current=root
    for part in p.parts:
        current=current/part
        if current.is_symlink():raise MigrationError(f'Symlink is not allowed: {relative}')
    if not _inside(target.resolve(),root.resolve()):raise MigrationError('Target leaves root.')
    return target

def git(repo: Path,*args: str) -> bytes:
    try:
        p=subprocess.run(['git','-C',str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    except (OSError,subprocess.CalledProcessError) as exc:
        raise MigrationError(f'Git read failed: {args[0]}') from exc
    return p.stdout

def verify_integrity(package: Path) -> int:
    manifest=package/'SHA256SUMS.txt'
    if not manifest.is_file():raise MigrationError('Missing package SHA256SUMS.txt.')
    seen=set()
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line:continue
        try:digest,relative=line.split('  ',1)
        except ValueError as exc:raise MigrationError('Malformed checksum line.') from exc
        if relative in seen:raise MigrationError('Duplicate checksum path.')
        seen.add(relative);target=safe_target(package,relative)
        if not target.is_file() or sha256(target.read_bytes())!=digest:
            raise MigrationError(f'Package integrity mismatch: {relative}')
    if not seen:raise MigrationError('Empty checksum manifest.')
    # Ignore user-generated Python bytecode only; no extra overlay/scripts accepted.
    actual={p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='SHA256SUMS.txt'}
    if actual != seen:raise MigrationError('Checksum inventory differs from package files.')
    return len(seen)

def ancestors(graph: dict[str,list[str]],node: str) -> set[str]:
    if node not in graph:raise MigrationError(f'Unknown node {node}')
    visiting=set();done=set()
    def visit(n: str) -> None:
        if n in visiting:raise MigrationError(f'Dependency cycle at {n}')
        if n in done:return
        if n not in graph:raise MigrationError(f'Unknown dependency {n}')
        visiting.add(n)
        for dep in graph[n]:visit(dep)
        visiting.remove(n);done.add(n)
    visit(node);done.discard(node);return done

def validate_graph(graph: dict[str,list[str]],contract: dict) -> None:
    for node in graph:ancestors(graph,node)
    core=ancestors(graph,contract['core_terminal'])
    if core.intersection(contract['core_must_not_depend_on']):
        raise MigrationError('Core route still depends on the optional extension.')

def transform_csv(data: bytes,mutation: dict,new_csv: Path,contract: dict) -> bytes:
    text=data.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text,newline=''))
    fields=reader.fieldnames
    if not fields or len(set(fields))!=len(fields):raise MigrationError('Invalid task header.')
    rows=list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise MigrationError('Malformed task CSV row.')
    byid={r['task_id']:r for r in rows}
    if len(byid)!=len(rows):raise MigrationError('Duplicate source task ID.')
    before_done={i:dict(r) for i,r in byid.items() if r.get('status')=='DONE'}
    for item in mutation['mutations']:
        i=item['task_id']
        if i not in byid:raise MigrationError(f'Missing target task {i}')
        row=byid[i]
        deps=row['depends_on'].split('|') if row['depends_on'] else []
        if deps!=item['expected_dependencies']:raise MigrationError(f'Dependency drift in {i}')
        if row['status']=='DONE':raise MigrationError(f'Refusing to rewrite historical DONE: {i}')
        if not set(item['changes']).issubset(fields):raise MigrationError('Unknown target field.')
        row.update(item['changes'])
    with new_csv.open(encoding='utf-8-sig',newline='') as f:
        added_reader=csv.DictReader(f)
        if added_reader.fieldnames!=fields:raise MigrationError('New tasks schema mismatch.')
        additions=list(added_reader)
    for row in additions:
        if row['task_id'] in byid:raise MigrationError('New task collides with existing ID.')
        if row['status']=='DONE':raise MigrationError('Cannot inject a pre-completed task.')
        byid[row['task_id']]=row;rows.append(row)
    if any(byid[i]!=r for i,r in before_done.items()):raise MigrationError('Historical DONE changed.')
    graph={r['task_id']:r['depends_on'].split('|') if r['depends_on'] else [] for r in rows}
    if graph!=contract['tasks']:raise MigrationError('Actual transformed task graph differs from reviewed 70-node contract.')
    validate_graph(graph,contract)
    newline='\r\n' if '\r\n' in text else '\n'
    buff=io.StringIO(newline='');writer=csv.DictWriter(buff,fieldnames=fields,lineterminator=newline)
    writer.writeheader();writer.writerows(rows)
    encoded=buff.getvalue().encode('utf-8')
    return (b'\xef\xbb\xbf'+encoded) if data.startswith(b'\xef\xbb\xbf') else encoded

def prepare_changes(repo: Path,package: Path=PACKAGE,*,check_integrity: bool=True) -> tuple[dict[str,bytes],dict]:
    repo=repo.resolve();package=package.resolve()
    # Read status before deriving any writes; this deliberately refuses existing work.
    status=git(repo,'status','--porcelain=v1','-z')
    if status:raise MigrationError('Worktree is not clean. Preserve your changes; no reset/clean is performed.')
    top=Path(git(repo,'rev-parse','--show-toplevel').decode().strip()).resolve()
    if top!=repo:raise MigrationError('--repo must be the Git worktree root.')
    cfgdir=package/'02_仓库升级';manifest=_load(cfgdir/'migration_manifest.json')
    if check_integrity:verify_integrity(package)
    head=git(repo,'rev-parse','HEAD').decode().strip()
    if head!=manifest['expected_commit']:raise MigrationError('HEAD mismatch. Re-audit the new revision instead of forcing this migration.')
    for path,expected in manifest['expected_source_blobs'].items():
        safe_target(repo,path)
        raw=git(repo,'show',f'HEAD:{path}')
        if git_blob(raw)!=expected:raise MigrationError(f'Pinned source blob mismatch: {path}')
    changes={}
    overlay=cfgdir/manifest['overlay_dir']
    for src in sorted(overlay.rglob('*')):
        if src.is_symlink():raise MigrationError('Overlay symlinks are not allowed.')
        if not src.is_file():continue
        rel=src.relative_to(overlay).as_posix()
        if rel!='SRP_UPGRADE_v1.2.md' and not rel.startswith(NEW_PREFIX):
            raise MigrationError('Overlay target is outside the reviewed additive namespace.')
        dest=safe_target(repo,rel)
        if dest.exists():raise MigrationError(f'Additive target already exists: {rel}')
        changes[rel]=src.read_bytes()
    notice=('> **2026-09-08 v1.2研究升级说明**：'+manifest['readme_notice']+'\n\n').encode('utf-8')
    for relative in manifest['prepend_notices']:
        if relative not in {'README.md','AGENTS.md'}:raise MigrationError('Unreviewed notice destination.')
        target=safe_target(repo,relative)
        changes[relative]=notice+target.read_bytes()
    mutation=_load(cfgdir/manifest['task_mutations'])
    csvpath=mutation['target_csv'];target=safe_target(repo,csvpath)
    contract=_load(overlay/NEW_PREFIX/'route_contract_v1.2.json')
    changes[csvpath]=transform_csv(target.read_bytes(),mutation,cfgdir/manifest['new_tasks_csv'],contract)
    return changes,{'status':'CHECK_PASS_NOT_APPLIED','head':head,'changed_or_added_files':len(changes),
                    'existing_task_updates':len(mutation['mutations']),'new_tasks':12,'target_graph_nodes':len(contract['tasks']),
                    'runtime_code_changed':False,'formal_collection_authorized':False,
                    'files':[{'path':p,'mode':'modify' if safe_target(repo,p).exists() else 'add','new_sha256':sha256(b)} for p,b in changes.items()]}

def atomic_write(path: Path,data: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.srp-tmp-'+uuid.uuid4().hex)
    try:tmp.write_bytes(data);os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

def apply_changes(repo: Path,changes: dict[str,bytes],backup: Path,report: dict) -> dict:
    repo=repo.resolve();backup=backup.resolve()
    if backup.exists() or _inside(backup,repo) or _inside(backup,PACKAGE.resolve()):
        raise MigrationError('Backup must be a NEW directory outside the repository and package.')
    before={p:safe_target(repo,p).read_bytes() if safe_target(repo,p).is_file() else None for p in changes}
    backup.mkdir(parents=True)
    receipt={'schema_version':'1.2','state':'APPLY_STARTED','repo':str(repo),'head':report['head'],'files':[]}
    for p,b in before.items():
        if b is not None:atomic_write(safe_target(backup/'originals',p),b)
        receipt['files'].append({'path':p,'existed':b is not None,'before_sha256':None if b is None else sha256(b),'after_sha256':sha256(changes[p])})
    atomic_write(backup/'receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode())
    written=[]
    try:
        for p,b in changes.items():
            target=safe_target(repo,p);atomic_write(target,b);written.append(p)
    except Exception:
        for p in reversed(written):
            if before[p] is None:safe_target(repo,p).unlink(missing_ok=True)
            else:atomic_write(safe_target(repo,p),before[p])
        receipt['state']='ERROR_ROLLED_BACK';atomic_write(backup/'receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode())
        raise
    receipt['state']='APPLIED';atomic_write(backup/'receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode())
    return {**report,'status':'APPLIED_DOCUMENTS_AND_TASKS_ONLY','backup':str(backup),'commit_or_push_performed':False}

def restore(repo: Path,backup: Path) -> dict:
    repo=repo.resolve();backup=backup.resolve();receipt=_load(backup/'receipt.json')
    if Path(receipt['repo']).resolve()!=repo:raise MigrationError('Backup belongs to another repository path.')
    if git(repo,'rev-parse','HEAD').decode().strip()!=receipt['head']:raise MigrationError('HEAD changed; automatic restore refused.')
    # Validate every path and byte first; never erase subsequent user edits.
    for row in receipt['files']:
        dest=safe_target(repo,row['path'])
        if dest.exists():
            if not dest.is_file() or sha256(dest.read_bytes()) not in {row['before_sha256'],row['after_sha256']}:
                raise MigrationError(f'Post-migration edit detected: {row["path"]}')
        elif row['existed']:raise MigrationError('An original file has since been removed.')
        if row['existed']:
            source=safe_target(backup/'originals',row['path'])
            if not source.is_file() or sha256(source.read_bytes())!=row['before_sha256']:raise MigrationError('Backup checksum mismatch.')
    for row in receipt['files']:
        dest=safe_target(repo,row['path'])
        if row['existed']:atomic_write(dest,safe_target(backup/'originals',row['path']).read_bytes())
        else:dest.unlink(missing_ok=True)
    receipt['state']='RESTORED';atomic_write(backup/'receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode())
    return {'status':'RESTORED_REVIEWED_FILES_ONLY','repo':str(repo),'backup':str(backup),'no_reset_or_clean':True}

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',required=True,type=Path)
    g=p.add_mutually_exclusive_group();g.add_argument('--check',action='store_true');g.add_argument('--apply',action='store_true');g.add_argument('--restore-from',type=Path)
    p.add_argument('--backup-dir',type=Path)
    a=p.parse_args()
    try:
        if a.restore_from:
            if a.backup_dir:raise MigrationError('--backup-dir is only for --apply.')
            result=restore(a.repo,a.restore_from)
        else:
            if a.apply and not a.backup_dir:raise MigrationError('--apply requires --backup-dir.')
            if not a.apply and a.backup_dir:raise MigrationError('--backup-dir is only for --apply.')
            changes,result=prepare_changes(a.repo)
            if a.apply:result=apply_changes(a.repo,changes,a.backup_dir,result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (MigrationError,OSError,UnicodeError,ValueError,KeyError) as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc),'no_commit_push_or_experiment':True},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__':main()
