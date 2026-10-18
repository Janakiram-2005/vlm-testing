import json

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🚀 HEALVLM: Qwen2-VL-2B-Instruct 4-Bit QLoRA Fine-Tuning\n",
                "**Autonomous Web Navigation Agent Fine-Tuning on Verified True Cases**\n",
                "- Architecture: `Qwen/Qwen2-VL-2B-Instruct` (Dynamic Resolution, Normalized Coordinates [0, 1000])\n",
                "- Target Hardware: Kaggle Free T4 GPU (16GB VRAM)\n",
                "- Dataset: 124 Pristine Live-Harvested Trajectories across 13 Web Platforms\n",
                "- Optimization: 4-Bit NF4 Quantization + LoRA (r=16, alpha=32) + Cross-Entropy Supervised Loss Masking"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 1. Install Required Dependencies\n",
                "!pip install -q -U torch torchvision transformers peft bitsandbytes accelerate"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 2. Verify GPU Acceleration\n",
                "import torch\n",
                "print(f\"PyTorch Version : {torch.__version__}\")\n",
                "print(f\"CUDA Available  : {torch.cuda.is_available()}\")\n",
                "if torch.cuda.is_available():\n",
                "    print(f\"GPU Model       : {torch.cuda.get_device_name(0)}\")\n",
                "    print(f\"Available VRAM  : {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB\")\n",
                "else:\n",
                "    print(\"⚠️ WARNING: No GPU detected! Please enable GPU accelerator in Kaggle Settings -> Accelerator -> GPU T4 x1.\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 3. Clone Repository or Extract Dataset\n",
                "import os, glob, zipfile, shutil\n",
                "\n",
                "if not os.path.exists(\"live_vlm_dataset\"):\n",
                "    zips = glob.glob(\"/kaggle/input/**/live_vlm_dataset.zip\", recursive=True) + glob.glob(\"*.zip\")\n",
                "    if zips:\n",
                "        print(f\"Extracting dataset from {zips[0]}...\")\n",
                "        with zipfile.ZipFile(zips[0], 'r') as zip_ref:\n",
                "            zip_ref.extractall(\".\")\n",
                "    else:\n",
                "        print(\"Cloning repository from GitHub...\")\n",
                "        !git clone https://github.com/Janakiram-2005/vlm-testing.git\n",
                "        if os.path.exists(\"vlm-testing/live_vlm_dataset\"):\n",
                "            if os.path.exists(\"live_vlm_dataset\"):\n",
                "                shutil.rmtree(\"live_vlm_dataset\")\n",
                "            shutil.copytree(\"vlm-testing/live_vlm_dataset\", \"live_vlm_dataset\")\n",
                "            shutil.copy(\"vlm-testing/train_qwen2_vl_lora.py\", \".\")\n",
                "\n",
                "print(f\"Dataset exists: {os.path.exists('live_vlm_dataset/verified_true_cases.jsonl')}\")\n",
                "if os.path.exists(\"live_vlm_dataset/images\"):\n",
                "    print(f\"Image count: {len(os.listdir('live_vlm_dataset/images'))}\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 4. Launch QLoRA Fine-Tuning\n",
                "!python train_qwen2_vl_lora.py"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 5. Package LoRA Adapter Weights for Download\n",
                "import shutil, os\n",
                "adapter_dir = \"healvlm_qwen2_vl_lora/final_adapter\"\n",
                "if os.path.exists(adapter_dir):\n",
                "    shutil.make_archive(\"healvlm_qwen2_vl_adapter\", \"zip\", adapter_dir)\n",
                "    zip_size = os.path.getsize(\"healvlm_qwen2_vl_adapter.zip\") / (1024 * 1024)\n",
                "    print(f\"✅ LoRA Adapter package created: healvlm_qwen2_vl_adapter.zip ({zip_size:.2f} MB)\")\n",
                "    print(\"Download from Kaggle Output tab to use in your local benchmark engine!\")\n",
                "else:\n",
                "    print(\"⚠️ Adapter directory not found! Check training log above.\")"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open("kaggle_train_qwen2_vl.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print("[SUCCESS] kaggle_train_qwen2_vl.ipynb generated successfully!")
