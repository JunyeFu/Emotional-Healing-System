"""
TD OSC Receiver — 拖入 TD 的 Execute DAT 中运行（Monitor 模式）
接在 OSC In DAT 后面，解析 OSC 消息并执行 TD Python 命令

支持的 OSC 地址:

    /td/exec          <script>                   执行任意 TD Python 代码
    /td/par/set       <path> <par> <val> [<val2>]  设置参数值
    /td/par/get       <path> <par> [<callback>]    读取参数值（回调 OSC Out）
    /td/op/create     <parent> <type> <name>       创建算子
    /td/op/delete     <path>                       删除算子
    /td/op/select     <path>                       选中算子
    /td/pulse         <path> <par>                 触发脉冲参数
    /td/file/load     <path> <file>                加载 tox/媒体文件
    /td/project/save  [filepath]                   保存工程
    /td/quit                                      退出 TD

示例:
    /td/par/set  /project1/geo1  tx  1.5
    /td/op/create  /project1  container  my_comp
    /td/exec  app.setStep(60)

OSC 协议: UDP port 7000 → OSC In DAT → 本脚本 (Execute DAT)
"""

DERIVATIVE = "Derivative"

import json
import os


# Development mutation control is opt-in. Formal/default TD runtime remains a
# read-only monitor even if this callback DAT is accidentally present.
DEVELOPMENT_CONTROL_ENABLED = os.getenv('SRP_TD_DEV_CONTROL', '') == '1'


def onReceiveOSC(dat, rowIndex, message, data):
    """
    DatExecute.onReceiveOSC callback.
    每个 OSC 事件都会触发此函数
    """
    addr = message.address
    values = message.values

    if addr != '/td/ping' and not DEVELOPMENT_CONTROL_ENABLED:
        debug(f'[OSC] blocked development control in formal mode: {addr}')
        _send_osc('/td/error', ['DEVELOPMENT_CONTROL_DISABLED'])
        return

    try:
        if addr == '/td/exec':
            _exec(values[0])

        elif addr == '/td/par/set':
            _par_set(values)

        elif addr == '/td/par/get':
            _par_get(values)

        elif addr == '/td/op/create':
            _create(values)

        elif addr == '/td/op/delete':
            op(values[0]).destroy()

        elif addr == '/td/op/select':
            op(values[0]).current = True

        elif addr == '/td/pulse':
            _pulse(values)

        elif addr == '/td/file/load':
            _load(values)

        elif addr == '/td/project/save':
            path = values[0] if values else None
            if path:
                project.save(path)
            else:
                project.save(project.folder, saveExternalLinks=True)

        elif addr == '/td/quit':
            app.quit()

        elif addr == '/td/ping':
            _send_osc('/td/pong', [project.name, int(absTime.frame)])

        else:
            debug(f'[OSC] 未知地址: {addr}')

    except Exception as e:
        debug(f'[OSC Error] {addr}: {e}')


# ---- helpers ----

def _exec(script):
    exec(str(script), {'me': me, 'parent': parent()})


def _par_set(vals):
    path, par = vals[0], vals[1]
    rest = list(vals[2:])
    if len(rest) == 1:
        op(path).par[par] = rest[0]
    else:
        op(path).par[par] = rest


def _par_get(vals):
    val = op(vals[0]).par[vals[1]].eval()
    addr = vals[2] if len(vals) > 2 else '/td/par/value'
    _send_osc(addr, [vals[0], vals[1], val])


def _create(vals):
    parent = vals[0] if len(vals) > 0 else '/project1'
    optype = vals[1] if len(vals) > 1 else 'container'
    name = vals[2] if len(vals) > 2 else None
    if name:
        new_op = parent().create(optype, name)
    else:
        new_op = parent().create(optype)
    debug(f'[OSC] Created: {new_op.path}')


def _pulse(vals):
    op(vals[0]).par[vals[1]].pulse()


def _load(vals):
    path, filepath = vals[0], vals[1]
    op(path).loadTox(filepath)
    debug(f'[OSC] Loaded: {filepath} → {path}')


def _send_osc(address, values):
    """回调 OSC Out 给外部（如需要双向通信）"""
    osc_out = op('oscout1') if op('oscout1') else None
    if osc_out:
        osc_out.sendOSC(address, values)

    return
