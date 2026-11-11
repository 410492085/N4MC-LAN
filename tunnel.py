"""Own exactly one frpc child; never scan or kill other processes."""
import json
from pathlib import Path
import queue
import re
import subprocess
import tempfile
import threading


def redact(text, secret):
    secrets = [secret] if isinstance(secret, str) else list(secret or [])
    variants = []
    for item in secrets:
        if not item: continue
        variants += [item, json.dumps(item, ensure_ascii=False)[1:-1],
                     json.dumps(item, ensure_ascii=True)[1:-1]]
        # Line-based process output may split a multiline token.
        variants += [x for x in item.splitlines() if x]
    for value in sorted(set(variants), key=len, reverse=True):
        text = text.replace(value, '***')
    return re.sub(r'(?i)((?:token|secretKey|privilege_key|privilegeKey|authorization)\s*[=:]\s*)\S+', r'\1***', text)


class Tunnel:
    def __init__(self, executable, prefix_args=None):
        self.executable = str(Path(executable).resolve())
        self.prefix_args = prefix_args or []
        self.events = queue.Queue(maxsize=1000)
        self._lock = threading.RLock()
        self._process = None
        self._thread = None
        self._stopping = False
        self.config_path = None

    @property
    def running(self):
        with self._lock:
            return self._process is not None

    def emit(self, kind, text):
        try:
            self.events.put_nowait((kind, text))
        except queue.Full:
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            try:
                self.events.put_nowait((kind, text))
            except queue.Full:
                pass

    def start(self, settings):
        config = settings.to_toml()
        with self._lock:
            if self._process is not None:
                raise RuntimeError('隧道已经启动，请先停止')
            if not Path(self.executable).is_file():
                raise ValueError('找不到 frpc.exe，请重新选择')
            temp = tempfile.TemporaryDirectory(prefix='mc-link-')
            self.config_path = Path(temp.name) / 'frpc.toml'
            self.config_path.write_text(config, encoding='utf-8')
            try:
                self._process = subprocess.Popen(
                    [self.executable, *self.prefix_args, '-c', str(self.config_path)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                    text=True, encoding='utf-8', errors='replace',
                )
            except Exception:
                temp.cleanup()
                self._process = None
                raise
            self._stopping = False
            self.emit('status', '连接中')
            self._thread = threading.Thread(target=self._read, args=(self._process, temp, (settings.token, settings.room_secret)), daemon=True)
            self._thread.start()

    def _read(self, process, temp, secret):
        try:
            for line in process.stdout:
                safe = redact(line.rstrip(), secret)
                self.emit('log', safe)
                if 'start proxy success' in line:
                    self.emit('status', '隧道已注册（未验证公网可达）')
                elif 'start visitor success' in line:
                    self.emit('status', '本地加入入口已就绪（尚未验证房主连接）')
                elif 'login to server success' in line:
                    self.emit('status', '节点已连接，等待隧道注册')
                elif any(x in line for x in ['start error', 'login to server failed', 'connect to server error']):
                    self.emit('status', '连接失败或重试中，请查看日志')
            code = process.wait()
        finally:
            process.stdout.close()
            try:
                temp.cleanup()
            finally:
                with self._lock:
                    stopped = self._stopping
                    self._process = None
                self.emit('status', '已停止' if stopped else f'进程已退出（代码 {process.returncode}）')

    def stop(self):
        with self._lock:
            process = self._process
            thread = self._thread
            self._stopping = True
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=4)
            except ProcessLookupError:
                pass
        if thread and thread is not threading.current_thread():
            thread.join(timeout=5)
