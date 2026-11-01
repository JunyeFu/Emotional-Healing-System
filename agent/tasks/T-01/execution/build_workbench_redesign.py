"""Translate the approved draw.io geometry to native TD panels and live fields."""
from pathlib import Path
import xml.etree.ElementTree as ET

_flow = Path(__file__).with_name('build_workbench_flow.py')
exec(compile(_flow.read_text(encoding='utf-8'), str(_flow), 'exec'), globals())
_flow_build = build
DESIGN = TASK_DIR.parents[2] / 'human/deliverables/t01-workbench-design-20261012/t01-workbench-redesign-final.drawio'


def build():
    shell = _flow_build()
    render = shell.op('Logic/render')
    render.par.active = False
    shell.op('Content').par.display = False
    ui_root = panel(shell, 'Design', width=1280, height=720)
    bounds(ui_root, x='=(parent().width-1280)/2', top='=(parent().height-720)/2', width=1280, height=720)
    for diagram in ET.parse(DESIGN).getroot().findall('diagram'):
        page = diagram.get('id')
        parent = panel(ui_root, page, width=1280, height=720)
        for order, cell in enumerate(diagram.findall('.//mxCell')):
            geo = cell.find('mxGeometry')
            if geo is None or cell.get('edge') == '1':
                continue
            x,y,w,h = [float(geo.get(k,'0')) for k in ('x','y','width','height')]
            value = cell.get('value','')
            style = dict(s.split('=',1) for s in cell.get('style','').split(';') if '=' in s)
            # History rows are generated from the actual session ledger below.
            if page in ('history','unselected') and 250 <= y <= 438:
                continue
            # Design-only progress bars cannot imply timing absent from the protocol.
            if page in ('running','paused','fault','abort') and x >= 896 and h <= 6 and 380 <= y <= 545:
                continue
            name = 'c_' + cell.get('id').replace('-','_')
            node = text(parent,name,value,x=x,top=y,width=w,height=h,size=float(style.get('fontSize',16)),align=style.get('align','left')) if value else panel(parent,name,x=x,top=y,width=w,height=h)
            # TD sorts equal-layer siblings by name; preserve draw.io paint order.
            setp(node, layer=order)
            fill = style.get('fillColor','none')
            if fill != 'none':
                color(node,fill)
            else:
                node.par.bgalpha = 0
            stroke = style.get('strokeColor','none')
            if stroke != 'none':
                setp(node,leftborder='bordera',rightborder='bordera',topborder='bordera',bottomborder='bordera',borderar=rgb(stroke)[0],borderag=rgb(stroke)[1],borderab=rgb(stroke)[2],borderaalpha=1)
            node.store('design_id',cell.get('id'))
            node.store('design_xy',(x,y))
            if value:
                setp(node,textpaddingl=0,textpaddingr=0,textpaddingt=0,textpaddingb=0,
                     fontcolorr=rgb(style.get('fontColor','#202832'))[0],fontcolorg=rgb(style.get('fontColor','#202832'))[1],fontcolorb=rgb(style.get('fontColor','#202832'))[2])
                node.store('design_text',value)
                action_name = {'实验':'back','实验记录':'history','明细':'details','准备下一位':'new','查看实验记录':'history','确认准备':'submit','取消准备':'cancel','暂停体验':'pause','恢复体验':'resume','中止本场':'abort_dialog','继续本场':'abort_cancel','确认中止':'abort_confirm','导出本场':'export','打开记录目录':'open','准备下一位参与者':'next','返回主页':'home','导出选中场次':'export','返回实验':'back','返回运行':'back','查看明细':'details','展开原始协议字段':'raw','复制会话编号':'copy'}.get(value)
                curve = {'呼吸':('resp','resp'),'加速度':('resp','acceleration'),'角速度':('resp','angular_velocity'),'心电':('ecg','ecg'),'RR间期':('ecg','rr'),'心率':('ecg','hr')}.get(value) if y in (367,617) else None
                if value == '准备下一位' and page in ('closeout','closed'):
                    action_name = 'next'
                if value == '继续体验':
                    action_name = 'abort_cancel'
                if value == '查看记录错误':
                    action_name = 'details'
                if action_name or curve:
                    node.store('design_action',action_name)
                    node.store('design_curve',curve)
                    callback = shell.op('Logic').create(panelexecuteDAT,'design_'+page+'_'+name)
                    setp(callback,panels=node.path,panelvalue='lselect',offtoon=True)
                    expr = 'select_curve'+repr(curve) if curve else 'design_action('+repr(action_name)+')'
                    callback.text = 'def onOffToOn(v):\n    op('+repr(render.path)+').module.'+expr+'\n'
        if page in ('prepare','waiting','running','paused','fault','abort'):
            for source,y in (('resp',233),('ecg',483)):
                wave = panel(parent,'live_'+source,x=82,top=y,width=756,height=110)
                setp(wave,top=SHELL+'/Logic/plot_'+source,topfill='stretch',layer=150)
            # Keep the confirmation dialog above the live plots.
            if page == 'abort':
                for node in parent.children:
                    key=node.fetch('design_id','')
                    if key.startswith('abort-') and key.split('-')[-1].isdigit() and int(key.split('-')[-1])>=112:
                        setp(node,layer=200+int(key.split('-')[-1]))
        if page in ('history','unselected'):
            rows=panel(parent,'rows',x=20,top=250,width=1240,height=188)
            setp(rows,layer=150)
            setp(rows,pvscrollbar='on',mousewheel=True)
            template=panel(shell.op('Logic'),'design_row_'+page,width=1240,height=62)
            for index,(x,w) in enumerate(((16,170),(206,150),(376,140),(536,130),(686,150),(856,150),(1026,198))):
                text(template,'col_'+str(index),'',x=x,top=18,width=w,height=26,size=14).par.enable=False
            line(template,'bottom',61,width=1240)
            select=text(template,'select','',width=1240,height=62)
            setp(select,layer=10,bgalpha=0)
        if page == 'details':
            raw=panel(parent,'raw',x=20,top=156,width=1240,height=486,background='canvas',border=True)
            setp(raw,layer=500)
            raw.par.display=False
            body=text(raw,'body','',x=16,top=12,width=1208,height=414,size=14,wrap=True)
            body.par.aligny='top'
            close=text(raw,'close','收起原始协议字段',x=16,top=440,width=240,height=32,size=16)
            close.store('design_action','raw')
            callback=shell.op('Logic').create(panelexecuteDAT,'raw_close')
            setp(callback,panels=close.path,panelvalue='lselect',offtoon=True)
            callback.text='def onOffToOn(v):\n    op('+repr(render.path)+').module.design_action("raw")\n'
    for source in ('resp','ecg'):
        bounds(shell.op('Content/Pages/overview/devices/'+source+'/wave'),width=756,height=110)
    render.text += '\n' + Path(__file__).with_name('workbench_redesign_runtime.py').read_text(encoding='utf-8')
    render.par.active=True
    render.module.onFrameStart(0)
    return shell
