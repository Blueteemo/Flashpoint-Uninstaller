"""A compact, non-blocking Windows GUI for Flashpoint Uninstaller 2.0."""
from __future__ import annotations

import queue
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import Inspection, SafetyError, discover_installations, inspect_installation, remove_installation
from .shortcuts import cleanup_shortcuts

BG = '#111720'
PANEL = '#1B2530'
TEXT = '#F4F6F8'
MUTED = '#B2BCC7'
ACCENT = '#F46B60'


def run() -> None:
    root = tk.Tk()
    root.title('Flashpoint Uninstaller 2.0')
    root.geometry('720x600')
    root.minsize(700, 570)
    root.configure(bg=BG)
    # Bundle the same identity into both the application window and the EXE.
    try:
        icon_file = Path(getattr(sys, '_MEIPASS', Path(__file__).parents[1])) / 'assets' / 'icon_v2.ico'
        if icon_file.is_file():
            root.iconbitmap(str(icon_file))
    except (OSError, tk.TclError):
        pass
    runner = Path(sys.executable if getattr(sys, 'frozen', False) else __file__)
    messages: queue.Queue[tuple[str, object]] = queue.Queue()
    active_inspection: Inspection | None = None
    busy = False

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('FP.TFrame', background=BG)
    style.configure('FP.TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 10))
    style.configure('FP.TEntry', font=('Segoe UI', 11), padding=9)
    style.configure('FP.TButton', font=('Segoe UI', 10), padding=8)
    style.configure('Danger.TButton', font=('Segoe UI', 11, 'bold'), padding=12,
                    background=ACCENT, foreground=BG)
    style.map('Danger.TButton', background=[('active', '#FF877E'), ('disabled', '#495360')],
              foreground=[('disabled', '#AAB2BA')])

    frame = ttk.Frame(root, style='FP.TFrame', padding=28)
    frame.pack(fill='both', expand=True)

    tk.Label(frame, text='FLASHPOINT  /  UNINSTALLER', font=('Segoe UI', 11, 'bold'),
             fg=ACCENT, bg=BG).pack(anchor='w')
    tk.Label(frame, text='安全移除 Flashpoint', font=('Segoe UI', 25, 'bold'),
             fg=TEXT, bg=BG).pack(anchor='w', pady=(12, 4))
    tk.Label(frame, text='独立运行 · 识别安装目录 · 删除前确认',
             font=('Segoe UI', 11), fg=MUTED, bg=BG).pack(anchor='w', pady=(0, 18))

    tk.Label(frame, text='安装目录', font=('Segoe UI', 10, 'bold'), fg=TEXT, bg=BG).pack(anchor='w', pady=(0, 7))
    path_var = tk.StringVar()
    path_row = ttk.Frame(frame, style='FP.TFrame')
    path_row.pack(fill='x')
    path_entry = ttk.Entry(path_row, textvariable=path_var, style='FP.TEntry')
    path_entry.pack(side='left', fill='x', expand=True)
    browse_btn = ttk.Button(path_row, text='浏览…', style='FP.TButton')
    browse_btn.pack(side='left', padx=(10, 0))

    notice = tk.Label(frame, text='请先检查目标目录，确认它属于 Flashpoint。',
                      font=('Segoe UI', 10), fg=MUTED, bg=BG, anchor='w', justify='left')
    notice.pack(fill='x', pady=(16, 8))

    details = tk.Text(frame, height=8, relief='flat', wrap='word', borderwidth=0,
                      bg=PANEL, fg=TEXT, font=('Consolas', 10), padx=14, pady=12)
    details.pack(fill='both', expand=True, pady=(0, 10))
    details.insert('1.0', '检测结果会显示在这里。\n\n不会删除安装目录以外的个人文件。')
    details.configure(state='disabled')

    acknowledgement = tk.BooleanVar(value=False)
    ack = tk.Checkbutton(frame, text='我已经检查目标路径，并理解游戏数据及部分存档可能永久丢失',
                         variable=acknowledgement, bg=BG, fg=TEXT, selectcolor=PANEL,
                         activebackground=BG, activeforeground=TEXT, font=('Segoe UI', 10))
    ack.pack(anchor='w', pady=(0, 10))

    button_row = ttk.Frame(frame, style='FP.TFrame')
    button_row.pack(fill='x')
    scan_btn = ttk.Button(button_row, text='检查目录', style='FP.TButton')
    scan_btn.pack(side='left')
    delete_btn = ttk.Button(button_row, text='卸载 Flashpoint', style='Danger.TButton', state='disabled')
    delete_btn.pack(side='right')

    tk.Label(frame, text='只处理已验证的安装目录；建议先备份收藏、播放列表和存档。',
             font=('Segoe UI', 9), fg=MUTED, bg=BG).pack(anchor='w', pady=(16, 0))

    def show_details(text: str) -> None:
        details.configure(state='normal')
        details.delete('1.0', 'end')
        details.insert('1.0', text)
        details.configure(state='disabled')

    def set_controls() -> None:
        enabled = not busy
        scan_btn.configure(state='normal' if enabled else 'disabled')
        browse_btn.configure(state='normal' if enabled else 'disabled')
        path_entry.configure(state='normal' if enabled else 'disabled')
        delete_btn.configure(state='normal' if enabled and active_inspection and acknowledgement.get() else 'disabled')

    def inspect() -> None:
        nonlocal active_inspection
        active_inspection = None
        acknowledgement.set(False)
        try:
            current = inspect_installation(path_var.get(), running_from=runner)
        except (SafetyError, OSError) as exc:
            notice.config(text='无法通过安全检查', fg=ACCENT)
            show_details(str(exc))
            set_controls()
            return
        active_inspection = current
        notice.config(text='已识别 Flashpoint 安装目录', fg='#9ED8B2')
        marks = '\n'.join(f'  ✓ {x}' for x in current.markers)
        backups = ('\n'.join(f'  • {x}' for x in current.backup_candidates)
                   if current.backup_candidates else '  未在常见位置发现数据目录；不代表没有存档。')
        show_details(f'目标：{current.path}\n\n识别依据：\n{marks}\n\n可能值得备份：\n{backups}\n\n'
                     '注意：部分游戏存档位于安装目录以外，不会由本工具清理。')
        set_controls()

    def browse() -> None:
        folder = filedialog.askdirectory(title='选择 Flashpoint 的主目录')
        if folder:
            path_var.set(folder)
            inspect()

    def on_path_change(*_args) -> None:
        nonlocal active_inspection
        active_inspection = None
        acknowledgement.set(False)
        set_controls()

    def perform() -> None:
        nonlocal busy
        current = active_inspection
        if busy or current is None or not acknowledgement.get():
            return
        if not messagebox.askyesno('最终确认',
            f'将永久删除以下目录的全部内容：\n\n{current.path}\n\n'
            '此操作不可撤销，可能包含已下载游戏、收藏和存档。\n\n确定继续？', icon='warning'):
            return
        busy = True
        set_controls()
        notice.config(text='正在删除，请不要关闭程序……', fg=MUTED)
        def worker() -> None:
            try:
                remove_installation(current, running_from=runner,
                                    on_progress=lambda s: messages.put(('progress', s)))
            except (OSError, SafetyError) as exc:
                messages.put(('error', str(exc)))
                return
            try:
                removed, errors = cleanup_shortcuts(current.path)
            except Exception as exc:
                # Deletion already succeeded; an optional shortcut failure must
                # never strand the GUI in its busy state.
                removed, errors = [], [f'快捷方式清理异常：{exc}']
            messages.put(('complete', (removed, errors)))
        threading.Thread(target=worker, daemon=True).start()

    def poll() -> None:
        nonlocal active_inspection, busy
        try:
            while True:
                kind, value = messages.get_nowait()
                if kind == 'progress':
                    notice.config(text=str(value), fg=MUTED)
                else:
                    busy = False
                    active_inspection = None
                    acknowledgement.set(False)
                    set_controls()
                    if kind == 'error':
                        notice.config(text='移除未完成', fg=ACCENT)
                        messagebox.showerror('操作失败', f'{value}\n\n请确认程序已关闭、权限足够。')
                    elif kind == 'complete':
                        removed, errors = value
                        notice.config(text='安装目录已删除', fg='#9ED8B2')
                        show_details(f'已删除安装目录。\n已清理 {len(removed)} 个经过目标验证的快捷方式。'
                                     + (f'\n快捷方式处理失败：{len(errors)} 个' if errors else ''))
                        messagebox.showinfo('完成', 'Flashpoint 安装目录已删除。')
        except queue.Empty:
            pass
        root.after(100, poll)

    path_var.trace_add('write', on_path_change)
    acknowledgement.trace_add('write', lambda *_: set_controls())
    browse_btn.configure(command=browse)
    scan_btn.configure(command=inspect)
    delete_btn.configure(command=perform)
    available = discover_installations()
    if available:
        path_var.set(str(available[0]))
        inspect()
    set_controls()
    def close() -> None:
        if busy:
            messagebox.showwarning('正在卸载', '删除操作尚未结束，请勿关闭窗口。')
            return
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    root.after(100, poll)
    root.mainloop()
