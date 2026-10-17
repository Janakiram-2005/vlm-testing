import tkinter as tk
import time
import os
import asyncio
import pyautogui
import cv2
import numpy as np
import gspread
import traceback
import webbrowser
import keyboard
import random
import datetime
import ctypes
import re
import json
import math
from google import genai
from google.genai import types

from network_guard import check_url_health, wait_for_visual_settle, trigger_f5_recovery, circuit_breaker
from live_scenario_bank import LIVE_SCENARIO_BANK

# Fix Windows Display Scaling so PyAutoGUI uses physical pixel coordinates correctly
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

pyautogui.FAILSAFE = False

DEBUG_MODE = True
# Default to Gemini 3.6 Flash on Global Endpoint
_env_model = os.environ.get('VLM_MODEL_NAME', 'gemini-3.6-flash')
MODEL_NAME = 'gemini-3.6-flash' if _env_model in ['gemini-2.5-flash', 'gemini-3.5-flash', ''] else _env_model
VERTEX_LOCATION = os.environ.get('VERTEX_LOCATION', 'global')
SPREADSHEET_ID = '1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY'
WORKSHEET_NAME = 'Live_Web_Benchmark'

# --- Live Web Behavioral Cloning Dataset Configuration ---
LIVE_DATASET_DIR = 'live_vlm_dataset'
LIVE_IMAGES_DIR = os.path.join(LIVE_DATASET_DIR, 'images')
LIVE_JSONL_FILE = os.path.join(LIVE_DATASET_DIR, 'dataset.jsonl')

GLOBAL_LIVE_TEST_ID = 1

# --- Tkinter Live Visual Overlay (Prominent Info Bar) ---
class VLMOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.attributes("-transparentcolor", "black")
        self.root.config(bg="black")
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        
        # Prominent Live Info Display Bar (Rendered visibly at top of screen)
        self.status_frame = tk.Frame(self.root, bg="#0d1117", highlightbackground="#30363d", highlightthickness=2)
        self.status_frame.place(relx=0.5, rely=0.015, anchor='n', width=1280, height=82)
        
        self.lbl_task = tk.Label(self.status_frame, text="Task: INITIALIZING LIVE ENGINE", font=("Consolas", 13, "bold"), bg='#0d1117', fg='#e1e4e8')
        self.lbl_task.pack(pady=3)
        
        bottom_frame = tk.Frame(self.status_frame, bg="#0d1117")
        bottom_frame.pack(fill=tk.X, padx=20)
        
        self.lbl_status = tk.Label(bottom_frame, text="Status: READY [Press ESC to Kill]", font=("Consolas", 11), bg='#0d1117', fg='#58a6ff')
        self.lbl_status.pack(side=tk.LEFT)
        
        self.lbl_model = tk.Label(bottom_frame, text=f"Model: {MODEL_NAME.upper()} ({VERTEX_LOCATION.upper()})", font=("Consolas", 10, "bold"), bg='#0d1117', fg='#a78bfa')
        self.lbl_model.pack(side=tk.LEFT, padx=30)
        
        self.lbl_result = tk.Label(bottom_frame, text="Result: PENDING", font=("Consolas", 11, "bold"), bg='#0d1117', fg='#f2cc60')
        self.lbl_result.pack(side=tk.RIGHT)
        
        self.border_frame = tk.Frame(self.root, bg="black", highlightbackground="#00f2fe", highlightthickness=10)
        self.root.update()
        
    def update_ui(self, task_text=None, status_text=None, status_color=None, result_text=None, result_color=None, model_text=None):
        if task_text is not None:
            self.lbl_task.config(text=f"Task: {task_text}")
        if status_text is not None:
            self.lbl_status.config(text=f"Status: {status_text} [Press ESC to Kill]", fg=status_color if status_color else '#58a6ff')
        if result_text is not None:
            self.lbl_result.config(text=f"Result: {result_text}", fg=result_color if result_color else '#f2cc60')
        if model_text is not None:
            self.lbl_model.config(text=f"Model: {model_text}")
        self.root.update()

    def flash_capture_effect(self):
        self.border_frame.place(x=0, y=0, width=self.screen_width, height=self.screen_height)
        self.root.update()
        time.sleep(0.10)
        self.border_frame.place_forget()
        self.root.update()

