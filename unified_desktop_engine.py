"""
UNIFIED DESKTOP ENGINE (Windows OS + Web Automation Core)
=========================================================
Ultra-fast, DPI-aware OS perception and interaction engine.
Supports in-memory screen capture (<10ms), standard [0, 1000] coordinate
translation, atomic mouse/keyboard primitives, and window state verification.
"""

import os
import sys
import time
import math
import ctypes
import subprocess
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import mss
import pyautogui
import pygetwindow as gw

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def attach_to_default_desktop():
    """Ensures thread is attached to interactive 'default' desktop on WinSta0."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW('default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

# 1. Attach to interactive desktop and enable Per-Monitor DPI Awareness
attach_to_default_desktop()
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# 2. PyAutoGUI safety configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

class UnifiedDesktopEngine:
    def __init__(self, target_vlm_res: int = 1024):
        attach_to_default_desktop()
        self.sct = mss.mss()
        # Use primary monitor
        self.monitor = self.sct.monitors[1]
        self.screen_width = self.monitor["width"]
        self.screen_height = self.monitor["height"]
        self.target_vlm_res = target_vlm_res
        
        print("=" * 65)
        print("🖥️ UNIFIED DESKTOP OS ENGINE INITIALIZED")
        print(f"• Physical Display Resolution : {self.screen_width} x {self.screen_height}")
        print(f"• Coordinate Space            : [0, 1000] x [0, 1000]")
        print(f"• VLM Compressed Resolution   : Max {self.target_vlm_res}px (Low-latency mode)")
        print(f"• Safety Failsafe             : Top-Left Corner (0,0) Aborts")
        print("=" * 65)

    def capture_screen(self, save_path: Optional[str] = None) -> Tuple[Image.Image, Image.Image]:
        """
        Captures the primary monitor using in-memory C-bindings (5-10ms).
        Returns:
            raw_img: Full resolution physical PIL image.
            vlm_img: Resized, optimized PIL image for Vertex / Qwen2-VL (30ms upload).
        """
        # Ensure attached to interactive desktop
        attach_to_default_desktop()
        # Grab raw screenshot
        sct_img = self.sct.grab(self.monitor)
        # Convert BGRA to RGB PIL Image
        raw_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # Downscale proportionally for low-latency VLM processing
        w, h = raw_img.size
        scale = min(self.target_vlm_res / w, self.target_vlm_res / h)
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            vlm_img = raw_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            vlm_img = raw_img.copy()

        if save_path:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            vlm_img.save(save_path, format="JPEG", quality=85)

        return raw_img, vlm_img

    def norm_to_pixel(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Maps [0, 1000] normalized coordinate to physical screen pixel (X, Y)."""
        px_x = int((norm_x / 1000.0) * self.screen_width)
        px_y = int((norm_y / 1000.0) * self.screen_height)
        # Clamp within display boundaries
        px_x = max(0, min(self.screen_width - 1, px_x))
        px_y = max(0, min(self.screen_height - 1, px_y))
        return px_x, px_y

    def pixel_to_norm(self, px_x: int, px_y: int) -> Tuple[int, int]:
        """Maps physical screen pixel to standard [0, 1000] coordinate."""
        norm_x = int((px_x / float(self.screen_width)) * 1000.0)
        norm_y = int((px_y / float(self.screen_height)) * 1000.0)
        return norm_x, norm_y

    def click(self, norm_x: float, norm_y: float, clicks: int = 1, interval: float = 0.1):
        """Moves cursor and clicks at normalized coordinate."""
        px_x, px_y = self.norm_to_pixel(norm_x, norm_y)
        pyautogui.moveTo(px_x, px_y, duration=0.15)
        pyautogui.click(px_x, px_y, clicks=clicks, interval=interval)
        print(f"🖱️ Click ({clicks}x) at norm [{int(norm_x)}, {int(norm_y)}] -> px ({px_x}, {px_y})")

    def double_click(self, norm_x: float, norm_y: float):
        """Atomic double click with locked cursor (critical for desktop icons/files)."""
        px_x, px_y = self.norm_to_pixel(norm_x, norm_y)
        pyautogui.moveTo(px_x, px_y, duration=0.15)
        pyautogui.doubleClick(px_x, px_y, interval=0.12)
        print(f"📂 Double-Click at norm [{int(norm_x)}, {int(norm_y)}] -> px ({px_x}, {px_y})")

    def type_text(self, text: str, press_enter: bool = False):
        """Types text with natural human micro-delays."""
        print(f"⌨️ Typing text: '{text}' (enter={press_enter})")
        pyautogui.write(text, interval=0.03)
        if press_enter:
            time.sleep(0.1)
            pyautogui.press("enter")

    def hotkey(self, *keys: str):
        """Executes hotkey combination e.g. ('win', 'r') or ('ctrl', 's')."""
        print(f"⚡ Hotkey: {' + '.join(keys)}")
        pyautogui.hotkey(*keys)

    def drag(self, start_norm: Tuple[float, float], end_norm: Tuple[float, float], duration: float = 0.5):
        """Executes click-and-drag from start to end (used for MS Paint, sliders, selections)."""
        sx, sy = self.norm_to_pixel(*start_norm)
        ex, ey = self.norm_to_pixel(*end_norm)
        print(f"🎨 Drag from norm {start_norm} to {end_norm} (px ({sx},{sy}) -> ({ex},{ey}))")
        pyautogui.moveTo(sx, sy, duration=0.15)
        pyautogui.dragTo(ex, ey, duration=duration, button='left')

    def ensure_window_focus(self, title_substring: str) -> bool:
        """Finds and focuses a window containing title_substring."""
        try:
            matches = [w for w in gw.getAllWindows() if title_substring.lower() in w.title.lower()]
            if matches:
                win = matches[0]
                if not win.isActive:
                    win.activate()
                    time.sleep(0.2)
                return True
        except Exception as e:
            print(f"Note: Could not focus window '{title_substring}': {e}")
        return False

    def get_active_window_title(self) -> str:
        """Returns the title of the currently focused window."""
        try:
            win = gw.getActiveWindow()
            return win.title if win else "Desktop"
        except Exception:
            return "Desktop"

    def compute_visual_difference(self, img_before: Image.Image, img_after: Image.Image) -> float:
        """
        Computes normalized percentage of pixel difference between two screenshots.
        Returns value between 0.0 (identical) and 100.0 (completely changed).
        """
        # Downscale both to 256x256 for instantaneous comparison (<3ms)
        small_a = img_before.resize((256, 256)).convert("L")
        small_b = img_after.resize((256, 256)).convert("L")
        
        diff = 0
        pixels_a = small_a.tobytes()
        pixels_b = small_b.tobytes()
        total_px = len(pixels_a)
        
        changed = sum(1 for i in range(total_px) if abs(pixels_a[i] - pixels_b[i]) > 20)
        diff_pct = (changed / float(total_px)) * 100.0
        return diff_pct

    def fast_shell_reset(self, process_names: list, paths_to_clean: list = None):
        """
        Instant state reset in ~30ms using fast shell commands.
        e.g. process_names=['notepad.exe', 'mspaint.exe']
        """
        for proc in process_names:
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", proc],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                pass
        if paths_to_clean:
            for p in paths_to_clean:
                if os.path.exists(p):
                    try:
                        if os.path.isdir(p):
                            subprocess.run(["rmdir", "/s", "/q", p], shell=True)
                        else:
                            os.remove(p)
                    except Exception:
                        pass

if __name__ == "__main__":
    engine = UnifiedDesktopEngine()
    print("Testing 10ms screen capture...")
    t0 = time.time()
    raw, vlm = engine.capture_screen("test_screen_sample.jpg")
    elapsed = (time.time() - t0) * 1000.0
    print(f"✅ Screen captured in {elapsed:.2f}ms | Raw size: {raw.size} | VLM size: {vlm.size}")
    print(f"✅ Active Window: {engine.get_active_window_title()}")
