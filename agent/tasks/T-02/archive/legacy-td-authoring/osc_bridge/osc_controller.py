"""
OSC Remote Controller — 外部 Python 脚本，远程操控 TouchDesigner

用法:
    python osc_controller.py ping                        测试连接
    python osc_controller.py exec "app.setStep(60)"      执行 TD Python 代码
    python osc_controller.py par /project1/some_op tx 1.5  设置参数
    python osc_controller.py create /project1 container my_comp  创建算子
    python osc_controller.py load /project1 path/tox/file.tox     加载文件

    # 互动模式
    python osc_controller.py

配置: 修改 TD_HOST / TD_PORT（默认 localhost:7000）

TD 侧前置条件:
    1. 拖入 OSC In DAT → port 7000
    2. 拖入 Execute DAT → 加载 td_osc_receiver.py → Monitor 模式
    3. OSC In DAT 名字改为 oscin1，Execute DAT 会收到回调
"""

import argparse
import json
try:
    import readline  # noqa: enables raw_input() line editing (unix)
except ImportError:
    try:
        import pyreadline3 as readline  # noqa: Windows fallback
    except ImportError:
        pass  # raw input without readline is fine
import sys

from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder

TD_HOST = '127.0.0.1'
TD_PORT = 7000


def build_msg(addr, *values):
    m = OscMessageBuilder(address=addr)
    for v in values:
        m.add_arg(v)
    return m.build()


def send(client, addr, *values):
    msg = build_msg(addr, *values)
    client.send(msg)
    print(f'  → {addr} {values}')


class Controller:
    """TD OSC 遥控器"""

    def __init__(self, host=TD_HOST, port=TD_PORT):
        self.client = udp_client.SimpleUDPClient(host, port)

    def ping(self):
        send(self.client, '/td/ping')

    def exec(self, script):
        send(self.client, '/td/exec', script)

    def par(self, path, par, value):
        send(self.client, '/td/par/set', path, par, value)

    def par_get(self, path, par):
        send(self.client, '/td/par/get', path, par, '/td/par/value')

    def create(self, parent, optype, name=''):
        send(self.client, '/td/op/create', parent, optype, name)

    def delete(self, path):
        send(self.client, '/td/op/delete', path)

    def pulse(self, path, par):
        send(self.client, '/td/pulse', path, par)

    def load(self, path, filepath):
        send(self.client, '/td/file/load', path, filepath)

    def save(self, path=''):
        send(self.client, '/td/project/save', path)

    def quit(self):
        send(self.client, '/td/quit')

    # --- SRP 专属快捷方法 ---

    def setup_srp_skeleton(self):
        """一键搭建 SRP 工程骨架:
        /project1
        ├── udp_in       (OSC In DAT → renamed)
        ├── monitor      (Container)
        │   ├── breath_circle  (Container)
        │   ├── prompt_display (Container)
        │   └── dashboard      (Container)
        ├── weather_viz  (Container)
        └── data_curve   (Container)
        """
        print('搭建 SRP 工程骨架...')
        p = '/project1'
        # 清理旧节点
        for name in ('udp_in', 'monitor', 'weather_viz', 'data_curve'):
            try:
                self.delete(f'{p}/{name}')
            except Exception:
                pass

        # UDP 接收
        self.create(p, 'dat', 'udp_in')

        # 三大容器
        self.create(p, 'container', 'monitor')
        self.create(f'{p}/monitor', 'container', 'breath_circle')
        self.create(f'{p}/monitor', 'container', 'prompt_display')
        self.create(f'{p}/monitor', 'container', 'dashboard')

        self.create(p, 'container', 'weather_viz')
        self.create(p, 'container', 'data_curve')

        print('Skeleton built OK')

    def setup_osc_receiver(self):
        """搭建 OSC 接收链: OSC In DAT → Execute DAT"""
        p = '/project1'
        self.create(p, 'oscin', 'oscin1')
        self.create(p, 'executeDAT', 'exec_osc')
        self.par(f'{p}/oscin1', 'port', TD_PORT)
        print('OSC receiver chain OK -> load td_osc_receiver.py into exec_osc')


# ---- CLI ----