def capture_video_buffer(duration=1.0, fps=5, filename="live_buffer.mp4"):
    """
    Captures video buffer at full native resolution with live display bar kept visible,
    giving the user continuous real-time feedback and Gemini razor-sharp visual information.
    """
    frames = []
    num_frames = int(duration * fps)
    last_img = None
    
    for _ in range(num_frames):
        start_time = time.time()
        try:
            img = pyautogui.screenshot()
            last_img = img
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frames.append(frame)
        except Exception:
            pass
            
        elapsed = time.time() - start_time
        sleep_time = max(0, (1.0 / fps) - elapsed)
        time.sleep(sleep_time)

    if frames:
        height, width, _ = frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        video = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        for frame in frames:
            video.write(frame)
        video.release()
        
    return last_img

def extract_coords_from_array(array_str, screen_w, screen_h):
    nums = re.findall(r'\d+', array_str)
    if len(nums) >= 4:
        ymin, xmin, ymax, xmax = map(int, nums[:4])
        norm_y = (ymin + ymax) / 2.0
        norm_x = (xmin + xmax) / 2.0
    elif len(nums) >= 2:
        norm_y, norm_x = int(nums[0]), int(nums[1])
    else:
        return None, None
        
    pixel_y = int((norm_y / 1000.0) * screen_h)
    pixel_x = int((norm_x / 1000.0) * screen_w)
    return pixel_x, pixel_y

def parse_type_command(sub):
    """
    Robust parser handling:
    1. Bracketed: TYPE [72, 233, 97, 348] text
    2. Raw numbers: TYPE 72 233 97 348 text
    3. Direct text (when already focused): TYPE text
    """
    m_bracket = re.search(r'TYPE\s*(\[.*?\])\s*(.*)', sub, re.IGNORECASE)
    if m_bracket:
        return m_bracket.group(1), m_bracket.group(2).strip().strip("'\"")
        
    m_raw = re.search(r'TYPE\s+((?:\d+[\s,]+){1,3}\d+)\s+(.*)', sub, re.IGNORECASE)
    if m_raw:
        return m_raw.group(1), m_raw.group(2).strip().strip("'\"")
        
    nums = re.findall(r'\d+', sub)
    if len(nums) >= 2:
        last_num = nums[3] if len(nums) >= 4 else nums[1]
        last_idx = sub.rfind(last_num) + len(last_num)
        text = sub[last_idx:].strip().strip("'\"")
        coord_str = " ".join(nums[:4] if len(nums) >= 4 else nums[:2])
        return coord_str, text
        
    # Support TYPE directly into already focused element (e.g. "TYPE deep learning")
    m_simple = re.search(r'TYPE\s+(.+)', sub, re.IGNORECASE)
    if m_simple:
        return None, m_simple.group(1).strip().strip("'\"")
        
    return None, None

