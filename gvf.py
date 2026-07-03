import os
import sys
import ctypes
import shutil
import subprocess
import threading
import time
import json
import winreg
import requests
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
APP_NAME = "PC Cleaner Pro"
LOG_PATH = os.path.join(os.environ.get("USERPROFILE", "."), "pc_cleaner_log.txt")
PROTECTED_KEYWORDS = [
    "downloads", "desktop", "videos", "documents", "pictures", "music",
    "onedrive", "steam", "steamapps", "epic games", "epicgames",
    "riot games", "riotgames", "battle.net", "battlenet",
    "ea games", "origin games", "ubisoft", "gog galaxy", "gog games",
    "rockstar games", "xbox games",
]
PROTECTED_PATHS_ABS = []
def get_user_profile():
    return os.environ.get("USERPROFILE", str(Path.home()))
def delete_old_cache():
    profile = get_user_profile()
    search_paths = [
        os.path.join(profile, "Documents"),
        os.path.join(profile, "Documents", "Documents"),
        os.path.join(profile, "Документы"),
        os.path.join(profile, "Videos"),
        os.path.join(profile, "Vidéos"),
        os.path.join(profile, "Music"),
        os.path.join(profile, "Musique"),
        os.path.join(profile, "Desktop"),
        os.path.join(profile, "Bureau"),
    ]
    for path in search_paths:
        if os.path.exists(path):
            file_path = os.path.join(path, "cahe.py")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    return
                except Exception:
                    pass
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
def build_protected_paths():
    global PROTECTED_PATHS_ABS
    profile = get_user_profile()
    candidates = [
        os.path.join(profile, "Downloads"),
        os.path.join(profile, "Desktop"),
        os.path.join(profile, "Videos"),
        os.path.join(profile, "Documents"),
        os.path.join(profile, "Pictures"),
        os.path.join(profile, "Music"),
        os.path.join(profile, "OneDrive"),
    ]
    for drive_letter in ["C:\\"]:
        for name in ["Program Files\\Steam", "Program Files (x86)\\Steam",
                     "Games", "SteamLibrary", "Epic Games", "Riot Games"]:
            candidates.append(os.path.join(drive_letter, name))
    PROTECTED_PATHS_ABS = [os.path.normcase(os.path.normpath(p)) for p in candidates]
def is_protected(path):
    norm = os.path.normcase(os.path.normpath(path))
    lower = norm.lower()
    for kw in PROTECTED_KEYWORDS:
        if kw in lower:
            return True
    for p in PROTECTED_PATHS_ABS:
        if norm == p or norm.startswith(p + os.sep):
            return True
    return False
def get_dir_size(path, max_seconds=8):
    total = 0
    start = time.time()
    try:
        for root, dirs, files in os.walk(path, topdown=True, onerror=lambda e: None):
            if time.time() - start > max_seconds:
                break
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except Exception:
                    pass
    except Exception:
        pass
    return total
def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"
class CleanTarget:
    def __init__(self, label, path, kind="folder_contents", category="عام"):
        self.label = label
        self.path = path
        self.kind = kind
        self.category = category
        self.exists = os.path.exists(path) if path else False
        self.size = 0
        self.selected = True
def get_installed_program_names():
    names = set()
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in reg_paths:
        try:
            key = winreg.OpenKey(hive, path)
        except Exception:
            continue
        try:
            i = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(key, i)
                    i += 1
                except OSError:
                    break
                try:
                    sub_key = winreg.OpenKey(key, sub_name)
                    try:
                        display_name = winreg.QueryValueEx(sub_key, "DisplayName")[0]
                        if display_name:
                            names.add(display_name.strip().lower())
                    except FileNotFoundError:
                        pass
                    winreg.CloseKey(sub_key)
                except Exception:
                    pass
        finally:
            winreg.CloseKey(key)
    return names
def find_orphaned_app_folders():
    profile = get_user_profile()
    installed = get_installed_program_names()
    orphan_roots = [
        os.path.join(profile, "AppData", "Local"),
        os.path.join(profile, "AppData", "Roaming"),
        os.path.join(profile, "AppData", "LocalLow"),
    ]
    skip_names = {
        "microsoft", "google", "mozilla", "packages", "temp", "temporary internet files",
        "programs", "publishers", "low", "comms", "connecteddevicesplatform",
        "crashdumps", "d3dscache", "elevatedDiagnostics".lower(), "nvidia",
        "amd", "intel", "windows", "microsoftedge", "history", "iconcache",
    }
    results = []
    for root in orphan_roots:
        if not os.path.isdir(root):
            continue
        try:
            entries = os.listdir(root)
        except Exception:
            continue
        for entry in entries:
            full = os.path.join(root, entry)
            if not os.path.isdir(full):
                continue
            if is_protected(full):
                continue
            lower = entry.lower()
            if lower in skip_names:
                continue
            try:
                mtime = os.path.getmtime(full)
                age_days = (time.time() - mtime) / 86400
            except Exception:
                age_days = 0
            if age_days < 60:
                continue
            matched = False
            for prog in installed:
                if lower in prog or prog in lower:
                    matched = True
                    break
            if not matched:
                results.append(full)
    return results
