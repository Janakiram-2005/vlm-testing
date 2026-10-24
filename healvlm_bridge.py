"""
HEALVLM BRIDGE
==============
Connects the fine-tuned Qwen2-VL LoRA adapter (healvlm_colab_adapter)
directly to your existing autonomous UI project (benchmark_engine.py).

Supports:
1. Local in-process execution (CPU / GPU)
2. Standalone verification test (--test)
3. Remote API client mode (when serving on Google Colab GPU)
"""

import os
import sys
import json
import re
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Suppress TF and logging noise
os.environ["USE_TF"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

DEFAULT_ADAPTER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "healvlm_colab_adapter"))
DEFAULT_BASE_MODEL = "Qwen/Qwen2-VL-2B-Instruct"

SYSTEM_PROMPT = """You are an expert autonomous web navigation agent.
Given a webpage screenshot and user goal, analyze the visual state, determine the required next step, and output:
THOUGHT: <concise reasoning explaining which UI element to interact with and why>
ACTION: <action primitive with exact normalized [ymin, xmin, ymax, xmax] coordinates (0-1000) or text parameter>

Valid action primitives:
- CLICK [ymin, xmin, ymax, xmax]
- DOUBLE_CLICK [ymin, xmin, ymax, xmax]
- TYPE "text"
- PRESS_ENTER
- SCROLL [direction] (up/down)
- HOVER [ymin, xmin, ymax, xmax]
- WAIT [seconds]
- DONE"""

_GLOBAL_MODEL = None
_GLOBAL_PROCESSOR = None
_GLOBAL_TOKENIZER = None

def load_healvlm_model(adapter_dir: str = DEFAULT_ADAPTER_DIR, base_model_id: str = DEFAULT_BASE_MODEL):
    """
    Loads base Qwen2-VL-2B model and merges/attaches the fine-tuned LoRA adapter.
    """
    global _GLOBAL_MODEL, _GLOBAL_PROCESSOR, _GLOBAL_TOKENIZER
    if _GLOBAL_MODEL is not None:
        return _GLOBAL_MODEL, _GLOBAL_PROCESSOR, _GLOBAL_TOKENIZER

    import torch
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

    try:
        from transformers import Qwen2TokenizerFast as AutoTokenizer
    except Exception:
        from transformers import AutoTokenizer

    from peft import PeftModel

    has_cuda = torch.cuda.is_available()
    device = torch.device("cuda:0" if has_cuda else "cpu")

    print("=" * 65)
    print("🧠 INITIALIZING HEALVLM MODEL BRIDGE")
    print("=" * 65)
    print(f"Base Model : {base_model_id}")
    print(f"LoRA Adapter: {adapter_dir}")
    print(f"Compute Device: {device} (CUDA: {has_cuda})")
    print("-" * 65)

    if not os.path.exists(adapter_dir):
        raise FileNotFoundError(
            f"Adapter directory not found at: {adapter_dir}\n"
            f"Please ensure healvlm_qwen2_vl_adapter.zip is extracted to {adapter_dir}"
        )

    print("Loading tokenizer and image processor...")
    _GLOBAL_TOKENIZER = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    _GLOBAL_PROCESSOR = AutoProcessor.from_pretrained(base_model_id, max_pixels=512 * 512, min_pixels=256 * 256)

    print("Loading base Qwen2-VL model weights...")
    dtype = torch.float16 if has_cuda else torch.float32
    base_model = Qwen2VLForConditionalGeneration.from_pretrained(
        base_model_id,
        torch_dtype=dtype,
        device_map="auto" if has_cuda else "cpu",
        trust_remote_code=True
    )

    print(f"Attaching fine-tuned LoRA adapter from {adapter_dir}...")
    _GLOBAL_MODEL = PeftModel.from_pretrained(base_model, adapter_dir)
    _GLOBAL_MODEL.eval()

    print("✅ HealVLM Adapter successfully attached and active!")
    print("=" * 65)
    return _GLOBAL_MODEL, _GLOBAL_PROCESSOR, _GLOBAL_TOKENIZER

def predict_healvlm_action(
    image_path: str,
    task_prompt: str,
    previous_actions: Optional[List[str]] = None,
    past_failure_chain: Optional[str] = None,
    adapter_dir: str = DEFAULT_ADAPTER_DIR
) -> str:
    """
    Drop-in replacement for ask_vlm_next_action(...) in benchmark_engine.py.
    Takes a screenshot and task prompt, runs HealVLM vision reasoning,
    and returns a string containing THOUGHT: ... and ACTION: ...
    """
    api_url = os.environ.get("HEALVLM_API_URL", "").strip()
    if api_url:
        import base64, requests
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        payload = {
            "image_b64": b64,
            "task_prompt": task_prompt,
            "previous_actions": previous_actions or [],
            "past_failure_chain": past_failure_chain or ""
        }
        res = requests.post(f"{api_url.rstrip('/')}/predict", json=payload, timeout=30)
        return res.json().get("prediction", "")

    import torch
    model, processor, tokenizer = load_healvlm_model(adapter_dir)
    device = next(model.parameters()).device

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Screenshot image not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    w, h = image.size
    if w * h > 512 * 512:
        scale = ((512 * 512) / (w * h)) ** 0.5
        new_w = max(28, int((w * scale) // 28) * 28)
        new_h = max(28, int((h * scale) // 28) * 28)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    history_str = " -> ".join(previous_actions) if previous_actions else "None"
    user_prompt = f"Goal: {task_prompt}\nPrevious Action History: {history_str}"
    if past_failure_chain:
        user_prompt += f"\n[Self-Healing Alert] Previous attempt failed: {past_failure_chain}. Correct your trajectory."

    # Format vision prompt tokens
    img_inputs = processor([image], return_tensors="pt")
    thw = img_inputs["image_grid_thw"][0]
    num_image_tokens = int((thw[1].item() * thw[2].item()) // 4)
    image_tokens = "<|image_pad|>" * num_image_tokens

    prompt_text = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n<|vision_start|>{image_tokens}<|vision_end|>{user_prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    inputs = tokenizer(prompt_text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)
    pixel_values = img_inputs["pixel_values"].to(device, dtype=torch.float16 if device.type == 'cuda' else torch.float32)
    image_grid_thw = img_inputs["image_grid_thw"].to(device)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            pixel_values=pixel_values,
            image_grid_thw=image_grid_thw,
            max_new_tokens=64,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
        )

    response = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
    return response

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test HealVLM Adapter Inference")
    parser.add_argument("--image", type=str, default="", help="Path to test screenshot")
    parser.add_argument("--prompt", type=str, default="Click the primary navigation element", help="Goal instruction")
    parser.add_argument("--adapter", type=str, default=DEFAULT_ADAPTER_DIR, help="Path to adapter folder")
    args = parser.parse_args()

    # Find a test image in dataset if none provided
    img_path = args.image
    if not img_path:
        sample_candidates = [
            "live_vlm_dataset/images/live_1792145245_step_1.jpg",
            "vlm_dataset/images/test_1792458123_step_1.jpg"
        ]
        for c in sample_candidates:
            if os.path.exists(c):
                img_path = c
                break

    if not img_path or not os.path.exists(img_path):
        print(f"❌ Error: Please specify a test screenshot via --image <path>")
        sys.exit(1)

    print(f"Testing inference on: {img_path}")
    print(f"Goal instruction: {args.prompt}")
    prediction = predict_healvlm_action(img_path, args.prompt, adapter_dir=args.adapter)
    print("\n" + "=" * 60)
    print("🎯 HEALVLM MODEL PREDICTION:")
    print("=" * 60)
    print(prediction)
    print("=" * 60)