def extract_commands(vlm_response):
    """
    Robustly extracts thoughts and commands from any VLM output formatting,
    stripping markdown bold, backticks, bullet numbers, and command prefixes.
    Guards against empty responses to prevent IndexError.
    """
    if not vlm_response or not vlm_response.strip():
        return "Analyzing current screen state.", "WAIT 1.0", ["WAIT 1.0"]

    lines = [l.strip() for l in vlm_response.strip().split('\n') if l.strip()]
    if not lines:
        return "Analyzing current screen state.", "WAIT 1.0", ["WAIT 1.0"]
        
    thought = ""
    command_str = ""
    
    for l in lines:
        if re.match(r'^(?:\*\*)?THOUGHT(?:\*\*)?:?', l, re.IGNORECASE):
            thought = re.sub(r'^(?:\*\*)?THOUGHT(?:\*\*)?:?\s*', '', l, flags=re.IGNORECASE).strip()
            break
    if not thought and lines:
        thought = lines[0]
        
    for l in reversed(lines):
        clean_l = re.sub(r'^(?:\*\*)?(?:COMMAND|ACTION)(?:\*\*)?:?\s*', '', l, flags=re.IGNORECASE).strip()
        clean_l = clean_l.strip('`* ')
        clean_l = re.sub(r'^\d+\.\s*', '', clean_l)
        if any(keyword in clean_l.upper() for keyword in ["CLICK", "TYPE", "PRESS", "SCROLL", "DONE", "FAILED", "WAIT", "ENTER", "HOVER", "DRAG"]):
            command_str = clean_l
            break
            
    if not command_str:
        if lines:
            command_str = re.sub(r'^(?:\*\*)?(?:COMMAND|ACTION)(?:\*\*)?:?\s*', '', lines[-1], flags=re.IGNORECASE).strip().strip('`* ')
        else:
            command_str = "WAIT 1.0"
        
    subs = re.split(r'\s+THEN\s+', command_str, flags=re.IGNORECASE)
    clean_subs = [s.strip().strip('`* ') for s in subs if s.strip()]
    if not clean_subs:
        clean_subs = ["WAIT 1.0"]
    return thought, command_str, clean_subs

_CACHED_WORKSHEET = None

def get_live_worksheet():
    global _CACHED_WORKSHEET
    if _CACHED_WORKSHEET is None:
        gc = gspread.service_account(filename='convertionalai-d8da9e4d43dd.json')
        sh = gc.open_by_key(SPREADSHEET_ID)
        _CACHED_WORKSHEET = sh.worksheet(WORKSHEET_NAME)
    return _CACHED_WORKSHEET

def log_to_live_sheet(batch_id, platform, scenario, page_load_ms, vlm_latency_ms, total_time_ms, status, error_type, action_chain, total_steps):
    global GLOBAL_LIVE_TEST_ID, _CACHED_WORKSHEET
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            worksheet = get_live_worksheet()
            
            if GLOBAL_LIVE_TEST_ID == 1:
                records = worksheet.get_all_values()
                GLOBAL_LIVE_TEST_ID = max(1, len(records))
                
            chain_str = " -> ".join(action_chain) if action_chain else "None"
            row = [
                f"Live-{GLOBAL_LIVE_TEST_ID:03d}",
                f"Batch-{batch_id:02d}",
                str(datetime.datetime.now()),
                platform,
                scenario,
                f"{round(page_load_ms, 1)}ms",
                f"{round(vlm_latency_ms, 1)}ms",
                f"{round(total_time_ms, 1)}ms",
                status,
                error_type,
                chain_str,
                total_steps
            ]
            worksheet.append_row(row)
            print(f"[DATABASE] Logged {status} ({error_type}) to Sheet 2 as Live-{GLOBAL_LIVE_TEST_ID:03d}")
            GLOBAL_LIVE_TEST_ID += 1
            return
        except Exception as e:
            print(f"[DATABASE WARN] Attempt {attempt} failed: {e}")
            _CACHED_WORKSHEET = None
            time.sleep(2)

