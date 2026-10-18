"""
HEALVLM: QWEN2-VL-2B-INSTRUCT 4-BIT QLORA TRAINING PIPELINE
============================================================
Designed for Kaggle Cloud Free 16GB T4 GPU / Colab / Linux GPU.
Trains exclusively on 100% verified True Cases harvested from live web benchmark runs.

Key Highlights:
1. 4-bit NormalFloat (NF4) quantization via BitsAndBytes.
2. Low-Rank Adaptation (LoRA) on all linear attention/MLP projections (r=16, alpha=32).
3. Dynamic multi-scale resolution patch processing (retaining native coordinate understanding).
4. Strict Cross-Entropy Loss Masking: Loss computed ONLY on model's THOUGHT and ACTION tokens;
   all prompt tokens, system instructions, and vision tokens are ignored (-100).
5. Fast, memory-efficient paged_adamw_8bit optimizer + gradient checkpointing.
"""

import os
import sys
import json
import torch
from dataclasses import dataclass
from typing import Any, Dict, List
from PIL import Image

# Reconfigure stdout/stderr for Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

os.environ["USE_TF"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
DATASET_FILE = "live_vlm_dataset/verified_true_cases.jsonl"
IMAGES_DIR = "live_vlm_dataset/images"
OUTPUT_DIR = "./healvlm_qwen2_vl_lora"

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

def check_environment():
    print("=" * 65)
    print("🚀 HEALVLM QWEN2-VL-2B QLORA TRAINING PIPELINE")
    print("=" * 65)
    print(f"PyTorch Version : {torch.__version__}")
    cuda_avail = torch.cuda.is_available()
    print(f"CUDA Available  : {cuda_avail}")
    if cuda_avail:
        print(f"Device Name     : {torch.cuda.get_device_name(0)}")
        total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"Total VRAM      : {total_mem:.2f} GB")
    else:
        print("⚠️ Warning: Running on CPU. For training, Kaggle T4 GPU is strongly recommended.")
    print("=" * 65)

