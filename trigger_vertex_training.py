"""
TRIGGER VERTEX AI / COLAB ENTERPRISE TRAINING PIPELINE
======================================================
Automates 100% headless GPU fine-tuning execution on Google Cloud Platform
using Vertex AI Colab Enterprise and Google Cloud Storage.

Configuration:
- Project ID        : convertionalai
- Region            : us-central1
- Runtime Template  : healvlm-t4-template (1x NVIDIA Tesla T4 GPU, n1-standard-4)
- GCS Bucket        : gs://healvlm-vertex-training-convertionalai
- Service Account   : agent-access-key@convertionalai.iam.gserviceaccount.com
"""

import os
import sys
import time
import json
import shutil
import subprocess
from datetime import datetime
from typing import Optional

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ID = "convertionalai"
REGION = "us-central1"
RUNTIME_TEMPLATE = "healvlm-t4-template"
GCS_BUCKET = "healvlm-vertex-training-convertionalai"
SERVICE_ACCOUNT = "agent-access-key@convertionalai.iam.gserviceaccount.com"
DEFAULT_NOTEBOOK = "google_colab_train_qwen2_vl.ipynb"

def run_command(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Executes a subprocess CLI command safely."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        if e.stdout:
            print(f"  [Stdout]: {e.stdout.strip()}")
        if e.stderr:
            print(f"  [Stderr]: {e.stderr.strip()}")
        raise

def upload_to_gcs(local_path: str, gcs_uri: str) -> bool:
    """Uploads a local file to Google Cloud Storage."""
    print(f"☁️ Uploading {local_path} -> {gcs_uri}...")
    cmd = ["gcloud", "storage", "cp", local_path, gcs_uri]
    res = run_command(cmd)
    if res.returncode == 0:
        print(f"  ✅ Uploaded successfully.")
        return True
    return False

def trigger_vertex_execution(
    notebook_file: str = DEFAULT_NOTEBOOK,
    job_display_name: Optional[str] = None,
    wait: bool = True
) -> str:
    """
    Submits a headless Colab Enterprise notebook execution on Vertex AI.
    """
    if not os.path.exists(notebook_file):
        raise FileNotFoundError(f"Notebook file not found: {notebook_file}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if not job_display_name:
        job_display_name = f"healvlm-train-{timestamp}"

    # Target GCS URIs
    gcs_notebook_uri = f"gs://{GCS_BUCKET}/notebooks/{os.path.basename(notebook_file)}"
    gcs_output_uri = f"gs://{GCS_BUCKET}/executions/{job_display_name}"

    print("=" * 65)
    print("🚀 LAUNCHING VERTEX AI COLAB ENTERPRISE EXECUTION")
    print("=" * 65)
    print(f"• GCP Project         : {PROJECT_ID}")
    print(f"• Compute Region      : {REGION}")
    print(f"• Runtime Template    : {RUNTIME_TEMPLATE} (1x NVIDIA T4 GPU)")
    print(f"• Execution Name      : {job_display_name}")
    print(f"• Source Notebook     : {notebook_file}")
    print(f"• GCS Notebook Target : {gcs_notebook_uri}")
    print(f"• GCS Output Location : {gcs_output_uri}")
    print(f"• Running Service Acct: {SERVICE_ACCOUNT}")
    print("-" * 65)

    # Step 1: Sync latest notebook to Cloud Storage
    upload_to_gcs(notebook_file, gcs_notebook_uri)

    # Step 2: Also upload dataset archive if it exists
    if os.path.exists("vlm_dataset.zip"):
        upload_to_gcs("vlm_dataset.zip", f"gs://{GCS_BUCKET}/datasets/vlm_dataset.zip")

    # Step 3: Trigger execution command
    cmd = [
        "gcloud", "colab", "executions", "create",
        f"--display-name={job_display_name}",
        f"--notebook-runtime-template={RUNTIME_TEMPLATE}",
        f"--gcs-notebook-uri={gcs_notebook_uri}",
        f"--service-account={SERVICE_ACCOUNT}",
        f"--gcs-output-uri={gcs_output_uri}",
        f"--region={REGION}"
    ]

    if not wait:
        cmd.append("--async")

    print("\n⚡ Submitting execution request to Vertex AI API...")
    res = run_command(cmd)

    output = res.stdout + "\n" + res.stderr
    print(output.strip())

    console_url = f"https://console.cloud.google.com/vertex-ai/colab/executions?project={PROJECT_ID}"
    print("=" * 65)
    print("✅ EXECUTION DISPATCHED SUCCESSFULLY!")
    print(f"🔗 View Real-Time Training in GCP Console:")
    print(f"   {console_url}")
    print("=" * 65)

    return job_display_name

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trigger Vertex AI Colab Training")
    parser.add_argument("--notebook", default=DEFAULT_NOTEBOOK, help="Path to notebook")
    parser.add_argument("--name", default=None, help="Custom job display name")
    parser.add_argument("--async-run", action="store_true", help="Submit and return immediately without waiting")

    args = parser.parse_args()

    try:
        trigger_vertex_execution(
            notebook_file=args.notebook,
            job_display_name=args.name,
            wait=not args.async_run
        )
    except Exception as e:
        print(f"\n❌ Execution failed: {e}")
        sys.exit(1)