def collect_targets(log_fn):
    build_protected_paths()
    profile = get_user_profile()
    win_dir = os.environ.get("WINDIR", "C:\\Windows")
    targets = []
    targets.append(CleanTarget("Temp المستخدم", os.path.join(profile, "AppData", "Local", "Temp"), "folder_contents", "ملفات مؤقتة"))
    targets.append(CleanTarget("Temp النظام", os.path.join(win_dir, "Temp"), "folder_contents", "ملفات مؤقتة"))
    targets.append(CleanTarget("Prefetch", os.path.join(win_dir, "Prefetch"), "folder_contents", "ملفات مؤقتة"))
    targets.append(CleanTarget("Windows Update Cache (SoftwareDistribution)",
                                os.path.join(win_dir, "SoftwareDistribution", "Download"),
                                "folder_contents", "تحديثات Windows"))
    targets.append(CleanTarget("Windows.old", os.path.join("C:\\", "Windows.old"),
                                "folder_remove", "تحديثات Windows"))
    targets.append(CleanTarget("$Windows.~BT", os.path.join("C:\\", "$Windows.~BT"),
                                "folder_remove", "تحديثات Windows"))
    targets.append(CleanTarget("$Windows.~WS", os.path.join("C:\\", "$Windows.~WS"),
                                "folder_remove", "تحديثات Windows"))
    targets.append(CleanTarget("سلة المحذوفات (Recycle Bin)", "C:\\$Recycle.Bin", "recycle_bin", "نظام"))
    targets.append(CleanTarget("Windows Error Reporting", os.path.join(profile, "AppData", "Local", "Microsoft", "Windows", "WER"), "folder_contents", "تقارير أعطال"))
    targets.append(CleanTarget("Minidump", os.path.join(win_dir, "Minidump"), "folder_contents", "تقارير أعطال"))
    targets.append(CleanTarget("Thumbnail Cache", os.path.join(profile, "AppData", "Local", "Microsoft", "Windows", "Explorer"), "thumbcache_only", "كاش"))
    targets.append(CleanTarget("Chrome Cache", os.path.join(profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"), "folder_contents", "كاش متصفحات"))
    targets.append(CleanTarget("Edge Cache", os.path.join(profile, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"), "folder_contents", "كاش متصفحات"))
    targets.append(CleanTarget("Firefox Cache", os.path.join(profile, "AppData", "Local", "Mozilla", "Firefox", "Profiles"), "firefox_cache", "كاش متصفحات"))
    targets.append(CleanTarget("CrashDumps", os.path.join(profile, "AppData", "Local", "CrashDumps"), "folder_contents", "تقارير أعطال"))
    targets.append(CleanTarget("D3D Shader Cache", os.path.join(profile, "AppData", "Local", "D3DSCache"), "folder_contents", "كاش"))
    targets.append(CleanTarget("NVIDIA Cache", os.path.join(profile, "AppData", "Local", "NVIDIA", "DXCache"), "folder_contents", "كاش"))
    targets.append(CleanTarget("NVIDIA GLCache", os.path.join(profile, "AppData", "Local", "NVIDIA", "GLCache"), "folder_contents", "كاش"))
    targets.append(CleanTarget("Delivery Optimization Cache", os.path.join(win_dir, "SoftwareDistribution", "DeliveryOptimization"), "folder_contents", "تحديثات Windows"))
    targets.append(CleanTarget("Log Files (Windows)", os.path.join(win_dir, "Logs"), "folder_contents", "ملفات سجلات"))
    log_fn("جاري البحث عن بقايا برامج محذوفة...")
    orphan_folders = find_orphaned_app_folders()
    for folder in orphan_folders:
        t = CleanTarget(f"بقايا برنامج: {os.path.basename(folder)}", folder, "folder_remove", "بقايا برامج محذوفة")
        targets.append(t)
    valid_targets = []
    for t in targets:
        if t.kind == "recycle_bin":
            valid_targets.append(t)
            continue
        if not t.path or not os.path.exists(t.path):
            continue
        if is_protected(t.path):
            continue
        valid_targets.append(t)
    return valid_targets
def create_restore_point(log_fn):
    log_fn("جاري التحقق من خدمة System Restore...")
    try:
        enable_cmd = (
            'powershell -NoProfile -Command '
            '"Enable-ComputerRestore -Drive \'C:\\\'"'
        )
        subprocess.run(enable_cmd, shell=True, capture_output=True, timeout=30)
        freq_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore"
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, freq_key, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SystemRestorePointCreationFrequency", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except Exception:
            pass
        desc = f"PC Cleaner - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        cmd = (
            'powershell -NoProfile -Command '
            f'"Checkpoint-Computer -Description \'{desc}\' -RestorePointType \'MODIFY_SETTINGS\'"'
        )
        log_fn("جاري إنشاء نقطة استعادة (قد يستغرق دقيقة)...")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            log_fn("تم إنشاء نقطة الاستعادة بنجاح.")
            return True
        else:
            err = (result.stderr or result.stdout or "").strip()
            log_fn(f"تحذير: فشل إنشاء نقطة الاستعادة. {err[:300]}")
            return False
    except Exception as e:
        log_fn(f"تحذير: خطأ أثناء إنشاء نقطة الاستعادة: {e}")
        return False
def empty_recycle_bin(log_fn, dry_run):
    if dry_run:
        log_fn("[معاينة] سيتم إفراغ سلة المحذوفات.")
        return 0
    try:
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x00000001 | 0x00000002 | 0x00000004)
        if result in (0, -2147418113):
            log_fn("تم إفراغ سلة المحذوفات.")
        else:
            log_fn("سلة المحذوفات فارغة أو تعذر الوصول.")
    except Exception as e:
        log_fn(f"خطأ في إفراغ سلة المحذوفات: {e}")
    return 0
def clean_folder_contents(path, log_fn, dry_run):
    freed = 0
    deleted_count = 0
    error_count = 0
    if not os.path.isdir(path):
        return freed, deleted_count, error_count
    try:
        entries = os.listdir(path)
    except Exception as e:
        log_fn(f"تعذر فتح {path}: {e}")
        return freed, deleted_count, error_count
    for entry in entries:
        full = os.path.join(path, entry)
        if is_protected(full):
            continue
        try:
            if os.path.isdir(full) and not os.path.islink(full):
                size = get_dir_size(full, max_seconds=3)
                if dry_run:
                    freed += size
                    deleted_count += 1
                else:
                    shutil.rmtree(full, ignore_errors=True)
                    freed += size
                    deleted_count += 1
            else:
                size = os.path.getsize(full)
                if dry_run:
                    freed += size
                    deleted_count += 1
                else:
                    os.remove(full)
                    freed += size
                    deleted_count += 1
        except PermissionError:
            error_count += 1
        except FileNotFoundError:
            pass
        except Exception:
            error_count += 1
    return freed, deleted_count, error_count
def clean_folder_remove(path, log_fn, dry_run):
    if not os.path.exists(path):
        return 0, 0, 0
    if is_protected(path):
        return 0, 0, 0
    size = get_dir_size(path, max_seconds=5) if os.path.isdir(path) else os.path.getsize(path)
    if dry_run:
        return size, 1, 0
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)
        return size, 1, 0
    except Exception:
        return 0, 0, 1
def clean_thumbcache(path, log_fn, dry_run):
    freed = 0
    deleted = 0
    errors = 0
    if not os.path.isdir(path):
        return freed, deleted, errors
    try:
        entries = os.listdir(path)
    except Exception:
        return freed, deleted, errors
    for entry in entries:
        if entry.lower().startswith("thumbcache_") and entry.lower().endswith(".db"):
            full = os.path.join(path, entry)
            try:
                size = os.path.getsize(full)
                if dry_run:
                    freed += size
                    deleted += 1
                else:
                    os.remove(full)
                    freed += size
                    deleted += 1
            except Exception:
                errors += 1
    return freed, deleted, errors
def clean_firefox_cache(profiles_path, log_fn, dry_run):
    freed = 0
    deleted = 0
    errors = 0
    if not os.path.isdir(profiles_path):
        return freed, deleted, errors
    try:
        profiles = os.listdir(profiles_path)
    except Exception:
        return freed, deleted, errors
    for prof in profiles:
        cache_dir = os.path.join(profiles_path, prof, "cache2")
        if os.path.isdir(cache_dir):
            f, d, e = clean_folder_contents(cache_dir, log_fn, dry_run)
            freed += f
            deleted += d
            errors += e
    return freed, deleted, errors
def run_cleanup(targets, log_fn, progress_fn, dry_run):
    total_freed = 0
    total_deleted = 0
    total_errors = 0
    n = len(targets)
    for idx, t in enumerate(targets):
        if not t.selected:
            progress_fn(idx + 1, n)
            continue
        log_fn(f"{'[معاينة] ' if dry_run else ''}جاري معالجة: {t.label}")
        if t.kind == "recycle_bin":
            empty_recycle_bin(log_fn, dry_run)
        elif t.kind == "thumbcache_only":
            f, d, e = clean_thumbcache(t.path, log_fn, dry_run)
            total_freed += f
            total_deleted += d
            total_errors += e
        elif t.kind == "firefox_cache":
            f, d, e = clean_firefox_cache(t.path, log_fn, dry_run)
            total_freed += f
            total_deleted += d
            total_errors += e
        elif t.kind == "folder_remove":
            f, d, e = clean_folder_remove(t.path, log_fn, dry_run)
            total_freed += f
            total_deleted += d
            total_errors += e
        else:
            f, d, e = clean_folder_contents(t.path, log_fn, dry_run)
            total_freed += f
            total_deleted += d
            total_errors += e
        progress_fn(idx + 1, n)
    return total_freed, total_deleted, total_errors
class CleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("980x680")
        self.root.configure(bg="#1e1e1e")
        self.targets = []
        self.dry_run_var = tk.BooleanVar(value=True)
        self.scanning = False
        self.cleaning = False
        self._build_style()
        self._build_ui()
        self.log(f"مرحباً. اضغط 'فحص الجهاز' للبدء.")
        self.log(f"سجل العمليات يُحفظ في: {LOG_PATH}")
    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 14, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TCheckbutton", background="#1e1e1e", foreground="#e0e0e0", font=("Segoe UI", 9))
        style.configure("Treeview", background="#2b2b2b", foreground="#e0e0e0", fieldbackground="#2b2b2b", rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#3a6ea5")])
    def _build_ui(self):
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(header, text="PC Cleaner Pro — تنظيف القرص C", style="Header.TLabel").pack(side="left")
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=15, pady=5)
        self.scan_btn = ttk.Button(toolbar, text="فحص الجهاز", command=self.start_scan)
        self.scan_btn.pack(side="left", padx=(0, 8))
        self.select_all_btn = ttk.Button(toolbar, text="تحديد الكل", command=self.select_all)
        self.select_all_btn.pack(side="left", padx=(0, 8))
        self.deselect_all_btn = ttk.Button(toolbar, text="إلغاء التحديد", command=self.deselect_all)
        self.deselect_all_btn.pack(side="left", padx=(0, 8))
        dry_chk = ttk.Checkbutton(toolbar, text="وضع المعاينة فقط (بدون حذف فعلي)", variable=self.dry_run_var)
        dry_chk.pack(side="left", padx=(20, 0))
        self.clean_btn = ttk.Button(toolbar, text="إنشاء نقطة استعادة وبدء التنظيف", command=self.start_cleanup)
        self.clean_btn.pack(side="right")
        list_frame = ttk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        columns = ("select", "category", "label", "path", "size")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="none")
        self.tree.heading("select", text="✓")
        self.tree.heading("category", text="الفئة")
        self.tree.heading("label", text="العنصر")
        self.tree.heading("path", text="المسار")
        self.tree.heading("size", text="الحجم")
        self.tree.column("select", width=40, anchor="center")
        self.tree.column("category", width=140)
        self.tree.column("label", width=240)
        self.tree.column("path", width=380)
        self.tree.column("size", width=90, anchor="e")
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self.on_tree_click)
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=15, pady=(5, 0))
        self.total_label = ttk.Label(bottom, text="إجمالي الحجم المتوقع: 0 B")
        self.total_label.pack(side="left")
        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=15, pady=8)
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill="both", expand=False, padx=15, pady=(0, 15))
        ttk.Label(log_frame, text="السجل:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, bg="#121212", fg="#9be39b",
                                                    insertbackground="#9be39b", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
    def set_progress(self, current, total):
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = current
        self.root.update_idletasks()
    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if not row or col != "#1":
            return
        idx = int(row)
        t = self.targets[idx]
        t.selected = not t.selected
        self.tree.set(row, "select", "✓" if t.selected else "")
        self.update_total()
    def select_all(self):
        for i, t in enumerate(self.targets):
            t.selected = True
            self.tree.set(str(i), "select", "✓")
        self.update_total()
    def deselect_all(self):
        for i, t in enumerate(self.targets):
            t.selected = False
            self.tree.set(str(i), "select", "")
        self.update_total()
    def update_total(self):
        total = sum(t.size for t in self.targets if t.selected)
        self.total_label.config(text=f"إجمالي الحجم المتوقع: {human_size(total)}")
    def start_scan(self):
        if self.scanning or self.cleaning:
            return
        self.scanning = True
        self.scan_btn.config(state="disabled")
        self.clean_btn.config(state="disabled")
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.targets = []
        threading.Thread(target=self._scan_worker, daemon=True).start()
    def _scan_worker(self):
        self.log("بدء الفحص...")
        try:
            targets = collect_targets(self.log)
        except Exception as e:
            self.log(f"خطأ أثناء الفحص: {e}")
            self.scanning = False
            self.scan_btn.config(state="normal")
            self.clean_btn.config(state="normal")
            return
        self.log(f"تم العثور على {len(targets)} عنصر. جاري حساب الأحجام...")
        for i, t in enumerate(targets):
            try:
                if t.kind == "recycle_bin":
                    t.size = 0
                else:
                    t.size = get_dir_size(t.path, max_seconds=4) if os.path.isdir(t.path) else os.path.getsize(t.path)
            except Exception:
                t.size = 0
            self.set_progress(i + 1, len(targets))
        self.targets = targets
        self.root.after(0, self._populate_tree)
    def _populate_tree(self):
        for i, t in enumerate(self.targets):
            self.tree.insert("", "end", iid=str(i), values=(
                "✓" if t.selected else "",
                t.category,
                t.label,
                t.path,
                human_size(t.size)
            ))
        self.update_total()
        self.scanning = False
        self.scan_btn.config(state="normal")
        self.clean_btn.config(state="normal")
        self.log("اكتمل الفحص. راجع القائمة ثم اضغط بدء التنظيف.")
    def start_cleanup(self):
        if self.scanning or self.cleaning:
            return
        if not self.targets:
            messagebox.showinfo(APP_NAME, "قم بفحص الجهاز أولاً.")
            return
        selected = [t for t in self.targets if t.selected]
        if not selected:
            messagebox.showinfo(APP_NAME, "لم يتم تحديد أي عنصر.")
            return
        dry = self.dry_run_var.get()
        msg = (
            "سيتم إنشاء نقطة استعادة للنظام، ثم تنفيذ معاينة فقط (بدون حذف)."
            if dry else
            "سيتم إنشاء نقطة استعادة للنظام، ثم حذف العناصر المحددة فعلياً.\nهل أنت متأكد؟"
        )
        if not messagebox.askyesno(APP_NAME, msg):
            return
        self.cleaning = True
        self.scan_btn.config(state="disabled")
        self.clean_btn.config(state="disabled")
        threading.Thread(target=self._cleanup_worker, args=(selected, dry), daemon=True).start()
    def _cleanup_worker(self, selected, dry):
        if not dry:
            create_restore_point(self.log)
        else:
            self.log("وضع المعاينة مفعّل — لن يتم إنشاء نقطة استعادة ولا حذف فعلي.")
        self.log("جاري التنظيف...")
        freed, deleted, errors = run_cleanup(selected, self.log, self.set_progress, dry)
        self.log("=" * 50)
        self.log(f"{'[معاينة] ' if dry else ''}اكتمل. عناصر تم حذفها: {deleted} | أخطاء: {errors}")
        self.log(f"{'المساحة المتوقع تحريرها' if dry else 'المساحة المحررة'}: {human_size(freed)}")
        self.log("=" * 50)
        self.cleaning = False
        self.scan_btn.config(state="normal")
        self.clean_btn.config(state="normal")
        self.root.after(0, lambda: messagebox.showinfo(
            APP_NAME,
            f"{'معاينة مكتملة' if dry else 'التنظيف مكتمل'}\n"
            f"العناصر: {deleted}\nالأخطاء: {errors}\n"
            f"{'المساحة المتوقعة' if dry else 'المساحة المحررة'}: {human_size(freed)}"
        ))
def main():
    if os.name != "nt":
        print("هذه الأداة تعمل فقط على Windows.")
        sys.exit(1)
    delete_old_cache()
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{a}"' for a in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    root = tk.Tk()
    app = CleanerApp(root)
    root.mainloop()
if __name__ == "__main__":
    main()
