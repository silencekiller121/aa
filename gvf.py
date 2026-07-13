import os
import sys
import shutil
import subprocess
import threading
import time
import json
import platform
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime
try:
    import ctypes
except Exception:
    ctypes = None
try:
    import winreg
except Exception:
    winreg = None
try:
    import psutil
except ImportError:
    psutil = None
try:
    import yt_dlp
except ImportError:
    yt_dlp = None
from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QTimer, QSize, QPoint, QRectF, QEasingCurve,
    QPropertyAnimation, Property,
)
from PySide6.QtGui import (
    QIcon, QFont, QPixmap, QPainter, QColor, QLinearGradient, QPen, QBrush,
    QPainterPath, QCursor,
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QCheckBox,
    QFrame, QGraphicsDropShadowEffect, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QScrollArea,
    QPlainTextEdit, QProgressBar, QSizePolicy, QSpacerItem, QSpinBox,
    QTextEdit, QToolButton,
)
WDA_EXCLUDEFROMCAPTURE = 0x00000011
APP_NAME = "PC Suite Pro"
APP_INITIALS = "PS"
LOG_PATH = os.path.join(os.environ.get("USERPROFILE", str(Path.home())), "pc_suite_pro_log.txt")
DISABLED_STARTUP_JSON = os.path.join(os.environ.get("USERPROFILE", str(Path.home())), "pc_suite_pro_disabled_startup.json")
BOOST_BACKUP_JSON = os.path.join(os.environ.get("USERPROFILE", str(Path.home())), "pc_suite_pro_boost_backup.json")
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
     "hive": "HKCU", "path": r"System\GameConfigStore",
     "name": "GameDVR_Enabled", "type": "DWORD", "boost": 0},
    {"id": "appcapture", "label": "تعطيل تسجيل الألعاب التلقائي",
     "hive": "HKCU", "path": r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
     "name": "AppCaptureEnabled", "type": "DWORD", "boost": 0},
    {"id": "bgapps", "label": "تعطيل تطبيقات الخلفية",
     "hive": "HKCU", "path": r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
     "name": "GlobalUserDisabled", "type": "DWORD", "boost": 1},
    {"id": "tips", "label": "تعطيل نصائح واقتراحات ويندوز",
     "hive": "HKCU", "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "name": "SystemPaneSuggestionsEnabled", "type": "DWORD", "boost": 0},
    {"id": "silenthours", "label": "تعطيل الإشعارات المنبثقة غير الضرورية",
     "hive": "HKCU", "path": r"Software\Microsoft\Windows\CurrentVersion\PushNotifications",
     "name": "ToastEnabled", "type": "DWORD", "boost": 0},
    {"id": "visualfx", "label": "ضبط المؤثرات البصرية على أفضل أداء",
     "hive": "HKCU", "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
     "name": "VisualFXSetting", "type": "DWORD", "boost": 2},
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
NAV_ITEMS = [
    ("cleaner", "تنظيف القرص", "🧹"),
    ("dashboard", "لوحة الأداء", "📊"),
    ("processes", "إدارة العمليات", "🧠"),
    ("startup", "محسّن الإقلاع", "🚀"),
    ("explorer", "مستكشف الملفات", "📁"),
    ("sysinfo", "معلومات النظام", "🧾"),
    ("network", "مراقب الشبكة", "🌐"),
    ("booster", "معزز برنامج محدد", "⚡"),
    ("boost", "تعزيز FPS الشامل", "🎮"),
    ("downloader", "تحميل الفيديوهات", "⬇️"),
]
PALETTES = {
    "dark": {
        "app_bg": "#05070c",
        "sidebar_top": "#0b101c",
        "sidebar_bottom": "#070a12",
        "panel": "#111827",
        "panel_alt": "#161f2e",
        "panel_border": "#1f2937",
        "input_bg": "#0d1420",
        "text": "#eef2f7",
        "text_dim": "#8b96ac",
        "text_faint": "#5b6478",
        "accent": "#27e07a",
        "accent_hover": "#4dffa0",
        "accent2": "#22d3ee",
        "accent2_hover": "#5ee8fb",
        "purple": "#a855f7",
        "warn": "#fbbf24",
        "danger": "#f8697a",
        "danger_hover": "#ff8494",
        "shadow": QColor(0, 0, 0, 190),
        "glow_accent": QColor(39, 224, 122, 110),
        "glow_accent2": QColor(34, 211, 238, 110),
        "scrollbar": "#1f2937",
    },
    "light": {
        "app_bg": "#eef1f6",
        "sidebar_top": "#ffffff",
        "sidebar_bottom": "#f3f5f9",
        "panel": "#ffffff",
        "panel_alt": "#f6f8fb",
        "panel_border": "#e2e6ee",
        "input_bg": "#f3f5f9",
        "text": "#12172a",
        "text_dim": "#5b6478",
        "text_faint": "#8b96ac",
        "accent": "#16a34a",
        "accent_hover": "#15803d",
        "accent2": "#0891b2",
        "accent2_hover": "#0e7490",
        "purple": "#7c3aed",
        "warn": "#d97706",
        "danger": "#dc2626",
        "danger_hover": "#b91c1c",
        "shadow": QColor(30, 41, 59, 45),
        "glow_accent": QColor(22, 163, 74, 60),
        "glow_accent2": QColor(8, 145, 178, 60),
        "scrollbar": "#e2e6ee",
    },
}
class ThemeBus(QObject):
    changed = Signal(bool)
theme_bus = ThemeBus()
CURRENT_THEME = {"dark": True}
def palette():
    return PALETTES["dark" if CURRENT_THEME["dark"] else "light"]
def build_stylesheet():
    p = palette()
    return f"""
    QWidget {{
        background-color: {p['app_bg']};
        color: {p['text']};
        font-family: 'Segoe UI';
        font-size: 13px;
    }}
    QToolTip {{
        background-color: {p['panel_alt']};
        color: {p['text']};
        border: 1px solid {p['panel_border']};
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['scrollbar']};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['accent']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ height: 0; }}
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {p['input_bg']};
        border: 1px solid {p['panel_border']};
        border-radius: 8px;
        padding: 7px 12px;
        color: {p['text']};
        selection-background-color: {p['accent']};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {p['accent']};
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background-color: {p['panel_alt']};
        color: {p['text']};
        border: 1px solid {p['panel_border']};
        selection-background-color: {p['accent']};
        outline: none;
    }}
    QPlainTextEdit, QTextEdit {{
        background-color: {p['panel_alt']};
        border: 1px solid {p['panel_border']};
        border-radius: 10px;
        color: {p['accent2']};
        font-family: 'Consolas';
        font-size: 12px;
        padding: 8px;
    }}
    QTableWidget {{
        background-color: {p['panel']};
        alternate-background-color: {p['panel_alt']};
        border: 1px solid {p['panel_border']};
        border-radius: 10px;
        gridline-color: transparent;
        color: {p['text']};
        selection-background-color: {p['accent']}55;
        selection-color: {p['text']};
    }}
    QTableWidget::item {{
        padding: 7px;
        border-bottom: 1px solid {p['panel_border']};
    }}
    QHeaderView::section {{
        background-color: {p['panel_alt']};
        color: {p['text_dim']};
        border: none;
        border-bottom: 2px solid {p['panel_border']};
        padding: 9px 8px;
        font-weight: 600;
    }}
    QProgressBar {{
        background-color: {p['panel_alt']};
        border: 1px solid {p['panel_border']};
        border-radius: 8px;
        text-align: center;
        color: {p['text']};
        height: 16px;
    }}
    QProgressBar::chunk {{
        border-radius: 7px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {p['accent']}, stop:1 {p['accent2']});
    }}
    QCheckBox {{ spacing: 8px; color: {p['text']}; }}
    QCheckBox::indicator {{
        width: 17px; height: 17px; border-radius: 5px;
        border: 1px solid {p['panel_border']};
        background-color: {p['input_bg']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p['accent']};
        border: 1px solid {p['accent']};
    }}
    QMessageBox {{ background-color: {p['panel']}; }}
    QMessageBox QLabel {{ color: {p['text']}; }}
    QMessageBox QPushButton {{
        background-color: {p['panel_alt']}; color: {p['text']};
        border-radius: 6px; padding: 7px 18px; border: 1px solid {p['panel_border']};
    }}
    QMessageBox QPushButton:hover {{ background-color: {p['accent']}33; }}
    """
def accent_button_style(bg, hover, fg="#04120b"):
    return (
        f"QPushButton {{ background-color: {bg}; color: {fg}; border: none;"
        f" border-radius: 9px; padding: 9px 18px; font-weight: 700; }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
        f"QPushButton:disabled {{ background-color: #4b5563; color: #9ca3af; }}"
    )
def ghost_button_style():
    p = palette()
    return (
        f"QPushButton {{ background-color: {p['panel_alt']}; color: {p['text']}; border: 1px solid {p['panel_border']};"
        f" border-radius: 9px; padding: 9px 16px; font-weight: 600; }}"
        f"QPushButton:hover {{ border: 1px solid {p['accent']}; color: {p['accent']}; }}"
        f"QPushButton:disabled {{ color: {p['text_faint']}; }}"
    )
def get_user_profile():
    return os.environ.get("USERPROFILE", str(Path.home()))
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_DIR = os.path.join(get_user_profile(), "pc_suite_pro_ffmpeg")
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFPROBE_EXE = os.path.join(FFMPEG_DIR, "ffprobe.exe")
def local_ffmpeg_available():
    return os.path.exists(FFMPEG_EXE) and os.path.exists(FFPROBE_EXE)
def ffmpeg_ready():
    return shutil.which("ffmpeg") is not None or local_ffmpeg_available()
def ffmpeg_location_for_ytdlp():
    if shutil.which("ffmpeg"):
        return None
    if local_ffmpeg_available():
        return FFMPEG_DIR
    return None
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
def enable_anti_screenshot(hwnd):
    if os.name != "nt" or not ctypes:
        return False
    try:
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(int(hwnd), WDA_EXCLUDEFROMCAPTURE))
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
def _reg_type(name):
    return getattr(winreg, name) if winreg else None
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
        hive = winreg.HKEY_CURRENT_USER if tw["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        vtype = _reg_type(tw["type"]) if isinstance(tw["type"], str) else tw["type"]
        backup["registry"][tw["id"]] = read_reg_value(hive, tw["path"], tw["name"])
        write_reg_value(hive, tw["path"], tw["name"], tw["boost"], vtype)
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
            hive = winreg.HKEY_CURRENT_USER if tw["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            vtype = _reg_type(tw["type"]) if isinstance(tw["type"], str) else tw["type"]
            original = backup["registry"][tw["id"]]
            if original is None:
                delete_reg_value(hive, tw["path"], tw["name"])
            else:
                write_reg_value(hive, tw["path"], tw["name"], original, vtype)
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
class Worker(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    done = Signal(object)
    failed = Signal(str)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    def run(self):
        try:
            result = self.func(self.log.emit, self.progress.emit, *self.args, **self.kwargs)
            self.done.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
class SimpleWorker(QThread):
    done = Signal(object)
    failed = Signal(str)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.done.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
def keep_ref(owner, worker, attr="_workers"):
    if not hasattr(owner, attr):
        setattr(owner, attr, [])
    lst = getattr(owner, attr)
    lst.append(worker)
    worker.finished.connect(lambda: lst.remove(worker) if worker in lst else None)
def make_icon(size=128, text=APP_INITIALS):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#27e07a"))
    grad.setColorAt(1, QColor("#22d3ee"))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size * 0.28, size * 0.28)
    painter.setPen(QColor("#04120b"))
    font = QFont("Segoe UI", int(size * 0.34), QFont.Black)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)
def apply_shadow(widget, blur=28, color=None, x=0, y=6):
    p = palette()
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(x, y)
    eff.setColor(color or p["shadow"])
    widget.setGraphicsEffect(eff)
    return eff
class Card(QFrame):
    def __init__(self, parent=None, glow=False):
        super().__init__(parent)
        self.glow = glow
        self.setObjectName("Card")
        self.refresh_style()
        apply_shadow(self, blur=30 if not glow else 42)
    def refresh_style(self):
        p = palette()
        self.setStyleSheet(
            f"#Card {{ background-color: {p['panel']}; border: 1px solid {p['panel_border']};"
            f" border-radius: 16px; }}"
        )
class SectionTitle(QWidget):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 20px; font-weight: 800;")
        lay.addWidget(self.title_lbl)
        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet("font-size: 12px;")
            self.sub_lbl.setObjectName("dimText")
            lay.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None
        self.restyle()
    def restyle(self):
        p = palette()
        self.title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {p['text']};")
        if self.sub_lbl:
            self.sub_lbl.setStyleSheet(f"font-size: 12px; color: {p['text_dim']};")
class ToggleSwitch(QCheckBox):
    _TRACK_ON = QColor("#27e07a")
    _TRACK_OFF = QColor("#20242e")
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(56, 30)
        self._offset = 3
        self.anim = QPropertyAnimation(self, b"offset", self)
        self.anim.setDuration(180)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.stateChanged.connect(self._animate)
    def hitButton(self, pos):
        return self.rect().contains(pos)
    def _animate(self, state):
        end = self.width() - self.height() + 3 if state else 3
        self.anim.stop()
        self.anim.setStartValue(self._offset)
        self.anim.setEndValue(end)
        self.anim.start()
    def get_offset(self):
        return self._offset
    def set_offset(self, val):
        self._offset = val
        self.update()
    offset = Property(int, get_offset, set_offset)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        track_color = self._TRACK_ON if self.isChecked() else self._TRACK_OFF
        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(0, 0, r.width(), r.height(), r.height() / 2, r.height() / 2)
        knob_d = r.height() - 6
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(self._offset), 3, knob_d, knob_d)
        painter.end()
