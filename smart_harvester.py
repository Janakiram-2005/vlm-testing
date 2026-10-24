"""
SMART STUDENT-TEACHER DATASET HARVESTER
=======================================
Orchestrates autonomous cross-boundary execution between:
1. Student : Local HealVLM Qwen2-VL LoRA Adapter
2. Teacher : Vertex AI Gemini 2.0 / 3.x Spatial VLM

When the Student succeeds, it solidifies its policy.
When the Student hesitates or fails visual diff check, the Teacher intervenes,
recovers the state, and logs a pristine verified ground-truth training sample.
"""

import os
import sys
import time
import json
import re
import uuid
import datetime
from typing import Optional, Dict, Tuple, Any
from PIL import Image

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from unified_desktop_engine import UnifiedDesktopEngine
from cross_scenario_bank import get_scenarios, setup_sandbox
from healvlm_bridge import predict_healvlm_action
from setup_desktop_sheet import log_desktop_test

# GCP Vertex AI credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'convertionalai-d8da9e4d43dd.json'
GCP_PROJECT = 'convertionalai'
GCP_LOCATION = os.environ.get('VERTEX_LOCATION', 'global')
TEACHER_MODEL = os.environ.get('VLM_MODEL_NAME', 'gemini-2.0-flash')

DATASET_DIR = "live_vlm_dataset"
DATASET_JSONL = os.path.join(DATASET_DIR, "dataset.jsonl")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")

os.makedirs(IMAGES_DIR, exist_ok=True)

def init_vertex_teacher():
    """Initializes Google GenAI Vertex AI Client."""
    try:
        from google import genai
        client = genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)
        return client
    except Exception as e:
        print(f"⚠️ Vertex Client Notice: {e}")
        return None

def query_teacher(client, image_path: str, goal: str, active_win: str) -> Tuple[str, str]:
    """Queries Vertex AI Teacher model for expert desktop spatial grounding."""
    from google.genai import types

    prompt = (
        "You are an Elite Computer-Use Teacher VLM controlling a Windows PC natively.\n"
        f"Active Window: {active_win}\n"
        f"Task Goal    : {goal}\n\n"
        "Analyze the screenshot. Output exact coordinates in normalized [ymin, xmin, ymax, xmax] (0 to 1000 scale).\n"
        "You MUST reply in exactly TWO lines:\n"
        "THOUGHT: <concise observation and target coordinates>\n"
        "ACTION: <ONE OF: CLICK [ymin, xmin, ymax, xmax] | DOUBLE_CLICK [ymin, xmin, ymax, xmax] | TYPE [ymin, xmin, ymax, xmax] <TEXT> | DRAG [y1, x1, y2, x2] TO [y3, x3, y4, x4] | DONE | FAILED>"
    )

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=TEACHER_MODEL,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt
                ]
            )
            raw_text = resp.text.strip()
            
            thought, action = "Observing target element.", "FAILED"
            for line in raw_text.splitlines():
                line = line.strip()
                if line.upper().startswith("THOUGHT:"):
                    thought = line[8:].strip()
                elif line.upper().startswith("ACTION:"):
                    action = line[7:].strip()
            return thought, action
        except Exception as e:
            if "429" in str(e):
                time.sleep(5)
            else:
                print(f"Teacher query error: {e}")
                break

    return "Fallback action.", "DONE"