async def ask_vlm_live_action(task_prompt, previous_actions):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'convertionalai-d8da9e4d43dd.json'
    client = genai.Client(vertexai=True, project='convertionalai', location=VERTEX_LOCATION)
    
    chain_history = " -> ".join(previous_actions) if previous_actions else "None"
    
    instruction = (
        "You are an elite Autonomous UI Agent operating on LIVE real-world websites. "
        "Analyze the 1-second video buffer of the screen to identify elements, visual layout shifts, and dynamic states. "
        "You have native spatial understanding. To interact with an element, output its 2D bounding box in normalized [ymin, xmin, ymax, xmax] format (0-1000 scale).\n\n"
        "NOTE: The top banner contains agent HUD telemetry (Task, Status, Model). Ignore it and interact with the target webpage underneath.\n\n"
        "PRIORITY 0 (MODAL & COOKIE DISMISSAL):\n"
        "- If a cookie consent banner, location dialog ('Deliver to...'), or promotional overlay obstructs the page, click its Dismiss / Close / 'Accept All' button first.\n\n"
        "MACRO PLANNING:\n"
        "- You may chain up to 3 commands using ' THEN ' (e.g. 'CLICK [coords] THEN TYPE text THEN PRESS_ENTER').\n\n"
        "You MUST reply in exactly TWO lines:\n"
        "1. A THOUGHT line starting with 'THOUGHT: ' explaining what you see, what you did previously, and your next step.\n"
        "2. The COMMAND line with your action(s):\n"
        "   - CLICK [ymin, xmin, ymax, xmax]\n"
        "   - DOUBLE_CLICK [ymin, xmin, ymax, xmax] (For spreadsheet cells or text selection)\n"
        "   - TYPE [ymin, xmin, ymax, xmax] <TEXT>\n"
        "   - PRESS_ENTER (Hits Enter on keyboard to submit search)\n"
        "   - HOVER [ymin, xmin, ymax, xmax] (To reveal hidden dropdowns/menus)\n"
        "   - SCROLL DOWN (Use if the target is below the current viewport)\n"
        "   - SCROLL UP (Use to scroll back up)\n"
        "   - WAIT [seconds] (e.g. WAIT 1.0 - Use between actions for page load)\n"
        "   - DONE (CRITICAL: When the goal is visibly achieved, output DONE immediately)\n"
        "   - FAILED (If stuck or target element does not exist)\n\n"
        f"Previous Action History: {chain_history}"
    )
    
    with open('live_buffer.mp4', 'rb') as f:
        video_bytes = f.read()
        
    def _call_api():
        for attempt in range(3):
            try:
                return client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        types.Part.from_bytes(data=video_bytes, mime_type='video/mp4'),
                        instruction + "\n\nUser Task: " + task_prompt
                    ]
                )
            except Exception as e:
                if '429' in str(e) and attempt < 2:
                    print("⚠️ API RATE LIMIT (429). Retrying in 8 seconds...")
                    time.sleep(8)
                else:
                    raise e
                    
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, _call_api)
    raw_text = response.text if (response and response.text) else ""
    if not raw_text.strip():
        try:
            if response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        raw_text += part.text
        except Exception:
            pass
    if not raw_text.strip():
        raw_text = "THOUGHT: Analyzing current screen state.\nCOMMAND: WAIT 1.0"
    return raw_text

