"""
OSC In DAT Callbacks — 接收外部 OSC 命令操控 TD
放到 Text DAT 中，然后将 OSC In DAT 的 Callbacks DAT 指向它

支持的 OSC 地址:
    /td/ping          → 通过 OSC Out 回复 pong
    /td/exec <code>   → 执行 Python 代码
    /td/par/set <path> <par> <val> → 设参数
"""

import os


DEVELOPMENT_CONTROL_ENABLED = os.getenv('SRP_TD_DEV_CONTROL', '') == '1'

def onReceiveOSC(dat, rowIndex, message, byteData, timeStamp, address, args, peer):
    if address == '/td/ping':
        _send_osc('/td/pong', [project.name, int(absTime.frame)])
        debug('[OSC] ping -> pong')

    elif not DEVELOPMENT_CONTROL_ENABLED:
        _send_osc('/td/error', ['DEVELOPMENT_CONTROL_DISABLED'])
        debug(f'[OSC] blocked development control in formal mode: {address}')

    elif address == '/td/exec':
        if args:
            try:
                exec(str(args[0]), {
                    'me': dat, 'op': op, 'project': project,
                    'root': root, 'debug': debug, 'parent': dat.parent
                })
                _send_osc('/td/ok', ['exec done'])
            except Exception as e:
                _send_osc('/td/error', [str(e)])
                debug(f'[OSC] exec error: {e}')

    elif address == '/td/par/set':
        if len(args) >= 3:
            try:
                path, par, val = args[0], args[1], args[2]
                op(path).par[par] = val
                _send_osc('/td/ok', [f'{path}.{par}={val}'])
            except Exception as e:
                _send_osc('/td/error', [str(e)])

    elif address == '/td/inspect':
        # Write full node tree to file
        path = args[0] if args else '/'
        try:
            tgt = op(path)
            import json
            def tree(o, d=0):
                r = []
                for c in o.children:
                    node = {'n': c.name, 't': str(c.type), 'p': c.path}
                    kids = tree(c, d+1)
                    if kids:
                        node['c'] = kids
                    r.append(node)
                return r
            result = {'project': project.name, 'path': path, 'tree': tree(tgt)}
            out = project.folder + '/_td_inspect.json'
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            _send_osc('/td/ok', [f'inspect written to {out}'])
        except Exception as e:
            _send_osc('/td/error', [str(e)])

    else:
        debug(f'[OSC] unknown: {address} {args}')


def _send_osc(addr, vals):
    oscout = op('oscout1')
    if oscout and oscout.valid:
        oscout.sendOSC(addr, vals)

debug('[OSC Callbacks] SRP OSC Bridge ready')
