# ===== 强制以管理员权限运行（必须最前面）=====
import ctypes, sys, os
def run_as_admin():
    if ctypes.windll.shell32.IsUserAnAdmin(): return True
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    except: pass
    return False
if not run_as_admin(): sys.exit()
# ==========================================

import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import winsound

# 高 DPI 适配
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    ctypes.windll.user32.SetProcessDPIAware()

FLASHPOINT_PATH = r"C:\Flashpoint"
SOUND_FILE = r"C:\Windows\Media\Windows Logon.wav"

def nuke():
    if not os.path.exists(FLASHPOINT_PATH):
        messagebox.showinfo("提示", "C:\\Flashpoint 已经不存在啦～")
        return

    if not messagebox.askyesno("确认", f"即将永久删除：\n{FLASHPOINT_PATH}\n\n确定吗？", icon="warning"):
        return

    status.config(text="删除中，请稍等……")
    root.update_idletasks()

    try:
        shutil.rmtree(FLASHPOINT_PATH)
    except Exception as e:
        status.config(text="删除失败")
        messagebox.showerror("失败", f"删除失败：\n{e}\n\n可能有文件被占用，请关闭 Flashpoint 后再试")
        return

    # 删除快捷方式
    for p in [os.path.expanduser("~/Desktop"),
              os.path.join(os.environ.get("APPDATA",""), "Microsoft\\Windows\\Start Menu\\Programs")]:
        try:
            for f in os.listdir(p):
                if "Flashpoint" in f and f.lower().endswith(('.lnk','.url')):
                    os.remove(os.path.join(p,f))
        except: pass

    # 播放提示音 + 更新界面
    try:
        winsound.PlaySound(SOUND_FILE, winsound.SND_ASYNC)
    except:
        pass

    status.config(text="已彻底删除干净！")
    btn.config(state="disabled", text="已完成")
    messagebox.showinfo("成功", "Flashpoint 已成功卸载！")

# GUI —— 100% 保留你原来的文字和布局
root = tk.Tk()
root.title("Flashpoint 卸载器")
root.geometry("560x380")
root.resizable(False, False)
root.configure(bg="#0d1117")

style = ttk.Style()
style.theme_use('clam')

# 强化红按钮样式，保证白字永远可见
style.configure("BigRed.TButton",
                font=("微软雅黑", 16, "bold"),
                padding=20,
                background="#ff2222",
                foreground="white")
style.map("BigRed.TButton",
          background=[('active', '#ff4444')],
          foreground=[('active', 'white')])

ttk.Label(root, text="Flashpoint 一键卸载", font=("微软雅黑", 22, "bold"),
          foreground="#ff4444", background="#0d1117").pack(pady=25)
ttk.Label(root, text="目标：", font=("Consolas",12), foreground="#ccc", background="#0d1117").pack()
ttk.Label(root, text=FLASHPOINT_PATH, font=("Consolas",14,"bold"), foreground="#00ff88", background="#0d1117").pack(pady=8)

status = ttk.Label(root, text="已获取管理员权限，准备就绪", font=("微软雅黑",11), foreground="#ffff66", background="#0d1117")
status.pack(pady=30)   # 原来进度条的位置空出来多一点呼吸感

btn = ttk.Button(root, text="一键彻底删除 Flashpoint", style="BigRed.TButton", command=nuke)
btn.pack(pady=20)

root.mainloop()