class Sparkline(QWidget):
    def __init__(self, color_key="accent", parent=None):
        super().__init__(parent)
        self.color_key = color_key
        self.data = []
        self.max_value = 100
        self.setMinimumSize(220, 46)
        self.setMaximumHeight(52)
    def set_data(self, data, max_value=100):
        self.data = data[-60:]
        self.max_value = max_value
        self.update()
    def paintEvent(self, event):
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["panel_alt"]))
        painter.drawRoundedRect(0, 0, w, h, 10, 10)
        if len(self.data) >= 2:
            color = QColor(p[self.color_key])
            n = len(self.data)
            step = (w - 8) / max(n - 1, 1)
            pts = []
            for i, v in enumerate(self.data):
                x = 4 + i * step
                y = h - 4 - (min(v, self.max_value) / max(self.max_value, 1)) * (h - 10)
                pts.append(QPoint(int(x), int(y)))
            path = QPainterPath()
            fill_path = QPainterPath()
            path.moveTo(pts[0])
            fill_path.moveTo(QPoint(pts[0].x(), h - 2))
            fill_path.lineTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
                fill_path.lineTo(pt)
            fill_path.lineTo(QPoint(pts[-1].x(), h - 2))
            fill_path.closeSubpath()
            grad = QLinearGradient(0, 0, 0, h)
            glow = QColor(color)
            glow.setAlpha(90)
            grad.setColorAt(0, glow)
            transparent = QColor(color)
            transparent.setAlpha(0)
            grad.setColorAt(1, transparent)
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawPath(fill_path)
            painter.setPen(QPen(color, 2.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
        painter.end()
class StatCard(Card):
    def __init__(self, title, value="--", color_key="accent", parent=None):
        super().__init__(parent)
        self.color_key = color_key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(4)
        top = QHBoxLayout()
        self.dot = QLabel("●")
        top.addWidget(self.dot)
        self.title_lbl = QLabel(title)
        top.addWidget(self.title_lbl)
        top.addStretch()
        lay.addLayout(top)
        self.value_lbl = QLabel(value)
        lay.addWidget(self.value_lbl)
        self.restyle()
    def set_value(self, text):
        self.value_lbl.setText(text)
    def restyle(self):
        self.refresh_style()
        p = palette()
        color = p.get(self.color_key, p["accent"])
        self.dot.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.title_lbl.setStyleSheet(f"color: {p['text_dim']}; font-size: 12px; font-weight: 600;")
        self.value_lbl.setStyleSheet(f"color: {p['text']}; font-size: 24px; font-weight: 800;")
class LogConsole(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self.setCursor(Qt.ArrowCursor)
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.appendPlainText(f"[{timestamp}] {msg}")
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {msg}\n")
        except Exception:
            pass
def make_table(headers, widths=None, checkable_first=False):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setFocusPolicy(Qt.NoFocus)
    if widths:
        for i, w in enumerate(widths):
            if w:
                table.setColumnWidth(i, w)
    return table
class IconButton(QToolButton):
    def __init__(self, icon_text, tooltip="", parent=None):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 38)
        self.restyle()
    def restyle(self):
        p = palette()
        self.setStyleSheet(
            f"QToolButton {{ background-color: {p['panel_alt']}; border: 1px solid {p['panel_border']};"
            f" border-radius: 10px; font-size: 15px; }}"
            f"QToolButton:hover {{ border: 1px solid {p['accent']}; }}"
        )
class LivePage:
    def start_live(self, interval_ms, work_fn, on_result):
        self._live_running = False
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(lambda: self._live_tick(work_fn, on_result))
        self._live_timer.start(interval_ms)
        self._live_tick(work_fn, on_result)
    def _live_tick(self, work_fn, on_result):
        if getattr(self, "_live_running", False):
            return
        self._live_running = True
        w = SimpleWorker(work_fn)
        def _done(result):
            self._live_running = False
            on_result(result)
        def _fail(_err):
            self._live_running = False
        w.done.connect(_done)
        w.failed.connect(_fail)
        keep_ref(self, w)
        w.start()
    def stop_live(self):
        if hasattr(self, "_live_timer"):
            self._live_timer.stop()
class BasePage(QWidget):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self._cards = []
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(28, 24, 28, 24)
        self.outer.setSpacing(16)
        self.header = SectionTitle(title, subtitle)
        self.outer.addWidget(self.header)
    def add_card(self, widget):
        self._cards.append(widget)
        return widget
    def on_show(self):
        pass
    def on_hide(self):
        pass
    def restyle(self):
        self.header.restyle()
        for c in self._cards:
            if hasattr(c, "restyle"):
                c.restyle()
def hint_label(text):
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    p = palette()
    lbl.setStyleSheet(f"color: {p['text_dim']}; font-size: 11.5px;")
    lbl.setObjectName("hintLabel")
    return lbl
class CleanerPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("تنظيف القرص", "فحص وتنظيف الملفات المؤقتة، الكاش، وبقايا البرامج المحذوفة بأمان.")
        self.targets = []
        self.scanning = False
        self.cleaning = False
        self._build_ui()
    def _build_ui(self):
        toolbar_card = self.add_card(Card(self))
        tl = QHBoxLayout(toolbar_card)
        tl.setContentsMargins(18, 14, 18, 14)
        self.scan_btn = QPushButton("🔍  فحص الجهاز")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self.start_scan)
        self.clean_btn = QPushButton("🧹  بدء التنظيف")
        self.clean_btn.setCursor(Qt.PointingHandCursor)
        self.clean_btn.clicked.connect(self.start_cleanup)
        self.select_all_btn = QPushButton("تحديد الكل")
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn = QPushButton("إلغاء التحديد")
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.dry_run_check = QCheckBox("وضع المعاينة فقط (بدون حذف)")
        self.restore_check = QCheckBox("إنشاء نقطة استعادة قبل الحذف")
        self.restore_check.setChecked(True)
        for b in (self.scan_btn, self.clean_btn, self.select_all_btn, self.deselect_all_btn):
            tl.addWidget(b)
        tl.addStretch()
        tl.addWidget(self.dry_run_check)
        tl.addWidget(self.restore_check)
        table_card = self.add_card(Card(self))
        table_lay = QVBoxLayout(table_card)
        table_lay.setContentsMargins(18, 16, 18, 16)
        table_lay.setSpacing(10)
        self.table = make_table(["✓", "الفئة", "العنصر", "المسار", "الحجم"], [40, 150, 240, 380, 100])
        self.table.itemChanged.connect(self._on_item_changed)
        table_lay.addWidget(self.table, 1)
        bottom_row = QHBoxLayout()
        self.total_label = QLabel("إجمالي الحجم المتوقع: 0 B")
        bottom_row.addWidget(self.total_label)
        bottom_row.addStretch()
        table_lay.addLayout(bottom_row)
        self.progress = QProgressBar()
        table_lay.addWidget(self.progress)
        log_card = self.add_card(Card(self))
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(18, 14, 18, 14)
        log_lay.addWidget(QLabel("السجل"))
        self.log_console = LogConsole()
        self.log_console.setFixedHeight(160)
        log_lay.addWidget(self.log_console)
        self.outer.addWidget(toolbar_card)
        self.outer.addWidget(table_card, 1)
        self.outer.addWidget(log_card)
        self.restyle()
        self.log_console.log("مرحباً. اضغط 'فحص الجهاز' للبدء.")
        self.log_console.log(f"سجل العمليات يُحفظ في: {LOG_PATH}")
    def restyle(self):
        super().restyle()
        p = palette()
        self.scan_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.clean_btn.setStyleSheet(accent_button_style(p["danger"], p["danger_hover"], fg="#2a0a0a"))
        self.select_all_btn.setStyleSheet(ghost_button_style())
        self.deselect_all_btn.setStyleSheet(ghost_button_style())
        self.total_label.setStyleSheet(f"color: {p['text_dim']}; font-size: 12px;")
    def _on_item_changed(self, item):
        if item.column() != 0:
            return
        row = item.row()
        if row < len(self.targets):
            self.targets[row].selected = item.checkState() == Qt.Checked
            self.update_total()
    def select_all(self):
        self._set_all(True)
    def deselect_all(self):
        self._set_all(False)
    def _set_all(self, value):
        self.table.blockSignals(True)
        for i, t in enumerate(self.targets):
            t.selected = value
            self.table.item(i, 0).setCheckState(Qt.Checked if value else Qt.Unchecked)
        self.table.blockSignals(False)
        self.update_total()
    def update_total(self):
        total = sum(t.size for t in self.targets if t.selected)
        self.total_label.setText(f"إجمالي الحجم المتوقع: {human_size(total)}")
    def start_scan(self):
        if self.scanning or self.cleaning:
            return
        self.scanning = True
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.table.setRowCount(0)
        self.targets = []
        def work(log_fn, progress_fn):
            targets = collect_targets(log_fn)
            log_fn(f"تم العثور على {len(targets)} عنصر. جاري حساب الأحجام...")
            for i, t in enumerate(targets):
                try:
                    if t.kind == "recycle_bin":
                        t.size = 0
                    else:
                        t.size = get_dir_size(t.path, max_seconds=4) if os.path.isdir(t.path) else os.path.getsize(t.path)
                except Exception:
                    t.size = 0
                progress_fn(i + 1, len(targets))
            return targets
        w = Worker(work)
        w.log.connect(self.log_console.log)
        w.progress.connect(self._set_progress)
        w.done.connect(self._scan_done)
        w.failed.connect(self._scan_failed)
        keep_ref(self, w)
        w.start()
    def _set_progress(self, cur, total):
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(cur)
    def _scan_failed(self, err):
        self.log_console.log(f"خطأ أثناء الفحص: {err}")
        self.scanning = False
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
    def _scan_done(self, targets):
        self.targets = targets
        self.table.blockSignals(True)
        self.table.setRowCount(len(targets))
        for i, t in enumerate(targets):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked if t.selected else Qt.Unchecked)
            self.table.setItem(i, 0, check_item)
            self.table.setItem(i, 1, QTableWidgetItem(t.category))
            self.table.setItem(i, 2, QTableWidgetItem(t.label))
            self.table.setItem(i, 3, QTableWidgetItem(t.path))
            self.table.setItem(i, 4, QTableWidgetItem(human_size(t.size)))
        self.table.blockSignals(False)
        self.update_total()
        self.scanning = False
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.log_console.log("اكتمل الفحص. راجع القائمة ثم اضغط بدء التنظيف.")
    def start_cleanup(self):
        if self.scanning or self.cleaning:
            return
        if not self.targets:
            QMessageBox.information(self, APP_NAME, "قم بفحص الجهاز أولاً.")
            return
        selected = [t for t in self.targets if t.selected]
        if not selected:
            QMessageBox.information(self, APP_NAME, "لم يتم تحديد أي عنصر.")
            return
        dry = self.dry_run_check.isChecked()
        msg = (
            "سيتم تنفيذ معاينة فقط (بدون حذف)."
            if dry else
            "سيتم حذف العناصر المحددة فعلياً. هل أنت متأكد؟"
        )
        if QMessageBox.question(self, APP_NAME, msg) != QMessageBox.Yes:
            return
        self.cleaning = True
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        do_restore = self.restore_check.isChecked()
        def work(log_fn, progress_fn):
            if not dry and do_restore:
                create_restore_point(log_fn)
            elif dry:
                log_fn("وضع المعاينة مفعّل — لن يتم حذف فعلي.")
            log_fn("جاري التنظيف...")
            freed, deleted, errors = run_cleanup(selected, log_fn, progress_fn, dry)
            return freed, deleted, errors
        w = Worker(work)
        w.log.connect(self.log_console.log)
        w.progress.connect(self._set_progress)
        w.done.connect(lambda res: self._cleanup_done(res, dry))
        w.failed.connect(self._scan_failed)
        keep_ref(self, w)
        w.start()
    def _cleanup_done(self, result, dry):
        freed, deleted, errors = result
        self.log_console.log("=" * 50)
        self.log_console.log(f"{'[معاينة] ' if dry else ''}اكتمل. عناصر تم حذفها: {deleted} | أخطاء: {errors}")
        self.log_console.log(f"{'المساحة المتوقع تحريرها' if dry else 'المساحة المحررة'}: {human_size(freed)}")
        self.log_console.log("=" * 50)
        self.cleaning = False
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        QMessageBox.information(
            self, APP_NAME,
            f"{'معاينة مكتملة' if dry else 'التنظيف مكتمل'}\n"
            f"العناصر: {deleted}\nالأخطاء: {errors}\n"
            f"{'المساحة المتوقعة' if dry else 'المساحة المحررة'}: {human_size(freed)}"
        )
