"""
PACKAGE FOR KAGGLE CLOUD TRAINING
=================================
Prepares a compact, ready-to-upload bundle for fine-tuning on Kaggle GPU.
"""

import os
import sys
import shutil
import zipfile

# UTF-8 stdout configuration for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BUNDLE_DIR = "kaggle_bundle"
ZIP_OUTPUT = os.path.join(BUNDLE_DIR, "live_vlm_dataset.zip")
VERIFIED_DATASET = "live_vlm_dataset/verified_true_cases.jsonl"
IMAGES_DIR = "live_vlm_dataset/images"

def package():
    print("=" * 60)
    print("[1/3] PACKAGING VERIFIED TRUE CASES FOR KAGGLE CLOUD")
    print("=" * 60)

    if not os.path.exists(VERIFIED_DATASET):
        print(f"Error: {VERIFIED_DATASET} not found. Run prepare_verified_dataset.py first.")
        return False

    os.makedirs(BUNDLE_DIR, exist_ok=True)

    # Count verified lines
    with open(VERIFIED_DATASET, "r", encoding="utf-8") as f:
        verified_count = sum(1 for line in f if line.strip())
    
    images_count = len(os.listdir(IMAGES_DIR)) if os.path.exists(IMAGES_DIR) else 0

    print(f"Verified True Cases : {verified_count} records")
    print(f"Verified Screenshots: {images_count} image files")

    print(f"\n[2/3] Compressing into {ZIP_OUTPUT}...")
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add dataset jsonl
        zipf.write(VERIFIED_DATASET, arcname="live_vlm_dataset/verified_true_cases.jsonl")
        # Add all images
        for root, _, files in os.walk(IMAGES_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, ".")
                zipf.write(file_path, arcname=arc_name)

    zip_size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print(f"[SUCCESS] Archive created: {ZIP_OUTPUT} ({zip_size_mb:.2f} MB)")

    print(f"\n[3/3] Copying Training Assets into {BUNDLE_DIR}/...")
    shutil.copy("train_qwen2_vl_lora.py", os.path.join(BUNDLE_DIR, "train_qwen2_vl_lora.py"))
    shutil.copy("kaggle_train_qwen2_vl.ipynb", os.path.join(BUNDLE_DIR, "kaggle_train_qwen2_vl.ipynb"))

    print("\n" + "=" * 60)
    print("KAGGLE DEPLOYMENT INSTRUCTIONS:")
    print("=" * 60)
    print("OPTION A (Browser - 2 Minutes):")
    print("  1. Go to https://www.kaggle.com/code and click 'New Notebook'")
    print("  2. In the top menu, click: File -> Import Notebook")
    print(f"  3. Select: {os.path.abspath(os.path.join(BUNDLE_DIR, 'kaggle_train_qwen2_vl.ipynb'))}")
    print("  4. In the right sidebar: Settings -> Accelerator -> GPU T4 x1 (Free)")
    print("  5. Click 'Run All'. When finished, download healvlm_qwen2_vl_adapter.zip (~80MB)")
    print("\nOPTION B (GitHub Sync):")
    print("  The notebook automatically clones your GitHub repo and starts training immediately!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    package()
