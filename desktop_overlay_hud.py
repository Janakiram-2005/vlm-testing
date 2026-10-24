"""
DESKTOP OVERLAY HUD (Live Transparent Status Banner)
====================================================
Non-intrusive, topmost floating transparent HUD for Windows OS automation.
Displays live scenario goal, active driver (Student vs Teacher), physical action,
and real-time CI/CD progress toward the 50-sample retraining threshold.
"""

import os
import sys
import time
import tkinter as tk
from typing import Optional

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class DesktopOverlayHUD:
    def __init__(self):
        self.root = None
        self._init_window()

    def _init_window(self):
        try:
            self.root = tk.Tk()
            self.root.attributes("-topmost", True)
            self.root.overrideredirect(True)
            self.root.attributes("-alpha", 0.92)
            self.root.config(bg="#090d16")

            screen_w = self.root.winfo_screenwidth()
            hud_w = min(1200, int(screen_w * 0.75))
            hud_h = 100
            pos_x = (screen_w - hud_w) // 2
            pos_y = 12

            self.root.geometry(f"{hud_w}x{hud_h}+{pos_x}+{pos_y}")

            # Outer glow border container
            self.outer_frame = tk.Frame(
                self.root,
                bg="#090d16",
                highlightbackground="#38bdf8",
                highlightthickness=2,
                padx=16,
                pady=8
            )
            self.outer_frame.pack(fill=tk.BOTH, expand=True)

            # Top row: Brand + Batch + Status + CI/CD Progress
            top_row = tk.Frame(self.outer_frame, bg="#090d16")
            top_row.pack(fill=tk.X)

            self.lbl_brand = tk.Label(
                top_row,
                text="⚡ HEALVLM AUTONOMOUS AGENT",
                font=("Segoe UI", 10, "bold"),
                bg="#090d16",
                fg="#38bdf8"
            )
            self.lbl_brand.pack(side=tk.LEFT)

            self.lbl_driver = tk.Label(
                top_row,
                text="[STUDENT LOCAL]",
                font=("Consolas", 10, "bold"),
                bg="#090d16",
                fg="#22c55e",
                padx=10
            )
            self.lbl_driver.pack(side=tk.LEFT)

            self.lbl_progress = tk.Label(
                top_row,
                text="CI/CD: 50.0% [25/50 samples]",
                font=("Consolas", 10, "bold"),
                bg="#090d16",
                fg="#f59e0b"
            )
            self.lbl_progress.pack(side=tk.RIGHT)

            # Middle row: Goal prompt
            self.lbl_goal = tk.Label(
                self.outer_frame,
                text="Goal: Initializing autonomous environment...",
                font=("Segoe UI", 10),
                bg="#090d16",
                fg="#e2e8f0",
                anchor="w",
                wraplength=hud_w - 40,
                justify="left"
            )
            self.lbl_goal.pack(fill=tk.X, pady=(4, 2))

            # Bottom row: Current Action / Thought
            bottom_row = tk.Frame(self.outer_frame, bg="#090d16")
            bottom_row.pack(fill=tk.X)

            self.lbl_action = tk.Label(
                bottom_row,
                text="Action: READY [Failsafe: Corner (0,0)]",
                font=("Consolas", 10, "bold"),
                bg="#090d16",
                fg="#38bdf8"
            )
            self.lbl_action.pack(side=tk.LEFT)

            self.lbl_status = tk.Label(
                bottom_row,
                text="RUNNING",
                font=("Consolas", 9, "bold"),
                bg="#090d16",
                fg="#94a3b8"
            )
            self.lbl_status.pack(side=tk.RIGHT)

            self.root.update()
        except Exception as e:
            print(f"HUD Notice: {e}")
            self.root = None

    def update_hud(
        self,
        batch_tag: str,
        scenario_name: str,
        goal: str,
        driver: str,
        action: str,
        status: str = "RUNNING",
        progress_str: str = ""
    ):
        """Updates all HUD metrics smoothly in real time."""
        if not self.root:
            return

        try:
            # Color-code border & driver badge
            if "TEACHER" in driver.upper():
                driver_color = "#c084fc"  # Purple for Vertex Gemini Teacher
                border_color = "#a855f7"
                driver_text = f"[{batch_tag}] 🎓 TEACHER VERTEX AI"
            else:
                driver_color = "#38bdf8"  # Cyan for Local HealVLM Student
                border_color = "#0ea5e9"
                driver_text = f"[{batch_tag}] 🤖 STUDENT HEALVLM"

            self.outer_frame.config(highlightbackground=border_color)
            self.lbl_driver.config(text=driver_text, fg=driver_color)

            # Truncate goal cleanly if too long
            display_goal = goal if len(goal) <= 120 else goal[:117] + "..."
            self.lbl_goal.config(text=f"Task: {scenario_name} | {display_goal}")

            # Action & Status
            display_act = action if len(action) <= 90 else action[:87] + "..."
            self.lbl_action.config(text=f"Action: {display_act}")

            status_color = "#22c55e" if "SUCCESS" in status.upper() or "COMPLETED" in status.upper() else (
                "#f43f5e" if "FAIL" in status.upper() else "#94a3b8"
            )
            self.lbl_status.config(text=status.upper(), fg=status_color)

            if progress_str:
                self.lbl_progress.config(text=progress_str)

            self.root.update()
        except Exception:
            pass

    def flash_action(self, color: str = "#22c55e"):
        """Flashes the HUD border momentarily upon action execution."""
        if not self.root:
            return
        try:
            orig = self.outer_frame.cget("highlightbackground")
            self.outer_frame.config(highlightbackground=color)
            self.root.update()
            time.sleep(0.08)
            self.outer_frame.config(highlightbackground=orig)
            self.root.update()
        except Exception:
            pass

    def close(self):
        """Cleanly destroys the HUD window."""
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

if __name__ == "__main__":
    hud = DesktopOverlayHUD()
    print("Testing HUD Display for 3 seconds...")
    hud.update_hud(
        batch_tag="Batch-01",
        scenario_name="Desktop -> Web Portal",
        goal="Open company_portal.html and click the blue Confirm button",
        driver="STUDENT_LOCAL",
        action="CLICK [188, 388, 218, 428]",
        status="RUNNING",
        progress_str="CI/CD: 50.0% [25/50 samples]"
    )
    time.sleep(1.5)
    hud.update_hud(
        batch_tag="Batch-01",
        scenario_name="Desktop PDF Reader",
        goal="Double click invoice_2026.pdf",
        driver="TEACHER_VERTEX",
        action="DOUBLE_CLICK [485, 290, 508, 381]",
        status="RECOVERED BY TEACHER",
        progress_str="CI/CD: 52.0% [26/50 samples]"
    )
    time.sleep(1.5)
    hud.close()
    print("✅ HUD Test Passed!")
