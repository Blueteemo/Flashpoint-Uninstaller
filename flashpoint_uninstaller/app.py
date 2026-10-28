"""Compact, responsive, bilingual Windows UI for Flashpoint Uninstaller 2.0.1."""
from __future__ import annotations

import queue
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import (Inspection, PartialRemovalError, SafetyError, discover_installations,
                   inspect_installation, remove_installation)
from .i18n import LANGUAGE_NAMES, detect_language, tr, translate_backend
from .shortcuts import cleanup_shortcuts

BG = '#111720'
PANEL = '#1B2530'
TEXT = '#F4F6F8'
MUTED = '#B2BCC7'
ACCENT = '#F46B60'
SUCCESS = '#9ED8B2'


def run() -> None:
    root = tk.Tk()
    root.title('Flashpoint Uninstaller 2.0.1')
    root.geometry('760x650')
    root.minsize(740, 620)
    root.configure(bg=BG)

    try:
        icon_file = Path(getattr(sys, '_MEIPASS', Path(__file__).parents[1])) / 'assets' / 'icon_v2.ico'
        if icon_file.is_file():
            root.iconbitmap(str(icon_file))
    except (OSError, tk.TclError):
        pass

    runner = Path(sys.executable if getattr(sys, 'frozen', False) else __file__)
    messages: queue.Queue[tuple[str, object]] = queue.Queue()
    language = detect_language()
    active_inspection: Inspection | None = None
    busy = False
    retry_after_failure = False
    status_key = 'status_initial'
    status_color = MUTED
    details_kind = 'initial'
    last_error = ''
    completed_removed = 0
    completed_errors = 0
    last_progress = ''

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('FP.TFrame', background=BG)
    style.configure('FP.TEntry', font=('Segoe UI', 11), padding=9)
    style.configure('FP.TButton', font=('Segoe UI', 10), padding=8)
    style.configure('FP.TCombobox', font=('Segoe UI', 10), padding=5)
    style.configure('Danger.TButton', font=('Segoe UI', 11, 'bold'), padding=12,
                    background=ACCENT, foreground=BG)
    style.map('Danger.TButton', background=[('active', '#FF877E'), ('disabled', '#495360')],
              foreground=[('disabled', '#AAB2BA')])

    frame = ttk.Frame(root, style='FP.TFrame', padding=28)
    frame.pack(fill='both', expand=True)

    top = ttk.Frame(frame, style='FP.TFrame')
    top.pack(fill='x')
    tk.Label(top, text='FLASHPOINT  /  UNINSTALLER', font=('Segoe UI', 11, 'bold'),
             fg=ACCENT, bg=BG).pack(side='left', anchor='w')
    language_box = ttk.Frame(top, style='FP.TFrame')
    language_box.pack(side='right')
    language_label = tk.Label(language_box, fg=MUTED, bg=BG, font=('Segoe UI', 9))
    language_label.pack(side='left', padx=(0, 8))
    language_var = tk.StringVar(value=LANGUAGE_NAMES[language])
    language_picker = ttk.Combobox(
        language_box, textvariable=language_var,
        values=tuple(LANGUAGE_NAMES.values()), state='readonly',
        width=12, style='FP.TCombobox')
    language_picker.pack(side='left')

    heading = tk.Label(frame, font=('Segoe UI', 25, 'bold'),
                       fg=TEXT, bg=BG, anchor='w')
    heading.pack(fill='x', pady=(12, 4))
    subtitle = tk.Label(frame, font=('Segoe UI', 11), fg=MUTED, bg=BG, anchor='w')
    subtitle.pack(fill='x', pady=(0, 18))

    path_label = tk.Label(frame, font=('Segoe UI', 10, 'bold'), fg=TEXT, bg=BG)
    path_label.pack(anchor='w', pady=(0, 7))
    path_var = tk.StringVar()
    path_row = ttk.Frame(frame, style='FP.TFrame')
    path_row.pack(fill='x')
    path_entry = ttk.Entry(path_row, textvariable=path_var, style='FP.TEntry')
    path_entry.pack(side='left', fill='x', expand=True)
    browse_btn = ttk.Button(path_row, style='FP.TButton')
    browse_btn.pack(side='left', padx=(10, 0))

    notice = tk.Label(frame, font=('Segoe UI', 10), fg=MUTED, bg=BG,
                      anchor='w', justify='left')
    notice.pack(fill='x', pady=(16, 8))

    details = tk.Text(frame, height=8, relief='flat', wrap='word', borderwidth=0,
                      bg=PANEL, fg=TEXT, font=('Consolas', 10), padx=14, pady=12)
    details.pack(fill='both', expand=True, pady=(0, 10))
    details.configure(state='disabled')

    acknowledgement = tk.BooleanVar(value=False)
    ack = tk.Checkbutton(frame, variable=acknowledgement, bg=BG, fg=TEXT,
                         selectcolor=PANEL, activebackground=BG, activeforeground=TEXT,
                         font=('Segoe UI', 10), anchor='w', justify='left', wraplength=660)
    ack.pack(fill='x', anchor='w', pady=(0, 10))

    button_row = ttk.Frame(frame, style='FP.TFrame')
    button_row.pack(fill='x')
    scan_btn = ttk.Button(button_row, style='FP.TButton')
    scan_btn.pack(side='left')
    delete_btn = ttk.Button(button_row, style='Danger.TButton', state='disabled')
    delete_btn.pack(side='right')

    footer = tk.Label(frame, font=('Segoe UI', 9), fg=MUTED, bg=BG, anchor='w')
    footer.pack(fill='x', pady=(16, 0))

    def set_details(value: str) -> None:
        details.configure(state='normal')
        details.delete('1.0', 'end')
        details.insert('1.0', value)
        details.configure(state='disabled')

    def t(key: str, **kwargs: object) -> str:
        return tr(key, language, **kwargs)

    def render_details() -> None:
        if details_kind == 'initial':
            set_details(t('details_initial'))
        elif details_kind == 'inspection' and active_inspection is not None:
            current = active_inspection
            marks = '\n'.join(f'  ✓ {marker}' for marker in current.markers)
            backups = ('\n'.join(f'  • {candidate}' for candidate in current.backup_candidates)
                       if current.backup_candidates else '  ' + t('no_backups'))
            set_details(f"{t('target')}: {current.path}\n\n"
                        f"{t('markers')}:\n{marks}\n\n"
                        f"{t('backups')}:\n{backups}\n\n"
                        + t('external_saves'))
        elif details_kind == 'error':
            set_details(translate_backend(last_error, language))
        elif details_kind == 'complete':
            set_details(t('done_details', count=completed_removed)
                        + (t('shortcuts_failed', count=completed_errors) if completed_errors else ''))

    def render_language() -> None:
        root.title(t('app_title'))
        language_label.configure(text=t('language'))
        heading.configure(text=t('heading'))
        subtitle.configure(text=t('subtitle'))
        path_label.configure(text=t('path_label'))
        browse_btn.configure(text=t('browse'))
        scan_btn.configure(text=t('inspect'))
        delete_btn.configure(text=t('uninstall'))
        ack.configure(text=t('ack'))
        footer.configure(text=t('footer'))
        if status_key == 'progress':
            notice.configure(text=translate_backend(last_progress, language), fg=status_color)
        else:
            notice.configure(text=t(status_key), fg=status_color)
        render_details()

    def change_language(_event=None) -> None:
        nonlocal language
        selected = language_var.get()
        language = 'zh' if selected == LANGUAGE_NAMES['zh'] else 'en'
        # Language changes never change the verified target or confirmations.
        render_language()

    def set_status(key: str, color: str = MUTED) -> None:
        nonlocal status_key, status_color
        status_key = key
        status_color = color
        notice.configure(text=t(key), fg=color)

    def set_controls() -> None:
        enabled = not busy
        scan_btn.configure(state='normal' if enabled else 'disabled')
        browse_btn.configure(state='normal' if enabled else 'disabled')
        path_entry.configure(state='normal' if enabled else 'disabled')
        delete_btn.configure(state='normal' if enabled and active_inspection
                             and acknowledgement.get() else 'disabled')

    def inspect() -> None:
        nonlocal active_inspection, retry_after_failure, details_kind, last_error
        retry_after_failure = False
        active_inspection = None
        acknowledgement.set(False)
        try:
            current = inspect_installation(path_var.get(), running_from=runner)
        except (SafetyError, OSError) as exc:
            last_error = str(exc)
            details_kind = 'error'
            set_status('status_bad', ACCENT)
            render_details()
            set_controls()
            return
        active_inspection = current
        details_kind = 'inspection'
        set_status('status_good', SUCCESS)
        render_details()
        set_controls()

    def browse() -> None:
        folder = filedialog.askdirectory(title=t('browse_title'))
        if folder:
            path_var.set(folder)
            inspect()

    def on_path_change(*_args) -> None:
        nonlocal active_inspection, retry_after_failure, details_kind
        retry_after_failure = False
        active_inspection = None
        details_kind = 'initial'
        acknowledgement.set(False)
        set_status('status_initial')
        render_details()
        set_controls()

    def perform() -> None:
        nonlocal busy
        current = active_inspection
        if busy or current is None or not acknowledgement.get():
            return
        if not messagebox.askyesno(
                t('confirm_title'), t('confirm_body', path=current.path),
                icon='warning'):
            return
        busy = True
        set_controls()
        set_status('status_working')

        def worker() -> None:
            try:
                remove_installation(
                    current, running_from=runner,
                    on_progress=lambda value: messages.put(('progress', value)),
                    allow_partial=retry_after_failure)
            except PartialRemovalError as exc:
                messages.put(('partial_error', str(exc)))
                return
            except (OSError, SafetyError) as exc:
                messages.put(('error', str(exc)))
                return
            try:
                removed, errors = cleanup_shortcuts(current.path)
            except Exception as exc:
                # Shortcut cleanup must not leave the GUI stuck or claim the
                # already-deleted installation is still present.
                removed, errors = [], [str(exc)]
            messages.put(('complete', (removed, errors)))

        threading.Thread(target=worker, daemon=True).start()

    def poll() -> None:
        nonlocal active_inspection, busy, retry_after_failure
        nonlocal details_kind, last_error, last_progress, completed_removed, completed_errors
        try:
            while True:
                kind, value = messages.get_nowait()
                if kind == 'progress':
                    last_progress = str(value)
                    set_status('status_working')
                    # Override only the display, not the language selection.
                    notice.configure(text=translate_backend(last_progress, language))
                    # Mark status as progress so switching language preserves it.
                    status_for_progress()
                    continue

                busy = False
                can_retry = False
                # Once the core has *proven* destructive progress, a later
                # non-destructive retry failure must not discard recovery.
                # The core still revalidates identity and safety on each retry.
                if (kind == 'partial_error' or retry_after_failure) and active_inspection is not None:
                    try:
                        st = active_inspection.path.stat()
                        can_retry = (st.st_dev, st.st_ino) == active_inspection.identity
                    except OSError:
                        pass
                retry_after_failure = can_retry
                if not can_retry:
                    active_inspection = None
                acknowledgement.set(False)
                set_controls()

                if kind in ('error', 'partial_error'):
                    last_error = str(value)
                    details_kind = 'error'
                    set_status('status_retry' if can_retry else 'status_failed', ACCENT)
                    render_details()
                    help_text = t('failed_help') + ('\n' + t('retry_help') if can_retry else '')
                    messagebox.showerror(t('failed_title'),
                                         translate_backend(value, language) + '\n\n' + help_text)
                elif kind == 'complete':
                    removed, errors = value
                    completed_removed, completed_errors = len(removed), len(errors)
                    details_kind = 'complete'
                    set_status('status_done', SUCCESS)
                    render_details()
                    messagebox.showinfo(t('done_title'), t('done_message'))
        except queue.Empty:
            pass
        root.after(100, poll)

    def status_for_progress() -> None:
        nonlocal status_key
        status_key = 'progress'

    path_var.trace_add('write', on_path_change)
    acknowledgement.trace_add('write', lambda *_: set_controls())
    browse_btn.configure(command=browse)
    scan_btn.configure(command=inspect)
    delete_btn.configure(command=perform)
    language_picker.bind('<<ComboboxSelected>>', change_language)

    render_language()
    available = discover_installations()
    if available:
        path_var.set(str(available[0]))
        inspect()
    set_controls()

    def close() -> None:
        if busy:
            messagebox.showwarning(t('busy_title'), t('busy_close'))
            return
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    root.after(100, poll)
    root.mainloop()
