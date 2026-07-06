import os
import sys
import ctypes
import shutil
import subprocess
import threading
import time
import json
import platform
import winreg
import urllib.request
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

try:
    import psutil
except ImportError:
    psutil = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

APP_NAME = "PC Suite Pro"
LOG_PATH = os.path.join(os.environ.get("USERPROFILE", "."), "pc_suite_pro_log.txt")
DISABLED_STARTUP_JSON = os.path.join(os.environ.get("USERPROFILE", "."), "pc_suite_pro_disabled_startup.json")
BOOST_BACKUP_JSON = os.path.join(os.environ.get("USERPROFILE", "."), "pc_suite_pro_boost_backup.json")

HIGH_PERF_POWER_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

TWEAK_SERVICES = {
    "DiagTrack": "خدمة تتبع الأحداث المتصلة (تيليمتري Microsoft)",
    "dmwappushsvc": "خدمة توجيه رسائل WAP Push",
    "SysMain": "التخزين المؤقت التنبؤي (Superfetch)",
    "WSearch": "فهرسة بحث ويندوز",
    "WerSvc": "خدمة تقارير أخطاء ويندوز",
    "PcaSvc": "مساعد توافق البرامج",
    "DoSvc": "خدمة التوصيل الأمثل (مشاركة تحديثات مع أجهزة أخرى)",
    "RetailDemo": "خدمة العرض التجريبي للأجهزة",
    "MapsBroker": "وسيط الخرائط غير المتصلة",
    "Fax": "خدمة الفاكس",
}

REGISTRY_TWEAKS = [
    {"id": "gamedvr", "label": "تعطيل تسجيل الألعاب في الخلفية (Xbox Game Bar / Game DVR)",
     "hive": winreg.HKEY_CURRENT_USER, "path": r"System\GameConfigStore",
     "name": "GameDVR_Enabled", "type": winreg.REG_DWORD, "boost": 0},
    {"id": "appcapture", "label": "تعطيل تسجيل الألعاب التلقائي",
     "hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
     "name": "AppCaptureEnabled", "type": winreg.REG_DWORD, "boost": 0},
    {"id": "bgapps", "label": "تعطيل تطبيقات الخلفية",
     "hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
     "name": "GlobalUserDisabled", "type": winreg.REG_DWORD, "boost": 1},
    {"id": "tips", "label": "تعطيل نصائح واقتراحات ويندوز",
     "hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "name": "SystemPaneSuggestionsEnabled", "type": winreg.REG_DWORD, "boost": 0},
    {"id": "silenthours", "label": "تعطيل الإشعارات المنبثقة غير الضرورية",
     "hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\PushNotifications",
     "name": "ToastEnabled", "type": winreg.REG_DWORD, "boost": 0},
    {"id": "visualfx", "label": "ضبط المؤثرات البصرية على أفضل أداء",
     "hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
     "name": "VisualFXSetting", "type": winreg.REG_DWORD, "boost": 2},
]

BOOST_EXTRA_OPTIONS = [
    ("nagle", "تحسين استجابة الشبكة (تعطيل خوارزمية Nagle لتقليل تأخير الألعاب)"),
    ("power", "تفعيل خطة الطاقة (أداء عالٍ) طوال فترة التعزيز"),
]

PROTECTED_KEYWORDS = [
    "downloads", "desktop", "videos", "documents", "pictures", "music",
    "onedrive", "steam", "steamapps", "epic games", "epicgames",
    "riot games", "riotgames", "battle.net", "battlenet",
    "ea games", "origin games", "ubisoft", "gog galaxy", "gog games",
    "rockstar games", "xbox games",
]
PROTECTED_PATHS_ABS = []

CRITICAL_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe", "svchost.exe",
    "dwm.exe", "explorer.exe", "fontdrvhost.exe", "wudfhost.exe",
}

HIGH_IMPACT_KEYWORDS = ["adobe", "onedrive", "skype", "spotify", "steam", "discord",
                         "teams", "dropbox", "epic", "origin", "battle.net", "creative cloud", "zoom"]
MED_IMPACT_KEYWORDS = ["update", "helper", "agent", "sync", "launcher"]

EXT_CATEGORIES = {
    "صور": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"},
    "فيديو": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"},
    "مستندات": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"},
    "تنفيذية": {".exe", ".msi"},
    "أرشيف": {".zip", ".rar", ".7z", ".tar", ".gz"},
}


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
        "crashdumps", "d3dscache", "elevateddiagnostics", "nvidia",
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
        desc = f"PC Suite Pro - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
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


def draw_sparkline(canvas, data, color, max_value=100):
    canvas.delete("all")
    canvas.update_idletasks()
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1:
        w = int(canvas["width"])
    if h <= 1:
        h = int(canvas["height"])
    if not data or w <= 1 or h <= 1:
        return
    n = len(data)
    step = w / max(n - 1, 1)
    points = []
    for i, v in enumerate(data):
        x = i * step
        y = h - (min(v, max_value) / max_value) * (h - 4) - 2
        points.append((x, y))
    if len(points) < 2:
        return
    flat = []
    for x, y in points:
        flat.append(x)
        flat.append(y)
    canvas.create_line(*flat, fill=color, width=2, smooth=True)


def categorize_process(exe, username, name):
    win_dir = os.environ.get("WINDIR", "C:\\Windows").lower()
    lname = (name or "").lower()
    if lname in CRITICAL_PROCESSES:
        return "System"
    if exe and exe.lower().startswith(win_dir):
        return "System"
    if not username:
        return "System"
    known_background = {
        "svchost.exe", "dwm.exe", "csrss.exe", "wininit.exe", "services.exe",
        "lsass.exe", "smss.exe", "spoolsv.exe", "taskhostw.exe", "runtimebroker.exe",
        "searchindexer.exe", "sihost.exe", "ctfmon.exe", "conhost.exe", "fontdrvhost.exe",
        "wmiprvse.exe", "dllhost.exe",
    }
    if lname in known_background:
        return "Background"
    return "User"


def get_startup_entries():
    entries = []
    run_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    ]
    for hive, path, hive_name in run_keys:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        except Exception:
            continue
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                i += 1
            except OSError:
                break
            entries.append({
                "source": "registry",
                "hive_name": hive_name,
                "hive": hive,
                "reg_path": path,
                "name": name,
                "command": value,
                "enabled": True,
            })
        winreg.CloseKey(key)
    startup_folders = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"),
    ]
    for folder in startup_folders:
        if os.path.isdir(folder):
            try:
                for f in os.listdir(folder):
                    full = os.path.join(folder, f)
                    if os.path.isfile(full):
                        entries.append({
                            "source": "folder",
                            "path": full,
                            "name": f,
                            "command": full,
                            "enabled": True,
                        })
            except Exception:
                pass
    disabled_folders = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "Disabled"),
    ]
    for folder in disabled_folders:
        if os.path.isdir(folder):
            try:
                for f in os.listdir(folder):
                    full = os.path.join(folder, f)
                    if os.path.isfile(full):
                        entries.append({
                            "source": "folder_disabled",
                            "path": full,
                            "name": f,
                            "command": full,
                            "enabled": False,
                        })
            except Exception:
                pass
    disabled_backup = load_disabled_startup_backup()
    for name, data in disabled_backup.items():
        entries.append({
            "source": "registry_disabled",
            "hive_name": data.get("hive_name"),
            "reg_path": data.get("reg_path"),
            "name": name,
            "command": data.get("command", ""),
            "enabled": False,
        })
    return entries