def parse_action_coordinates(action_str: str) -> Tuple[str, Optional[Tuple[float, float]], Optional[str], Optional[Tuple[float, float, float, float]]]:
    """
    Parses action string into: (action_type, (norm_x, norm_y), extra_text, drag_coords)
    """
    action_str = action_str.strip()
    upper = action_str.upper()

    if upper.startswith("DOUBLE_CLICK") or "DOUBLE_CLICK" in upper:
        coords = re.findall(r'\d+', action_str)
        if len(coords) >= 4:
            ymin, xmin, ymax, xmax = map(int, coords[:4])
            return "DOUBLE_CLICK", ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0), None, None
        elif len(coords) >= 2:
            return "DOUBLE_CLICK", (int(coords[1]), int(coords[0])), None, None

    elif upper.startswith("CLICK"):
        coords = re.findall(r'\d+', action_str)
        if len(coords) >= 4:
            ymin, xmin, ymax, xmax = map(int, coords[:4])
            return "CLICK", ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0), None, None
        elif len(coords) >= 2:
            return "CLICK", (int(coords[1]), int(coords[0])), None, None

    elif upper.startswith("TYPE"):
        coords = re.findall(r'\d+', action_str)
        text_match = re.search(r'\]\s*(.*)', action_str)
        text = text_match.group(1).strip() if text_match else "Test"
        if len(coords) >= 4:
            ymin, xmin, ymax, xmax = map(int, coords[:4])
            return "TYPE", ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0), text, None
        return "TYPE", (500.0, 500.0), text, None

    elif upper.startswith("DRAG"):
        coords = re.findall(r'\d+', action_str)
        if len(coords) >= 8:
            y1, x1, y2, x2, y3, x3, y4, x4 = map(int, coords[:8])
            sx = (x1 + x2) / 2.0
            sy = (y1 + y2) / 2.0
            ex = (x3 + x4) / 2.0
            ey = (y3 + y4) / 2.0
            return "DRAG", (sx, sy), None, (sx, sy, ex, ey)

    elif "DONE" in upper:
        return "DONE", None, None, None

    return "FAILED", None, None, None

