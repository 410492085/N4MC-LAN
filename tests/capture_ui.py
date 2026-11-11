"""Capture only this app's client area for visual QA on Windows."""
import subprocess
import sys
from pathlib import Path
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import App

root = tk.Tk()
app = App(root, ROOT / 'build/preview-no-settings.json')
root.geometry('880x830+20+20')
root.attributes('-topmost', True)
root.update()


def capture():
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    out = str(ROOT / 'build/N4tsum3-preview.png').replace("'", "''")
    script = ("Add-Type -AssemblyName System.Drawing; "
              f'$bmp = New-Object System.Drawing.Bitmap({w},{h}); '
              '$g = [System.Drawing.Graphics]::FromImage($bmp); '
              f'$g.CopyFromScreen({x},{y},0,0,$bmp.Size); '
              f"$bmp.Save('{out}',[System.Drawing.Imaging.ImageFormat]::Png); "
              '$g.Dispose(); $bmp.Dispose()')
    subprocess.run(['powershell', '-NoProfile', '-Command', script], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    assert root.title().startswith('N4tsum3')
    app.destroy()


root.after(700, capture)
root.mainloop()
