import tkinter as tk
import time
import os
import asyncio
import pyautogui
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
import os
import json
from google import genai
from google.genai import types

# --- MEMORY SYSTEM ---
MEMORY_FILE = 'spatial_memory.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_memory(mem):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=4)
# ---------------------

# Fix Windows Display Scaling so PyAutoGUI uses physical pixel coordinates correctly
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

pyautogui.FAILSAFE = False

DEBUG_MODE = True
MODEL_NAME = 'gemini-2.5-flash'  # High-speed multi-step model

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
        
        # --- Advanced Live UI ---
        self.status_frame = tk.Frame(self.root, bg="#0d1117", highlightbackground="#30363d", highlightthickness=2)
        self.status_frame.place(relx=0.5, rely=0.02, anchor='n', width=1200, height=80)
        
        self.lbl_task = tk.Label(self.status_frame, text="Task: IDLE", font=("Consolas", 14, "bold"), bg='#0d1117', fg='#e1e4e8')
        self.lbl_task.pack(pady=4)
        
        bottom_frame = tk.Frame(self.status_frame, bg="#0d1117")
        bottom_frame.pack(fill=tk.X, padx=20)
        
        self.lbl_status = tk.Label(bottom_frame, text="Status: WAITING [Press ESC to Kill]", font=("Consolas", 12), bg='#0d1117', fg='#58a6ff')
        self.lbl_status.pack(side=tk.LEFT)
        
        self.lbl_result = tk.Label(bottom_frame, text="Result: PENDING", font=("Consolas", 12, "bold"), bg='#0d1117', fg='#f2cc60')
        self.lbl_result.pack(side=tk.RIGHT)
        
        self.border_frame = tk.Frame(self.root, bg="black", highlightbackground="#00f2fe", highlightthickness=12)
        
    def update_ui(self, task_text=None, status_text=None, status_color=None, result_text=None, result_color=None):
        if task_text is not None:
            self.lbl_task.config(text=f"Task: {task_text}")
        if status_text is not None:
            self.lbl_status.config(text=f"Status: {status_text} [Press ESC to Kill]", fg=status_color if status_color else '#58a6ff')
        if result_text is not None:
            self.lbl_result.config(text=f"Result: {result_text}", fg=result_color if result_color else '#f2cc60')
        self.root.update()
        
    def flash_capture_effect(self):
        self.border_frame.place(x=0, y=0, width=self.screen_width, height=self.screen_height)
        self.root.update()
        time.sleep(0.15)
        self.border_frame.place_forget()
        self.root.update()

async def ask_vlm_next_action(img_path, task_prompt, previous_actions):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'convertionalai-d8da9e4d43dd.json'
    client = genai.Client(vertexai=True, project='convertionalai', location='us-central1')
    
    chain_history = " -> ".join(previous_actions) if previous_actions else "None"
    
    instruction = (
        "You are an elite Autonomous UI Agent controlling a computer screen natively. "
        "Analyze the User Task, verify the current screen state, and execute the NEXT logical step. "
        "You have native spatial understanding. To interact with an element, output its 2D bounding box in normalized [ymin, xmin, ymax, xmax] format (0-1000 scale).\n\n"
        "You MUST reply in exactly TWO lines:\n"
        "1. A THOUGHT line starting with 'THOUGHT: ' explaining what you see, what you did previously (memory), and what you need to do next.\n"
        "2. The COMMAND line with exactly ONE of these commands (OR chain them with ' THEN ' for MACRO-PLANNING):\n"
        "   - CLICK [ymin, xmin, ymax, xmax]\n"
        "   - TYPE [ymin, xmin, ymax, xmax] <TEXT>\n"
        "   - DRAG [y1, x1, y2, x2] TO [y3, x3, y4, x4] (Used to drag an object to a target zone)\n"
        "   - COPY [ymin, xmin, ymax, xmax] (Double-clicks the coordinates to highlight text, then hits Ctrl+C)\n"
        "   - PASTE [ymin, xmin, ymax, xmax] (Clicks the coordinates to focus an input field, then hits Ctrl+V)\n"
        "   - HOVER [ymin, xmin, ymax, xmax] (Moves the mouse to the target to reveal hidden hover-menus without clicking)\n"
        "   - SCROLL DOWN (Use if the target is not visible on screen)\n"
        "   - WAIT [seconds] (e.g. WAIT 1.5 - Use this to wait for an animation to finish between actions)\n"
        "   - DONE (CRITICAL: If your memory shows you achieved the goal, and you visually see success, output DONE.)\n"
        "   - FAILED (If you cannot see the target element or are stuck)\n\n"
        "SPECIAL RULES:\n"
        "- MACRO-PLANNING: You may output up to 3 commands at once separated by ' THEN ' (e.g. 'CLICK [x] THEN WAIT 0.5 THEN CLICK [y]'). ALWAYS insert a WAIT between actions if the layout might shift or open a popup. If an action will completely load a new page, stop and wait for a new screenshot.\n"
        "- If your command includes SCROLL DOWN, it must be the LAST command in your chain. You cannot chain clicks after a scroll.\n"
        "- If a sudden POPUP warning appears on the screen (e.g. Session Timeout), you MUST CLICK to close it before doing anything else!\n"
        "- CRITICAL STATE CHECK: If the target is ALREADY in the correct state (e.g., checkbox is already checked, or item is already in the target column), you MUST immediately output DONE. Do NOT click it again or you will undo the success!\n\n"
        f"Previous Action History: {chain_history}"
    )
    
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
        
    def _call_api():
        for attempt in range(3):
            try:
                return client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'),
                        instruction + "\n\nUser Task: " + task_prompt
                    ]
                )
            except Exception as e:
                if '429' in str(e) and attempt < 2:
                    print("⚠️ API RATE LIMIT (429). Retrying in 10 seconds...")
                    time.sleep(10)
                else:
                    raise e
                    
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, _call_api)
    return response.text.strip()

