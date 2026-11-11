"""MC Link — native Windows UI, fully usable offline for preparing configuration."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import Settings, check_port, load_settings, save_settings
from tunnel import Tunnel

BASE = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MC-Link'


class App:
    def __init__(self, root, data_path=None):
        self.root = root
        self.data_path = Path(data_path) if data_path else DATA / 'settings.json'
        self.tunnel = None
        self.busy = False
        self.closing = False
        self._cancel_start = threading.Event()
        self._launch_lock = threading.Lock()
        self.events = queue.Queue()
        self.vars = {k: tk.StringVar(value=str(v)) for k, v in asdict(Settings()).items()
                     if k not in ['scopes', 'system_ca']}
        self.system_ca = tk.BooleanVar()
        self.heartbeats = tk.BooleanVar(value=True)
        self.workconns = tk.BooleanVar(value=True)
        self.remember = tk.BooleanVar()
        self.exe = tk.StringVar(value=str(BASE / 'bin/frpc.exe'))
        self.status = tk.StringVar(value='未启动 · 可先保存配置，服务器以后再填')
        self.address = tk.StringVar(value='等待填写节点地址与公网端口')
        self.tls_hint = tk.StringVar()
        root.title('N4tsum3 · Java 局域网联机助手')
        root.geometry('880x830')
        root.minsize(780, 750)
        root.configure(bg='#eef3f5')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#eef3f5')
        style.configure('TLabel', background='#eef3f5', font=('Microsoft YaHei UI', 10))
        style.configure('TLabelframe', background='#eef3f5')
        style.configure('TLabelframe.Label', background='#eef3f5', font=('Microsoft YaHei UI', 10, 'bold'))
        style.configure('TButton', font=('Microsoft YaHei UI', 10), padding=(14, 9),
                        background='#ffffff', foreground='#334f55', bordercolor='#c7d7db',
                        lightcolor='#ffffff', darkcolor='#ffffff', borderwidth=1,
                        relief='flat', focusthickness=2, focuscolor='#67b5a5', anchor='center')
        style.map('TButton', background=[('disabled', '#e6edef'), ('pressed', '#d9e9e8'), ('active', '#f0f9f6')],
                  foreground=[('disabled', '#92a4a9')],
                  bordercolor=[('disabled', '#d8e2e5'), ('focus', '#389d89'), ('active', '#8ebcaf')])
        style.configure('Primary.TButton', background='#167565', foreground='#ffffff',
                        bordercolor='#167565', lightcolor='#167565', darkcolor='#167565',
                        font=('Microsoft YaHei UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('disabled', '#dce8e5'), ('pressed', '#105448'), ('active', '#1b8a77')],
                  foreground=[('disabled', '#7e9992'), ('!disabled', '#ffffff')],
                  bordercolor=[('disabled', '#dce8e5'), ('focus', '#0c4a3f'), ('!disabled', '#167565')])
        style.configure('Stop.TButton', background='#fff4f2', foreground='#ae443a', bordercolor='#e9c5bf')
        style.map('Stop.TButton', background=[('disabled', '#e6edef'), ('pressed', '#f6d4ce'), ('active', '#ffe7e2')],
                  foreground=[('disabled', '#92a4a9'), ('!disabled', '#ae443a')],
                  bordercolor=[('disabled', '#d8e2e5'), ('active', '#d88a7e')])
        style.configure('Copy.TButton', background='#e0f1eb', foreground='#155e53', bordercolor='#b8dcd0',
                        font=('Microsoft YaHei UI', 10, 'bold'))
        style.map('Copy.TButton', background=[('pressed', '#bddfd1'), ('active', '#cfe9de')],
                  bordercolor=[('focus', '#389d89'), ('active', '#82b8a7')])
        style.configure('TEntry', padding=(7, 3), bordercolor='#c7d7db', lightcolor='#ffffff',
                        darkcolor='#ffffff', fieldbackground='#ffffff', foreground='#243e44')
        style.map('TEntry', bordercolor=[('focus', '#389d89')],
                  fieldbackground=[('readonly', '#f5f9f8')])
        style.configure('TNotebook', background='#eef3f5', borderwidth=0)
        style.configure('TNotebook.Tab', font=('Microsoft YaHei UI', 10), padding=(16, 8),
                        background='#e4edef', foreground='#61757b')
        style.map('TNotebook.Tab', background=[('selected', '#ffffff'), ('active', '#edf7f3')],
                  foreground=[('selected', '#155e53'), ('active', '#155e53')])
        style.configure('TCheckbutton', background='#eef3f5', font=('Microsoft YaHei UI', 9))
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='N4tsum3', font=('Segoe UI', 26, 'bold'), foreground='#155e53').pack(anchor='w')
        ttk.Label(frame, text='把你的单人世界，连接到朋友身边。', foreground='#51616a').pack(anchor='w', pady=(0, 8))
        ttk.Label(frame, text='① 游戏内开放局域网    →    ② 填入端口并启动    →    ③ 朋友使用「直接连接」').pack(anchor='w', pady=(0, 8))

        tabs = ttk.Notebook(frame)
        tabs.pack(fill='x')
        connection = ttk.Frame(tabs, padding=6)
        security = ttk.Frame(tabs, padding=6)
        tabs.add(connection, text=' 联机配置 ')
        tabs.add(security, text=' 安全与客户端 ')
        node = ttk.LabelFrame(connection, text=' 1  中转节点（自有服务器或标准 frp 服务） ', padding=10)
        node.pack(fill='x')
        node.columnconfigure(1, weight=1)
        node.columnconfigure(3, weight=1)
        self.entry(node, '节点 IP / 域名', 'server', 0, 0)
        self.entry(node, '控制端口', 'server_port', 0, 2)
        self.entry(node, '认证 Token', 'token', 1, 0, secret=True)
        self.entry(node, '公网游戏端口', 'remote_port', 1, 2)
        self.entry(node, '玩家连接 IP / 域名', 'public_host', 2, 0)
        self.entry(node, '隧道名称', 'name', 2, 2)
        ttk.Label(node, text='玩家地址可留空，默认使用节点地址；不要填写 :端口。', foreground='#61717a', font=('Microsoft YaHei UI', 9)).grid(row=3, column=0, columnspan=4, sticky='w', pady=(5, 0))

        game = ttk.LabelFrame(connection, text=' 2  当前 MC 世界 ', padding=10)
        game.pack(fill='x', pady=10)
        game.columnconfigure(1, weight=1)
        game.columnconfigure(3, weight=1)
        self.entry(game, '本地地址', 'local_host', 0, 0)
        self.entry(game, '游戏显示的局域网端口', 'local_port', 0, 2)
        ttk.Button(game, text='检查游戏端口', command=self.check_game).grid(row=1, column=0, pady=(6, 0), sticky='w')
        ttk.Label(game, text='重新开放世界后端口可能变化；这里不是固定的 25565。', foreground='#61717a', font=('Microsoft YaHei UI', 9)).grid(row=1, column=1, columnspan=3, sticky='w')

        advanced = ttk.LabelFrame(security, text=' 3  安全与客户端 ', padding=10)
        advanced.pack(fill='x')
        advanced.columnconfigure(1, weight=1)
        ttk.Checkbutton(advanced, text='验证系统 CA', variable=self.system_ca, command=self.update_tls_hint).grid(row=0, column=0, sticky='w')
        ttk.Label(advanced, text='TLS 服务器名').grid(row=0, column=1, sticky='e')
        ttk.Entry(advanced, textvariable=self.vars['server_name'], width=24).grid(row=0, column=2, sticky='ew', padx=6)
        ttk.Label(advanced, text='可信 CA 文件').grid(row=1, column=0, sticky='w', pady=4)
        ttk.Entry(advanced, textvariable=self.vars['ca_file']).grid(row=1, column=1, columnspan=2, sticky='ew', padx=6)
        ttk.Button(advanced, text='选择 CA', command=self.choose_ca).grid(row=1, column=3)
        ttk.Label(advanced, textvariable=self.tls_hint, foreground='#8a5a14', font=('Microsoft YaHei UI', 9)).grid(row=2, column=0, columnspan=4, sticky='w')
        options = ttk.Frame(advanced)
        options.grid(row=3, column=0, columnspan=4, sticky='w', pady=4)
        ttk.Checkbutton(options, text='心跳鉴权', variable=self.heartbeats).pack(side='left')
        ttk.Checkbutton(options, text='工作连接鉴权', variable=self.workconns).pack(side='left', padx=12)
        ttk.Checkbutton(options, text='保存 Token 到本机明文配置', variable=self.remember).pack(side='left')
        ttk.Label(advanced, text='frpc 程序').grid(row=4, column=0, sticky='w')
        ttk.Entry(advanced, textvariable=self.exe).grid(row=4, column=1, columnspan=2, sticky='ew', padx=6)
        ttk.Button(advanced, text='选择程序', command=self.choose_exe).grid(row=4, column=3)

        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=10)
        self.start_button = ttk.Button(actions, text='启动联机', style='Primary.TButton', width=11, command=self.start)
        self.start_button.pack(side='left')
        self.stop_button = ttk.Button(actions, text='停止联机', style='Stop.TButton', width=9, command=self.stop, state='disabled')
        self.stop_button.pack(side='left', padx=8)
        ttk.Button(actions, text='保存设置', command=self.save).pack(side='left')
        ttk.Button(actions, text='导入配置', command=self.import_config).pack(side='right')
        ttk.Button(actions, text='导出配置', command=self.export_config).pack(side='right', padx=8)

        ttk.Label(frame, textvariable=self.status, foreground='#155e53', font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor='w')
        share = ttk.Frame(frame)
        share.pack(fill='x', pady=(5, 8))
        ttk.Entry(share, textvariable=self.address, state='readonly', font=('Consolas', 12)).pack(side='left', fill='x', expand=True)
        ttk.Button(share, text='复制联机地址', style='Copy.TButton', command=self.copy_address).pack(side='right', padx=(10, 0))
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill='both', expand=True)
        self.log = tk.Text(log_frame, height=6, bg='#182b30', fg='#d5e9e3', insertbackground='white',
                           font=('Consolas', 9), relief='flat', wrap='word', state='disabled')
        scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.log.pack(fill='both', expand=True)
        ttk.Label(frame, text='世界和助手需保持开启。隧道注册成功不等于已验证公网可达。', font=('Microsoft YaHei UI', 9), foreground='#61717a').pack(anchor='w', pady=(6, 0))
        self.load()
        self.update_tls_hint()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self._poll_id = root.after(100, self.poll)

    def entry(self, parent, label, key, row, col, secret=False):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky='w', padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=self.vars[key], show='●' if secret else '', width=22).grid(
            row=row, column=col + 1, sticky='ew', padx=(0, 14), pady=4)

    def snapshot(self):
        values = {k: var.get() if k == 'token' else var.get().strip() for k, var in self.vars.items()}
        for key in ['server_port', 'local_port', 'remote_port']:
            try:
                values[key] = int(values[key])
            except ValueError:
                raise ValueError('端口必须填写整数（MC 端口由游戏显示）')
        values['system_ca'] = self.system_ca.get()
        values['scopes'] = (['HeartBeats'] if self.heartbeats.get() else []) + (['NewWorkConns'] if self.workconns.get() else [])
        return Settings(**values)

    def apply(self, settings):
        for k, var in self.vars.items():
            var.set(str(getattr(settings, k)))
        self.system_ca.set(settings.system_ca)
        self.heartbeats.set('HeartBeats' in settings.scopes)
        self.workconns.set('NewWorkConns' in settings.scopes)
        self.update_tls_hint()

    def update_tls_hint(self):
        enabled = self.system_ca.get() or self.vars['ca_file'].get().strip()
        self.tls_hint.set('TLS 加密 + 验证节点证书' if enabled else 'TLS 加密已开启；未验证节点证书，请按服务端证书设置 CA。')

    def choose_ca(self):
        path = filedialog.askopenfilename(title='选择可信 CA 证书', filetypes=[('Certificate', '*.crt *.pem'), ('All', '*.*')])
        if path:
            self.vars['ca_file'].set(path)
            self.update_tls_hint()

    def choose_exe(self):
        path = filedialog.askopenfilename(title='选择受信任的 frpc.exe', filetypes=[('Windows executable', '*.exe')])
        if path:
            self.exe.set(path)

    def load(self):
        if not self.data_path.exists():
            return
        try:
            self.apply(load_settings(self.data_path))
            data = json.loads(self.data_path.read_text('utf-8'))
            self.remember.set(bool(data.get('_remember', False)))
            if data.get('_executable'):
                self.exe.set(data['_executable'])
        except Exception:
            self.append_log('保存的设置无法读取，已使用默认值。')

    def save(self):
        try:
            save_settings(self.data_path, self.snapshot(), self.remember.get(), self.exe.get())
            self.append_log('设置已保存。' + ('Token 已按选择保存在本机明文文件。' if self.remember.get() else '未保存 Token。'))
        except Exception as e:
            messagebox.showerror('无法保存', str(e))

    def import_config(self):
        if self.busy or (self.tunnel and self.tunnel.running):
            messagebox.showinfo('请先停止', '请先停止当前隧道，再导入新配置。')
            return
        path = filedialog.askopenfilename(title='导入单个 TCP 隧道配置', filetypes=[('TOML', '*.toml')])
        if not path:
            return
        try:
            settings = Settings.from_toml(Path(path).read_text('utf-8-sig'), Path(path).parent)
            self.apply(settings)
            self.address.set(settings.join_address())
            self.append_log('配置已导入，Token 不会自动保存。请确认玩家连接地址。')
        except Exception as e:
            messagebox.showerror('无法导入', str(e))

    def export_config(self):
        try:
            config = self.snapshot().to_toml()
            if not messagebox.askyesno('导出含认证信息', '导出的 TOML 含明文 Token，仅供自己使用。继续导出？'):
                return
            path = filedialog.asksaveasfilename(title='导出 frpc 配置', defaultextension='.toml', initialfile='frpc-minecraft.toml')
            if path:
                Path(path).write_text(config, encoding='utf-8')
                self.append_log('配置已导出；请妥善保管，勿发送给朋友。')
        except Exception as e:
            messagebox.showerror('无法导出', str(e))

    def check_game(self):
        try:
            hostname = self.vars['local_host'].get().strip()
            port = int(self.vars['local_port'].get())
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror('端口无效', '请填写游戏显示的 1–65535 局域网端口。')
            return
        self.append_log('正在检查本地游戏端口…')

        def run():
            try:
                check_port(hostname, port)
                text = '本地端口可连接（尚未验证是否为 Minecraft 或公网可达）。'
            except OSError:
                text = '本地端口不可连接：请先在游戏中开放局域网，并检查端口。'
            self.events.put(('log', text))
        threading.Thread(target=run, daemon=True).start()

    def start(self):
        if self.busy or (self.tunnel and self.tunnel.running):
            return
        try:
            settings = self.snapshot()
            settings.validate()
            exe = self.exe.get().strip()
            if not Path(exe).is_file():
                raise ValueError('找不到 frpc.exe，请选择客户端程序。')
        except Exception as e:
            messagebox.showerror('请检查配置', str(e))
            return
        self.busy = True
        self.start_button.configure(state='disabled')
        self.status.set('正在检查游戏端口…')
        self.address.set(settings.join_address())
        self.tunnel = Tunnel(exe)
        self._cancel_start.clear()

        def run():
            try:
                check_port(settings.local_host, settings.local_port)
                with self._launch_lock:
                    if self._cancel_start.is_set():
                        return
                    self.tunnel.start(settings)
            except PermissionError:
                self.events.put(('log', '系统拒绝运行 frpc。此电脑曾检测到 Defender PUA:Win32/FRProxy；请查看 Windows 安全中心记录。'))
                self.events.put(('status', '启动被系统拒绝'))
            except OSError:
                self.events.put(('log', '启动失败：请确认 MC 已开放局域网、端口正确且 frpc 程序可运行。'))
                self.events.put(('status', '启动失败'))
            except Exception:
                self.events.put(('log', '启动失败，请检查配置与客户端程序。'))
                self.events.put(('status', '启动失败'))
            finally:
                self.events.put(('idle', ''))
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        if self.busy:
            return
        self.busy = True
        self.stop_button.configure(state='disabled')
        self.status.set('正在停止…')

        def run():
            try:
                if self.tunnel:
                    self.tunnel.stop()
            finally:
                self.events.put(('idle', ''))
        threading.Thread(target=run, daemon=True).start()

    def copy_address(self):
        try:
            if self.tunnel and self.tunnel.running:
                address = self.address.get()  # Use the active session, not edited form fields.
            else:
                settings = self.snapshot()
                settings.validate()
                address = settings.join_address()
            self.root.clipboard_clear()
            self.root.clipboard_append(address)
            self.append_log('已复制联机地址。朋友在 MC「多人游戏 → 直接连接」中粘贴。')
        except Exception as e:
            messagebox.showerror('无法复制', str(e))

    def append_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        if int(self.log.index('end-1c').split('.')[0]) > 600:
            self.log.delete('1.0', '100.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def poll(self):
        for source in [self.events] + ([self.tunnel.events] if self.tunnel else []):
            for _ in range(150):
                try:
                    kind, text = source.get_nowait()
                except queue.Empty:
                    break
                if kind == 'log':
                    self.append_log(text)
                elif kind == 'status':
                    self.status.set(text)
                elif kind == 'idle':
                    self.busy = False
        running = bool(self.tunnel and self.tunnel.running)
        self.start_button.configure(state='disabled' if self.busy or running or self.closing else 'normal')
        self.stop_button.configure(state='normal' if running and not self.busy and not self.closing else 'disabled')
        if self.closing and not self.busy and not running:
            self.destroy()
            return
        if self.closing and not self.busy and running:
            self.stop()
        self._poll_id = self.root.after(100, self.poll)

    def destroy(self):
        if self._poll_id:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None
        self.root.destroy()

    def close(self):
        self.closing = True
        self._cancel_start.set()
        self.status.set('正在退出并清理隧道…')
        # DNS resolution cannot be interrupted by socket timeouts. If no launch
        # owns the gate, cancellation guarantees this worker can never spawn frpc.
        if self._launch_lock.acquire(blocking=False):
            try:
                if not self.tunnel or not self.tunnel.running:
                    self.destroy()
            finally:
                self._launch_lock.release()


def main():
    root = tk.Tk()
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            app = App(root, Path(directory) / 'settings.json')
            root.withdraw()
            root.update()
            assert app.snapshot().server_port == 7000
            root.destroy()
        Path(sys.argv[2]).write_text('PASS: packaged Tkinter runtime and application loaded', encoding='utf-8')
        return
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