async def execute_live_test(overlay, batch_id, platform, url, scenario, page_load_ms):
    overlay.update_ui(task_text=f"[{platform}] {scenario}", status_text="RUNNING LIVE SPATIAL TEST...", status_color="#58a6ff", result_text="PENDING", result_color="#f2cc60")
    
    start_time = time.time()
    vlm_total_latency_ms = 0.0
    action_chain = []
    trajectory_buffer = []
    click_history = []
    consecutive_repeats = 0
    max_steps = 8  # Ample step budget for overlay dismissal + multi-step navigation
    status = "FAILED"
    error_type = "AI_SPATIAL_MISS"
    
    screen_w, screen_h = overlay.screen_width, overlay.screen_height
    
    for step in range(1, max_steps + 1):
        overlay.update_ui(status_text=f"STEP {step}/{max_steps}: CAPTURING LIVE BUFFER...", status_color="#58a6ff")
        overlay.flash_capture_effect()
        captured_pil = capture_video_buffer(duration=1.0, fps=5, filename="live_buffer.mp4")
        
        overlay.update_ui(status_text=f"STEP {step}/{max_steps}: {MODEL_NAME.upper()} INFERENCE...", status_color="#db61a2")
        vlm_t0 = time.time()
        
        try:
            vlm_response = await ask_vlm_live_action(scenario, action_chain)
            vlm_latency = (time.time() - vlm_t0) * 1000.0
            vlm_total_latency_ms += vlm_latency
            print(f"\n[STEP {step}] VLM Response ({round(vlm_latency, 1)}ms):\n{vlm_response}")
        except Exception as e:
            print("[VLM ERROR]", e)
            error_type = "API_INFERENCE_ERROR"
            break
            
        thought_line, full_command, sub_commands = extract_commands(vlm_response)
        step_done = False
        
        for sub in sub_commands:
            sub = sub.strip()
            action_chain.append(sub)
            sub_upper = sub.upper()
            
            if "DONE" in sub_upper:
                status = "PASSED"
                error_type = "NONE"
                step_done = True
                break
            elif "FAILED" in sub_upper:
                status = "FAILED"
                error_type = "AI_ABORTED"
                step_done = True
                break
            elif "SCROLL DOWN" in sub_upper:
                overlay.update_ui(status_text="ACTION: SCROLL DOWN", status_color="#3fb950")
                pyautogui.scroll(-280)
                time.sleep(1.0)
            elif "SCROLL UP" in sub_upper:
                overlay.update_ui(status_text="ACTION: SCROLL UP", status_color="#3fb950")
                pyautogui.scroll(280)
                time.sleep(1.0)
            elif any(k in sub_upper for k in ["PRESS_ENTER", "PRESS ENTER", "HIT ENTER"]) or sub_upper == "ENTER":
                overlay.update_ui(status_text="ACTION: PRESS ENTER", status_color="#3fb950")
                pyautogui.press('enter')
                time.sleep(1.2)
            elif "DOUBLE_CLICK" in sub_upper:
                px, py = extract_coords_from_array(sub, screen_w, screen_h)
                if px is not None and py is not None:
                    overlay.update_ui(status_text=f"ACTION: DOUBLE_CLICK ({px}, {py})", status_color="#3fb950")
                    pyautogui.moveTo(px, py, duration=0.25, tween=pyautogui.easeInOutQuad)
                    pyautogui.doubleClick()
                    time.sleep(0.8)
            elif "DRAG" in sub_upper:
                matches = re.findall(r'\[\s*[\d,\s]+\s*\]', sub)
                if len(matches) >= 2:
                    p1x, p1y = extract_coords_from_array(matches[0], screen_w, screen_h)
                    p2x, p2y = extract_coords_from_array(matches[1], screen_w, screen_h)
                    if p1x is not None and p2x is not None:
                        overlay.update_ui(status_text=f"ACTION: DRAG ({p1x},{p1y}) -> ({p2x},{p2y})", status_color="#3fb950")
                        pyautogui.moveTo(p1x, p1y, duration=0.25, tween=pyautogui.easeInOutQuad)
                        pyautogui.dragTo(p2x, p2y, duration=0.8, button='left')
                        time.sleep(0.8)
            elif "HOVER" in sub_upper:
                px, py = extract_coords_from_array(sub, screen_w, screen_h)
                if px is not None and py is not None:
                    overlay.update_ui(status_text=f"ACTION: HOVER ({px}, {py})", status_color="#3fb950")
                    pyautogui.moveTo(px, py, duration=0.3, tween=pyautogui.easeInOutQuad)
                    time.sleep(0.8)
            elif "CLICK" in sub_upper:
                px, py = extract_coords_from_array(sub, screen_w, screen_h)
                if px is not None and py is not None:
                    # Anti-Stagnation Watchdog: Detect repetitive clicks on same element
                    if click_history and math.hypot(px - click_history[-1][0], py - click_history[-1][1]) < 28:
                        consecutive_repeats += 1
                    else:
                        consecutive_repeats = 0
                    click_history.append((px, py))
                    
                    if consecutive_repeats >= 1:
                        jitter_x = random.choice([-16, 16])
                        jitter_y = random.choice([-14, 14])
                        px = max(10, min(screen_w - 10, px + jitter_x))
                        py = max(10, min(screen_h - 10, py + jitter_y))
                        print(f"⚠️ [ANTI-STAGNATION] Jitter offset applied: ({jitter_x:+d}, {jitter_y:+d}) -> clicking ({px}, {py})")
                        overlay.update_ui(status_text=f"JITTER HEAL: CLICK ({px}, {py})", status_color="#f2cc60")
                        action_chain.append(f"STAGNATION_HEAL: Offset applied to ({px},{py})")
                    else:
                        overlay.update_ui(status_text=f"ACTION: CLICK ({px}, {py})", status_color="#3fb950")
                        
                    pyautogui.moveTo(px, py, duration=0.25, tween=pyautogui.easeInOutQuad)
                    pyautogui.click()
                    time.sleep(0.8)
            elif "TYPE" in sub_upper:
                coord_str, text_to_type = parse_type_command(sub)
                if text_to_type is not None:
                    overlay.update_ui(status_text=f"ACTION: TYPE '{text_to_type}'", status_color="#3fb950")
                    if coord_str is not None:
                        px, py = extract_coords_from_array(coord_str, screen_w, screen_h)
                        if px is not None and py is not None:
                            pyautogui.moveTo(px, py, duration=0.25)
                            pyautogui.click()
                            time.sleep(0.2)
                            # Clear old placeholder/previous search input cleanly
                            pyautogui.hotkey('ctrl', 'a')
                            time.sleep(0.1)
                    pyautogui.write(text_to_type, interval=0.03)
                    time.sleep(0.5)
            elif "WAIT" in sub_upper:
                wait_match = re.search(r'\d+(?:\.\d+)?', sub)
                sec = float(wait_match.group(0)) if wait_match else 1.0
                time.sleep(sec)
                
        # [BEHAVIORAL CLONING] Buffer trajectory frame
        if captured_pil is not None and "DONE" not in full_command.upper():
            trajectory_buffer.append({
                "step": step,
                "image": captured_pil,
                "thought": thought_line,
                "action_label": full_command,
                "history": list(action_chain)
            })
            
        if step_done:
            break
            
    total_time_ms = (time.time() - start_time) * 1000.0
    res_color = "#3fb950" if status == "PASSED" else "#ff7b72"
    overlay.update_ui(result_text=status, result_color=res_color, status_text=f"COMPLETED ({round(total_time_ms, 1)}ms)", status_color=res_color)
    
    # [LIVE BEHAVIORAL CLONING] Flush buffer to live_vlm_dataset ONLY if trajectory was PERFECT
    if status == "PASSED" and trajectory_buffer:
        os.makedirs(LIVE_IMAGES_DIR, exist_ok=True)
        run_id = f"live_{int(time.time())}"
        with open(LIVE_JSONL_FILE, "a", encoding="utf-8") as f:
            for item in trajectory_buffer:
                img_filename = f"{run_id}_step_{item['step']}.jpg"
                img_path = os.path.join(LIVE_IMAGES_DIR, img_filename)
                item['image'].save(img_path, quality=90)
                record = {
                    "image_file": img_filename,
                    "platform": platform,
                    "instruction": scenario,
                    "thought": item.get("thought", ""),
                    "history": item["history"][:-1],
                    "ground_truth": item["action_label"]
                }
                f.write(json.dumps(record) + "\n")
        print(f"\n[LIVE DATASET] Harvested {len(trajectory_buffer)} live web frames for Behavioral Cloning in '{LIVE_DATASET_DIR}'!")
    
    # Log to Google Sheets (Sheet 2)
    log_to_live_sheet(batch_id, platform, scenario, page_load_ms, vlm_total_latency_ms, total_time_ms, status, error_type, action_chain, len(action_chain))
    time.sleep(1.5)