# Global state for Test ID tracking across batches
GLOBAL_TEST_ID = 1

def log_to_sheets(batch_id, model_name, scenario, total_time_ms, status, action_chain, total_steps):
    global GLOBAL_TEST_ID
    try:
        gc = gspread.service_account(filename='convertionalai-d8da9e4d43dd.json')
        sh = gc.open_by_key('1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY')
        worksheet = sh.sheet1
        
        if GLOBAL_TEST_ID == 1:
            records = worksheet.get_all_values()
            GLOBAL_TEST_ID = max(1, len(records)) 
            
        chain_str = " -> ".join(action_chain) if action_chain else "None"
        row = [
            f"Test-{GLOBAL_TEST_ID:03d}",
            f"Batch-{batch_id:02d}",
            str(datetime.datetime.now()), 
            model_name, 
            scenario, 
            f"{abs(round(total_time_ms, 2))}ms", 
            status, 
            chain_str, 
            total_steps
        ]
        worksheet.append_row(row)
        print(f"[DATABASE] Logged {status} to Google Sheets as Test-{GLOBAL_TEST_ID:03d}")
        GLOBAL_TEST_ID += 1
    except Exception as e:
        print("[LOG ERROR]", e)

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

async def execute_multi_step_test(overlay, batch_id, scenario):
    overlay.update_ui(task_text=scenario, status_text="INIT", result_text="PENDING", result_color="#f2cc60")
    
    task_start_time = time.time()
    action_chain = []
    status = "IN_PROGRESS"
    max_steps = 8
    step_count = 0
    
    # [BEHAVIORAL CLONING] Buffer to hold trajectory data for offline ML
    trajectory_buffer = []
    
    for step in range(max_steps):
        step_count += 1
        overlay.update_ui(status_text=f"Step {step_count} CAPTURING", status_color="#f2cc60")
        
        sct_img = pyautogui.screenshot()
        sct_img.save('screenshot.jpg', quality=75)
        
        overlay.update_ui(status_text=f"Step {step_count} VLM THINKING...", status_color="#f2cc60")
        
        try:
            mem = load_memory()
            if scenario in mem and step_count == 1:
                # FAST PATH: MEMORY HIT
                raw_command = mem[scenario]
                overlay.update_ui(status_text="⚡ MEMORY HIT", status_color="#a78bfa")
                print(f"VLM MEMORY HIT: {raw_command}")
                time.sleep(1.0)
            else:
                # NORMAL PATH: VLM INFERENCE
                raw_command = await asyncio.wait_for(ask_vlm_next_action('screenshot.jpg', scenario, action_chain), timeout=60.0)
                print(f"VLM RAW OUTPUT: {raw_command}")
                
                # Cache successful first actions
                if step_count == 1 and ('CLICK' in raw_command.upper() or 'TYPE' in raw_command.upper()):
                    mem[scenario] = raw_command
                    save_memory(mem)
            raw_upper = raw_command.upper()
            
            command_line = raw_upper
            lines = raw_upper.strip().split('\n')
            for line in reversed(lines):
                if line.startswith("COMMAND:") or "CLICK" in line or "TYPE" in line or "DONE" in line or "SCROLL" in line:
                    command_line = line
                    break
            
            command_line = re.sub(r'^COMMAND:\s*', '', command_line).strip()
            sub_commands = [c.strip() for c in re.split(r'\bTHEN\b', command_line) if c.strip()]
            
            for idx, sub_cmd in enumerate(sub_commands):
                if re.search(r'DONE\s*$', sub_cmd, re.MULTILINE):
                    base_command = 'DONE'
                elif re.search(r'FAILED\s*$', sub_cmd, re.MULTILINE):
                    base_command = 'FAILED'
                elif re.search(r'SCROLL_DOWN\s*$', sub_cmd, re.MULTILINE) or re.search(r'SCROLL DOWN\s*$', sub_cmd, re.MULTILINE):
                    base_command = 'SCROLL_DOWN'
                elif re.search(r'DRAG', sub_cmd, re.MULTILINE):
                    base_command = 'DRAG'
                elif re.search(r'WAIT\s+([\d.]+)', sub_cmd, re.MULTILINE):
                    base_command = 'WAIT'
                    wait_match = re.search(r'WAIT\s+([\d.]+)', sub_cmd, re.MULTILINE)
                    wait_time = float(wait_match.group(1)) if wait_match else 1.0
                else:
                    click_match = re.search(r'CLICK\s*\[([\d,\s]+)\]', sub_cmd, re.MULTILINE)
                    type_match = re.search(r'TYPE\s*\[([\d,\s]+)\](?:\s+(.*))?', sub_cmd, re.MULTILINE)
                    copy_match = re.search(r'COPY\s*\[([\d,\s]+)\]', sub_cmd, re.MULTILINE)
                    paste_match = re.search(r'PASTE\s*\[([\d,\s]+)\]', sub_cmd, re.MULTILINE)
                    hover_match = re.search(r'HOVER\s*\[([\d,\s]+)\]', sub_cmd, re.MULTILINE)
                    
                    if click_match:
                        base_command = 'CLICK'
                        array_str = click_match.group(1)
                    elif type_match:
                        base_command = 'TYPE'
                        array_str = type_match.group(1)
                        text_to_type = type_match.group(2) if type_match.group(2) else ""
                    elif copy_match:
                        base_command = 'COPY'
                        array_str = copy_match.group(1)
                    elif paste_match:
                        base_command = 'PASTE'
                        array_str = paste_match.group(1)
                    elif hover_match:
                        base_command = 'HOVER'
                        array_str = hover_match.group(1)
                    else:
                        base_command = 'UNKNOWN'
                
                if base_command == "DONE":
                    action_chain.append("Done")
                    overlay.update_ui(status_text="VERIFIED DONE!", status_color="#3fb950", result_text="PASSED", result_color="#3fb950")
                    status = "PASSED"
                    trajectory_buffer.append({
                        "step": step_count,
                        "image": sct_img,
                        "action_label": "DONE",
                        "history": list(action_chain)
                    })
                    break
                    
                elif base_command == "FAILED":
                    action_chain.append("Failed-VLM")
                    overlay.update_ui(status_text="VLM GAVE UP", status_color="#ff7b72", result_text="FAILED", result_color="#ff7b72")
                    status = "FAILED"
                    break
                    
                elif base_command == "SCROLL_DOWN":
                    action_chain.append("Scroll")
                    overlay.update_ui(status_text="SCROLLING DOWN", status_color="#3fb950")
                    pyautogui.scroll(-500)
                    time.sleep(1) 
                    
                elif base_command == "DRAG":
                    matches = re.findall(r'\[\s*[\d,\s]+\s*\]', sub_cmd)
                    if len(matches) >= 2:
                        p1x, p1y = extract_coords_from_array(matches[0], overlay.screen_width, overlay.screen_height)
                        p2x, p2y = extract_coords_from_array(matches[1], overlay.screen_width, overlay.screen_height)
                        
                        if p1x is not None and p2x is not None:
                            action_str = f"Drag({p1x},{p1y}->{p2x},{p2y})"
                            
                            is_repetitive = False
                            if len(action_chain) > 0 and action_chain[-1].startswith("Drag("):
                                last_coords = re.findall(r'\d+', action_chain[-1])
                                if len(last_coords) >= 4:
                                    l_p1x, l_p1y, l_p2x, l_p2y = map(int, last_coords[:4])
                                    if math.hypot(p1x - l_p1x, p1y - l_p1y) < 40 and math.hypot(p2x - l_p2x, p2y - l_p2y) < 40:
                                        is_repetitive = True
                                        
                            if is_repetitive:
                                print("⚠️ REPETITIVE ACTION (DRAG JITTER) DETECTED! Forcing DONE.")
                                action_chain.append("Forced-Done")
                                overlay.update_ui(status_text="VERIFIED DONE (Forced)", status_color="#3fb950", result_text="PASSED", result_color="#3fb950")
                                status = "PASSED"
                                trajectory_buffer.append({
                                    "step": step_count,
                                    "image": sct_img,
                                    "action_label": "DONE",
                                    "history": list(action_chain)
                                })
                                break
                                
                            action_chain.append(action_str)
                            overlay.update_ui(status_text="DRAGGING...", status_color="#3fb950")
                            
                            pyautogui.moveTo(p1x, p1y, duration=0.2)
                            pyautogui.dragTo(p2x, p2y, duration=0.8, button='left')
                            time.sleep(1)
                        else:
                            action_chain.append("Failed-Parse")
                            status = "ERROR"
                            break
                    else:
                        action_chain.append("Failed-Parse")
                        status = "ERROR"
                        break
    
                elif base_command == "CLICK":
                    px, py = extract_coords_from_array(array_str, overlay.screen_width, overlay.screen_height)
                    if px is not None:
                        action_str = f"Click({px},{py})"
                        
                        is_repetitive = False
                        if len(action_chain) > 0 and action_chain[-1].startswith("Click("):
                            last_coords = re.findall(r'\d+', action_chain[-1])
                            if len(last_coords) >= 2:
                                last_px, last_py = int(last_coords[0]), int(last_coords[1])
                                if math.hypot(px - last_px, py - last_py) < 40:
                                    is_repetitive = True
                                    
                        if is_repetitive:
                            print("⚠️ REPETITIVE ACTION (JITTER) DETECTED! Forcing DONE to prevent infinite loop.")
                            action_chain.append("Forced-Done")
                            overlay.update_ui(status_text="VERIFIED DONE (Forced)", status_color="#3fb950", result_text="PASSED", result_color="#3fb950")
                            status = "PASSED"
                            trajectory_buffer.append({
                                "step": step_count,
                                "image": sct_img,
                                "action_label": "DONE",
                                "history": list(action_chain)
                            })
                            break
                            
                        action_chain.append(action_str)
                        overlay.update_ui(status_text=f"CLICKING {px},{py}", status_color="#3fb950")
                        
                        pyautogui.moveTo(px, py, duration=0.2)
                        pyautogui.click()
                        time.sleep(1) # Base safety delay for DOM updates
                    else:
                        action_chain.append("Failed-Parse")
                        status = "ERROR"
                        break
                        
                elif base_command == "TYPE":
                    px, py = extract_coords_from_array(array_str, overlay.screen_width, overlay.screen_height)
                    if px is not None:
                        action_str = f"Type('{text_to_type}')"
                        
                        is_repetitive = False
                        if len(action_chain) > 0 and action_chain[-1].startswith("Type("):
                            if action_chain[-1] == action_str:
                                is_repetitive = True
                                
                        if is_repetitive:
                            print("⚠️ REPETITIVE ACTION DETECTED! Forcing DONE to prevent infinite loop.")
                            action_chain.append("Forced-Done")
                            overlay.update_ui(status_text="VERIFIED DONE (Forced)", status_color="#3fb950", result_text="PASSED", result_color="#3fb950")
                            status = "PASSED"
                            trajectory_buffer.append({
                                "step": step_count,
                                "image": sct_img,
                                "action_label": "DONE",
                                "history": list(action_chain)
                            })
                            break
                            
                        action_chain.append(action_str)
                        overlay.update_ui(status_text="TYPING...", status_color="#3fb950")
                        
                        pyautogui.moveTo(px, py, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        pyautogui.write(text_to_type, interval=0.05)
                        time.sleep(1)
                    else:
                        action_chain.append("Failed-Parse")
                        status = "ERROR"
                        break
                        
                elif base_command == "COPY":
                    px, py = extract_coords_from_array(array_str, overlay.screen_width, overlay.screen_height)
                    if px is not None:
                        action_chain.append(f"Copy({px},{py})")
                        overlay.update_ui(status_text=f"COPYING TEXT AT {px},{py}", status_color="#a78bfa")
                        pyautogui.moveTo(px, py, duration=0.2)
                        pyautogui.click(clicks=3, interval=0.1)
                        time.sleep(0.2)
                        pyautogui.hotkey('ctrl', 'c')
                        time.sleep(1)
                    else:
                        action_chain.append("Failed-Parse")
                        status = "ERROR"
                        break
                        
                elif base_command == "PASTE":
                    px, py = extract_coords_from_array(array_str, overlay.screen_width, overlay.screen_height)
                    if px is not None:
                        action_chain.append(f"Paste({px},{py})")
                        overlay.update_ui(status_text=f"PASTING AT {px},{py}", status_color="#a78bfa")
                        pyautogui.moveTo(px, py, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.2)
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.1)
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(1)
                    else:
                        action_chain.append("Failed-Parse")
                        status = "ERROR"
                        break
                        
                elif base_command == "HOVER":
                    px, py = extract_coords_from_array(array_str, overlay.screen_width, overlay.screen_height)
                    if px is not None:
                        action_chain.append(f"Hover({px},{py})")
                        overlay.update_ui(status_text=f"HOVERING AT {px},{py}", status_color="#3fb950")
                        pyautogui.moveTo(px, py, duration=0.2)
                        pyautogui.moveRel(1, 1, duration=0.1)
                        pyautogui.moveRel(-1, -1, duration=0.1)
                        time.sleep(1)
                    else:
                        action_chain.append("Failed-Parse")
                        status = "ERROR"
                        break
                        
                elif base_command == "WAIT":
                    action_chain.append(f"Wait({wait_time}s)")
                    overlay.update_ui(status_text=f"WAITING {wait_time}s...", status_color="#a78bfa")
                    time.sleep(wait_time)
                    
                else:
                    action_chain.append(f"Unknown")
                    status = "FAILED"
                    break
                    
                # Macro-Action Safety Pause (Default fallback)
                if status == "IN_PROGRESS" and idx < len(sub_commands) - 1:
                    next_cmd_is_wait = bool(re.search(r'WAIT\s+', sub_commands[idx+1], re.MULTILINE))
                    if base_command != "WAIT" and not next_cmd_is_wait:
                        overlay.update_ui(status_text="MACRO-PAUSE (0.5s)...", status_color="#a78bfa")
                        time.sleep(0.5)
                    
            # [BEHAVIORAL CLONING] Save valid command sequence to buffer
            if status == "IN_PROGRESS" and base_command != "DONE":
                trajectory_buffer.append({
                    "step": step_count,
                    "image": sct_img,
                    "action_label": command_line,
                    "history": list(action_chain)
                })
                
        except asyncio.TimeoutError:
            action_chain.append("Timeout")
            overlay.update_ui(status_text="TIMEOUT EXCEEDED", status_color="#ff7b72", result_text="TIMEOUT", result_color="#ff7b72")
            status = "TIMEOUT"
            break
        except Exception as e:
            action_chain.append("API-Error")
            overlay.update_ui(status_text="API ERROR", status_color="#ff7b72", result_text="ERROR", result_color="#ff7b72")
            print("API Error:", e)
            status = "ERROR"
            break

    if status == "IN_PROGRESS" and step_count == max_steps:
        status = "MAX_STEPS_REACHED"
        overlay.update_ui(result_text="MAX_STEPS_REACHED", result_color="#ff7b72")

    task_end_time = time.time()
    total_latency = (task_end_time - task_start_time) * 1000
    
    # [BEHAVIORAL CLONING] Flush buffer to disk ONLY if trajectory was PERFECT
    if status == "PASSED":
        os.makedirs("vlm_dataset/images", exist_ok=True)
        dataset_file = "vlm_dataset/dataset.jsonl"
        run_id = f"test_{int(time.time())}"
        
        with open(dataset_file, "a", encoding="utf-8") as f:
            for item in trajectory_buffer:
                img_filename = f"{run_id}_step_{item['step']}.jpg"
                img_path = os.path.join("vlm_dataset/images", img_filename)
                item['image'].save(img_path, quality=85)
                
                record = {
                    "image_file": img_filename,
                    "instruction": scenario,
                    "history": item["history"][:-1], # exclude current action
                    "ground_truth": item["action_label"]
                }
                f.write(json.dumps(record) + "\n")
        print(f"\n[DATASET] Harvested {len(trajectory_buffer)} perfect frames for Behavioral Cloning!")
    
    log_to_sheets(batch_id, MODEL_NAME, scenario, total_latency, status, action_chain, step_count)
    
    if os.path.exists('screenshot.jpg'): pass 
    
    pyautogui.press('enter') 
    time.sleep(1)