def load_disabled_startup_backup():
    if not os.path.exists(DISABLED_STARTUP_JSON):
        return {}
    try:
        with open(DISABLED_STARTUP_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_disabled_startup_backup(data):
    try:
        with open(DISABLED_STARTUP_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def disable_startup_entry(entry):
    if entry["source"] == "registry":
        hive = winreg.HKEY_CURRENT_USER if entry["hive_name"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        try:
            key = winreg.OpenKey(hive, entry["reg_path"], 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, entry["name"])
            winreg.CloseKey(key)
        except Exception:
            return False
        backup = load_disabled_startup_backup()
        backup[entry["name"]] = {
            "hive_name": entry["hive_name"],
            "reg_path": entry["reg_path"],
            "command": entry["command"],
        }
        save_disabled_startup_backup(backup)
        return True
    if entry["source"] == "folder":
        folder = os.path.dirname(entry["path"])
        disabled_dir = os.path.join(folder, "Disabled")
        os.makedirs(disabled_dir, exist_ok=True)
        try:
            shutil.move(entry["path"], os.path.join(disabled_dir, os.path.basename(entry["path"])))
            return True
        except Exception:
            return False
    return False


def enable_startup_entry(entry):
    if entry["source"] == "registry_disabled":
        hive = winreg.HKEY_CURRENT_USER if entry["hive_name"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        try:
            key = winreg.OpenKey(hive, entry["reg_path"], 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, entry["name"], 0, winreg.REG_SZ, entry["command"])
            winreg.CloseKey(key)
        except Exception:
            return False
        backup = load_disabled_startup_backup()
        backup.pop(entry["name"], None)
        save_disabled_startup_backup(backup)
        return True
    if entry["source"] == "folder_disabled":
        disabled_dir = os.path.dirname(entry["path"])
        target_dir = os.path.dirname(disabled_dir)
        try:
            shutil.move(entry["path"], os.path.join(target_dir, os.path.basename(entry["path"])))
            return True
        except Exception:
            return False
    return False


def impact_score(name, command):
    text = f"{name} {command}".lower()
    for k in HIGH_IMPACT_KEYWORDS:
        if k in text:
            return "مرتفع"
    for k in MED_IMPACT_KEYWORDS:
        if k in text:
            return "متوسط"
    return "منخفض"


def matches_ext_category(filename, category):
    if category == "الكل":
        return True
    ext = os.path.splitext(filename)[1].lower()
    return ext in EXT_CATEGORIES.get(category, set())


def scan_files(root_path, name_filter, ext_filter, min_size_bytes, max_results=800, max_seconds=20):
    results = []
    start = time.time()
    try:
        for r, dirs, files in os.walk(root_path, onerror=lambda e: None):
            if time.time() - start > max_seconds or len(results) >= max_results:
                break
            for f in files:
                full = os.path.join(r, f)
                try:
                    if name_filter and name_filter.lower() not in f.lower():
                        continue
                    if not matches_ext_category(f, ext_filter):
                        continue
                    size = os.path.getsize(full)
                    if size < min_size_bytes:
                        continue
                    mtime = os.path.getmtime(full)
                    results.append((f, full, size, mtime))
                    if len(results) >= max_results:
                        break
                except Exception:
                    continue
    except Exception:
        pass
    return results


def get_gpu_info():
    try:
        result = subprocess.run(["wmic", "path", "win32_VideoController", "get", "Name"],
                                 capture_output=True, text=True, timeout=10)
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip().lower() != "name"]
        if lines:
            return lines
    except Exception:
        pass
    try:
        cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if lines:
            return lines
    except Exception:
        pass
    return ["غير معروف"]


def get_cpu_temp():
    try:
        cmd = ('powershell -NoProfile -Command '
               '"(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature '
               '| Select-Object -First 1 -ExpandProperty CurrentTemperature)"')
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
        raw = result.stdout.strip()
        if raw:
            celsius = float(raw) / 10 - 273.15
            if -10 < celsius < 120:
                return celsius
    except Exception:
        pass
    return None


def get_gpu_temp():
    try:
        result = subprocess.run(
            "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits",
            shell=True, capture_output=True, text=True, timeout=8)
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if lines:
            return float(lines[0])
    except Exception:
        pass
    return None


def speedtest_download():
    url = "https://speed.cloudflare.com/__down?bytes=25000000"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        total = 0
        start = time.time()
        with urllib.request.urlopen(req, timeout=15) as resp:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if time.time() - start > 8:
                    break
        elapsed = max(time.time() - start, 0.001)
        if total <= 0:
            return None
        return (total * 8) / elapsed / 1_000_000
    except Exception:
        return None


def speedtest_upload():
    url = "https://speed.cloudflare.com/__up"
    try:
        data = os.urandom(5_000_000)
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/octet-stream", "User-Agent": "Mozilla/5.0"})
        start = time.time()
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        elapsed = max(time.time() - start, 0.001)
        return (len(data) * 8) / elapsed / 1_000_000
    except Exception:
        return None


def get_service_start_mode(name):
    try:
        result = subprocess.run(f'sc qc "{name}"', shell=True, capture_output=True, text=True, timeout=10)
        for line in result.stdout.splitlines():
            up = line.upper()
            if "START_TYPE" in up:
                if "AUTO_START" in up:
                    return "auto"
                if "DEMAND_START" in up:
                    return "demand"
                if "DISABLED" in up:
                    return "disabled"
                if "SYSTEM_START" in up:
                    return "system"
    except Exception:
        pass
    return "auto"


def set_service_start_mode(name, mode):
    try:
        subprocess.run(f'sc config "{name}" start= {mode}', shell=True, capture_output=True, text=True, timeout=15)
    except Exception:
        pass


def stop_service(name):
    try:
        subprocess.run(f'sc stop "{name}"', shell=True, capture_output=True, text=True, timeout=15)
    except Exception:
        pass


def start_service(name):
    try:
        subprocess.run(f'sc start "{name}"', shell=True, capture_output=True, text=True, timeout=15)
    except Exception:
        pass


def read_reg_value(hive, path, name):
    try:
        key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, name)
            return val
        finally:
            winreg.CloseKey(key)
    except Exception:
        return None


def write_reg_value(hive, path, name, value, value_type):
    try:
        key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(key, name, 0, value_type, value)
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False


def delete_reg_value(hive, path, name):
    try:
        key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, name)
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass


def get_network_interface_guids():
    guids = []
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
        try:
            i = 0
            while True:
                try:
                    guids.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass
    return guids


def load_boost_backup():
    if os.path.exists(BOOST_BACKUP_JSON):
        try:
            with open(BOOST_BACKUP_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_boost_backup(data):
    try:
        with open(BOOST_BACKUP_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def apply_boost(selected_ids, log_fn):
    backup = {"services": {}, "registry": {}, "power_scheme": None, "network_interfaces": []}
    for svc_name, desc in TWEAK_SERVICES.items():
        if svc_name not in selected_ids:
            continue
        backup["services"][svc_name] = get_service_start_mode(svc_name)
        stop_service(svc_name)
        set_service_start_mode(svc_name, "disabled")
        log_fn(f"تم تعطيل: {desc}")
    for tw in REGISTRY_TWEAKS:
        if tw["id"] not in selected_ids:
            continue
        backup["registry"][tw["id"]] = read_reg_value(tw["hive"], tw["path"], tw["name"])
        write_reg_value(tw["hive"], tw["path"], tw["name"], tw["boost"], tw["type"])
        log_fn(f"تم تطبيق: {tw['label']}")
    if "nagle" in selected_ids:
        for guid in get_network_interface_guids():
            path = rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{guid}"
            backup["network_interfaces"].append({
                "guid": guid,
                "ack": read_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TcpAckFrequency"),
                "delay": read_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TCPNoDelay"),
            })
            write_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TcpAckFrequency", 1, winreg.REG_DWORD)
            write_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TCPNoDelay", 1, winreg.REG_DWORD)
        log_fn("تم تحسين استجابة الشبكة (تعطيل Nagle).")
    if "power" in selected_ids:
        try:
            result = subprocess.run("powercfg /getactivescheme", shell=True, capture_output=True, text=True, timeout=10)
            for part in result.stdout.split():
                if len(part) == 36 and part.count("-") == 4:
                    backup["power_scheme"] = part
                    break
        except Exception:
            pass
        subprocess.run(f"powercfg /setactive {HIGH_PERF_POWER_GUID}", shell=True,
                        capture_output=True, text=True, timeout=10)
        log_fn("تم تفعيل خطة الطاقة (أداء عالٍ).")
    save_boost_backup(backup)
    log_fn("اكتمل تفعيل تعزيز FPS. أعد تشغيل الجهاز لأفضل نتيجة.")


def restore_boost(log_fn):
    backup = load_boost_backup()
    if not backup:
        log_fn("لا توجد إعدادات محفوظة للاستعادة.")
        return
    for svc_name, mode in backup.get("services", {}).items():
        mode = mode or "auto"
        set_service_start_mode(svc_name, mode)
        if mode in ("auto", "system", "demand"):
            start_service(svc_name)
        log_fn(f"تمت استعادة خدمة: {svc_name}")
    for tw in REGISTRY_TWEAKS:
        if tw["id"] in backup.get("registry", {}):
            original = backup["registry"][tw["id"]]
            if original is None:
                delete_reg_value(tw["hive"], tw["path"], tw["name"])
            else:
                write_reg_value(tw["hive"], tw["path"], tw["name"], original, tw["type"])
    for entry in backup.get("network_interfaces", []):
        path = rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{entry['guid']}"
        if entry.get("ack") is None:
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TcpAckFrequency")
        else:
            write_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TcpAckFrequency", entry["ack"], winreg.REG_DWORD)
        if entry.get("delay") is None:
            delete_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TCPNoDelay")
        else:
            write_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "TCPNoDelay", entry["delay"], winreg.REG_DWORD)
    if backup.get("power_scheme"):
        subprocess.run(f"powercfg /setactive {backup['power_scheme']}", shell=True,
                        capture_output=True, text=True, timeout=10)
    log_fn("تمت استعادة جميع الإعدادات الأصلية بنجاح.")
    try:
        os.remove(BOOST_BACKUP_JSON)
    except Exception:
        pass


def get_system_info():
    info = {}
    info["اسم الجهاز"] = platform.node()
    info["نظام التشغيل"] = platform.platform()
    info["المعالج"] = platform.processor() or "غير معروف"
    if psutil is not None:
        info["نوى المعالج"] = f"{psutil.cpu_count(logical=False)} فيزيائية / {psutil.cpu_count(logical=True)} منطقية"
        freq = psutil.cpu_freq()
        if freq:
            info["تردد المعالج"] = f"{freq.current:.0f} MHz"
        vm = psutil.virtual_memory()
        info["الذاكرة (RAM)"] = f"{human_size(vm.total)} - المستخدم حالياً {vm.percent}%"
    info["كرت الشاشة (GPU)"] = "، ".join(get_gpu_info())
    try:
        total, used, free = shutil.disk_usage("C:\\")
        info["القرص C"] = f"الإجمالي {human_size(total)} | المستخدم {human_size(used)} | المتاح {human_size(free)}"
    except Exception:
        pass
    return info


def text_report_to_pdf(lines, output_path):
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def to_ascii(s):
        return s.encode("ascii", errors="replace").decode("ascii")

    content_lines = ["BT", "/F1 12 Tf", "50 780 Td", "14 TL"]
    first = True
    for line in lines:
        safe_line = esc(to_ascii(line))
        if first:
            content_lines.append(f"({safe_line}) Tj")
            first = False
        else:
            content_lines.append("T*")
            content_lines.append(f"({safe_line}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines)
    content_bytes = content_stream.encode("latin-1", errors="replace")

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> "
        "/MediaBox [0 0 612 792] /Contents 4 0 R >>",
        f"<< /Length {len(content_bytes)} >>\nstream\n{content_stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    buf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{i} 0 obj\n".encode("latin-1") + obj.encode("latin-1", errors="replace") + b"\nendobj\n"
    xref_offset = len(buf)
    buf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    buf += b"0000000000 65535 f \n"
    for off in offsets:
        buf += f"{off:010d} 00000 n \n".encode("latin-1")
    buf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
    with open(output_path, "wb") as f:
        f.write(buf)


def get_arp_devices():
    try:
        result = subprocess.run("arp -a", shell=True, capture_output=True, text=True, timeout=10)
        devices = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].count(".") == 3:
                ip = parts[0]
                mac = parts[1] if len(parts) > 1 else ""
                kind = parts[2] if len(parts) > 2 else ""
                devices.append((ip, mac, kind))
        return devices
    except Exception:
        return []


def ping_test(host="8.8.8.8"):
    try:
        result = subprocess.run(f"ping -n 4 {host}", shell=True, capture_output=True, text=True, timeout=15)
        out = result.stdout
        for line in out.splitlines():
            if "Average" in line or "متوسط" in line:
                return line.strip()
        tail = out.strip().splitlines()
        return tail[-1] if tail else "لا توجد استجابة"
    except Exception as e:
        return f"فشل الاختبار: {e}"


NAV_ITEMS = [
    ("cleaner", "🧹 تنظيف القرص"),
    ("dashboard", "📊 لوحة الأداء"),
    ("processes", "🧠 إدارة العمليات"),
    ("startup", "🚀 محسّن الإقلاع"),
    ("explorer", "📁 مستكشف الملفات"),
    ("sysinfo", "🧾 معلومات النظام"),
    ("network", "🌐 مراقب الشبكة"),
    ("booster", "⚡ معزز الأداء لبرنامج محدد"),
    ("boost", "🎮 تعزيز FPS الشامل"),
    ("downloader", "⬇️ تحميل الفيديوهات"),
]

BG_MAIN = "#111827"
BG_SIDEBAR = "#0b0f19"
BG_PANEL = "#1f2937"
FG_TEXT = "#f3f4f6"
ACCENT = "#22c55e"
ACCENT2 = "#06b6d4"


def styled_frame(parent):
    return tk.Frame(parent, bg=BG_MAIN)


def section_title(parent, text):
    return tk.Label(parent, text=text, bg=BG_MAIN, fg=ACCENT, font=("Segoe UI", 14, "bold"))


def make_treeview(parent, columns, headers, widths):
    wrapper = ttk.Frame(parent)
    tree = ttk.Treeview(wrapper, columns=columns, show="headings", selectmode="browse")
    for col, head, w in zip(columns, headers, widths):
        tree.heading(col, text=head)
        tree.column(col, width=w, anchor="w")
    vsb = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return wrapper, tree


class CleanerFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.targets = []
        self.scanning = False
        self.cleaning = False
        self.dry_run_var = tk.BooleanVar(value=True)
        self.restore_var = tk.BooleanVar(value=True)
        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(header, text="تنظيف القرص C", style="Header.TLabel").pack(side="left")
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=15, pady=5)
        self.scan_btn = ttk.Button(toolbar, text="فحص الجهاز", command=self.start_scan)
        self.scan_btn.pack(side="left", padx=(0, 8))
        self.select_all_btn = ttk.Button(toolbar, text="تحديد الكل", command=self.select_all)
        self.select_all_btn.pack(side="left", padx=(0, 8))
        self.deselect_all_btn = ttk.Button(toolbar, text="إلغاء التحديد", command=self.deselect_all)
        self.deselect_all_btn.pack(side="left", padx=(0, 8))
        dry_chk = ttk.Checkbutton(toolbar, text="وضع المعاينة فقط (بدون حذف فعلي)", variable=self.dry_run_var)
        dry_chk.pack(side="left", padx=(20, 0))
        restore_chk = ttk.Checkbutton(toolbar, text="إنشاء نقطة استعادة", variable=self.restore_var)
        restore_chk.pack(side="left", padx=(20, 0))
        self.clean_btn = ttk.Button(toolbar, text="بدء التنظيف", command=self.start_cleanup)
        self.clean_btn.pack(side="right")
        list_frame = ttk.Frame(self)
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
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=15, pady=(5, 0))
        self.total_label = ttk.Label(bottom, text="إجمالي الحجم المتوقع: 0 B")
        self.total_label.pack(side="left")
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=15, pady=8)
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=False, padx=15, pady=(0, 15))
        ttk.Label(log_frame, text="السجل:").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, bg=BG_PANEL, fg=ACCENT2,
                                                    insertbackground=ACCENT2, font=("Consolas", 9),
                                                    state="disabled", cursor="arrow", takefocus=0)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.bind("<Button-1>", lambda e: "break")
        self.log_text.bind("<B1-Motion>", lambda e: "break")
        self.log_text.bind("<Double-Button-1>", lambda e: "break")
        self.log_text.bind("<Triple-Button-1>", lambda e: "break")
        self.log_text.bind("<Key>", lambda e: "break")
        self.log("مرحباً. اضغط 'فحص الجهاز' للبدء.")
        self.log(f"سجل العمليات يُحفظ في: {LOG_PATH}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.update_idletasks()
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def set_progress(self, current, total):
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = current
        self.update_idletasks()

    def _update_freed_progress(self, freed):
        try:
            total, used, free = shutil.disk_usage("C:\\")
        except Exception:
            total = 0
        percent = (freed / total * 100) if total > 0 else 0
        percent = max(0, min(percent, 100))
        self.progress["maximum"] = 100
        self.progress["value"] = percent

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
        self.after(0, self._populate_tree)

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
        if not dry and self.restore_var.get():
            create_restore_point(self.log)
        elif dry:
            self.log("وضع المعاينة مفعّل — لن يتم حذف فعلي.")
        self.log("جاري التنظيف...")
        freed, deleted, errors = run_cleanup(selected, self.log, self.set_progress, dry)
        self.log("=" * 50)
        self.log(f"{'[معاينة] ' if dry else ''}اكتمل. عناصر تم حذفها: {deleted} | أخطاء: {errors}")
        self.log(f"{'المساحة المتوقع تحريرها' if dry else 'المساحة المحررة'}: {human_size(freed)}")
        self.log("=" * 50)
        self.after(0, lambda: self._update_freed_progress(freed))
        self.cleaning = False
        self.scan_btn.config(state="normal")
        self.clean_btn.config(state="normal")
        self.after(0, lambda: messagebox.showinfo(
            APP_NAME,
            f"{'معاينة مكتملة' if dry else 'التنظيف مكتمل'}\n"
            f"العناصر: {deleted}\nالأخطاء: {errors}\n"
            f"{'المساحة المتوقعة' if dry else 'المساحة المحررة'}: {human_size(freed)}"
        ))


class DashboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.active = False
        self.cpu_history = []
        self.ram_history = []
        self.proc_cache = {}
        self.temp_active = False
        self._build_ui()

    def _build_ui(self):
        section_title(self, "لوحة الأداء المباشرة").pack(anchor="w", padx=20, pady=(20, 10))
        stats = tk.Frame(self, bg=BG_MAIN)
        stats.pack(fill="x", padx=20)
        self.cpu_label = tk.Label(stats, text="المعالج (CPU): --%", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11))
        self.cpu_label.grid(row=0, column=0, sticky="w", pady=6)
        self.cpu_canvas = tk.Canvas(stats, width=320, height=50, bg=BG_PANEL, highlightthickness=0)
        self.cpu_canvas.grid(row=0, column=1, padx=20)
        self.ram_label = tk.Label(stats, text="الذاكرة (RAM): --%", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11))
        self.ram_label.grid(row=1, column=0, sticky="w", pady=6)
        self.ram_canvas = tk.Canvas(stats, width=320, height=50, bg=BG_PANEL, highlightthickness=0)
        self.ram_canvas.grid(row=1, column=1, padx=20)
        self.disk_label = tk.Label(stats, text="القرص C: --%", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11))
        self.disk_label.grid(row=2, column=0, sticky="w", pady=6)
        self.cputemp_label = tk.Label(stats, text="حرارة المعالج (CPU): -- °C", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11))
        self.cputemp_label.grid(row=3, column=0, sticky="w", pady=6)
        self.gputemp_label = tk.Label(stats, text="حرارة كرت الشاشة (GPU): -- °C", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11))
        self.gputemp_label.grid(row=4, column=0, sticky="w", pady=6)
        tk.Label(stats, text="ملاحظة: قراءة الحرارة تعتمد على دعم اللوحة الأم/التعريفات. كرت شاشة NVIDIA فقط مدعوم حالياً.",
                 bg=BG_MAIN, fg="#9ca3af", font=("Segoe UI", 8)).grid(row=5, column=0, sticky="w", pady=(0, 6))
        tk.Label(self, text="أكثر البرامج استهلاكاً", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=20, pady=(20, 5))
        wrapper, self.tree = make_treeview(self, ("name", "pid", "cpu", "ram"),
                                            ("اسم العملية", "PID", "CPU %", "الذاكرة"), (260, 80, 100, 120))
        wrapper.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def on_show(self):
        self.active = True
        self.temp_active = True
        if psutil is None:
            messagebox.showerror(APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ الأمر التالي في cmd:\npip install psutil")
            return
        self._loop()
        self._temp_loop()

    def on_hide(self):
        self.active = False
        self.temp_active = False

    def _loop(self):
        if not self.active:
            return
        threading.Thread(target=self._update_once, daemon=True).start()
        self.after(1500, self._loop)

    def _temp_loop(self):
        if not self.temp_active:
            return
        threading.Thread(target=self._update_temps, daemon=True).start()
        self.after(5000, self._temp_loop)

    def _update_temps(self):
        cpu_temp = get_cpu_temp()
        gpu_temp = get_gpu_temp()
        self.after(0, lambda: self._render_temps(cpu_temp, gpu_temp))

    def _render_temps(self, cpu_temp, gpu_temp):
        self.cputemp_label.config(
            text=f"حرارة المعالج (CPU): {cpu_temp:.0f} °C" if cpu_temp is not None else "حرارة المعالج (CPU): غير متوفرة")
        self.gputemp_label.config(
            text=f"حرارة كرت الشاشة (GPU): {gpu_temp:.0f} °C" if gpu_temp is not None else "حرارة كرت الشاشة (GPU): غير متوفرة")

    def _update_once(self):
        try:
            cpu = psutil.cpu_percent(interval=0.4)
            vm = psutil.virtual_memory()
            total, used, free = shutil.disk_usage("C:\\")
            disk_percent = used / total * 100 if total else 0
            current_pids = set(psutil.pids())
            for pid in list(self.proc_cache):
                if pid not in current_pids:
                    del self.proc_cache[pid]
            for pid in current_pids:
                if pid not in self.proc_cache:
                    try:
                        proc = psutil.Process(pid)
                        proc.cpu_percent(None)
                        self.proc_cache[pid] = proc
                    except Exception:
                        continue
            rows = []
            for pid, proc in list(self.proc_cache.items()):
                try:
                    cpu_p = proc.cpu_percent(None)
                    mem = proc.memory_info().rss
                    name = proc.name()
                    rows.append((name, pid, cpu_p, mem))
                except Exception:
                    continue
            rows.sort(key=lambda x: x[2], reverse=True)
            top = rows[:12]
        except Exception:
            return
        self.after(0, lambda: self._render(cpu, vm.percent, disk_percent, top))

    def _render(self, cpu, ram_percent, disk_percent, top):
        self.cpu_history.append(cpu)
        self.ram_history.append(ram_percent)
        self.cpu_history = self.cpu_history[-60:]
        self.ram_history = self.ram_history[-60:]
        self.cpu_label.config(text=f"المعالج (CPU): {cpu:.1f}%")
        self.ram_label.config(text=f"الذاكرة (RAM): {ram_percent:.1f}%")
        self.disk_label.config(text=f"القرص C: {disk_percent:.1f}%")
        draw_sparkline(self.cpu_canvas, self.cpu_history, ACCENT)
        draw_sparkline(self.ram_canvas, self.ram_history, ACCENT2)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for name, pid, cpu_p, mem in top:
            self.tree.insert("", "end", values=(name, pid, f"{cpu_p:.1f}", human_size(mem)))


class ProcessFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.active = False
        self.proc_cache = {}
        self.filter_var = tk.StringVar(value="الكل")
        self._build_ui()

    def _build_ui(self):
        section_title(self, "إدارة العمليات الذكية").pack(anchor="w", padx=20, pady=(20, 10))
        toolbar = tk.Frame(self, bg=BG_MAIN)
        toolbar.pack(fill="x", padx=20)
        tk.Label(toolbar, text="تصفية:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        filter_box = ttk.Combobox(toolbar, textvariable=self.filter_var, state="readonly",
                                   values=["الكل", "System", "User", "Background"], width=14)
        filter_box.pack(side="left", padx=8)
        ttk.Button(toolbar, text="إنهاء العملية المحددة", command=self.kill_selected).pack(side="left", padx=8)
        wrapper, self.tree = make_treeview(self, ("name", "pid", "category", "cpu", "ram"),
                                            ("اسم العملية", "PID", "التصنيف", "CPU %", "الذاكرة"),
                                            (240, 80, 110, 90, 120))
        wrapper.pack(fill="both", expand=True, padx=20, pady=15)

    def on_show(self):
        self.active = True
        if psutil is None:
            messagebox.showerror(APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ: pip install psutil")
            return
        self._loop()

    def on_hide(self):
        self.active = False

    def _loop(self):
        if not self.active:
            return
        threading.Thread(target=self._update_once, daemon=True).start()
        self.after(2000, self._loop)

    def _update_once(self):
        try:
            current_pids = set(psutil.pids())
            for pid in list(self.proc_cache):
                if pid not in current_pids:
                    del self.proc_cache[pid]
            for pid in current_pids:
                if pid not in self.proc_cache:
                    try:
                        proc = psutil.Process(pid)
                        proc.cpu_percent(None)
                        self.proc_cache[pid] = proc
                    except Exception:
                        continue
            rows = []
            for pid, proc in list(self.proc_cache.items()):
                try:
                    name = proc.name()
                    exe = proc.exe() if proc.exe() else ""
                    username = proc.username() if hasattr(proc, "username") else ""
                    category = categorize_process(exe, username, name)
                    cpu_p = proc.cpu_percent(None)
                    mem = proc.memory_info().rss
                    rows.append((name, pid, category, cpu_p, mem))
                except Exception:
                    continue
            rows.sort(key=lambda x: x[3], reverse=True)
        except Exception:
            return
        self.after(0, lambda: self._render(rows))

    def _render(self, rows):
        flt = self.filter_var.get()
        for row in self.tree.get_children():
            self.tree.delete(row)
        for name, pid, category, cpu_p, mem in rows:
            if flt != "الكل" and category != flt:
                continue
            self.tree.insert("", "end", values=(name, pid, category, f"{cpu_p:.1f}", human_size(mem)))

    def kill_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "اختر عملية من القائمة أولاً.")
            return
        values = self.tree.item(sel[0], "values")
        pid = int(values[1])
        if values[0].lower() in CRITICAL_PROCESSES:
            messagebox.showwarning(APP_NAME, "لا يمكن إنهاء عملية نظام أساسية.")
            return
        if not messagebox.askyesno(APP_NAME, f"هل تريد إنهاء العملية {values[0]} (PID {pid})؟"):
            return
        try:
            psutil.Process(pid).terminate()
        except Exception as e:
            messagebox.showerror(APP_NAME, f"تعذر إنهاء العملية: {e}")


class StartupFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.entries = []
        self._build_ui()

    def _build_ui(self):
        section_title(self, "محسّن الإقلاع").pack(anchor="w", padx=20, pady=(20, 10))
        toolbar = tk.Frame(self, bg=BG_MAIN)
        toolbar.pack(fill="x", padx=20)
        ttk.Button(toolbar, text="تحديث القائمة", command=self.refresh).pack(side="left")
        ttk.Button(toolbar, text="تعطيل المحدد", command=self.disable_selected).pack(side="left", padx=8)
        ttk.Button(toolbar, text="تفعيل المحدد", command=self.enable_selected).pack(side="left", padx=8)
        wrapper, self.tree = make_treeview(self, ("name", "status", "impact", "source", "command"),
                                            ("الاسم", "الحالة", "التأثير المتوقع", "المصدر", "الأمر / المسار"),
                                            (180, 90, 130, 110, 320))
        wrapper.pack(fill="both", expand=True, padx=20, pady=15)

    def on_show(self):
        self.refresh()

    def on_hide(self):
        pass

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.entries = get_startup_entries()
        for i, e in enumerate(self.entries):
            status = "مفعّل" if e.get("enabled", True) else "معطّل"
            score = impact_score(e["name"], e.get("command", ""))
            self.tree.insert("", "end", iid=str(i), values=(e["name"], status, score, e["source"], e.get("command", "")))

    def disable_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "اختر عنصراً من القائمة أولاً.")
            return
        idx = int(sel[0])
        entry = self.entries[idx]
        if not entry.get("enabled", True):
            messagebox.showinfo(APP_NAME, "هذا العنصر معطّل بالفعل.")
            return
        if disable_startup_entry(entry):
            messagebox.showinfo(APP_NAME, f"تم تعطيل {entry['name']} من الإقلاع.")
        else:
            messagebox.showerror(APP_NAME, "تعذر تعطيل هذا العنصر.")
        self.refresh()

    def enable_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "اختر عنصراً من القائمة أولاً.")
            return
        idx = int(sel[0])
        entry = self.entries[idx]
        if entry.get("enabled", True):
            messagebox.showinfo(APP_NAME, "هذا العنصر مفعّل بالفعل.")
            return
        if enable_startup_entry(entry):
            messagebox.showinfo(APP_NAME, f"تم تفعيل {entry['name']} في الإقلاع.")
        else:
            messagebox.showerror(APP_NAME, "تعذر تفعيل هذا العنصر.")
        self.refresh()


class ExplorerFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.path_var = tk.StringVar(value="C:\\")
        self.name_var = tk.StringVar(value="")
        self.ext_var = tk.StringVar(value="الكل")
        self.min_size_var = tk.StringVar(value="0")
        self.results = []
        self._build_ui()

    def _build_ui(self):
        section_title(self, "مستكشف الملفات المتقدم").pack(anchor="w", padx=20, pady=(20, 10))
        row1 = tk.Frame(self, bg=BG_MAIN)
        row1.pack(fill="x", padx=20)
        tk.Label(row1, text="المسار:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        ttk.Entry(row1, textvariable=self.path_var, width=45).pack(side="left", padx=5)
        ttk.Button(row1, text="استعراض", command=self.browse).pack(side="left", padx=5)
        row2 = tk.Frame(self, bg=BG_MAIN)
        row2.pack(fill="x", padx=20, pady=8)
        tk.Label(row2, text="اسم يحتوي على:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        ttk.Entry(row2, textvariable=self.name_var, width=20).pack(side="left", padx=5)
        tk.Label(row2, text="النوع:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left", padx=(15, 0))
        ttk.Combobox(row2, textvariable=self.ext_var, state="readonly",
                     values=["الكل"] + list(EXT_CATEGORIES.keys()), width=12).pack(side="left", padx=5)
        tk.Label(row2, text="أقل حجم (MB):", bg=BG_MAIN, fg=FG_TEXT).pack(side="left", padx=(15, 0))
        ttk.Entry(row2, textvariable=self.min_size_var, width=8).pack(side="left", padx=5)
        ttk.Button(row2, text="بحث", command=self.start_search).pack(side="left", padx=(15, 0))
        ttk.Button(row2, text="أكبر الملفات", command=self.start_largest).pack(side="left", padx=8)
        wrapper, self.tree = make_treeview(self, ("name", "path", "size", "date"),
                                            ("الاسم", "المسار", "الحجم", "تاريخ التعديل"), (220, 380, 100, 150))
        wrapper.pack(fill="both", expand=True, padx=20, pady=15)
        for col in ("name", "path", "size", "date"):
            self.tree.heading(col, command=lambda c=col: self.sort_by(c))
        self.status_label = tk.Label(self, text="", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9))
        self.status_label.pack(anchor="w", padx=20, pady=(0, 10))
        self._sort_reverse = {}

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.path_var.set(d)

    def start_search(self):
        self.status_label.config(text="جاري البحث...")
        threading.Thread(target=self._search_worker, args=(False,), daemon=True).start()

    def start_largest(self):
        self.status_label.config(text="جاري البحث عن أكبر الملفات...")
        threading.Thread(target=self._search_worker, args=(True,), daemon=True).start()

    def _search_worker(self, largest_mode):
        try:
            min_mb = float(self.min_size_var.get() or 0)
        except ValueError:
            min_mb = 0
        min_bytes = int(min_mb * 1024 * 1024)
        root_path = self.path_var.get().strip() or "C:\\"
        results = scan_files(root_path, self.name_var.get().strip(), self.ext_var.get(), min_bytes)
        if largest_mode:
            results.sort(key=lambda r: r[2], reverse=True)
            results = results[:100]
        self.results = results
        self.after(0, self._populate)

    def _populate(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for name, full, size, mtime in self.results:
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            self.tree.insert("", "end", values=(name, full, human_size(size), date_str))
        self.status_label.config(text=f"تم العثور على {len(self.results)} ملف.")

    def sort_by(self, col):
        idx_map = {"name": 0, "path": 1, "size": 2, "date": 3}
        idx = idx_map[col]
        reverse = self._sort_reverse.get(col, False)
        self.results.sort(key=lambda r: r[idx], reverse=reverse)
        self._sort_reverse[col] = not reverse
        self._populate()


class SysInfoFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.info = {}
        self._build_ui()

    def _build_ui(self):
        section_title(self, "معلومات النظام").pack(anchor="w", padx=20, pady=(20, 10))
        toolbar = tk.Frame(self, bg=BG_MAIN)
        toolbar.pack(fill="x", padx=20)
        ttk.Button(toolbar, text="تحديث", command=self.refresh).pack(side="left")
        ttk.Button(toolbar, text="تصدير تقرير PDF", command=self.export_pdf).pack(side="left", padx=8)
        wrapper, self.tree = make_treeview(self, ("key", "value"), ("الخاصية", "القيمة"), (200, 500))
        wrapper.pack(fill="both", expand=True, padx=20, pady=15)

    def on_show(self):
        if not self.info:
            self.refresh()

    def on_hide(self):
        pass

    def refresh(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        info = get_system_info()
        self.after(0, lambda: self._populate(info))

    def _populate(self, info):
        self.info = info
        for row in self.tree.get_children():
            self.tree.delete(row)
        for k, v in info.items():
            self.tree.insert("", "end", values=(k, v))

    def export_pdf(self):
        if not self.info:
            messagebox.showinfo(APP_NAME, "قم بالتحديث أولاً.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                             initialfile="system_report.pdf")
        if not path:
            return
        lines = [f"PC Suite Pro - System Report", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        for k, v in self.info.items():
            lines.append(f"{k}: {v}")
        try:
            text_report_to_pdf(lines, path)
            messagebox.showinfo(APP_NAME, f"تم حفظ التقرير في:\n{path}")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"تعذر إنشاء الملف: {e}")


class NetworkFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.active = False
        self.last_counters = None
        self._build_ui()

    def _build_ui(self):
        section_title(self, "مراقب الشبكة").pack(anchor="w", padx=20, pady=(20, 10))
        speed_frame = tk.Frame(self, bg=BG_MAIN)
        speed_frame.pack(fill="x", padx=20)
        self.down_label = tk.Label(speed_frame, text="التنزيل: -- KB/s", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 12))
        self.down_label.pack(side="left", padx=(0, 30))
        self.up_label = tk.Label(speed_frame, text="الرفع: -- KB/s", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 12))
        self.up_label.pack(side="left")
        ping_frame = tk.Frame(self, bg=BG_MAIN)
        ping_frame.pack(fill="x", padx=20, pady=15)
        ttk.Button(ping_frame, text="اختبار البينج (Ping)", command=self.run_ping).pack(side="left")
        self.ping_label = tk.Label(ping_frame, text="", bg=BG_MAIN, fg=FG_TEXT)
        self.ping_label.pack(side="left", padx=15)
        speedtest_frame = tk.Frame(self, bg=BG_MAIN)
        speedtest_frame.pack(fill="x", padx=20, pady=(0, 10))
        ttk.Button(speedtest_frame, text="قياس سرعة الإنترنت", command=self.run_speedtest).pack(side="left")
        self.speedtest_status = tk.Label(speedtest_frame, text="", bg=BG_MAIN, fg=FG_TEXT)
        self.speedtest_status.pack(side="left", padx=15)
        result_frame = tk.Frame(self, bg=BG_MAIN)
        result_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.download_mbps_label = tk.Label(result_frame, text="التنزيل: -- Mbps", bg=BG_MAIN, fg=ACCENT,
                                             font=("Segoe UI", 12, "bold"))
        self.download_mbps_label.pack(side="left", padx=(0, 30))
        self.upload_mbps_label = tk.Label(result_frame, text="الرفع: -- Mbps", bg=BG_MAIN, fg=ACCENT2,
                                           font=("Segoe UI", 12, "bold"))
        self.upload_mbps_label.pack(side="left")
        tk.Label(self, text="الأجهزة المتصلة بالشبكة", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=20, pady=(10, 5))
        ttk.Button(self, text="فحص الأجهزة المتصلة", command=self.scan_devices).pack(anchor="w", padx=20)
        wrapper, self.tree = make_treeview(self, ("ip", "mac", "type"), ("عنوان IP", "MAC Address", "النوع"),
                                            (180, 200, 120))
        wrapper.pack(fill="both", expand=True, padx=20, pady=15)

    def on_show(self):
        self.active = True
        if psutil is None:
            messagebox.showerror(APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ: pip install psutil")
            return
        self._loop()

    def on_hide(self):
        self.active = False

    def _loop(self):
        if not self.active:
            return
        threading.Thread(target=self._update_once, daemon=True).start()
        self.after(1000, self._loop)

    def _update_once(self):
        try:
            counters = psutil.net_io_counters()
            now = time.time()
            if self.last_counters:
                prev, prev_time = self.last_counters
                elapsed = max(now - prev_time, 0.001)
                down_speed = (counters.bytes_recv - prev.bytes_recv) / elapsed
                up_speed = (counters.bytes_sent - prev.bytes_sent) / elapsed
            else:
                down_speed = 0
                up_speed = 0
            self.last_counters = (counters, now)
        except Exception:
            return
        self.after(0, lambda: self._render(down_speed, up_speed))

    def _render(self, down_speed, up_speed):
        self.down_label.config(text=f"التنزيل: {human_size(down_speed)}/s")
        self.up_label.config(text=f"الرفع: {human_size(up_speed)}/s")

    def run_ping(self):
        self.ping_label.config(text="جاري الاختبار...")
        threading.Thread(target=self._ping_worker, daemon=True).start()

    def _ping_worker(self):
        result = ping_test()
        self.after(0, lambda: self.ping_label.config(text=result))

    def run_speedtest(self):
        self.speedtest_status.config(text="جاري قياس السرعة، الرجاء الانتظار...")
        self.download_mbps_label.config(text="التنزيل: -- Mbps")
        self.upload_mbps_label.config(text="الرفع: -- Mbps")
        threading.Thread(target=self._speedtest_worker, daemon=True).start()

    def _speedtest_worker(self):
        down = speedtest_download()
        self.after(0, lambda: self.download_mbps_label.config(
            text=f"التنزيل: {down:.1f} Mbps" if down is not None else "التنزيل: تعذر القياس"))
        up = speedtest_upload()
        self.after(0, lambda: self.upload_mbps_label.config(
            text=f"الرفع: {up:.1f} Mbps" if up is not None else "الرفع: تعذر القياس"))
        self.after(0, lambda: self.speedtest_status.config(text="اكتمل قياس السرعة."))

    def scan_devices(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        threading.Thread(target=self._devices_worker, daemon=True).start()

    def _devices_worker(self):
        devices = get_arp_devices()
        self.after(0, lambda: self._populate_devices(devices))

    def _populate_devices(self, devices):
        for ip, mac, kind in devices:
            self.tree.insert("", "end", values=(ip, mac, kind))


class BoosterFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.selected_var = tk.StringVar(value="")
        self.search_var = tk.StringVar(value="")
        self.pid_map = {}
        self.all_values = []
        self._build_ui()

    def _build_ui(self):
        section_title(self, "معزز أداء المعالج والذاكرة").pack(anchor="w", padx=20, pady=(20, 10))
        tk.Label(self, text="يرفع أولوية البرنامج المحدد (مثل لعبة) ويخفض أولوية باقي البرامج غير الأساسية لتحسين الأداء.",
                 bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        search_row = tk.Frame(self, bg=BG_MAIN)
        search_row.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(search_row, text="ابحث عن التطبيق:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=8)
        self.search_entry.bind("<KeyRelease>", self._on_search)
        row = tk.Frame(self, bg=BG_MAIN)
        row.pack(fill="x", padx=20, pady=10)
        tk.Label(row, text="اختر البرنامج:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        self.combo = ttk.Combobox(row, textvariable=self.selected_var, state="readonly", width=45)
        self.combo.pack(side="left", padx=8)
        ttk.Button(row, text="تحديث القائمة", command=self.refresh_list).pack(side="left", padx=8)
        actions = tk.Frame(self, bg=BG_MAIN)
        actions.pack(fill="x", padx=20)
        ttk.Button(actions, text="⚡ تفعيل التعزيز", command=self.boost).pack(side="left")
        ttk.Button(actions, text="استعادة الأولوية الطبيعية للجميع", command=self.restore).pack(side="left", padx=8)
        self.status_label = tk.Label(self, text="", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9))
        self.status_label.pack(anchor="w", padx=20, pady=15)

    def on_show(self):
        self.refresh_list()

    def on_hide(self):
        pass

    def refresh_list(self):
        if psutil is None:
            messagebox.showerror(APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ: pip install psutil")
            return
        self.pid_map = {}
        display_values = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                name = p.info["name"] or "?"
                if name.lower() in CRITICAL_PROCESSES:
                    continue
                label = f"{name} (PID {p.info['pid']})"
                self.pid_map[label] = p.info["pid"]
                display_values.append(label)
            except Exception:
                continue
        display_values.sort()
        self.all_values = display_values
        self._on_search()

    def _on_search(self, event=None):
        query = self.search_var.get().strip().lower()
        if not query:
            filtered = self.all_values
        else:
            filtered = [v for v in self.all_values if query in v.lower()]
        self.combo["values"] = filtered
        if self.selected_var.get() not in filtered:
            self.selected_var.set(filtered[0] if filtered else "")

    def boost(self):
        label = self.selected_var.get()
        if not label or label not in self.pid_map:
            messagebox.showinfo(APP_NAME, "اختر برنامجاً من القائمة أولاً.")
            return
        pid = self.pid_map[label]
        threading.Thread(target=self._boost_worker, args=(pid, label), daemon=True).start()

    def _boost_worker(self, pid, label):
        try:
            target = psutil.Process(pid)
            target.nice(psutil.HIGH_PRIORITY_CLASS)
            try:
                target.io_priority(psutil.IOPRIO_HIGH)
            except Exception:
                pass
        except Exception as e:
            self.after(0, lambda: self.status_label.config(text=f"تعذر رفع أولوية البرنامج المستهدف: {e}"))
            return
        count = 0
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if p.info["pid"] == pid:
                    continue
                lname = (p.info["name"] or "").lower()
                if lname in CRITICAL_PROCESSES:
                    continue
                proc = psutil.Process(p.info["pid"])
                proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                count += 1
            except Exception:
                continue
        self.after(0, lambda: self.status_label.config(
            text=f"تم رفع أولوية {label} وخفض أولوية {count} عملية أخرى."))

    def restore(self):
        threading.Thread(target=self._restore_worker, daemon=True).start()

    def _restore_worker(self):
        count = 0
        for p in psutil.process_iter(["pid", "name"]):
            try:
                lname = (p.info["name"] or "").lower()
                if lname in CRITICAL_PROCESSES:
                    continue
                proc = psutil.Process(p.info["pid"])
                proc.nice(psutil.NORMAL_PRIORITY_CLASS)
                count += 1
            except Exception:
                continue
        self.after(0, lambda: self.status_label.config(text=f"تمت استعادة الأولوية الطبيعية لـ {count} عملية."))


class BoostFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.vars = {}
        self.log_lines = []
        self._build_ui()

    def _build_ui(self):
        section_title(self, "تعزيز FPS والأداء الشامل").pack(anchor="w", padx=20, pady=(20, 10))
        tk.Label(self,
                 text="يعطّل هذا الخيار خدمات ومزايا Windows غير الضرورية للألعاب (تيليمتري، فهرسة، تسجيل الألعاب،\n"
                      "تطبيقات الخلفية، إشعارات) ويضبط الشبكة وخطة الطاقة لتقليل زمن الاستجابة. لا يتم لمس أي\n"
                      "إعداد أمني مثل Windows Defender أو الجدار الناري أو التحديثات الأمنية.",
                 bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9), justify="right").pack(anchor="w", padx=20)

        scroll_wrapper = tk.Frame(self, bg=BG_MAIN)
        scroll_wrapper.pack(fill="both", expand=True, padx=20, pady=(15, 5))
        canvas = tk.Canvas(scroll_wrapper, bg=BG_MAIN, highlightthickness=0, height=280)
        vsb = ttk.Scrollbar(scroll_wrapper, orient="vertical", command=canvas.yview)
        options_frame = tk.Frame(canvas, bg=BG_MAIN)
        options_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=options_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        tk.Label(options_frame, text="خدمات Microsoft غير الضرورية", bg=BG_MAIN, fg=ACCENT2,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5, 3))
        for svc_name, desc in TWEAK_SERVICES.items():
            var = tk.BooleanVar(value=True)
            self.vars[svc_name] = var
            ttk.Checkbutton(options_frame, text=f"{desc} ({svc_name})", variable=var).pack(anchor="w", padx=5, pady=2)

        tk.Label(options_frame, text="مزايا وواجهة النظام", bg=BG_MAIN, fg=ACCENT2,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 3))
        for tw in REGISTRY_TWEAKS:
            var = tk.BooleanVar(value=True)
            self.vars[tw["id"]] = var
            ttk.Checkbutton(options_frame, text=tw["label"], variable=var).pack(anchor="w", padx=5, pady=2)

        tk.Label(options_frame, text="الشبكة وخطة الطاقة", bg=BG_MAIN, fg=ACCENT2,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 3))
        for opt_id, opt_label in BOOST_EXTRA_OPTIONS:
            var = tk.BooleanVar(value=True)
            self.vars[opt_id] = var
            ttk.Checkbutton(options_frame, text=opt_label, variable=var).pack(anchor="w", padx=5, pady=2)

        actions = tk.Frame(self, bg=BG_MAIN)
        actions.pack(fill="x", padx=20, pady=15)
        ttk.Button(actions, text="⚡ تفعيل تعزيز FPS", command=self.apply).pack(side="left")
        ttk.Button(actions, text="استعادة الإعدادات الأصلية", command=self.restore).pack(side="left", padx=8)
        ttk.Button(actions, text="تحديد الكل", command=lambda: self._set_all(True)).pack(side="left", padx=8)
        ttk.Button(actions, text="إلغاء تحديد الكل", command=lambda: self._set_all(False)).pack(side="left", padx=8)

        self.log_box = scrolledtext.ScrolledText(self, height=8, bg=BG_PANEL, fg=FG_TEXT,
                                                   font=("Consolas", 9), state="disabled")
        self.log_box.pack(fill="both", expand=False, padx=20, pady=(0, 20))

    def on_show(self):
        pass

    def on_hide(self):
        pass

    def _set_all(self, value):
        for var in self.vars.values():
            var.set(value)

    def _log(self, message):
        def _write():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _write)

    def apply(self):
        if not messagebox.askyesno(
                APP_NAME,
                "سيتم تطبيق تعديلات على خدمات وإعدادات النظام لتحسين الأداء أثناء الألعاب.\n"
                "لا يشمل ذلك أي إعداد أمني، ويمكنك التراجع في أي وقت من زر الاستعادة.\nهل تريد المتابعة؟"):
            return
        selected_ids = [key for key, var in self.vars.items() if var.get()]
        threading.Thread(target=self._apply_worker, args=(selected_ids,), daemon=True).start()

    def _apply_worker(self, selected_ids):
        self._log("جاري تفعيل تعزيز FPS...")
        try:
            apply_boost(selected_ids, self._log)
        except Exception as e:
            self._log(f"حدث خطأ أثناء التفعيل: {e}")

    def restore(self):
        if not messagebox.askyesno(APP_NAME, "سيتم استعادة كل الإعدادات إلى وضعها الأصلي قبل التعزيز. هل تريد المتابعة؟"):
            return
        threading.Thread(target=self._restore_worker, daemon=True).start()

    def _restore_worker(self):
        self._log("جاري استعادة الإعدادات الأصلية...")
        try:
            restore_boost(self._log)
        except Exception as e:
            self._log(f"حدث خطأ أثناء الاستعادة: {e}")


class VideoDownloaderFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_MAIN)
        self.controller = controller
        self.formats_data = []
        self.output_dir = os.path.join(get_user_profile(), "Downloads")
        self._build_ui()

    def _build_ui(self):
        section_title(self, "تحميل الفيديوهات").pack(anchor="w", padx=20, pady=(20, 10))
        tk.Label(self, text="يدعم يوتيوب وتيك توك وإنستقرام وأي منصة أخرى مدعومة من مكتبة yt-dlp.",
                 bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=20)

        url_row = tk.Frame(self, bg=BG_MAIN)
        url_row.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(url_row, text="رابط الفيديو:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        self.url_var = tk.StringVar()
        ttk.Entry(url_row, textvariable=self.url_var, width=55).pack(side="left", padx=8)
        ttk.Button(url_row, text="جلب الجودات المتاحة", command=self.fetch_formats).pack(side="left", padx=8)

        wrapper, self.tree = make_treeview(
            self, ("quality", "ext", "size", "kind", "fps"),
            ("الجودة", "الامتداد", "الحجم التقريبي", "النوع", "FPS"), (110, 70, 130, 130, 60))
        wrapper.pack(fill="both", expand=True, padx=20, pady=10)

        out_row = tk.Frame(self, bg=BG_MAIN)
        out_row.pack(fill="x", padx=20, pady=(0, 5))
        tk.Label(out_row, text="مجلد الحفظ:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left")
        self.output_label = tk.Label(out_row, text=self.output_dir, bg=BG_MAIN, fg=ACCENT2, font=("Segoe UI", 9))
        self.output_label.pack(side="left", padx=8)
        ttk.Button(out_row, text="تغيير المجلد", command=self.choose_folder).pack(side="left", padx=8)

        actions = tk.Frame(self, bg=BG_MAIN)
        actions.pack(fill="x", padx=20, pady=10)
        ttk.Button(actions, text="⬇️ تحميل بالجودة المحددة", command=self.download_selected).pack(side="left")

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(5, 5))
        self.status_label = tk.Label(self, text="", bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9))
        self.status_label.pack(anchor="w", padx=20, pady=(0, 15))

    def on_show(self):
        pass

    def on_hide(self):
        pass

    def fetch_formats(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showinfo(APP_NAME, "أدخل رابط الفيديو أولاً.")
            return
        if yt_dlp is None:
            messagebox.showerror(APP_NAME, "المكتبة yt-dlp غير مثبتة.\nنفّذ: pip install yt-dlp")
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.formats_data = []
        self.status_label.config(text="جاري جلب الجودات المتاحة...")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            self.after(0, lambda: self.status_label.config(text=f"تعذر جلب المعلومات: {e}"))
            return
        formats = info.get("formats") or []
        rows = []
        for f in formats:
            vcodec = f.get("vcodec") or "none"
            acodec = f.get("acodec") or "none"
            if vcodec == "none" and acodec == "none":
                continue
            height = f.get("height") or 0
            if vcodec == "none":
                quality = f"صوت فقط ({f.get('abr') or '?'} kbps)"
                kind = "صوت فقط"
            else:
                quality = f"{height}p" if height else (f.get("format_note") or "غير معروف")
                kind = "فيديو+صوت" if acodec != "none" else "فيديو فقط"
            size = f.get("filesize") or f.get("filesize_approx")
            rows.append({
                "format_id": f.get("format_id"),
                "ext": f.get("ext") or "",
                "quality": quality,
                "height": height,
                "size": human_size(size) if size else "غير معروف",
                "kind": kind,
                "fps": f.get("fps") or "",
            })
        rows.sort(key=lambda r: r["height"], reverse=True)
        title = info.get("title", "")
        self.after(0, lambda: self._populate(rows, title))

    def _populate(self, rows, title):
        self.formats_data = rows
        for row in self.tree.get_children():
            self.tree.delete(row)
        for r in rows:
            self.tree.insert("", "end", values=(r["quality"], r["ext"], r["size"], r["kind"], r["fps"]))
        self.status_label.config(
            text=f"تم العثور على {len(rows)} جودة - {title}" if rows else "لم يتم العثور على أي جودة لهذا الرابط.")

    def choose_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir = d
            self.output_label.config(text=d)

    def download_selected(self):
        if yt_dlp is None:
            messagebox.showerror(APP_NAME, "المكتبة yt-dlp غير مثبتة.\nنفّذ: pip install yt-dlp")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "اختر جودة من القائمة أولاً.")
            return
        url = self.url_var.get().strip()
        if not url:
            return
        idx = self.tree.index(sel[0])
        fmt = self.formats_data[idx]
        self.progress["value"] = 0
        self.status_label.config(text="جاري التحميل...")
        threading.Thread(target=self._download_worker, args=(url, fmt), daemon=True).start()

    def _download_worker(self, url, fmt):
        format_id = fmt["format_id"]
        format_selector = f"{format_id}+bestaudio/best" if fmt["kind"] == "فيديو فقط" else format_id
        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        def hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    pct = downloaded / total * 100
                    self.after(0, lambda: self.progress.config(value=pct))
            elif d.get("status") == "finished":
                self.after(0, lambda: self.progress.config(value=100))

        opts = {
            "format": format_selector,
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
            "merge_output_format": "mp4",
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, lambda: self.status_label.config(text=f"تم التحميل بنجاح إلى: {self.output_dir}"))
        except Exception as e:
            self.after(0, lambda: self.status_label.config(text=f"فشل التحميل: {e}"))


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1250x750")
        self.root.configure(bg=BG_MAIN)
        self.current_key = None
        self._build_style()
        self._build_layout()

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG_MAIN)
        style.configure("TLabel", background=BG_MAIN, foreground=FG_TEXT, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=BG_MAIN, foreground=ACCENT, font=("Segoe UI", 14, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background=ACCENT, foreground="#ffffff")
        style.map("TButton", background=[("active", "#16a34a"), ("pressed", "#15803d")])
        style.configure("TCheckbutton", background=BG_MAIN, foreground=FG_TEXT, font=("Segoe UI", 9))
        style.configure("TCombobox", fieldbackground=BG_PANEL, background=BG_PANEL, foreground=FG_TEXT)
        style.configure("Treeview", background=BG_PANEL, foreground=FG_TEXT, fieldbackground=BG_PANEL, rowheight=24)
        style.configure("Treeview.Heading", background="#374151", foreground=FG_TEXT, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT2)], foreground=[("selected", BG_MAIN)])
        style.configure("Horizontal.TProgressbar", troughcolor=BG_PANEL, background=ACCENT,
                         bordercolor=BG_PANEL, lightcolor=ACCENT, darkcolor=ACCENT)

    def _build_layout(self):
        outer = tk.Frame(self.root, bg=BG_MAIN)
        outer.pack(fill="both", expand=True)
        sidebar = tk.Frame(outer, bg=BG_SIDEBAR, width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text=APP_NAME, bg=BG_SIDEBAR, fg=ACCENT, font=("Segoe UI", 13, "bold")).pack(
            pady=(20, 15), padx=15, anchor="w")
        self.nav_buttons = {}
        for key, label in NAV_ITEMS:
            btn = tk.Button(sidebar, text=label, anchor="w", bg=BG_SIDEBAR, fg="#e5e7eb",
                             activebackground=BG_PANEL, activeforeground="#ffffff",
                             bd=0, font=("Segoe UI", 10), padx=15, pady=10, cursor="hand2",
                             command=lambda k=key: self.show_frame(k))
            btn.pack(fill="x")
            self.nav_buttons[key] = btn
        content = tk.Frame(outer, bg=BG_MAIN)
        content.pack(side="left", fill="both", expand=True)
        self.content = content
        classes = {
            "cleaner": CleanerFrame,
            "dashboard": DashboardFrame,
            "processes": ProcessFrame,
            "startup": StartupFrame,
            "explorer": ExplorerFrame,
            "sysinfo": SysInfoFrame,
            "network": NetworkFrame,
            "booster": BoosterFrame,
            "boost": BoostFrame,
            "downloader": VideoDownloaderFrame,
        }
        self.frames = {}
        for key, cls in classes.items():
            frame = cls(content, self)
            frame.place(relwidth=1, relheight=1)
            self.frames[key] = frame
        self.show_frame("cleaner")

    def show_frame(self, key):
        if self.current_key and self.current_key in self.frames:
            prev = self.frames[self.current_key]
            if hasattr(prev, "on_hide"):
                prev.on_hide()
        for k, btn in self.nav_buttons.items():
            btn.config(bg=ACCENT if k == key else BG_SIDEBAR, fg="#ffffff" if k == key else "#e5e7eb")
        frame = self.frames[key]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()
        self.current_key = key


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
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
