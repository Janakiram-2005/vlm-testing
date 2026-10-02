import os
import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
from tqdm import tqdm

class VLMBehaviorDataset(Dataset):
    def __init__(self, jsonl_file, img_dir, processor):
        self.data = []
        self.img_dir = img_dir
        self.processor = processor
        
        print(f"Loading dataset from {jsonl_file}...")
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.data.append(json.loads(line))
        print(f"Loaded {len(self.data)} samples.")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Load Image
        img_path = os.path.join(self.img_dir, item['image_file'])
        image = Image.open(img_path).convert("RGB")
        
        # Construct Prompt
        history_str = " -> ".join(item['history']) if item['history'] else "None"
        prompt = f"<OD> Task: {item['instruction']}\nHistory: {history_str}\nAction:"
        
        # Ground Truth Label
        label = item['ground_truth']
        
        return {
            "image": image,
            "prompt": prompt,
            "label": label
        }

def collate_fn(batch, processor):
    images = [item["image"] for item in batch]
    prompts = [item["prompt"] for item in batch]
    labels = [item["label"] for item in batch]
    
    # Process inputs
    inputs = processor(text=prompts, images=images, return_tensors="pt", padding=True)
    
    # Process labels
    labels_encoded = processor.tokenizer(text=labels, return_tensors="pt", padding=True, return_attention_mask=False)["input_ids"]
    
    # Replace padding token id with -100 so cross-entropy ignores it
    labels_encoded[labels_encoded == processor.tokenizer.pad_token_id] = -100
    inputs["labels"] = labels_encoded
    
    return inputs

def train_florence2():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Training on device: {device}")
    
    model_id = "microsoft/Florence-2-base"
    print(f"Loading {model_id}...")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True).to(device)
    
    # For fine-tuning, unfreeze the vision encoder and language model depending on compute
    # Here, we keep it simple and train the whole model (requires decent VRAM)
    model.train()
    
    dataset = VLMBehaviorDataset(
        jsonl_file="vlm_dataset/dataset.jsonl",
        img_dir="vlm_dataset/images",
        processor=processor
    )
    
    dataloader = DataLoader(dataset, batch_size=2, shuffle=True, collate_fn=lambda b: collate_fn(b, processor))
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5)
    epochs = 3
    
    print("Starting training loop...")
    for epoch in range(epochs):
        total_loss = 0
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}")
        
        for batch in progress_bar:
            batch = {k: v.to(device) for k, v in batch.items()}
            
            outputs = model(**batch)
            loss = outputs.loss
            
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            
            total_loss += loss.item()
            progress_bar.set_postfix({"loss": f"{loss.item():.4f}"})
            
        print(f"Epoch {epoch+1} completed. Average Loss: {total_loss / len(dataloader):.4f}")
        
        # Save checkpoint
        checkpoint_dir = f"checkpoints/florence2-vlm-epoch{epoch+1}"
        os.makedirs(checkpoint_dir, exist_ok=True)
        model.save_pretrained(checkpoint_dir)
        processor.save_pretrained(checkpoint_dir)
        print(f"Saved checkpoint to {checkpoint_dir}")

if __name__ == "__main__":
    train_florence2()