def run_batch_loop(overlay, total_batches):
    
    SCENARIO_BANK = {
        'test_ui_1.html': {
            'normal': [
                "Select 'Project Alpha' from the project dropdown",
                "Click on the 'Team' navigation tab",
                "Toggle the 'Dark Mode' switch",
                "Click the 'Deploy' button in the Quick Actions card"
            ],
            'difficult': [
                "Select 'Project Beta' from the dropdown, then click the 'Deploy' button, then toggle 'Dark Mode'"
            ]
        },
        'test_ui_2.html': {
            'normal': [
                "Click the 'New Event' button",
                "Select the checkbox for 'Team Sync'",
                "Click the 'Month' view tab",
                "Type 'Doctor Appointment' into the search bar"
            ],
            'difficult': [
                "Switch to the 'Month' view, select the 'Team Sync' event, and then click 'New Event'"
            ]
        },
        'test_ui_3.html': {
            'normal': [
                "Type 'jane@example.com' into the Email Address field",
                "Select the 'Express' shipping method",
                "Check the agree to Terms of Service box",
                "Click the 'Place Order' button"
            ],
            'difficult': [
                "Type 'jane@example.com' in the email, select Overnight Shipping, check the TOS box, and place the order"
            ]
        },
        'test_ui_4.html': {
            'normal': [
                "Click on the 'Security' tab in the sidebar",
                "Turn off the 'Email Notifications' toggle",
                "Type 'John Doe' into the Full Name input field",
                "Click the 'Save Changes' button"
            ],
            'difficult': [
                "Switch to the Security tab, turn off Email Notifications, and then click Save Changes"
            ]
        },
        'test_ui_5.html': {
            'normal': [
                "Click the 'Add Task' button",
                "Drag the 'Design Homepage' card to the 'In Progress' column",
                "Click the filter icon next to the search bar",
                "Type 'Urgent' into the search tasks input"
            ],
            'difficult': [
                "Type 'Urgent' in the search bar, then drag 'Design Homepage' to 'In Progress'"
            ]
        },
        'test_ui_6.html': {
            'normal': [
                "Click on the 'Billing' tab",
                "Select the 'Annual Plan' radio button",
                "Toggle the 'Two-Factor Auth' switch",
                "Click the 'Save Changes' button"
            ],
            'difficult': [
                "Switch to the Billing tab, select Annual Plan, and then click Save Changes"
            ]
        },
        'test_ui_7.html': {
            'normal': [
                "Click the 'Upload File' button",
                "Select the 'Images' folder in the sidebar",
                "Click the sort icon next to the Name column header",
                "Type 'report.pdf' into the search files input"
            ],
            'difficult': [
                "Go to the Images folder, search for 'report.pdf', and then click Upload File"
            ]
        },
        'test_ui_8.html': {
            'normal': [
                "Click the 'See more like this' link for the Samsung Monitor",
                "Check the 'Sony' checkbox in the Brand filter",
                "Type 'Gaming Laptop' into the search bar and click the search icon button",
                "Click the 'Add to cart' button for the LG OLED TV"
            ],
            'difficult': [
                "Check the Apple brand filter, click 4 Stars & Up, and then click Add to cart for the Macbook"
            ]
        },
        'test_ui_9.html': {
            'normal': [
                "Click the 'Compose' button",
                "Click on the email from 'Alice Smith'",
                "Type 'Project Update' into the search mail input",
                "Hover over the email from 'HR Department' to reveal the hidden menu, and click the Delete button"
            ],
            'difficult': [
                "Hover over the email from 'AWS' and click Archive"
            ]
        },
        'test_ui_10.html': {
            'normal': [
                "Click the 'Generate Report' button",
                "Select the 'Last 7 Days' option from the date range dropdown",
                "Hover over the 'Revenue' bar chart to see the exact value",
                "Type 'Sales' into the filter dashboard input"
            ],
            'difficult': [
                "Copy the Revenue for Q3, paste it into the 'Q3 Raw Revenue' input box, and then click the Submit Audit Request button"
            ]
        }
    }
    
    async def _async_loop():
        for remaining in range(5, 0, -1):
            overlay.update_ui(task_text="INIT", status_text=f"ENGINE LOADED! TEST STARTING IN {remaining}s...", status_color="#58a6ff")
            time.sleep(1)
            
        for batch_number in range(1, total_batches + 1):
            ui_file = random.choice(list(SCENARIO_BANK.keys()))
            
            overlay.update_ui(task_text=f"BATCH {batch_number}", status_text=f"LOADING UI: {ui_file}", status_color="#58a6ff")
            html_path = f"file:///{os.path.abspath(ui_file).replace(chr(92), '/')}"
            webbrowser.open(html_path)
            time.sleep(4) 
            
            selected_normal = random.sample(SCENARIO_BANK[ui_file]['normal'], min(3, len(SCENARIO_BANK[ui_file]['normal'])))
            selected_diff = random.sample(SCENARIO_BANK[ui_file]['difficult'], 1)
            scenarios = selected_normal + selected_diff
            random.shuffle(scenarios) 
            
            for scenario in scenarios:
                await execute_multi_step_test(overlay, batch_number, f"[{ui_file}] {scenario}")
                time.sleep(2) 
            
            # Prevent RAM leak: Close the browser tab after the batch
            pyautogui.hotkey('ctrl', 'w')
            time.sleep(1)
            
            # Thermal Cooldown: 15-minute break every 10 batches
            if batch_number % 10 == 0 and batch_number < total_batches:
                for _ in range(5):
                    pyautogui.hotkey('ctrl', 'w') # extra cleanup
                    time.sleep(0.5)
                for remaining_mins in range(15, 0, -1):
                    overlay.update_ui(task_text="THERMAL COOLDOWN", status_text=f"COOLING LAPTOP: {remaining_mins} MINS LEFT", status_color="#ff7b72", result_text="PAUSED", result_color="#ff7b72")
                    time.sleep(60)
            
            if batch_number < total_batches:
                for remaining in range(5, 0, -1):
                    overlay.update_ui(task_text=f"BATCH {batch_number} COMPLETE", status_text=f"NEXT IN {remaining}s...", status_color="#ff7b72")
                    time.sleep(1)
                    
        overlay.update_ui(task_text="FINISHED", status_text=f"ALL {total_batches} BATCHES COMPLETE!", status_color="#3fb950", result_text="SHUTTING DOWN", result_color="#3fb950")
        time.sleep(3)
        os._exit(0)
            
    asyncio.run(_async_loop())

if __name__ == "__main__":
    print("Welcome to VLM MULTI-STEP TESTING (NATIVE SPATIAL EDITION)!")
    batches_str = input("Enter the number of batches to run (4 tests per batch): ")
    try:
        total_batches = int(batches_str)
    except ValueError:
        total_batches = 1
        
    keyboard.add_hotkey('esc', lambda: os._exit(0))
    print("[INFO] Press ESC at any time to kill the benchmark engine.")
    
    app = VLMOverlay()
    import threading
    threading.Thread(target=run_batch_loop, args=(app, total_batches), daemon=True).start()
    app.root.mainloop()

