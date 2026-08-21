"""
TD WebServer DAT Callbacks — 让 Claude Code 通过 HTTP 操控 TD
粘贴到 WebServer DAT 的 Callbacks 页签中即可。

API:
    GET  /                    → 工程状态
    GET  /inspect?path=/      → 递归导出节点树
    POST /exec  {"script":"..."} → 执行 Python
    POST /params/set {"path":"..","params":{...}} → 设参数
"""

import json
import os


DEVELOPMENT_CONTROL_ENABLED = os.getenv('SRP_TD_DEV_CONTROL', '') == '1'


def onHTTPRequest(webServerDat, request, response):
    if not DEVELOPMENT_CONTROL_ENABLED:
        response['statusCode'] = 403
        response['mimeType'] = 'application/json'
        response['data'] = json.dumps({'error': 'DEVELOPMENT_CONTROL_DISABLED'})
        return
    method = request.get('method', 'GET')
    uri = request.get('uri', '/')

    try:
        if method == 'GET':
            if uri == '/' or uri == '':
                info = {
                    'project': project.name,
                    'folder': project.folder,
                    'fps': project.fps,
                    'frame': absTime.frame,
                    'children': [c.name for c in root.children]
                }
                response['statusCode'] = 200
                response['mimeType'] = 'application/json'
                response['data'] = json.dumps(info, ensure_ascii=False)

            elif uri == '/inspect':
                path = request.get('pars', {}).get('path', '/')
                tgt = op(path)
                if tgt is None:
                    response['statusCode'] = 404
                    response['data'] = 'path not found'
                    return

                def tree(o, d=0):
                    r = []
                    for c in o.children:
                        node = {'n': c.name, 't': str(c.type), 'p': c.path}
                        kids = tree(c, d + 1)
                        if kids:
                            node['c'] = kids
                        r.append(node)
                    return r

                result = {'ok': True, 'path': path, 'tree': tree(tgt)}
                response['statusCode'] = 200
                response['mimeType'] = 'application/json'
                response['data'] = json.dumps(result, ensure_ascii=False)

            elif uri == '/errors':
                path = request.get('pars', {}).get('path', '/')
                tgt = op(path)
                if tgt is None:
                    response['statusCode'] = 404
                    response['data'] = 'path not found'
                    return
                errs = []
                def check(o):
                    e = o.errors()
                    if e:
                        errs.append({'p': o.path, 'e': str(e)})
                    for c in o.children:
                        check(c)
                check(tgt)
                response['statusCode'] = 200
                response['mimeType'] = 'application/json'
                response['data'] = json.dumps(errs, ensure_ascii=False)

            else:
                response['statusCode'] = 404
                response['data'] = 'not found: ' + uri

        elif method == 'POST':
            body = request.get('data', '{}')
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body) if body else {}

            if uri == '/exec':
                script = data.get('script', '')
                if not script:
                    response['statusCode'] = 400
                    response['data'] = 'missing script'
                    return
                import io as _io, sys as _sys
                _old = _sys.stdout
                _sys.stdout = _cap = _io.StringIO()
                try:
                    exec(script, {'me': me, 'parent': parent(), 'op': op,
                                  'project': project, 'root': root, 'debug': debug,
                                  'mod': mod, 'absTime': absTime})
                except Exception as e:
                    _sys.stdout = _old
                    response['statusCode'] = 500
                    response['mimeType'] = 'application/json'
                    response['data'] = json.dumps({'error': str(e)})
                    return
                _sys.stdout = _old
                response['statusCode'] = 200
                response['mimeType'] = 'application/json'
                response['data'] = json.dumps({'ok': True, 'output': _cap.getvalue()})

            elif uri == '/params/set':
                path = data.get('path', '')
                params = data.get('params', {})
                tgt = op(path)
                if tgt is None:
                    response['statusCode'] = 404
                    response['data'] = 'path not found'
                    return
                for k, v in params.items():
                    tgt.par[k] = v
                response['statusCode'] = 200
                response['mimeType'] = 'application/json'
                response['data'] = json.dumps({'ok': True})

            elif uri == '/node/create':
                p_path = data.get('parent', '/project1')
                otype = data.get('type', 'container')
                name = data.get('name')
                params = data.get('params', {})
                p = op(p_path)
                new_op = p.create(otype, name) if name else p.create(otype)
                for k, v in params.items():
                    new_op.par[k] = v
                response['statusCode'] = 200
                response['mimeType'] = 'application/json'
                response['data'] = json.dumps({'ok': True, 'path': new_op.path})

            else:
                response['statusCode'] = 404
                response['data'] = 'not found'

    except Exception as e:
        response['statusCode'] = 500
        response['mimeType'] = 'application/json'
        response['data'] = json.dumps({'error': str(e)})


debug('[WebServer] SRP Bridge ready — / /inspect /exec /params/set /node/create /errors')
