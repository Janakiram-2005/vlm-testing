# 📜 Project History & Work Log: Live Web VLM Benchmarking Suite

## 💬 Session & Chat Resume Info
* **Antigravity Conversation ID**: `5a2d7f24-c796-4a5d-9566-8327e5f84d4c`
* **Resume Command** (Terminal):
  ```bash
  agy resume 5a2d7f24-c796-4a5d-9566-8327e5f84d4c
  ```
* **Git Repository**: `https://github.com/Janakiram-2005/vlm-testing.git` (Branch: `main`)
* **Google Cloud Project**: `convertionalai` (Vertex AI, `us-central1`, Gemini 2.5 Flash)
* **Google Spreadsheet ID**: `1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY`

---

## 🚀 Summary of Upgrades & Milestones Completed

### 1. Dual-Sheet Telemetry Architecture (Google Sheets)
* **`Sheet1`**: Preserved untouched as the synthetic baseline (95 historical tests across 10 mock HTML UIs).
* **`Live_Web_Benchmark` (Sheet 2)**: Initialized via `setup_sheet2.py` with 12 structured columns:
  - `Test ID`, `Batch ID`, `Timestamp`, `Platform`, `Task`
  - `Page Load Latency` vs. `VLM Latency` vs. `Total Latency`
  - `Status` (`PASSED`, `FAILED`, `HEALED`, `SKIPPED`)
  - `Error Classification` (`NONE`, `AI_SPATIAL_MISS`, `NET_BAD_GATEWAY`, `NET_TIMEOUT`, `RENDER_BLANK`)
  - `Action Chain` and `Total Steps`

### 2. Live Web Resilience & Anti-Lag Engine (`network_guard.py`)
* **Pre-Flight Health Ping (`check_url_health`)**: Sub-second check to detect genuine 500/502/503/504 Bad Gateways and DNS drops before launching the browser. Gracefully hands off bot-shielded endpoints (Cloudflare/Akamai/GitHub) directly to Chrome.
* **Adaptive Visual Settling Watchdog (`wait_for_visual_settle`)**: Measures structural pixel variance between two downsampled screen frames (320×180). Proceeds immediately when the page settles (< 1% variance) rather than relying on arbitrary static delays.
* **Auto-Healing `F5` Recovery Loop (`trigger_f5_recovery`)**: Automatically triggers a browser refresh and secondary settle check if client-side render lag or a blank screen occurs.
* **Domain Circuit Breaker (`DomainCircuitBreaker`)**: Temporarily suspends any platform that encounters 2 consecutive network/gateway timeouts, keeping the benchmark suite running smoothly.

### 3. Curated Live Scenario Bank (`live_scenario_bank.py`)
Created non-destructive real-world tasks across 5 core platforms:
* **Amazon**: Search input, 4 Stars & Up filter sidebar, product card clicks.
* **Wikipedia**: Search inputs, language selections, Table of Contents jumps.
* **YouTube**: Search input, video thumbnail clicks, media player controls.
* **GitHub**: Topics exploration, repository search, filter bars.
* **Online Spreadsheet Sandbox**: Cell selection (`C3`, `B2`), formula typing, and 18px micro-target formatting icons (Bold **B**).

### 4. Dedicated Live Dataset Pipeline (`live_vlm_dataset/`)
* **Autonomous Trajectory Harvester**: Automatically flushes all passing trajectories into:
  - `live_vlm_dataset/dataset.jsonl`
  - `live_vlm_dataset/images/*.jpg`
* **Behavioral Cloning Pipeline (`train_tiny_ml.py`)**: Updated to automatically load `live_vlm_dataset` for fine-tuning Microsoft Florence-2 on real-world web trajectories.

### 5. Critical Fixes & Hardening Applied
* **Flexible Action Parser**: Implemented `parse_type_command()` in `benchmark_live_engine.py` to seamlessly parse both bracketed (`TYPE [72, 233, 97, 348] text`) and unbracketed (`TYPE 72 233 97 348 text`) VLM outputs.
* **Google Sheets Connection Caching**: Cached worksheet connection (`get_live_worksheet()`) to eliminate transient `RemoteDisconnected` socket errors during high-frequency logging.
* **Git Dataset Upload**: Successfully staged and pushed all 456 historical synthetic step images and dataset files to GitHub in 5 optimized chunks without hitting HTTP 408 size timeouts.
* **Credential Protection**: Strict `.gitignore` rules preventing any leakage of `convertionalai-d8da9e4d43dd.json`.

---

## 🏃 Quick Command Reference

| Action | Command |
| :--- | :--- |
| **Run Live Web Benchmark** | `python benchmark_live_engine.py` |
| **Run Synthetic HTML Benchmark** | `python benchmark_engine.py` |
| **Generate Comparative Analytics** | `python analyze_results.py` |
| **Train Behavioral Cloning Model** | `python train_tiny_ml.py` |
| **Re-Initialize Sheet 2** | `python setup_sheet2.py` |
| **Resume AI Assistant** | `agy resume 5a2d7f24-c796-4a5d-9566-8327e5f84d4c` |