def run_live_batch_loop(overlay, total_batches):
    async def _async_loop():
        for remaining in range(4, 0, -1):
            overlay.update_ui(task_text="LIVE BENCHMARK INIT", status_text=f"STARTING LIVE WEB SUITE IN {remaining}s...", status_color="#58a6ff")
            time.sleep(1)
            
        platforms = list(LIVE_SCENARIO_BANK.keys())
        screen_w, screen_h = overlay.screen_width, overlay.screen_height
        
        for batch_number in range(1, total_batches + 1):
            platform = platforms[(batch_number - 1) % len(platforms)]
            plat_data = LIVE_SCENARIO_BANK[platform]
            url = plat_data['url']
            
            overlay.update_ui(task_text=f"BATCH {batch_number}: {platform}", status_text="RUNNING PRE-FLIGHT HEALTH PING...", status_color="#f2cc60")
            
            # Step 1: Sub-second pre-flight health check
            is_healthy, health_reason = check_url_health(url)
            if not is_healthy:
                print(f"[FAST-FAIL] Skipping {platform} due to {health_reason}")
                overlay.update_ui(status_text=f"SKIPPED: {health_reason}", status_color="#ff7b72", result_text="SKIPPED", result_color="#ff7b72")
                log_to_live_sheet(batch_number, platform, "URL Health Check", 0.0, 0.0, 200.0, "SKIPPED", health_reason, ["PRE_FLIGHT_FAIL"], 0)
                time.sleep(2)
                continue
                
            # Select scenarios (1 normal, 1 difficult) - guaranteed distinct dimensions
            selected_normal = random.sample(plat_data['normal'], 1)
            selected_diff = random.sample(plat_data['difficult'], 1)
            scenarios = selected_normal + selected_diff
            
            for sc_idx, sc in enumerate(scenarios, 1):
                overlay.update_ui(task_text=f"BATCH {batch_number} [{sc_idx}/2]: {platform}", status_text=f"LAUNCHING FRESH TAB FOR {platform}...", status_color="#58a6ff")
                webbrowser.open(url)
                time.sleep(2.5)
                
                # Adaptive Visual Settling Watchdog for clean initial render
                settled, page_load_ms = wait_for_visual_settle(max_timeout=7.0)
                if not settled:
                    print("[WATCHDOG WARN] Visual variance high or blank. Attempting F5 self-healing...")
                    trigger_f5_recovery()
                    settled, extra_ms = wait_for_visual_settle(max_timeout=5.0)
                    page_load_ms += extra_ms
                    
                overlay.update_ui(status_text=f"PAGE SETTLED IN {round(page_load_ms, 1)}ms", status_color="#3fb950")
                time.sleep(0.5)
                
                await execute_live_test(overlay, batch_number, platform, url, sc, page_load_ms)
                time.sleep(1.0)
                
                # Cleanup: Close browser tab cleanly so next scenario gets 100% fresh slate
                pyautogui.hotkey('ctrl', 'w')
                time.sleep(1.0)
            
        overlay.update_ui(task_text="ALL BATCHES FINISHED", status_text=f"COMPLETED {total_batches} LIVE BATCHES!", status_color="#3fb950", result_text="DONE", result_color="#3fb950")
        time.sleep(3)
        os._exit(0)
        
    asyncio.run(_async_loop())

