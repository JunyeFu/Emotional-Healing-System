"""Check the delivered editable pages and drawing-software exports."""
from pathlib import Path
import json
import urllib.parse
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / 'human/deliverables/t01-workbench-design-20261012'
PAGES = ['home','prepare','waiting','running','paused','closeout','history',
         'details','closed','unselected','fault','abort']
STEMS = ['01-home','02-prepare','03-waiting','04-running','05-paused','06-closeout',
         '07-history','08-details','09-closed','10-unselected','11-fault','12-abort']


def ink(image, box, color):
    rgb = tuple(int(color[i:i+2], 16) for i in (1,3,5))
    return sum(max(abs(a-b) for a,b in zip(pixel,rgb)) < 12
               for pixel in image.convert('RGB').crop(box).get_flattened_data())


def check():
    root = ET.parse(OUT/'t01-workbench-redesign-final.drawio').getroot()
    assert [p.get('id') for p in root] == PAGES
    results=[]
    for p,stem in zip(root,STEMS):
        cells=p.find('mxGraphModel/root')
        ids=[c.get('id') for c in cells]
        assert len(ids)==len(set(ids))
        assert not any('image=' in c.get('style','') for c in cells)
        for c in cells:
            if c.get('vertex')!='1':
                continue
            g=c.find('mxGeometry')
            x,y,w,h=(float(g.get(v,'0')) for v in ('x','y','width','height'))
            assert x>=0 and y>=0 and x+w<=1280.01 and y+h<=720.01,(p.get('id'),c.get('id'))
        values=[c.get('value','') for c in cells]
        assert not any('固定量程' in value for value in values)
        assert not any(label in value for value in values
                       for label in ('设计示例', 'fade步骤'))
        if p.get('id') in ('closeout','closed'):
            assert '13:20' in values and '13:34' in values
        if p.get('id')=='unselected':
            assert '尚未选择记录' in values
            export=next(c for c in cells if c.get('value')=='导出选中场次')
            assert 'fillColor=#E9EDF2' in export.get('style')
        if p.get('id')=='fault':
            assert '不可判定' in values and '信号质量 未知' in values
        if p.get('id')=='abort':
            overlay=next(c for c in cells if c.get('id')=='abort-overlay')
            assert float(overlay.find('mxGeometry').get('height'))==672
        image=Image.open(OUT/(stem+'.drawio.png'))
        assert image.width in (1280,1281) and image.height in (720,721)
        embedded=ET.fromstring(urllib.parse.unquote(image.info['mxfile']))
        assert len(embedded)==1 and embedded[0].get('id')==p.get('id')
        counts={}
        if p.get('id') in ('prepare','waiting','running','paused','fault'):
            counts['resp']=ink(image,(82,233,580,344),'#56616F' if p.get('id')=='fault' else '#2563A6')
            counts['ecg']=ink(image,(82,483,838,594),'#237A47')
            assert counts['resp']>150 and counts['ecg']>150,(p.get('id'),counts)
        results.append(dict(page=p.get('id'),editable_cells=len(cells)-2,
                            export_size=list(image.size),embedded_pages=1,plot_ink_pixels=counts))
    return dict(result='PASS',pages=results,scope='Editable design and native exports only; not TD runtime validation')


if __name__=='__main__':
    report=check()
    Path(__file__).with_name('validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
