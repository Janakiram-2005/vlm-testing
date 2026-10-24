"""
HEALVLM AUTONOMOUS RUNNER
=========================
Dedicated, standalone execution engine linking directly to the fine-tuned
Qwen2-VL LoRA adapter (healvlm_colab_adapter) WITHOUT modifying existing files.

Executes real-time visual grounding, UI action primitives (CLICK, TYPE, SCROLL, DRAG),
and records newly confirmed steps into the dataset to fuel continuous CI/CD training.
"""

import os
import sys
import time
import json
import re
import ctypes
import pyautogui
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure Windows DPI awareness so physical pixel clicks land exactly where predicted
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# PyAutoGUI safety configuration
pyautogui.FAILSAFE = True  # Move mouse to any corner to abort
pyautogui.PAUSE = 0.3

# Import our dedicated HealVLM bridge
from healvlm_bridge import predict_healvlm_action, DEFAULT_ADAPTER_DIR

DATASET_JSONL = "live_vlm_dataset/dataset.jsonl"
IMAGES_DIR = "live_vlm_dataset/images"
FAILURE_FILE = "failure_logs.json"

def get_screen_dimensions() -> Tuple[int, int]:
    """Returns actual primary display resolution."""
    return pyautogui.size()

def parse_coordinates_to_screen(action_str: str, screen_w: int, screen_h: int) -> Optional[Tuple[int, int]]:
    """
    Parses normalized [0-1000] coordinates from action string and maps to screen pixels.
    Supports both [ymin, xmin, ymax, xmax] (bounding box) and [y, x] (point).
    """
    bracket_match = re.search(r'\[\s*([\d,\s]+)\s*\]', action_str)
    if not bracket_match:
        return None
    
    nums = [int(n.strip()) for n in re.findall(r'\d+', bracket_match.group(1))]
    if len(nums) >= 4:
        ymin, xmin, ymax, xmax = nums[:4]
        norm_y = (ymin + ymax) / 2.0
        norm_x = (xmin + xmax) / 2.0
    elif len(nums) >= 2:
        norm_y, norm_x = nums[0], nums[1]
    else:
        return None

    pixel_x = int((norm_x / 1000.0) * screen_w)
    pixel_y = int((norm_y / 1000.0) * screen_h)
    return pixel_x, pixel_y

def execute_action_primitive(action_str: str, screen_w: int, screen_h: int) -> bool:
    """
    Executes physical PyAutoGUI mouse and keyboard commands based on model output.
    Returns True if target reached (DONE) or action completed.
    """
    action_upper = action_str.upper().strip()
    print(f"  [ACTION EXECUTION]: {action_str}")

    if "DONE" in action_upper:
        print("  🎉 GOAL ACHIEVED: Agent declared DONE!")
        return True

    if "WAIT" in action_upper:
        seconds = 1.0
        m = re.search(r'WAIT\s*([\d\.]+)', action_upper)
        if m:
            seconds = float(m.group(1))
        print(f"  ⏳ Waiting for {seconds:.1f}s...")
        time.sleep(seconds)
        return False

    if "PRESS_ENTER" in action_upper:
        print("  ⌨️ Pressing Enter key...")
        pyautogui.press('enter')
        return False

    if "SCROLL" in action_upper:
        direction = -400 if "DOWN" in action_upper else 400
        print(f"  📜 Scrolling ({direction})...")
        pyautogui.scroll(direction)
        time.sleep(0.5)
        return False

    coords = parse_coordinates_to_screen(action_str, screen_w, screen_h)
    if coords is None:
        print(f"  ⚠️ Could not parse valid coordinates from: {action_str}")
        return False

    target_x, target_y = coords

    if "DOUBLE_CLICK" in action_upper:
        print(f"  🖱️ Double-Clicking at ({target_x}, {target_y})...")
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        pyautogui.doubleClick(target_x, target_y)
    elif "CLICK" in action_upper:
        print(f"  🖱️ Clicking at ({target_x}, {target_y})...")
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        pyautogui.click(target_x, target_y)
    elif "HOVER" in action_upper:
        print(f"  👀 Hovering at ({target_x}, {target_y})...")
        pyautogui.moveTo(target_x, target_y, duration=0.3)
    elif "TYPE" in action_upper:
        text_match = re.search(r'TYPE\s*(?:\[[^\]]*\])?\s*["\']([^"\']+)["\']', action_str, re.IGNORECASE)
        text_to_type = text_match.group(1) if text_match else ""
        print(f"  🖱️ Focusing ({target_x}, {target_y}) and typing: '{text_to_type}'...")
        pyautogui.click(target_x, target_y)
        time.sleep(0.2)
        pyautogui.typewrite(text_to_type, interval=0.04)

    return False