if __name__ == "__main__":
    print("==================================================")
    print("🌐 VLM AUTONOMOUS LIVE WEB BENCHMARK ENGINE")
    print(f"Active Model: {MODEL_NAME} ({VERTEX_LOCATION})")
    print(f"Targeting {len(LIVE_SCENARIO_BANK)} Live Platforms: {', '.join(LIVE_SCENARIO_BANK.keys())}")
    print("Telemetry: Logging to 'Live_Web_Benchmark' (Sheet 2)")
    print("Resilience: Pre-flight Ping + Visual Settling Watchdog + F5 Healing")
    print("==================================================")
    
    import sys
    total_platforms = len(LIVE_SCENARIO_BANK)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        total_batches = int(sys.argv[1])
    elif len(sys.argv) > 1 and sys.argv[1].lower() in ['--all', 'all']:
        total_batches = total_platforms
    else:
        try:
            batches_str = input(f"Enter number of batches to run (press Enter for all {total_platforms} platforms): ")
            total_batches = int(batches_str) if batches_str.strip() else total_platforms
        except Exception:
            total_batches = total_platforms
        
    print(f"[ENGINE] Launching suite for {total_batches} batches (2 live tests per platform)...")
    keyboard.add_hotkey('esc', lambda: os._exit(0))
    print("[INFO] Press ESC at any time to kill the benchmark engine.")
    
    app = VLMOverlay()
    import threading
    threading.Thread(target=run_live_batch_loop, args=(app, total_batches), daemon=True).start()
    app.root.mainloop()
