# PREPARE VERIFIED TRUE CASES DATASET
# Filters and normalizes live web trajectories into a 100% clean, verified training dataset.

import os
import sys
import json
import re
from PIL import Image

# Reconfigure stdout/stderr for Unicode support on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

RAW_DATASET_FILE = 'live_vlm_dataset/dataset.jsonl'
IMAGES_DIR = 'live_vlm_dataset/images'
VERIFIED_OUTPUT_FILE = 'live_vlm_dataset/verified_true_cases.jsonl'

VALID_ACTION_PRIMITIVES = [
    "CLICK", "DOUBLE_CLICK", "DRAG", "HOVER",
    "TYPE", "SCROLL", "PRESS_ENTER", "WAIT", "DONE"
]

def sanitize_action_string(action_str: str) -> str:
    """
    Normalizes legacy prefixes (e.g. 'ACTION: CLICK' -> 'CLICK')
    and strips markdown backticks or irregular whitespaces.
    """
    if not action_str:
        return ""
    
    # Strip leading 'ACTION:' or 'COMMAND:' prefixes from sub-commands
    cleaned = re.sub(r'^(?:\*\*)?(?:ACTION|COMMAND)(?:\*\*)?:?\s*', '', action_str, flags=re.IGNORECASE).strip()
    
    # Handle chained actions separated by ' THEN '
    sub_cmds = re.split(r'\s+THEN\s+', cleaned, flags=re.IGNORECASE)
    sanitized_subs = []
    
    for sub in sub_cmds:
        sub = re.sub(r'^(?:\*\*)?(?:ACTION|COMMAND)(?:\*\*)?:?\s*', '', sub, flags=re.IGNORECASE).strip('`* ')
        if sub:
            sanitized_subs.append(sub)
            
    return " THEN ".join(sanitized_subs)

def validate_coordinates(action_str: str) -> bool:
    """
    Verifies that all [ymin, xmin, ymax, xmax] coordinates are within [0, 1000].
    """
    bracket_matches = re.findall(r'\[\s*([\d,\s]+)\s*\]', action_str)
    for match in bracket_matches:
        nums = [int(n.strip()) for n in re.findall(r'\d+', match)]
        if len(nums) >= 2:
            for num in nums:
                if num < 0 or num > 1000:
                    return False
    return True

def extract_true_cases():
    print("==================================================")
    print("🔍 AUDITING & EXTRACTING VERIFIED TRUE CASES")
    print(f"Source: {RAW_DATASET_FILE}")
    print(f"Target: {VERIFIED_OUTPUT_FILE}")
    print("==================================================")
    
    if not os.path.exists(RAW_DATASET_FILE):
        print(f"❌ Error: {RAW_DATASET_FILE} does not exist!")
        return
        
    os.makedirs(os.path.dirname(VERIFIED_OUTPUT_FILE), exist_ok=True)
    
    total_raw = 0
    total_verified = 0
    rejected = 0
    
    platform_stats = {}
    action_stats = {}
    
    verified_records = []
    
    with open(RAW_DATASET_FILE, 'r', encoding='utf-8') as f:
        for line_idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            total_raw += 1
            
            try:
                record = json.loads(line)
            except Exception as e:
                print(f"⚠️ [Line {line_idx}] JSON Decode Error: {e}")
                rejected += 1
                continue
                
            img_file = record.get('image_file', '')
            instruction = record.get('instruction', '').strip()
            raw_gt = record.get('ground_truth', '').strip()
            thought = record.get('thought', '').strip()
            platform = record.get('platform', 'Unknown').strip()
            history = record.get('history', [])
            
            # Check 1: Image exists and is readable
            img_path = os.path.join(IMAGES_DIR, img_file)
            if not os.path.exists(img_path):
                print(f"⚠️ [Line {line_idx}] Missing image file: {img_file}")
                rejected += 1
                continue
                
            try:
                with Image.open(img_path) as im:
                    width, height = im.size
                    if width < 100 or height < 100:
                        print(f"⚠️ [Line {line_idx}] Degenerate image size: {width}x{height}")
                        rejected += 1
                        continue
            except Exception as e:
                print(f"⚠️ [Line {line_idx}] Unreadable image: {e}")
                rejected += 1
                continue
                
            # Check 2: Instruction must be non-empty
            if not instruction:
                print(f"⚠️ [Line {line_idx}] Empty instruction prompt")
                rejected += 1
                continue
                
            # Check 3: Ground truth action must be valid and non-empty
            sanitized_gt = sanitize_action_string(raw_gt)
            if not sanitized_gt or "FAILED" in sanitized_gt.upper() or "PARSE" in sanitized_gt.upper():
                print(f"⚠️ [Line {line_idx}] Invalid ground truth action: '{raw_gt}'")
                rejected += 1
                continue
                
            # Check 4: Must contain a valid action primitive
            has_primitive = any(prim in sanitized_gt.upper() for prim in VALID_ACTION_PRIMITIVES)
            if not has_primitive:
                print(f"⚠️ [Line {line_idx}] No recognized action primitive: '{sanitized_gt}'")
                rejected += 1
                continue
                
            # Check 5: Coordinate bounds validation
            if not validate_coordinates(sanitized_gt):
                print(f"⚠️ [Line {line_idx}] Out of bounds coordinates: '{sanitized_gt}'")
                rejected += 1
                continue
                
            # Construct pristine verified record
            verified_record = {
                "image_file": img_file,
                "platform": platform,
                "instruction": instruction,
                "thought": thought if thought else "Identify target visual element and execute primary action.",
                "history": history,
                "ground_truth": sanitized_gt
            }
            
            verified_records.append(verified_record)
            total_verified += 1
            
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
            first_prim = sanitized_gt.split()[0].upper()
            action_stats[first_prim] = action_stats.get(first_prim, 0) + 1
            
    # Write verified records
    with open(VERIFIED_OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        for r in verified_records:
            out_f.write(json.dumps(r) + "\n")
            
    print("\n✅ [EXTRACTION COMPLETE]")
    print(f"Total Raw Samples Processed : {total_raw}")
    print(f"Verified True Cases Accepted: {total_verified} ({round((total_verified/total_raw)*100, 1) if total_raw else 0}%)")
    print(f"Rejected / Corrupt Samples  : {rejected}")
    
    print("\n📊 Verified Distribution by Platform:")
    for plat, count in sorted(platform_stats.items(), key=lambda x: -x[1]):
        print(f"  - {plat:20}: {count:3d} samples")
        
    print("\n⚡ Verified Distribution by Action Primitive:")
    for act, count in sorted(action_stats.items(), key=lambda x: -x[1]):
        print(f"  - {act:20}: {count:3d} samples")
        
    print(f"\n🎯 Output saved to: {VERIFIED_OUTPUT_FILE}")

if __name__ == "__main__":
    extract_true_cases()
