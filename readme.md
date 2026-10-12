# VLM Autonomous Testing Engine (Native Spatial Edition)

An autonomous, zero-shot Vision-Language Model (VLM) engine that navigates complex graphical user interfaces using purely visual grounding (no DOM parsing). Powered by Gemini 2.5 Flash, it features Macro-Action Pipelining, Euclidean Jitter Detection, and a Self-Healing Memory loop.

## 🚀 How to Run

### 1. Run the Synthetic HTML Benchmark (Sheet 1)
Tests across 10 local HTML UIs (`test_ui_1.html` - `test_ui_10.html`):
```bash
python benchmark_engine.py
```

### 2. Run the Live Web Benchmark (Sheet 2: `Live_Web_Benchmark`)
Autonomous testing on **live real-world websites** (Amazon, Wikipedia, YouTube, GitHub, Online Spreadsheet) equipped with pre-flight health pings, visual settling watchdogs, and F5 auto-healing:
```bash
python benchmark_live_engine.py
```

### 3. Generate Dual-Sheet Analytics & Comparison
Generates side-by-side comparative charts (`Synthetic vs. Live Web` pass rates, latency distributions, and error breakdowns):
```bash
python analyze_results.py
```

## 💬 Developer Notes (Resuming the AI Assistant)
**Antigravity Conversation ID**: `5a2d7f24-c796-4a5d-9566-8327e5f84d4c`

To resume this exact chat context, run:
```bash
agy resume 5a2d7f24-c796-4a5d-9566-8327e5f84d4c
```

---

## 🛠️ V2 Upgrade Implementation Plan (Scaling to the Live Web)

### Phase 1: Video Inference & 3D Motion (Weeks 1-2)
- **Goal**: Handle dynamic backgrounds (YouTube) and 3D WebGL animations.
- **Implementation**: 
  - Swap `pyautogui.screenshot()` with a fast screen-recording buffer (e.g., using `cv2` or `mss`).
  - Capture exactly 1.0 second of video at 10 FPS.
  - Modify the Vertex AI call to pass `video/mp4` instead of `image/jpeg`.
  - Update the Meta-Prompt to instruct the VLM to calculate spatial trajectories of moving elements.

### Phase 2: Live CAPTCHA Resolution (Weeks 3-4)
- **Goal**: Natively bypass image grid CAPTCHAs (e.g., "Select all traffic lights").
- **Implementation**:
  - Update the `THEN` pipelining logic to allow up to 6 chained actions (instead of 3).
  - Train the VLM to recognize CAPTCHA sub-grids and return an array of 2D coordinates for a sequential `CLICK` chain.
  - Implement a `VERIFY_CAPTCHA` Macro-Pause to ensure the DOM loads before proceeding.

### Phase 3: Advanced Self-Healing Reflection (Weeks 5-6)
- **Goal**: Solidify the `failure_logs.json` system into a true semantic search memory.
- **Implementation**:
  - Instead of direct string-matching, implement local embeddings for the `scenario` descriptions.
  - If a new task semantically matches a past failed task (e.g., "Delete email" vs "Remove message"), inject the past failure warning into the prompt to preemptively avoid mistakes.
  - Set up a continuous offline loop to format `failure_logs.json` into a fine-tuning dataset for Behavioral Cloning.