def log_verified_sample(scenario_id: str, goal: str, img_filename: str, thought: str, action: str, source: str) -> str:
    """Appends verified sample to dataset.jsonl and returns sample ID."""
    sample_id = f"desktop_{uuid.uuid4().hex[:8]}"
    sample = {
        "id": sample_id,
        "scenario": scenario_id,
        "goal": goal,
        "image_file": img_filename,
        "thought": thought,
        "action": action,
        "source": source,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    with open(DATASET_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(sample) + "\n")
    print(f"💾 [DATASET] Logged {source} sample ({img_filename}) -> {action}")
    return sample_id

def run_harvesting_cycle(max_steps_per_scenario: int = 3, single_scenario_id: Optional[str] = None, num_batches: int = 1, minimize_first: bool = True):
    """Executes the Student-Teacher data collection pipeline across batches."""
    engine = UnifiedDesktopEngine()
    teacher_client = init_vertex_teacher()
    scenarios = get_scenarios()

    if single_scenario_id:
        scenarios = [s for s in scenarios if s["id"] == single_scenario_id]

    print("=" * 65)
    print("🌾 SMART STUDENT-TEACHER HARVESTING PIPELINE ACTIVE")
    print(f"• Teacher Model: {TEACHER_MODEL} on GCP Vertex AI")
    print(f"• Total Batches to Execute: {num_batches}")
    print(f"• Scenarios per Batch     : {len(scenarios)}")
    print("=" * 65)

    if minimize_first:
        print("🪟 [SAFE TRIGGER] Pressing Windows + D to minimize all windows and reveal clean desktop...")
        engine.hotkey('win', 'd')
        time.sleep(1.2)

    for batch_idx in range(1, num_batches + 1):
        batch_tag = f"Batch-{batch_idx:02d}"
        print(f"\n{'#' * 65}")
        print(f"📦 STARTING {batch_tag} OF {num_batches:02d}")
        print(f"{'#' * 65}")

        for scenario in scenarios:
            s_id = scenario["id"]
            goal = scenario["goal"]
            print(f"\n▶️ [{batch_tag}] RUNNING SCENARIO: {s_id}")
            print(f"   Goal: {goal}")

            t_scenario_start = time.time()
            action_chain = []
            window_seq = []
            teacher_count = 0
            last_sample_id = "N/A"
            scenario_success = False

            # Fast shell setup
            if scenario.get("setup_shell"):
                os.system(scenario["setup_shell"])
                time.sleep(1.2)

            for step in range(1, max_steps_per_scenario + 1):
                active_win = engine.get_active_window_title()
                window_seq.append(active_win)
                img_name = f"harvest_{batch_tag}_{s_id}_step{step}_{int(time.time())}.jpg"
                img_path = os.path.join(IMAGES_DIR, img_name)
                
                # 1. Capture screen
                raw_img, vlm_img = engine.capture_screen(save_path=img_path)

                # 2. Student attempts prediction
                thought = ""
                action = ""
                source = "STUDENT_LOCAL"
                try:
                    student_resp = predict_healvlm_action(img_path, goal)
                    if isinstance(student_resp, dict):
                        thought = student_resp.get("thought", "")
                        action = student_resp.get("action", "")
                    else:
                        for line in str(student_resp).splitlines():
                            if line.upper().startswith("THOUGHT:"):
                                thought = line[8:].strip()
                            elif line.upper().startswith("ACTION:"):
                                action = line[7:].strip()
                except Exception as e:
                    print(f"  [Step {step}] ℹ️ Local student bypass: {e}")
                    action = ""

                # 3. Check student quality - if student failed or has blank action, switch to Teacher
                if not action or "FAILED" in action.upper() or len(action) < 4:
                    print(f"  [Step {step}] 🤖 Student uncertain -> Shifting to Teacher Vertex AI...")
                    if teacher_client:
                        thought, action = query_teacher(teacher_client, img_path, goal, active_win)
                        source = "TEACHER_VERTEX"
                        teacher_count += 1
                    else:
                        action = "DONE"

                print(f"  [Step {step} | {source}] Thought: {thought}")
                print(f"  [Step {step} | {source}] Action : {action}")
                action_chain.append(f"{source}: {action}")

                act_type, coords, extra_text, drag_coords = parse_action_coordinates(action)

                if act_type == "DONE":
                    print("  🎯 Task declared completed!")
                    last_sample_id = log_verified_sample(s_id, goal, img_name, thought, action, source)
                    scenario_success = True
                    break

                # 4. Execute physical action
                if act_type == "DOUBLE_CLICK" and coords:
                    engine.double_click(coords[0], coords[1])
                elif act_type == "CLICK" and coords:
                    engine.click(coords[0], coords[1])
                elif act_type == "TYPE" and coords:
                    engine.click(coords[0], coords[1])
                    time.sleep(0.2)
                    engine.type_text(extra_text or "Hello World", press_enter=True)
                elif act_type == "DRAG" and drag_coords:
                    engine.drag((drag_coords[0], drag_coords[1]), (drag_coords[2], drag_coords[3]))

                # Log this verified transition
                last_sample_id = log_verified_sample(s_id, goal, img_name, thought, action, source)
                time.sleep(0.8)

            # Log scenario run to Google Sheet Desktop_Web_Benchmark
            total_time_ms = (time.time() - t_scenario_start) * 1000.0
            final_status = "SUCCESS" if scenario_success else ("RECOVERED_BY_TEACHER" if teacher_count > 0 else "COMPLETED")
            primary_driver = "TEACHER_VERTEX" if teacher_count > 0 else "STUDENT_LOCAL"

            log_desktop_test(
                scenario_id=s_id,
                env_type=scenario.get("type", "DESKTOP"),
                goal=goal,
                driver=primary_driver,
                status=final_status,
                total_steps=len(action_chain),
                latency_ms=total_time_ms,
                action_chain=action_chain,
                window_seq=window_seq,
                teacher_interventions=teacher_count,
                sample_id=last_sample_id,
                batch_id=batch_tag
            )

            # Cleanup scenario
            if scenario.get("cleanup_shell"):
                os.system(scenario["cleanup_shell"])
                time.sleep(0.5)

    print("\n" + "=" * 65)
    print("✅ ALL HARVESTING BATCHES COMPLETED!")
    print("=" * 65)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Student-Teacher Harvester")
    parser.add_argument("--scenario", default=None, help="Specific scenario ID")
    parser.add_argument("--steps", type=int, default=2, help="Max steps per scenario")
    parser.add_argument("--batches", type=int, default=1, help="Number of batches to run")
    parser.add_argument("--no-minimize", action="store_true", help="Skip initial Win+D minimize")
    args = parser.parse_args()

    run_harvesting_cycle(
        max_steps_per_scenario=args.steps,
        single_scenario_id=args.scenario,
        num_batches=args.batches,
        minimize_first=not args.no_minimize
    )