class WebActionDataset(torch.utils.data.Dataset):
    """
    Loads verified true cases and prepares vision-language samples.
    """
    def __init__(self, dataset_path: str, images_dir: str, tokenizer, image_processor, max_pixels: int = 768 * 28 * 28):
        self.tokenizer = tokenizer
        self.image_processor = image_processor
        self.images_dir = images_dir
        self.max_pixels = max_pixels
        self.assistant_prefix_ids = tokenizer.encode("<|im_start|>assistant\n", add_special_tokens=False)
        self.samples = []

        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        with open(dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.samples.append(json.loads(line))
        print(f"Loaded {len(self.samples)} verified samples from {dataset_path}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = self.samples[idx]
        img_file = item.get("image_file", "")
        img_path = os.path.join(self.images_dir, img_file)
        
        # Load and convert image
        image = Image.open(img_path).convert("RGB")
        
        # Resize to stay within max_pixels while preserving aspect ratio and divisible by 28
        w, h = image.size
        curr_pixels = w * h
        if curr_pixels > self.max_pixels:
            scale = (self.max_pixels / curr_pixels) ** 0.5
            new_w = int((w * scale) // 28) * 28
            new_h = int((h * scale) // 28) * 28
            image = image.resize((max(28, new_w), max(28, new_h)), Image.Resampling.LANCZOS)

        instruction = item.get("instruction", "").strip()
        thought = item.get("thought", "Identify target visual element and execute primary action.").strip()
        ground_truth = item.get("ground_truth", "").strip()

        # Format full conversation
        prompt_text = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>{instruction}<|im_end|>\n"
            f"<|im_start|>assistant\nTHOUGHT: {thought}\nACTION: {ground_truth}<|im_end|>\n"
        )

        input_ids = self.tokenizer.encode(prompt_text, add_special_tokens=False)

        # Loss masking: locate <|im_start|>assistant\n
        prefix_len = len(self.assistant_prefix_ids)
        start_idx = -1
        for i in range(len(input_ids) - prefix_len + 1):
            if input_ids[i : i + prefix_len] == self.assistant_prefix_ids:
                start_idx = i + prefix_len
                break

        labels = [-100] * len(input_ids)
        if start_idx != -1:
            for i in range(start_idx, len(input_ids)):
                labels[i] = input_ids[i]

        # Process image with image_processor
        img_inputs = self.image_processor([image], return_tensors="pt")
        pixel_values = img_inputs["pixel_values"].squeeze(0) # [patches, channels]
        image_grid_thw = img_inputs["image_grid_thw"].squeeze(0) # [3]

        return {
            "input_ids": input_ids,
            "labels": labels,
            "pixel_values": pixel_values,
            "image_grid_thw": image_grid_thw
        }

@dataclass
class Qwen2VLDataCollator:
    """
    Pads text sequences and concatenates vision tensors for batched training.
    """
    tokenizer: Any
    pad_token_id: int

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        batch_input_ids = [f["input_ids"] for f in features]
        batch_labels = [f["labels"] for f in features]
        
        max_len = max(len(ids) for ids in batch_input_ids)

        padded_input_ids = []
        padded_attention_masks = []
        padded_labels = []

        for ids, lbl in zip(batch_input_ids, batch_labels):
            pad_len = max_len - len(ids)
            padded_input_ids.append(ids + [self.pad_token_id] * pad_len)
            padded_attention_masks.append([1] * len(ids) + [0] * pad_len)
            padded_labels.append(lbl + [-100] * pad_len)

        pixel_values = torch.cat([f["pixel_values"] for f in features], dim=0)
        image_grid_thw = torch.stack([f["image_grid_thw"] for f in features], dim=0)

        return {
            "input_ids": torch.tensor(padded_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(padded_attention_masks, dtype=torch.long),
            "labels": torch.tensor(padded_labels, dtype=torch.long),
            "pixel_values": pixel_values,
            "image_grid_thw": image_grid_thw
        }

def train():
    check_environment()
    
    from transformers import (
        AutoTokenizer,
        Qwen2VLImageProcessor,
        Qwen2VLForConditionalGeneration,
        TrainingArguments,
        Trainer
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    print("\n[Phase 1/4] Initializing Tokenizer, Processor & 4-Bit Model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    img_processor = Qwen2VLImageProcessor.from_pretrained(MODEL_ID)
    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

    # 4-bit Quantization Config (NF4)
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        model = prepare_model_for_kbit_training(model)
    else:
        print("Loading in FP32 on CPU for testing...")
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            device_map="cpu",
            torch_dtype=torch.float32,
            trust_remote_code=True
        )

    # LoRA Target Modules
    print("\n[Phase 2/4] Applying LoRA Adapter (r=16, alpha=32)...")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Dataset & Collator
    print("\n[Phase 3/4] Preparing Dataset & Batched Collator...")
    dataset = WebActionDataset(
        dataset_path=DATASET_FILE,
        images_dir=IMAGES_DIR,
        tokenizer=tokenizer,
        image_processor=img_processor
    )
    collator = Qwen2VLDataCollator(tokenizer=tokenizer, pad_token_id=pad_token_id)

    # Training Arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2 if has_cuda else 1,
        gradient_accumulation_steps=4 if has_cuda else 2,
        warmup_ratio=0.05,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=has_cuda,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=2,
        optim="paged_adamw_8bit" if has_cuda else "adamw_torch",
        gradient_checkpointing=True,
        report_to="none",
        dataloader_num_workers=2 if os.name != 'nt' else 0,
        remove_unused_columns=False
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collator
    )

    print("\n[Phase 4/4] Starting Fine-Tuning on Verified True Cases...")
    trainer.train()

    # Save final LoRA adapter
    final_save_dir = os.path.join(OUTPUT_DIR, "final_adapter")
    print(f"\n💾 Saving fine-tuned LoRA adapter to: {final_save_dir}")
    model.save_pretrained(final_save_dir)
    tokenizer.save_pretrained(final_save_dir)
    img_processor.save_pretrained(final_save_dir)
    print("🎉 HEALVLM Fine-Tuning Completed Successfully!")

if __name__ == "__main__":
    train()