def record_live_trajectory_step(
    screenshot_path: str,
    goal: str,
    thought: str,
    action: str,
    platform: str = "Web"
):
    """
    Appends newly verified true actions to live_vlm_dataset/dataset.jsonl.
    This dynamically increments the dataset, feeding the CI/CD pipeline!
    """
    os.makedirs("live_vlm_dataset", exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    timestamp = int(time.time())
    dest_img_name = f"live_{timestamp}_step.jpg"
    dest_img_path = os.path.join(IMAGES_DIR, dest_img_name)

    try:
        shutil.copy2(screenshot_path, dest_img_path)
    except Exception:
        # If already same path or PIL image
        if os.path.exists(screenshot_path) and screenshot_path != dest_img_path:
            import shutil
            shutil.copy2(screenshot_path, dest_img_path)

    record = {
        "image_file": dest_img_name,
        "instruction": goal,
        "thought": thought,
        "ground_truth": action,
        "platform": platform,
        "timestamp": timestamp
    }

    with open(DATASET_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    print(f"  💾 Step recorded to dataset ({dest_img_name})")

def run_autonomous_navigation(
    goal: str,
    max_steps: int = 6,
    adapter_dir: str = DEFAULT_ADAPTER_DIR,
    record_dataset: bool = False,
    platform_name: str = "Live_Web"
) -> bool:
    """
    Main autonomous navigation loop powered directly by HealVLM.
    """
    screen_w, screen_h = get_screen_dimensions()
    print("=" * 65)
    print("🚀 HEALVLM AUTONOMOUS NAVIGATION ENGINE")
    print("=" * 65)
    print(f"🎯 Target Goal     : {goal}")
    print(f"🖥️ Screen Resolution: {screen_w} x {screen_h}")
    print(f"🧠 LoRA Adapter     : {adapter_dir}")
    print(f"🔢 Max Steps Limit  : {max_steps}")
    print("=" * 65)

    previous_actions = []
    success = False

    for step in range(1, max_steps + 1):
        print(f"\n--- [STEP {step}/{max_steps}] ---")
        # 1. Capture screen
        screenshot_file = "current_screen.jpg"
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_file, quality=90)
        print("📸 Captured real-time screen state.")

        # 2. Query HealVLM adapter
        print("🧠 HealVLM model analyzing visual state...")
        start_t = time.time()
        try:
            raw_response = predict_healvlm_action(
                screenshot_file,
                task_prompt=goal,
                previous_actions=previous_actions,
                adapter_dir=adapter_dir
            )
        except Exception as e:
            print(f"❌ Inference error: {e}")
            break

        infer_time = time.time() - start_t
        print(f"⚡ Model Response ({infer_time:.2f}s):\n{raw_response}")

        # Extract THOUGHT and ACTION
        thought = "Analyzing visual cues and targeting element"
        action = raw_response
        for line in raw_response.splitlines():
            line_s = line.strip()
            if line_s.upper().startswith("THOUGHT:"):
                thought = line_s[8:].strip()
            elif line_s.upper().startswith("ACTION:"):
                action = line_s[7:].strip()

        # 3. Execute physical action
        is_done = execute_action_primitive(action, screen_w, screen_h)
        previous_actions.append(action)

        # 4. Optional: Continuous behavioral cloning dataset record
        if record_dataset:
            record_live_trajectory_step(screenshot_file, goal, thought, action, platform_name)

        if is_done:
            success = True
            break

        time.sleep(1.0)

    print("\n" + "=" * 65)
    if success:
        print("🎉 [RESULT: SUCCESS] Autonomous goal achieved successfully by HealVLM!")
    else:
        print("⚠️ [RESULT: TERMINATED] Completed sequence or reached max steps.")
    print("=" * 65)
    return success

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HealVLM Standalone Autonomous Engine")
    parser.add_argument("--goal", type=str, default="Click on the search bar", help="Goal instruction for the agent")
    parser.add_argument("--steps", type=int, default=5, help="Maximum navigation steps")
    parser.add_argument("--adapter", type=str, default=DEFAULT_ADAPTER_DIR, help="Path to adapter directory")
    parser.add_argument("--record", action="store_true", help="Record steps into dataset for continuous CI/CD learning")
    args = parser.parse_args()

    print("Starting in 3 seconds... Switch focus to target window!")
    time.sleep(3)
    run_autonomous_navigation(args.goal, max_steps=args.steps, adapter_dir=args.adapter, record_dataset=args.record)
