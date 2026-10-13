"""Package reproducible fixtures and actual TD exports for human inspection."""
import argparse
from pathlib import Path
import zipfile


def package(evidence,dataset,output):
    evidence,dataset,output=map(Path,(evidence,dataset,output))
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.write(Path(__file__).parents[1]/'design/全过程模拟数据使用说明.txt','请先阅读.txt')
        z.write(Path(__file__).parents[1]/'design/physiology-study-v6.md','文献与设计说明.md')
        for f in dataset.rglob('*'):
            if f.is_file(): z.write(f,'输入数据/'+str(f.relative_to(dataset)))
        for f in evidence.rglob('*'):
            if f.is_file(): z.write(f,'TD验证/'+str(f.relative_to(evidence)))
        for name in ('study_simulation.py','verify_study.py'):
            z.write(Path(__file__).with_name(name),'复算代码/'+name)
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('evidence'); p.add_argument('dataset'); p.add_argument('output'); a=p.parse_args()
    print(package(a.evidence,a.dataset,a.output))