def interactive(ctrl):
    print('TD OSC Controller — 输入 help 查看命令, quit 退出\n')
    while True:
        try:
            cmd = input('osc> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd == 'quit':
            break
        parts = cmd.split(maxsplit=2)
        action = parts[0]

        try:
            if action == 'help':
                print("""
命令列表:
  ping                             测试连通性
  exec <script>                    执行 TD Python
  par <path> <param> <val>         设置参数
  get  <path> <param>              读取参数
  create <parent> <type> [name]    创建算子
  delete <path>                    删除算子
  pulse <path> <par>               触发脉冲
  load <path> <file>               加载tox文件
  save [path]                      保存工程
  srp                              一键搭建 SRP 工程骨架
  osc                              搭建 OSC 接收链
  quit                             退出
""")
            elif action == 'ping':
                ctrl.ping()
            elif action == 'exec':
                ctrl.exec(parts[2])
            elif action == 'par' and len(parts) > 2:
                args = parts[2].split(maxsplit=2)
                if len(args) == 3:
                    # auto-convert numeric values
                    try:
                        val = float(args[2])
                        if val == int(val):
                            val = int(val)
                    except ValueError:
                        val = args[2]
                    ctrl.par(args[0], args[1], val)
            elif action == 'get':
                args = parts[2].split(maxsplit=1)
                ctrl.par_get(args[0], args[1])
            elif action == 'create':
                args = parts[2].split(maxsplit=2)
                ctrl.create(*args)
            elif action == 'delete':
                ctrl.delete(parts[2])
            elif action == 'pulse':
                args = parts[2].split(maxsplit=1)
                ctrl.pulse(args[0], args[1])
            elif action == 'load':
                args = parts[2].split(maxsplit=1)
                ctrl.load(args[0], args[1])
            elif action == 'srp':
                ctrl.setup_srp_skeleton()
            elif action == 'osc':
                ctrl.setup_osc_receiver()
            elif action == 'save':
                ctrl.save(parts[2] if len(parts) > 2 else '')
            elif action == 'quit':
                break
            else:
                print(f'  未知命令: {cmd}')
        except Exception as e:
            print(f'  Error: {e}')
    print('退出.')


def main():
    parser = argparse.ArgumentParser(description='TD OSC Remote Controller')
    parser.add_argument('--host', default=TD_HOST, help=f'TouchDesigner host (default: {TD_HOST})')
    parser.add_argument('--port', type=int, default=TD_PORT, help=f'OSC port (default: {TD_PORT})')
    sub = parser.add_subparsers(dest='cmd')

    sub.add_parser('ping', help='测试连接')
    e = sub.add_parser('exec', help='执行 TD Python')
    e.add_argument('script', help='Python 代码字符串')
    p = sub.add_parser('par', help='设置参数')
    p.add_argument('path', help='算子路径')
    p.add_argument('param', help='参数名')
    p.add_argument('value', help='参数值')
    c = sub.add_parser('create', help='创建算子')
    c.add_argument('parent', help='父节点路径')
    c.add_argument('type', help='算子类型名')
    c.add_argument('name', nargs='?', default='', help='可选名称')
    d = sub.add_parser('delete', help='删除算子')
    d.add_argument('path', help='算子路径')
    lo = sub.add_parser('load', help='加载 tox 文件')
    lo.add_argument('path', help='算子路径')
    lo.add_argument('file', help='tox 文件路径')
    sub.add_parser('srp', help='一键搭建 SRP 骨架')
    sub.add_parser('osc_setup', help='搭建 OSC 接收链')

    args = parser.parse_args()
    ctrl = Controller(args.host, args.port)

    if args.cmd == 'ping':
        ctrl.ping()
    elif args.cmd == 'exec':
        ctrl.exec(args.script)
    elif args.cmd == 'par':
        try:
            val = float(args.value)
            if val == int(val):
                val = int(val)
        except ValueError:
            val = args.value
        ctrl.par(args.path, args.param, val)
    elif args.cmd == 'create':
        ctrl.create(args.parent, args.type, args.name)
    elif args.cmd == 'delete':
        ctrl.delete(args.path)
    elif args.cmd == 'load':
        ctrl.load(args.path, args.file)
    elif args.cmd == 'srp':
        ctrl.setup_srp_skeleton()
    elif args.cmd == 'osc_setup':
        ctrl.setup_osc_receiver()
    else:
        interactive(ctrl)


if __name__ == '__main__':
    main()
