"""Embedded in the candidate executeDAT after the existing workflow runtime."""
_flow_frame = onFrameStart
abort_confirmation = False
raw_expanded = False


def design_action(name):
    global abort_confirmation, raw_expanded, export_note
    if name == 'abort_dialog':
        abort_confirmation = workflow.stage in ('RUNNING','PAUSED') and not workflow.pending
    elif name == 'abort_cancel':
        abort_confirmation = False
    elif name == 'abort_confirm':
        if abort_confirmation:
            abort_confirmation = False
            action('abort')
    elif name == 'export':
        item = workflow.history[history_selection] if workflow.view == 'HISTORY' and history_selection is not None else workflow.current if workflow.view != 'HISTORY' else None
        if item and item.get('sealed'):
            export_record()
    elif name == 'open':
        open_record()
    elif name == 'copy':
        ui.clipboard = workflow.current['session_id'] if workflow.current else ''
    elif name == 'raw':
        raw_expanded = not raw_expanded
    else:
        action(name)
    render_design(time.monotonic_ns())


def render_design(now):
    global abort_confirmation
    shell = op(ROOT+'/WorkbenchA')
    root = shell.op('Design')
    c = workflow.current or {}
    stage = workflow.stage
    if stage not in ('RUNNING','PAUSED'):
        abort_confirmation = False
    page = ('history' if history_selection is not None else 'unselected') if workflow.view == 'HISTORY' else 'details' if workflow.view == 'DETAILS' else 'abort' if abort_confirmation else 'fault' if c.get('status') == 'RECORDING_FAILED' else 'closed' if stage == 'CLOSEOUT' and workflow.can_close else stage.lower()
    shell.store('design_page',page)
    for p in root.panelChildren:
        p.par.display = p.name == page
    p = root.op(page)
    fields = {n.fetch('field'):str(n.par.text.eval()) for n in shell.op('Content').findChildren(type=textCOMP) if n.fetch('field',None)}
    eff,total = workflow.times(now)
    duration = session_module.duration
    connected = all(streams.get(k, {}).get('age_ms', 1e9) < 1000 for k in ('resp','ecg'))
    result = {'COMPLETED':'正常结束','ABORTED':'已中止','RECORDING_FAILED':'记录失败'}.get(c.get('status'),'未结束')
    def put(index,value):
        node = p.op('c_'+page+'_'+str(index))
        if node is not None:
            node.par.text = str(value)
    error_text={'NOT_READY_TO_START':'未确认准备','OPERATOR_START_REQUIRED':'待手动开始',
        'REQUEST_RECEIPT_MISMATCH':'回执不匹配','MOCK_DISCONNECTED':'接入中断',
        'CAPTURE_WRITE_FAILED':'记录失败','REQUEST_REJECTED':'请求被拒绝'}
    put(12, error_text.get(workflow.error, '需处理') if workflow.error else ('等待确认' if workflow.pending else '已接入' if connected else '未接入'))
    if page not in ('home','history','unselected'):
        for i,v in ((14,c.get('participant','—')),(16,c.get('condition','—')),(18,c.get('session_id','—')[-14:]),(20,duration(eff)),(22,duration(total))):
            put(i,v)
    if page == 'home':
        for i,v in {23:'等待准备回执',24:'尚未建立场次',27:'待确认',28:'尚未开始',31:'逐场确认',32:'记录目录已建立',34:fields.get('resp_state','未接入'),35:fields.get('ecg_state','未接入'),36:'本轮共 '+str(len(workflow.history))+' 场'}.items():
            put(i,v)
        put(23, '已接入' if connected else '未接入')
        put(24, '模拟模式')
        put(32, str(len(workflow.history)) + ' 场')
    if page in ('prepare','waiting','running','paused','abort','fault'):
        for n in p.findChildren(type=textCOMP):
            x,y=n.fetch('design_xy',(-1,-1))
            source='resp' if y<400 else 'ecg'
            base=0 if source=='resp' else 250
            old=shell.op('Content/Pages/overview/devices/'+source)
            value=None
            if x==570 and y in (163,413): value=fields.get(source+'_state','未接入')
            if x==36 and y in (199,449): value=session_module.LABELS[selected[source]]+' / '+session_module.UNITS[selected[source]]
            if x==726 and y in (199,449): value='6秒窗口' if selected[source]=='ecg' else '30秒窗口'
            if x==29 and y-base in (224,279,334): value=old.op('ymax' if y-base==224 else 'ymin').par.text.eval() if y-base!=279 else ''
            if x in (40,418,796) and y-base==345: value=old.op({40:'axis_left',418:'axis',796:'axis_right'}[x]).par.text.eval()
            if x==418 and y in (367,617): value='最近数据：'+fields.get(source+'_age','未接入')
            if x==638 and y==367: value='信号质量 '+fields.get('resp_sqi','未接入')
            if x==638 and y==617: value='HR '+fields.get('heart_rate','—')+'  RR '+fields.get('rr_interval','—')
            if x==1040 and y==207: value=c.get('weather',fields.get('module_id','未接入'))
            if x==1040 and y==251: value=c.get('segment',fields.get('segment','未接入'))
            if x==1040 and y==295: value=fields.get('actual_step_id','未接入')
            if x==1048 and y in (386,443,500): value=c.get({386:'ideal',443:'guide',500:'actual'}[y],'未接入')
            if x==896 and y==566: value='呼吸估计置信度 '+fields.get('actual_confidence','未接入')
            if value is not None: n.par.text=str(value)
        if page=='prepare':
            for i,v in {88:c.get('participant','—')+' / '+c.get('condition','—'),91:'已收到' if c.get('pretest') else '待回执',94:'等待确认',97:'已确认' if c.get('unity_ready') else '待回执',100:'已确认' if c.get('store_ready') else '待回执',103:fields.get('resp_state','未接入')+' / '+fields.get('ecg_state','未接入'),105:'可提交准备' if workflow.ready else '等待分配、前测和准备回执'}.items(): put(i,v)
        if page=='waiting':
            put(91,'已收到' if capture.state=='CLICKED' else '未收到')
            if shell.fetch('manual_workbench',False):
                put(90,'2  开始请求')
                put(94,'等待确认' if workflow.pending else '未请求')
                put(96,'等待开始')
                put(97,'未记录')
        if page=='fault':
            put(110,workflow.error or '记录失败')
        if page=='abort':
            put(115,c.get('participant','—')+' / '+c.get('condition','—')+' / '+duration(eff))
    if page in ('closeout','closed'):
        for i,v in {26:c.get('participant','—')+' · '+result,28:'总历时 '+duration(total),31:result,34:'已封存' if c.get('sealed') else '待封存',37:'已收到' if c.get('posttest') else '待回执',40:export_note or ('可导出' if c.get('sealed') else '不可导出'),42:'收尾已就绪' if workflow.can_close else '等待封存与后测回执'}.items(): put(i,v)
    if page=='details':
        for i,v in {26:c.get('participant','—')+' · 当前快照',31:fields.get('resp_state','未接入'),33:fields.get('resp_sqi','未接入'),35:fields.get('resp_rate','未接入'),37:fields.get('motion_state','未接入'),39:fields.get('resp_age','—'),44:fields.get('ecg_state','未接入'),46:fields.get('ecg_sqi','未接入'),48:fields.get('ecg_rate','未接入'),50:'ECG / RR / HR',52:fields.get('ecg_age','—'),56:result+' · '+str(capture.count)+' 条',58:'UDP '+str(op(ROOT+'/Sources/UdpTelemetryAdapter/udp_in').par.port.eval())+' · '+fields.get('frame_seq','—')}.items(): put(i,v)
        put(59,('收起原始协议字段' if raw_expanded else '展开原始协议字段'))
        p.op('raw').par.display=raw_expanded
        import json
        p.op('raw/body').par.text=json.dumps(c,ensure_ascii=False,indent=2)
    if page in ('history','unselected'):
        put(20,'本轮记录 · 共 '+str(len(workflow.history))+' 场')
        put(21,'当前：'+stage)
        if history_selection is None:
            sealed_count=sum(bool(item.get('sealed')) for item in workflow.history)
            put(58,'暂无记录' if not workflow.history else '已封存 '+str(sealed_count)+' 场 · 待封存 '+str(len(workflow.history)-sealed_count)+' 场')
            put(60,'')
        rows=p.op('rows')
        for index,item in enumerate(workflow.history):
            n=rows.op('row_'+str(index))
            if n is None:
                n=rows.copy(shell.op('Logic/design_row_'+page),name='row_'+str(index))
                n.par.y.expr='parent().height - '+str((index+1)*62)
                callback=shell.op('Logic').create(panelexecuteDAT,'design_history_'+page+'_'+str(index))
                callback.par.panels=n.op('select').path
                callback.par.panelvalue='lselect'
                callback.par.offtoon=True
                callback.text='def onOffToOn(v):\n    op('+repr(shell.op('Logic/render').path)+').module.inspect_history('+str(index)+')\n'
            n.par.bgcolorr,n.par.bgcolorg,n.par.bgcolorb=session_module.rgb('#EAF1F7' if index==history_selection else '#FFFFFF')
            exported=bool(item.get('path') and (workflow.root/'exports'/(Path(item['path']).stem+'.zip')).exists())
            values=('—',item['participant'],item['condition'],duration(item.get('effective_ns',0)),{'COMPLETED':'正常结束','ABORTED':'已中止'}.get(item['status'],item['status']),'已封存' if item.get('sealed') else '待封存','已导出' if exported else '未导出')
            for j,v in enumerate(values): n.op('col_'+str(j)).par.text=v
        if history_selection is not None:
            item=workflow.history[history_selection]
            title=p.op('c_history_selected_record_title')
            title.par.text='正在查看：'+item['participant']+' / '+item['condition']
            put(59,item['status']+' · 后测：'+('已收到' if item.get('posttest') else '待回执'))
            put(61,item['session_id'])
    for n in p.findChildren(type=textCOMP):
        act=n.fetch('design_action',None)
        if act:
            enabled=not workflow.pending
            if act in ('next','home'): enabled=workflow.can_close and not workflow.pending
            if act=='submit': enabled=workflow.ready and not workflow.pending
            if shell.fetch('manual_workbench',False) and act in ('submit','start','resume','posttest'):
                enabled=enabled and connected
            if act=='start': enabled=enabled and stage=='WAITING'
            if act=='posttest': enabled=enabled and stage=='CLOSEOUT' and c.get('sealed') and not c.get('posttest')
            if act in ('details','copy'): enabled=enabled and bool(workflow.current)
            if act=='open':
                item=workflow.history[history_selection] if workflow.view=='HISTORY' and history_selection is not None else c if workflow.view!='HISTORY' else {}
                enabled=bool(item.get('path'))
            if act=='export':
                item=workflow.history[history_selection] if workflow.view=='HISTORY' and history_selection is not None else c if workflow.view!='HISTORY' else {}
                enabled=bool(item.get('sealed'))
            if page=='abort' and act not in ('abort_cancel','abort_confirm'): enabled=False
            n.par.enable=enabled
            n.par.opacity=1 if enabled else .4
        x,y=n.fetch('design_xy',(-1,-1))
        if x==36 and y==674:
            n.par.text=workflow.error or ('等待确认：'+workflow.pending['action'] if workflow.pending else export_note or '已记录 '+str(capture.count)+' 条')


def onFrameStart(frame):
    _flow_frame(frame)
    render_design(time.monotonic_ns())