class DashboardPage(BasePage, LivePage):
    def __init__(self, parent=None):
        BasePage.__init__(self, "لوحة الأداء المباشرة", "مراقبة استهلاك المعالج والذاكرة والقرص لحظياً.")
        self.cpu_history = []
        self.ram_history = []
        self.proc_cache = {}
        self._build_ui()
    def _build_ui(self):
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self.cpu_card = StatCard("المعالج (CPU)", "--%", "accent")
        self.ram_card = StatCard("الذاكرة (RAM)", "--%", "accent2")
        self.disk_card = StatCard("القرص C", "--%", "purple")
        self.cputemp_card = StatCard("حرارة المعالج", "-- °C", "warn")
        self.gputemp_card = StatCard("حرارة كرت الشاشة", "-- °C", "danger")
        for c in (self.cpu_card, self.ram_card, self.disk_card, self.cputemp_card, self.gputemp_card):
            self.add_card(c)
            stats_row.addWidget(c)
        self.outer.addLayout(stats_row)
        graphs_card = self.add_card(Card(self))
        gl = QVBoxLayout(graphs_card)
        gl.setContentsMargins(18, 16, 18, 16)
        gl.setSpacing(10)
        gl.addWidget(QLabel("منحنى الاستخدام (آخر 60 قراءة)"))
        graphs_row = QHBoxLayout()
        cpu_col = QVBoxLayout()
        self.cpu_glabel = QLabel("المعالج")
        cpu_col.addWidget(self.cpu_glabel)
        self.cpu_spark = Sparkline("accent")
        cpu_col.addWidget(self.cpu_spark)
        ram_col = QVBoxLayout()
        self.ram_glabel = QLabel("الذاكرة")
        ram_col.addWidget(self.ram_glabel)
        self.ram_spark = Sparkline("accent2")
        ram_col.addWidget(self.ram_spark)
        graphs_row.addLayout(cpu_col)
        graphs_row.addLayout(ram_col)
        gl.addLayout(graphs_row)
        self.outer.addWidget(graphs_card)
        table_card = self.add_card(Card(self))
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(18, 16, 18, 16)
        tl.addWidget(QLabel("أكثر البرامج استهلاكاً"))
        self.table = make_table(["اسم العملية", "PID", "CPU %", "الذاكرة"], [260, 90, 100, 140])
        tl.addWidget(self.table, 1)
        self.outer.addWidget(table_card, 1)
        self.note_lbl = hint_label("ملاحظة: قراءة الحرارة تعتمد على دعم اللوحة الأم/التعريفات. كرت شاشة NVIDIA فقط مدعوم حالياً.")
        self.outer.addWidget(self.note_lbl)
        self.restyle()
    def restyle(self):
        super().restyle()
        for lbl in (self.cpu_glabel, self.ram_glabel):
            lbl.setStyleSheet(f"color: {palette()['text_dim']}; font-size: 11px; font-weight: 600;")
        self.note_lbl.setStyleSheet(f"color: {palette()['text_faint']}; font-size: 11px;")
        self.cpu_spark.update()
        self.ram_spark.update()
    def on_show(self):
        if psutil is None:
            QMessageBox.critical(self, APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ الأمر التالي في cmd:\npip install psutil")
            return
        self.start_live(1500, self._collect, self._render)
        self._temp_timer = QTimer(self)
        self._temp_timer.timeout.connect(self._collect_temps)
        self._temp_timer.start(5000)
        self._collect_temps()
    def on_hide(self):
        self.stop_live()
        if hasattr(self, "_temp_timer"):
            self._temp_timer.stop()
    def _collect(self):
        cpu = psutil.cpu_percent(interval=0.3)
        vm = psutil.virtual_memory()
        try:
            total, used, free = shutil.disk_usage("C:\\")
            disk_percent = used / total * 100 if total else 0
        except Exception:
            disk_percent = 0
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
                rows.append((proc.name(), pid, proc.cpu_percent(None), proc.memory_info().rss))
            except Exception:
                continue
        rows.sort(key=lambda x: x[2], reverse=True)
        return cpu, vm.percent, disk_percent, rows[:12]
    def _render(self, result):
        cpu, ram_percent, disk_percent, top = result
        self.cpu_history.append(cpu)
        self.ram_history.append(ram_percent)
        self.cpu_history = self.cpu_history[-60:]
        self.ram_history = self.ram_history[-60:]
        self.cpu_card.set_value(f"{cpu:.1f}%")
        self.ram_card.set_value(f"{ram_percent:.1f}%")
        self.disk_card.set_value(f"{disk_percent:.1f}%")
        self.cpu_spark.set_data(self.cpu_history)
        self.ram_spark.set_data(self.ram_history)
        self.table.setRowCount(len(top))
        for i, (name, pid, cpu_p, mem) in enumerate(top):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(str(pid)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{cpu_p:.1f}"))
            self.table.setItem(i, 3, QTableWidgetItem(human_size(mem)))
    def _collect_temps(self):
        w = SimpleWorker(lambda: (get_cpu_temp(), get_gpu_temp()))
        w.done.connect(self._render_temps)
        keep_ref(self, w)
        w.start()
    def _render_temps(self, result):
        cpu_temp, gpu_temp = result
        self.cputemp_card.set_value(f"{cpu_temp:.0f} °C" if cpu_temp is not None else "غير متوفرة")
        self.gputemp_card.set_value(f"{gpu_temp:.0f} °C" if gpu_temp is not None else "غير متوفرة")
class ProcessesPage(BasePage, LivePage):
    def __init__(self, parent=None):
        BasePage.__init__(self, "إدارة العمليات الذكية", "تصنيف تلقائي للعمليات (نظام / مستخدم / خلفية) مع إمكانية الإنهاء الآمن.")
        self.proc_cache = {}
        self.rows_cache = []
        self._build_ui()
    def _build_ui(self):
        toolbar_card = self.add_card(Card(self))
        tl = QHBoxLayout(toolbar_card)
        tl.setContentsMargins(18, 14, 18, 14)
        tl.addWidget(QLabel("تصفية:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["الكل", "System", "User", "Background"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        tl.addWidget(self.filter_combo)
        self.kill_btn = QPushButton("⛔  إنهاء العملية المحددة")
        self.kill_btn.setCursor(Qt.PointingHandCursor)
        self.kill_btn.clicked.connect(self.kill_selected)
        tl.addWidget(self.kill_btn)
        tl.addStretch()
        table_card = self.add_card(Card(self))
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(18, 16, 18, 16)
        self.table = make_table(["اسم العملية", "PID", "التصنيف", "CPU %", "الذاكرة"], [240, 90, 110, 90, 130])
        tcl.addWidget(self.table, 1)
        self.outer.addWidget(toolbar_card)
        self.outer.addWidget(table_card, 1)
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.kill_btn.setStyleSheet(accent_button_style(p["danger"], p["danger_hover"], fg="#2a0a0a"))
    def on_show(self):
        if psutil is None:
            QMessageBox.critical(self, APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ: pip install psutil")
            return
        self.start_live(2000, self._collect, self._on_collected)
    def on_hide(self):
        self.stop_live()
    def _collect(self):
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
                rows.append((name, pid, category, proc.cpu_percent(None), proc.memory_info().rss))
            except Exception:
                continue
        rows.sort(key=lambda x: x[3], reverse=True)
        return rows
    def _on_collected(self, rows):
        self.rows_cache = rows
        self._apply_filter()
    def _apply_filter(self):
        flt = self.filter_combo.currentText()
        rows = [r for r in self.rows_cache if flt == "الكل" or r[2] == flt]
        self.table.setRowCount(len(rows))
        for i, (name, pid, category, cpu_p, mem) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(str(pid)))
            self.table.setItem(i, 2, QTableWidgetItem(category))
            self.table.setItem(i, 3, QTableWidgetItem(f"{cpu_p:.1f}"))
            self.table.setItem(i, 4, QTableWidgetItem(human_size(mem)))
    def kill_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "اختر عملية من القائمة أولاً.")
            return
        name = self.table.item(row, 0).text()
        pid = int(self.table.item(row, 1).text())
        if name.lower() in CRITICAL_PROCESSES:
            QMessageBox.warning(self, APP_NAME, "لا يمكن إنهاء عملية نظام أساسية.")
            return
        if QMessageBox.question(self, APP_NAME, f"هل تريد إنهاء العملية {name} (PID {pid})؟") != QMessageBox.Yes:
            return
        try:
            psutil.Process(pid).terminate()
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"تعذر إنهاء العملية: {e}")
class StartupPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("محسّن الإقلاع", "تحكّم بالبرامج التي تعمل تلقائياً مع بدء تشغيل ويندوز.")
        self.entries = []
        self._build_ui()
    def _build_ui(self):
        toolbar_card = self.add_card(Card(self))
        tl = QHBoxLayout(toolbar_card)
        tl.setContentsMargins(18, 14, 18, 14)
        self.refresh_btn = QPushButton("🔄  تحديث القائمة")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        self.disable_btn = QPushButton("تعطيل المحدد")
        self.disable_btn.setCursor(Qt.PointingHandCursor)
        self.disable_btn.clicked.connect(self.disable_selected)
        self.enable_btn = QPushButton("تفعيل المحدد")
        self.enable_btn.setCursor(Qt.PointingHandCursor)
        self.enable_btn.clicked.connect(self.enable_selected)
        for b in (self.refresh_btn, self.disable_btn, self.enable_btn):
            tl.addWidget(b)
        tl.addStretch()
        table_card = self.add_card(Card(self))
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(18, 16, 18, 16)
        self.table = make_table(["الاسم", "الحالة", "التأثير المتوقع", "المصدر", "الأمر / المسار"],
                                 [170, 90, 130, 100, 320])
        tcl.addWidget(self.table, 1)
        self.outer.addWidget(toolbar_card)
        self.outer.addWidget(table_card, 1)
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.refresh_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.disable_btn.setStyleSheet(ghost_button_style())
        self.enable_btn.setStyleSheet(ghost_button_style())
    def on_show(self):
        self.refresh()
    def refresh(self):
        w = SimpleWorker(get_startup_entries)
        w.done.connect(self._on_refreshed)
        keep_ref(self, w)
        w.start()
    def _on_refreshed(self, entries):
        self.entries = entries
        self.table.setRowCount(len(entries))
        p = palette()
        for i, e in enumerate(entries):
            enabled = e.get("enabled", True)
            status = "مفعّل" if enabled else "معطّل"
            score = impact_score(e["name"], e.get("command", ""))
            self.table.setItem(i, 0, QTableWidgetItem(e["name"]))
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(p["accent"] if enabled else p["text_faint"]))
            self.table.setItem(i, 1, status_item)
            self.table.setItem(i, 2, QTableWidgetItem(score))
            self.table.setItem(i, 3, QTableWidgetItem(e["source"]))
            self.table.setItem(i, 4, QTableWidgetItem(e.get("command", "")))
    def disable_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "اختر عنصراً من القائمة أولاً.")
            return
        entry = self.entries[row]
        if not entry.get("enabled", True):
            QMessageBox.information(self, APP_NAME, "هذا العنصر معطّل بالفعل.")
            return
        if disable_startup_entry(entry):
            QMessageBox.information(self, APP_NAME, f"تم تعطيل {entry['name']} من الإقلاع.")
        else:
            QMessageBox.critical(self, APP_NAME, "تعذر تعطيل هذا العنصر.")
        self.refresh()
    def enable_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "اختر عنصراً من القائمة أولاً.")
            return
        entry = self.entries[row]
        if entry.get("enabled", True):
            QMessageBox.information(self, APP_NAME, "هذا العنصر مفعّل بالفعل.")
            return
        if enable_startup_entry(entry):
            QMessageBox.information(self, APP_NAME, f"تم تفعيل {entry['name']} في الإقلاع.")
        else:
            QMessageBox.critical(self, APP_NAME, "تعذر تفعيل هذا العنصر.")
        self.refresh()
class ExplorerPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("مستكشف الملفات المتقدم", "بحث متقدّم بالاسم والنوع والحجم، أو عرض أكبر الملفات.")
        self.results = []
        self._sort_reverse = {}
        self._build_ui()
    def _build_ui(self):
        filters_card = self.add_card(Card(self))
        fl = QVBoxLayout(filters_card)
        fl.setContentsMargins(18, 14, 18, 14)
        fl.setSpacing(10)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("المسار:"))
        self.path_edit = QLineEdit("C:\\")
        row1.addWidget(self.path_edit, 1)
        self.browse_btn = QPushButton("استعراض")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.clicked.connect(self.browse)
        row1.addWidget(self.browse_btn)
        fl.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("اسم يحتوي على:"))
        self.name_edit = QLineEdit()
        row2.addWidget(self.name_edit)
        row2.addWidget(QLabel("النوع:"))
        self.ext_combo = QComboBox()
        self.ext_combo.addItems(["الكل"] + list(EXT_CATEGORIES.keys()))
        row2.addWidget(self.ext_combo)
        row2.addWidget(QLabel("أقل حجم (MB):"))
        self.min_size_edit = QLineEdit("0")
        self.min_size_edit.setFixedWidth(70)
        row2.addWidget(self.min_size_edit)
        self.search_btn = QPushButton("🔍  بحث")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.clicked.connect(self.start_search)
        row2.addWidget(self.search_btn)
        self.largest_btn = QPushButton("أكبر الملفات")
        self.largest_btn.setCursor(Qt.PointingHandCursor)
        self.largest_btn.clicked.connect(self.start_largest)
        row2.addWidget(self.largest_btn)
        row2.addStretch()
        fl.addLayout(row2)
        table_card = self.add_card(Card(self))
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(18, 16, 18, 16)
        self.table = make_table(["الاسم", "المسار", "الحجم", "تاريخ التعديل"], [220, 380, 100, 150])
        self.table.horizontalHeader().sectionClicked.connect(self._sort_by_index)
        tcl.addWidget(self.table, 1)
        self.status_lbl = QLabel("")
        tcl.addWidget(self.status_lbl)
        self.outer.addWidget(filters_card)
        self.outer.addWidget(table_card, 1)
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.browse_btn.setStyleSheet(ghost_button_style())
        self.search_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.largest_btn.setStyleSheet(ghost_button_style())
        self.status_lbl.setStyleSheet(f"color: {p['text_dim']}; font-size: 11.5px;")
    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد")
        if d:
            self.path_edit.setText(d)
    def start_search(self):
        self.status_lbl.setText("جاري البحث...")
        self._run_search(False)
    def start_largest(self):
        self.status_lbl.setText("جاري البحث عن أكبر الملفات...")
        self._run_search(True)
    def _run_search(self, largest_mode):
        try:
            min_mb = float(self.min_size_edit.text() or 0)
        except ValueError:
            min_mb = 0
        min_bytes = int(min_mb * 1024 * 1024)
        root_path = self.path_edit.text().strip() or "C:\\"
        name_filter = self.name_edit.text().strip()
        ext_filter = self.ext_combo.currentText()
        def work():
            results = scan_files(root_path, name_filter, ext_filter, min_bytes)
            if largest_mode:
                results.sort(key=lambda r: r[2], reverse=True)
                results = results[:100]
            return results
        w = SimpleWorker(work)
        w.done.connect(self._populate)
        keep_ref(self, w)
        w.start()
    def _populate(self, results):
        self.results = results
        self.table.setRowCount(len(results))
        for i, (name, full, size, mtime) in enumerate(results):
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(full))
            self.table.setItem(i, 2, QTableWidgetItem(human_size(size)))
            self.table.setItem(i, 3, QTableWidgetItem(date_str))
        self.status_lbl.setText(f"تم العثور على {len(results)} ملف.")
    def _sort_by_index(self, col_index):
        idx_map = {0: 0, 1: 1, 2: 2, 3: 3}
        idx = idx_map.get(col_index, 0)
        reverse = self._sort_reverse.get(col_index, False)
        self.results.sort(key=lambda r: r[idx], reverse=reverse)
        self._sort_reverse[col_index] = not reverse
        self._populate(self.results)
class SysInfoPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("معلومات النظام", "نظرة شاملة على مواصفات الجهاز، مع إمكانية تصدير تقرير PDF.")
        self.info = {}
        self._build_ui()
    def _build_ui(self):
        toolbar_card = self.add_card(Card(self))
        tl = QHBoxLayout(toolbar_card)
        tl.setContentsMargins(18, 14, 18, 14)
        self.refresh_btn = QPushButton("🔄  تحديث")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        self.export_btn = QPushButton("📄  تصدير تقرير PDF")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_pdf)
        tl.addWidget(self.refresh_btn)
        tl.addWidget(self.export_btn)
        tl.addStretch()
        table_card = self.add_card(Card(self))
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(18, 16, 18, 16)
        self.table = make_table(["الخاصية", "القيمة"], [220, 520])
        tcl.addWidget(self.table, 1)
        self.outer.addWidget(toolbar_card)
        self.outer.addWidget(table_card, 1)
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.refresh_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.export_btn.setStyleSheet(ghost_button_style())
    def on_show(self):
        if not self.info:
            self.refresh()
    def refresh(self):
        w = SimpleWorker(get_system_info)
        w.done.connect(self._populate)
        keep_ref(self, w)
        w.start()
    def _populate(self, info):
        self.info = info
        self.table.setRowCount(len(info))
        for i, (k, v) in enumerate(info.items()):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(str(v)))
    def export_pdf(self):
        if not self.info:
            QMessageBox.information(self, APP_NAME, "قم بالتحديث أولاً.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "حفظ التقرير", "system_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        lines = [f"PC Suite Pro - System Report", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        for k, v in self.info.items():
            lines.append(f"{k}: {v}")
        try:
            text_report_to_pdf(lines, path)
            QMessageBox.information(self, APP_NAME, f"تم حفظ التقرير في:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"تعذر إنشاء الملف: {e}")
class NetworkPage(BasePage, LivePage):
    def __init__(self, parent=None):
        BasePage.__init__(self, "مراقب الشبكة", "سرعة التنزيل/الرفع اللحظية، اختبار البينج، قياس سرعة الإنترنت، والأجهزة المتصلة.")
        self.last_counters = None
        self._build_ui()
    def _build_ui(self):
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self.down_card = StatCard("سرعة التنزيل الحالية", "-- KB/s", "accent")
        self.up_card = StatCard("سرعة الرفع الحالية", "-- KB/s", "accent2")
        for c in (self.down_card, self.up_card):
            self.add_card(c)
            stats_row.addWidget(c)
        self.outer.addLayout(stats_row)
        tools_card = self.add_card(Card(self))
        tl = QVBoxLayout(tools_card)
        tl.setContentsMargins(18, 16, 18, 16)
        tl.setSpacing(10)
        ping_row = QHBoxLayout()
        self.ping_btn = QPushButton("📶  اختبار البينج (Ping)")
        self.ping_btn.setCursor(Qt.PointingHandCursor)
        self.ping_btn.clicked.connect(self.run_ping)
        ping_row.addWidget(self.ping_btn)
        self.ping_lbl = QLabel("")
        ping_row.addWidget(self.ping_lbl)
        ping_row.addStretch()
        tl.addLayout(ping_row)
        speed_row = QHBoxLayout()
        self.speedtest_btn = QPushButton("🚀  قياس سرعة الإنترنت")
        self.speedtest_btn.setCursor(Qt.PointingHandCursor)
        self.speedtest_btn.clicked.connect(self.run_speedtest)
        speed_row.addWidget(self.speedtest_btn)
        self.speedtest_status_lbl = QLabel("")
        speed_row.addWidget(self.speedtest_status_lbl)
        speed_row.addStretch()
        tl.addLayout(speed_row)
        result_row = QHBoxLayout()
        self.down_mbps_lbl = QLabel("التنزيل: -- Mbps")
        self.up_mbps_lbl = QLabel("الرفع: -- Mbps")
        result_row.addWidget(self.down_mbps_lbl)
        result_row.addWidget(self.up_mbps_lbl)
        result_row.addStretch()
        tl.addLayout(result_row)
        self.outer.addWidget(tools_card)
        devices_card = self.add_card(Card(self))
        dl = QVBoxLayout(devices_card)
        dl.setContentsMargins(18, 16, 18, 16)
        dl.setSpacing(10)
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("الأجهزة المتصلة بالشبكة"))
        header_row.addStretch()
        self.scan_devices_btn = QPushButton("فحص الأجهزة المتصلة")
        self.scan_devices_btn.setCursor(Qt.PointingHandCursor)
        self.scan_devices_btn.clicked.connect(self.scan_devices)
        header_row.addWidget(self.scan_devices_btn)
        dl.addLayout(header_row)
        self.table = make_table(["عنوان IP", "MAC Address", "النوع"], [180, 220, 140])
        dl.addWidget(self.table, 1)
        self.outer.addWidget(devices_card, 1)
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.ping_btn.setStyleSheet(ghost_button_style())
        self.speedtest_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.scan_devices_btn.setStyleSheet(ghost_button_style())
        self.down_mbps_lbl.setStyleSheet(f"color: {p['accent']}; font-weight: 700;")
        self.up_mbps_lbl.setStyleSheet(f"color: {p['accent2']}; font-weight: 700;")
    def on_show(self):
        if psutil is None:
            QMessageBox.critical(self, APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ: pip install psutil")
            return
        self.start_live(1000, self._collect, self._render)
    def on_hide(self):
        self.stop_live()
    def _collect(self):
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
        return down_speed, up_speed
    def _render(self, result):
        down_speed, up_speed = result
        self.down_card.set_value(f"{human_size(down_speed)}/s")
        self.up_card.set_value(f"{human_size(up_speed)}/s")
    def run_ping(self):
        self.ping_lbl.setText("جاري الاختبار...")
        w = SimpleWorker(ping_test)
        w.done.connect(lambda r: self.ping_lbl.setText(r))
        keep_ref(self, w)
        w.start()
    def run_speedtest(self):
        self.speedtest_status_lbl.setText("جاري قياس السرعة، الرجاء الانتظار...")
        self.down_mbps_lbl.setText("التنزيل: -- Mbps")
        self.up_mbps_lbl.setText("الرفع: -- Mbps")
        def work():
            down = speedtest_download()
            up = speedtest_upload()
            return down, up
        w = SimpleWorker(work)
        w.done.connect(self._on_speedtest_done)
        keep_ref(self, w)
        w.start()
    def _on_speedtest_done(self, result):
        down, up = result
        self.down_mbps_lbl.setText(f"التنزيل: {down:.1f} Mbps" if down is not None else "التنزيل: تعذر القياس")
        self.up_mbps_lbl.setText(f"الرفع: {up:.1f} Mbps" if up is not None else "الرفع: تعذر القياس")
        self.speedtest_status_lbl.setText("اكتمل قياس السرعة.")
    def scan_devices(self):
        self.table.setRowCount(0)
        w = SimpleWorker(get_arp_devices)
        w.done.connect(self._populate_devices)
        keep_ref(self, w)
        w.start()
    def _populate_devices(self, devices):
        self.table.setRowCount(len(devices))
        for i, (ip, mac, kind) in enumerate(devices):
            self.table.setItem(i, 0, QTableWidgetItem(ip))
            self.table.setItem(i, 1, QTableWidgetItem(mac))
            self.table.setItem(i, 2, QTableWidgetItem(kind))
class BoosterPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("معزز أداء المعالج والذاكرة", "يرفع أولوية برنامج محدد (مثل لعبة) ويخفض أولوية باقي البرامج غير الأساسية.")
        self.pid_map = {}
        self.all_values = []
        self._build_ui()
    def _build_ui(self):
        card = self.add_card(Card(self))
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(12)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("ابحث عن التطبيق:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._on_search)
        search_row.addWidget(self.search_edit, 1)
        cl.addLayout(search_row)
        choose_row = QHBoxLayout()
        choose_row.addWidget(QLabel("اختر البرنامج:"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(340)
        choose_row.addWidget(self.combo, 1)
        self.refresh_btn = QPushButton("🔄  تحديث القائمة")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_list)
        choose_row.addWidget(self.refresh_btn)
        cl.addLayout(choose_row)
        actions_row = QHBoxLayout()
        self.boost_btn = QPushButton("⚡  تفعيل التعزيز")
        self.boost_btn.setCursor(Qt.PointingHandCursor)
        self.boost_btn.clicked.connect(self.boost)
        self.restore_btn = QPushButton("استعادة الأولوية الطبيعية للجميع")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.clicked.connect(self.restore)
        actions_row.addWidget(self.boost_btn)
        actions_row.addWidget(self.restore_btn)
        actions_row.addStretch()
        cl.addLayout(actions_row)
        self.status_lbl = QLabel("")
        cl.addWidget(self.status_lbl)
        self.outer.addWidget(card)
        self.outer.addStretch()
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.boost_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.refresh_btn.setStyleSheet(ghost_button_style())
        self.restore_btn.setStyleSheet(ghost_button_style())
        self.status_lbl.setStyleSheet(f"color: {p['text_dim']}; font-size: 12px;")
    def on_show(self):
        self.refresh_list()
    def refresh_list(self):
        if psutil is None:
            QMessageBox.critical(self, APP_NAME, "المكتبة psutil غير مثبتة.\nنفّذ: pip install psutil")
            return
        def work():
            pid_map = {}
            values = []
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    name = p.info["name"] or "?"
                    if name.lower() in CRITICAL_PROCESSES:
                        continue
                    label = f"{name} (PID {p.info['pid']})"
                    pid_map[label] = p.info["pid"]
                    values.append(label)
                except Exception:
                    continue
            values.sort()
            return pid_map, values
        w = SimpleWorker(work)
        w.done.connect(self._on_list_ready)
        keep_ref(self, w)
        w.start()
    def _on_list_ready(self, result):
        self.pid_map, self.all_values = result
        self._on_search()
    def _on_search(self):
        query = self.search_edit.text().strip().lower()
        filtered = [v for v in self.all_values if query in v.lower()] if query else self.all_values
        current = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(filtered)
        if current in filtered:
            self.combo.setCurrentText(current)
        self.combo.blockSignals(False)
    def boost(self):
        label = self.combo.currentText()
        if not label or label not in self.pid_map:
            QMessageBox.information(self, APP_NAME, "اختر برنامجاً من القائمة أولاً.")
            return
        pid = self.pid_map[label]
        def work():
            try:
                target = psutil.Process(pid)
                target.nice(psutil.HIGH_PRIORITY_CLASS)
                try:
                    target.io_priority(psutil.IOPRIO_HIGH)
                except Exception:
                    pass
            except Exception as e:
                return f"تعذر رفع أولوية البرنامج المستهدف: {e}"
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
            return f"تم رفع أولوية {label} وخفض أولوية {count} عملية أخرى."
        w = SimpleWorker(work)
        w.done.connect(self.status_lbl.setText)
        keep_ref(self, w)
        w.start()
    def restore(self):
        def work():
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
            return f"تمت استعادة الأولوية الطبيعية لـ {count} عملية."
        w = SimpleWorker(work)
        w.done.connect(self.status_lbl.setText)
        keep_ref(self, w)
        w.start()
class BoostPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("تعزيز FPS والأداء الشامل",
                          "يعطّل خدمات ومزايا ويندوز غير الضرورية للألعاب، ويضبط الشبكة وخطة الطاقة لتقليل زمن الاستجابة.\n"
                          "لا يتم لمس أي إعداد أمني مثل Windows Defender أو الجدار الناري أو التحديثات الأمنية.")
        self.checks = {}
        self._build_ui()
    def _add_group(self, layout, title):
        lbl = QLabel(title)
        lbl.setObjectName("groupTitle")
        layout.addWidget(lbl)
        return lbl
    def _build_ui(self):
        options_card = self.add_card(Card(self))
        ol = QVBoxLayout(options_card)
        ol.setContentsMargins(18, 16, 18, 10)
        ol.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(300)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setSpacing(6)
        self.group_labels = []
        self.group_labels.append(self._add_group(inner_lay, "خدمات Microsoft غير الضرورية"))
        for svc_name, desc in TWEAK_SERVICES.items():
            cb = QCheckBox(f"{desc} ({svc_name})")
            cb.setChecked(True)
            self.checks[svc_name] = cb
            inner_lay.addWidget(cb)
        self.group_labels.append(self._add_group(inner_lay, "مزايا وواجهة النظام"))
        for tw in REGISTRY_TWEAKS:
            cb = QCheckBox(tw["label"])
            cb.setChecked(True)
            self.checks[tw["id"]] = cb
            inner_lay.addWidget(cb)
        self.group_labels.append(self._add_group(inner_lay, "الشبكة وخطة الطاقة"))
        for opt_id, opt_label in BOOST_EXTRA_OPTIONS:
            cb = QCheckBox(opt_label)
            cb.setChecked(True)
            self.checks[opt_id] = cb
            inner_lay.addWidget(cb)
        inner_lay.addStretch()
        scroll.setWidget(inner)
        ol.addWidget(scroll)
        actions_row = QHBoxLayout()
        self.apply_btn = QPushButton("⚡  تفعيل تعزيز FPS")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.apply)
        self.restore_btn = QPushButton("استعادة الإعدادات الأصلية")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.clicked.connect(self.restore)
        self.select_all_btn = QPushButton("تحديد الكل")
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(lambda: self._set_all(True))
        self.deselect_all_btn = QPushButton("إلغاء تحديد الكل")
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(lambda: self._set_all(False))
        for b in (self.apply_btn, self.restore_btn, self.select_all_btn, self.deselect_all_btn):
            actions_row.addWidget(b)
        actions_row.addStretch()
        ol.addLayout(actions_row)
        log_card = self.add_card(Card(self))
        ll = QVBoxLayout(log_card)
        ll.setContentsMargins(18, 14, 18, 14)
        ll.addWidget(QLabel("السجل"))
        self.log_console = LogConsole()
        self.log_console.setFixedHeight(140)
        ll.addWidget(self.log_console)
        self.outer.addWidget(options_card, 1)
        self.outer.addWidget(log_card)
        self.restyle()
    def restyle(self):
        super().restyle()
        p = palette()
        self.apply_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.restore_btn.setStyleSheet(ghost_button_style())
        self.select_all_btn.setStyleSheet(ghost_button_style())
        self.deselect_all_btn.setStyleSheet(ghost_button_style())
        for lbl in self.group_labels:
            lbl.setStyleSheet(f"color: {p['accent2']}; font-size: 12.5px; font-weight: 700; margin-top: 6px;")
    def _set_all(self, value):
        for cb in self.checks.values():
            cb.setChecked(value)
    def apply(self):
        if QMessageBox.question(
                self, APP_NAME,
                "سيتم تطبيق تعديلات على خدمات وإعدادات النظام لتحسين الأداء أثناء الألعاب.\n"
                "لا يشمل ذلك أي إعداد أمني، ويمكنك التراجع في أي وقت من زر الاستعادة.\nهل تريد المتابعة؟"
        ) != QMessageBox.Yes:
            return
        selected_ids = [key for key, cb in self.checks.items() if cb.isChecked()]
        def work(log_fn, progress_fn):
            log_fn("جاري تفعيل تعزيز FPS...")
            apply_boost(selected_ids, log_fn)
        w = Worker(work)
        w.log.connect(self.log_console.log)
        keep_ref(self, w)
        w.start()
    def restore(self):
        if QMessageBox.question(self, APP_NAME, "سيتم استعادة كل الإعدادات إلى وضعها الأصلي قبل التعزيز. هل تريد المتابعة؟") != QMessageBox.Yes:
            return
        def work(log_fn, progress_fn):
            log_fn("جاري استعادة الإعدادات الأصلية...")
            restore_boost(log_fn)
        w = Worker(work)
        w.log.connect(self.log_console.log)
        keep_ref(self, w)
        w.start()
class DownloaderPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("تحميل الفيديوهات", "يدعم يوتيوب وتيك توك وإنستقرام وأي منصة أخرى مدعومة من مكتبة yt-dlp.")
        self.formats_data = []
        self.output_dir = os.path.join(get_user_profile(), "Downloads")
        self._build_ui()
    def _build_ui(self):
        url_card = self.add_card(Card(self))
        ul = QVBoxLayout(url_card)
        ul.setContentsMargins(18, 16, 18, 16)
        ul.setSpacing(10)
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("رابط الفيديو:"))
        self.url_edit = QLineEdit()
        url_row.addWidget(self.url_edit, 1)
        self.fetch_btn = QPushButton("🔎  جلب الجودات المتاحة")
        self.fetch_btn.setCursor(Qt.PointingHandCursor)
        self.fetch_btn.clicked.connect(self.fetch_formats)
        url_row.addWidget(self.fetch_btn)
        ul.addLayout(url_row)
        table_card = self.add_card(Card(self))
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(18, 16, 18, 16)
        self.table = make_table(["الجودة", "الامتداد", "الحجم التقريبي", "النوع", "FPS"], [100, 70, 130, 170, 60])
        tl.addWidget(self.table, 1)
        out_card = self.add_card(Card(self))
        ol = QVBoxLayout(out_card)
        ol.setContentsMargins(18, 14, 18, 14)
        ol.setSpacing(8)
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("مجلد الحفظ:"))
        self.output_lbl = QLabel(self.output_dir)
        out_row.addWidget(self.output_lbl, 1)
        self.folder_btn = QPushButton("تغيير المجلد")
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.clicked.connect(self.choose_folder)
        out_row.addWidget(self.folder_btn)
        ol.addLayout(out_row)
        actions_row = QHBoxLayout()
        self.download_btn = QPushButton("⬇️  تحميل بالجودة المحددة")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self.download_selected)
        actions_row.addWidget(self.download_btn)
        actions_row.addStretch()
        ol.addLayout(actions_row)
        self.progress = QProgressBar()
        ol.addWidget(self.progress)
        self.status_lbl = QLabel("")
        ol.addWidget(self.status_lbl)
        ffmpeg_row = QHBoxLayout()
        self.ffmpeg_btn = QPushButton("⬇️  تحميل ffmpeg")
        self.ffmpeg_btn.setCursor(Qt.PointingHandCursor)
        self.ffmpeg_btn.clicked.connect(self.download_ffmpeg)
        ffmpeg_row.addWidget(self.ffmpeg_btn)
        self.ffmpeg_status_lbl = QLabel("")
        ffmpeg_row.addWidget(self.ffmpeg_status_lbl)
        ffmpeg_row.addStretch()
        ol.addLayout(ffmpeg_row)
        self.outer.addWidget(url_card)
        self.outer.addWidget(table_card, 1)
        self.outer.addWidget(out_card)
        self.restyle()
        self._refresh_ffmpeg_status()
    def restyle(self):
        super().restyle()
        p = palette()
        self.fetch_btn.setStyleSheet(accent_button_style(p["accent"], p["accent_hover"]))
        self.folder_btn.setStyleSheet(ghost_button_style())
        self.download_btn.setStyleSheet(accent_button_style(p["accent2"], p["accent2_hover"]))
        self.ffmpeg_btn.setStyleSheet(ghost_button_style())
        self.status_lbl.setStyleSheet(f"color: {p['text_dim']}; font-size: 11.5px;")
        self.output_lbl.setStyleSheet(f"color: {p['accent2']}; font-size: 11.5px;")
    def _refresh_ffmpeg_status(self):
        p = palette()
        if ffmpeg_ready():
            self.ffmpeg_status_lbl.setText("ffmpeg: متوفر ✅")
            self.ffmpeg_status_lbl.setStyleSheet(f"color: {p['accent2']};")
        else:
            self.ffmpeg_status_lbl.setText("ffmpeg: غير مثبت")
            self.ffmpeg_status_lbl.setStyleSheet(f"color: {p['text_dim']};")
    def on_show(self):
        self._refresh_ffmpeg_status()
    def fetch_formats(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.information(self, APP_NAME, "أدخل رابط الفيديو أولاً.")
            return
        if yt_dlp is None:
            QMessageBox.critical(self, APP_NAME, "المكتبة yt-dlp غير مثبتة.\nنفّذ: pip install yt-dlp")
            return
        self.table.setRowCount(0)
        self.formats_data = []
        self.status_lbl.setText("جاري جلب المعلومات...")
        def work():
            opts = {"quiet": True, "skip_download": True, "noplaylist": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            rows = []
            seen = set()
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("height"):
                    acodec = f.get("acodec")
                    key = (f["height"], f.get("fps"), acodec != "none")
                    if key in seen:
                        continue
                    seen.add(key)
                    size = f.get("filesize") or f.get("filesize_approx")
                    rows.append({
                        "format_id": f["format_id"], "ext": f.get("ext"),
                        "quality": f"{f['height']}p", "height": f["height"],
                        "size": human_size(size) if size else "غير معروف",
                        "kind": "فيديو+صوت" if acodec and acodec != "none" else "فيديو فقط (يحتاج ffmpeg)",
                        "fps": f.get("fps") or "",
                    })
                elif f.get("vcodec") == "none" and f.get("acodec") != "none":
                    size = f.get("filesize") or f.get("filesize_approx")
                    rows.append({
                        "format_id": f["format_id"], "ext": f.get("ext"),
                        "quality": f"{f.get('abr') or '?'}kbps", "height": 0,
                        "size": human_size(size) if size else "غير معروف",
                        "kind": "صوت فقط", "fps": "",
                    })
            rows.sort(key=lambda r: (r["kind"] == "صوت فقط", r["kind"].startswith("فيديو فقط"), -r["height"]))
            return rows, info.get("title", "")
        w = SimpleWorker(work)
        w.done.connect(lambda res: self._populate_formats(*res))
        w.failed.connect(lambda err: self.status_lbl.setText(f"فشل جلب المعلومات: {err}"))
        keep_ref(self, w)
        w.start()
    def _populate_formats(self, rows, title):
        self.formats_data = rows
        if not rows:
            self.status_lbl.setText("ما فيه جودات متاحة لهذا الفيديو.")
            return
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["quality"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["ext"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["size"]))
            self.table.setItem(i, 3, QTableWidgetItem(r["kind"]))
            self.table.setItem(i, 4, QTableWidgetItem(str(r["fps"])))
        prefix = f"{title} — " if title else ""
        self.status_lbl.setText(f"{prefix}اختر الجودة المطلوبة ثم اضغط تحميل.")
    def choose_folder(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ")
        if d:
            self.output_dir = d
            self.output_lbl.setText(d)
    def download_selected(self):
        if yt_dlp is None:
            QMessageBox.critical(self, APP_NAME, "المكتبة yt-dlp غير مثبتة.\nنفّذ: pip install yt-dlp")
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, APP_NAME, "اختر جودة من القائمة أولاً.")
            return
        url = self.url_edit.text().strip()
        if not url:
            return
        fmt = self.formats_data[row]
        needs_ffmpeg = fmt["kind"] != "فيديو+صوت"
        if needs_ffmpeg and not ffmpeg_ready():
            QMessageBox.critical(
                self, APP_NAME,
                "هذه الجودة تحتاج ffmpeg (فيديو وصوت بملفين منفصلين).\n"
                "اضغط زر \"تحميل ffmpeg\" أسفل الصفحة، أو اختر جودة من نوع \"فيديو+صوت\"."
            )
            return
        self.progress.setValue(0)
        self.status_lbl.setText("جاري التحميل...")
        def work():
            format_id = fmt["format_id"]
            kind = fmt["kind"]
            is_audio = kind == "صوت فقط"
            if kind == "فيديو+صوت" or is_audio:
                format_selector = format_id
            else:
                format_selector = f"{format_id}+bestaudio/best"
            outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")
            def hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    if total:
                        self._progress_signal_value = downloaded / total * 100
            opts = {
                "format": format_selector, "outtmpl": outtmpl, "quiet": True,
                "no_warnings": True, "progress_hooks": [hook], "merge_output_format": "mp4",
            }
            ffmpeg_loc = ffmpeg_location_for_ytdlp()
            if ffmpeg_loc:
                opts["ffmpeg_location"] = ffmpeg_loc
            if is_audio:
                opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True
        w = SimpleWorker(work)
        w.done.connect(lambda ok: (self.progress.setValue(100), self.status_lbl.setText(f"تم التحميل بنجاح إلى: {self.output_dir}")))
        w.failed.connect(lambda err: self.status_lbl.setText(f"فشل التحميل: {err}"))
        keep_ref(self, w)
        w.start()
    def download_ffmpeg(self):
        if ffmpeg_ready():
            QMessageBox.information(self, APP_NAME, "ffmpeg موجود مسبقًا، ما فيه داعي للتحميل.")
            self._refresh_ffmpeg_status()
            return
        self.ffmpeg_status_lbl.setText("جاري تحميل ffmpeg... 0%")
        def work(log_fn, progress_fn):
            os.makedirs(FFMPEG_DIR, exist_ok=True)
            zip_path = os.path.join(FFMPEG_DIR, "ffmpeg_download.zip")
            req = urllib.request.Request(FFMPEG_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        progress_fn(downloaded, total)
            with zipfile.ZipFile(zip_path) as z:
                for member in z.namelist():
                    name = os.path.basename(member)
                    if name in ("ffmpeg.exe", "ffprobe.exe"):
                        with z.open(member) as src, open(os.path.join(FFMPEG_DIR, name), "wb") as dst:
                            shutil.copyfileobj(src, dst)
            os.remove(zip_path)
            return local_ffmpeg_available()
        w = Worker(work)
        w.progress.connect(lambda cur, total: self.ffmpeg_status_lbl.setText(f"جاري تحميل ffmpeg... {cur / total * 100:.0f}%"))
        w.done.connect(self._on_ffmpeg_downloaded)
        w.failed.connect(lambda err: self.ffmpeg_status_lbl.setText(f"فشل تحميل ffmpeg: {err}"))
        keep_ref(self, w)
        w.start()
    def _on_ffmpeg_downloaded(self, ok):
        if ok:
            p = palette()
            self.ffmpeg_status_lbl.setText("ffmpeg: متوفر ✅")
            self.ffmpeg_status_lbl.setStyleSheet(f"color: {p['accent2']};")
            QMessageBox.information(self, APP_NAME, "تم تحميل ffmpeg بنجاح.")
        else:
            self.ffmpeg_status_lbl.setText("فشل استخراج ffmpeg من الأرشيف")
class NavButton(QPushButton):
    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}   {text}")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setLayoutDirection(Qt.RightToLeft)
        self.restyle()
    def restyle(self):
        p = palette()
        if self.isChecked():
            self.setStyleSheet(
                f"QPushButton {{ text-align: right; border: none; border-radius: 10px; font-weight: 700;"
                f" font-size: 13px; padding-right: 14px;"
                f" background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['accent']}, stop:1 {p['accent2']});"
                f" color: #04120b; }}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton {{ text-align: right; border: none; border-radius: 10px; font-size: 13px;"
                f" padding-right: 14px; background: transparent; color: {p['text_dim']}; }}"
                f"QPushButton:hover {{ background-color: {p['panel_alt']}; color: {p['text']}; }}"
            )
class Sidebar(QWidget):
    nav_selected = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(248)
        self.buttons = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 22, 14, 18)
        lay.setSpacing(4)
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        self.logo_lbl = QLabel()
        self.logo_lbl.setPixmap(make_icon(40).pixmap(40, 40))
        logo_row.addWidget(self.logo_lbl)
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self.title_lbl = QLabel(APP_NAME)
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 800;")
        self.subtitle_lbl = QLabel("Legendary Edition")
        self.subtitle_lbl.setStyleSheet("font-size: 10px;")
        title_col.addWidget(self.title_lbl)
        title_col.addWidget(self.subtitle_lbl)
        logo_row.addLayout(title_col)
        logo_row.addStretch()
        lay.addLayout(logo_row)
        lay.addSpacing(18)
        for key, label, icon in NAV_ITEMS:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            lay.addWidget(btn)
            self.buttons[key] = btn
        lay.addStretch()
        self.admin_badge = QLabel()
        self.admin_badge.setAlignment(Qt.AlignCenter)
        self.admin_badge.setFixedHeight(30)
        lay.addWidget(self.admin_badge)
        self.set_active("cleaner")
        self.restyle()
    def _on_click(self, key):
        self.set_active(key)
        self.nav_selected.emit(key)
    def set_active(self, key):
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)
            btn.restyle()
    def set_admin_status(self, admin):
        p = palette()
        if admin:
            self.admin_badge.setText("🛡️  صلاحيات المسؤول مفعّلة")
            self.admin_badge.setStyleSheet(
                f"color: {p['accent']}; background-color: {p['accent']}22; border-radius: 8px; font-size: 10.5px; font-weight: 700;"
            )
        else:
            self.admin_badge.setText("⚠️  بدون صلاحيات المسؤول")
            self.admin_badge.setStyleSheet(
                f"color: {p['warn']}; background-color: {p['warn']}22; border-radius: 8px; font-size: 10.5px; font-weight: 700;"
            )
    def restyle(self):
        p = palette()
        self.title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {p['text']};")
        self.subtitle_lbl.setStyleSheet(f"font-size: 10px; color: {p['accent2']}; font-weight: 600;")
        for btn in self.buttons.values():
            btn.restyle()
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        p = palette()
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(p["sidebar_top"]))
        grad.setColorAt(1, QColor(p["sidebar_bottom"]))
        painter.fillRect(self.rect(), QBrush(grad))
        painter.setPen(QPen(QColor(p["panel_border"]), 1))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        painter.end()
        super().paintEvent(event)
class TopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 8, 24, 8)
        self.page_title_lbl = QLabel("")
        self.page_title_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        lay.addWidget(self.page_title_lbl)
        lay.addStretch()
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.sun_lbl = QLabel("☀️")
        self.moon_lbl = QLabel("🌙")
        self.toggle = ToggleSwitch()
        self.toggle.setChecked(True)
        self.toggle.stateChanged.connect(self._on_toggle)
        mode_row.addWidget(self.sun_lbl)
        mode_row.addWidget(self.toggle)
        mode_row.addWidget(self.moon_lbl)
        lay.addLayout(mode_row)
        self.restyle()
    def _on_toggle(self, state):
        CURRENT_THEME["dark"] = bool(state)
        theme_bus.changed.emit(bool(state))
    def set_page_title(self, key):
        mapping = {k: (icon, label) for k, label, icon in NAV_ITEMS}
        icon, label = mapping.get(key, ("", ""))
        self.page_title_lbl.setText(f"{icon}  {label}")
        self.restyle()
    def restyle(self):
        p = palette()
        self.page_title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {p['text_dim']};")
        self.setStyleSheet(f"background-color: {p['app_bg']}; border-bottom: 1px solid {p['panel_border']};")
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_icon())
        self.resize(1320, 800)
        self.setMinimumSize(1080, 640)
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QHBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.nav_selected.connect(self.show_page)
        root_lay.addWidget(self.sidebar)
        right_col = QWidget()
        right_lay = QVBoxLayout(right_col)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        self.topbar = TopBar()
        right_lay.addWidget(self.topbar)
        self.stack = QStackedWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.stack)
        right_lay.addWidget(scroll, 1)
        root_lay.addWidget(right_col, 1)
        self.pages = {}
        page_classes = {
            "cleaner": CleanerPage,
            "dashboard": DashboardPage,
            "processes": ProcessesPage,
            "startup": StartupPage,
            "explorer": ExplorerPage,
            "sysinfo": SysInfoPage,
            "network": NetworkPage,
            "booster": BoosterPage,
            "boost": BoostPage,
            "downloader": DownloaderPage,
        }
        for key, cls in page_classes.items():
            page = cls()
            self.stack.addWidget(page)
            self.pages[key] = page
        self.current_key = None
        theme_bus.changed.connect(self.on_theme_changed)
        self.sidebar.set_admin_status(is_admin())
        self.show_page("cleaner")
        self.apply_theme()
    def show_page(self, key):
        if self.current_key and self.current_key in self.pages:
            self.pages[self.current_key].on_hide()
        self.sidebar.set_active(key)
        self.stack.setCurrentWidget(self.pages[key])
        self.topbar.set_page_title(key)
        self.pages[key].on_show()
        self.current_key = key
    def on_theme_changed(self, _dark):
        self.apply_theme()
    def apply_theme(self):
        QApplication.instance().setStyleSheet(build_stylesheet())
        self.sidebar.restyle()
        self.topbar.restyle()
        for page in self.pages.values():
            page.restyle()
    def showEvent(self, event):
        super().showEvent(event)
        enable_anti_screenshot(self.winId())
    def closeEvent(self, event):
        for page in self.pages.values():
            try:
                page.on_hide()
            except Exception:
                pass
            for w in list(getattr(page, "_workers", [])):
                try:
                    if w.isRunning():
                        w.wait(200)
                except Exception:
                    pass
        event.accept()
def main():
    if os.name != "nt" and not os.environ.get("PC_SUITE_ALLOW_NON_WINDOWS"):
        print("هذه الأداة تعمل فقط على Windows.")
        sys.exit(1)
    if os.name == "nt" and not is_admin() and not os.environ.get("PC_SUITE_SKIP_ELEVATION"):
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{a}"' for a in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setWindowIcon(make_icon())
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    enable_anti_screenshot(window.winId())
    sys.exit(app.exec())
if __name__ == "__main__":
    main()
