# 🤖 VLM Autonomous Testing Engine

![VLM Benchmark Engine](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Language-Python%203.10+-blue) ![Gemini](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-orange)

An elite, multi-step Autonomous UI Agent testing framework powered by Vision-Language Models (VLMs). This project is built to aggressively benchmark the spatial reasoning, logic, and GUI navigation capabilities of native VLMs by forcing them to interact with simulated graphical environments.

## 🌟 The Vision
The ultimate goal of this project is to create an autonomous agent that can perfectly navigate **any** graphical user interface purely through visual reasoning, without relying on DOM manipulation, HTML scraping, or browser extensions. 

**"If a human can see it and click it, the AI should be able to do it too."**

## 🧠 Core Architecture
The engine is built on a custom python wrapper that orchestrates the entire test suite:
1. **The Environments:** Custom built HTML UI layouts (`test_ui.html` - `test_ui_7.html`) featuring complex interactive elements: Drag & Drop, Captcha sliders, hidden hover menus, and sudden blocking popups.
2. **The Overlay:** A transparent, topmost `Tkinter` window that provides a live telemetry dashboard (Task, Status, Result) directly over the active test.
3. **The VLM Fast-Path:** Screenshots are rapidly captured via `pyautogui`, piped into Google's **Gemini 2.5 Flash** model (Vertex AI), and processed with a highly optimized System Prompt.
4. **Action Execution:** The VLM's output (normalized 0-1000 coordinate bounding boxes) is parsed using a robust RegEx engine, mapped to the user's physical screen resolution, and executed natively via `pyautogui` mouse/keyboard commands.
5. **Data Lake:** Every trajectory, millisecond latency, and action chain is streamed securely into a cloud database.

📊 **Live Data Dashboard (Google Sheets):** [VLM Benchmark Telemetry](https://docs.google.com/spreadsheets/d/1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY/edit)

## 🚀 Progress & Features (Stage 1)
We have successfully built the **Dynamics Engine (v15)**.
- [x] **Native Spatial Coordinate System:** Zero DOM dependency. Normalized `[ymin, xmin, ymax, xmax]` bounding boxes mapped to physical OS pixels.
- [x] **Action Arsenal:** `CLICK`, `TYPE`, `DRAG`, and `SCROLL_DOWN` supported.
- [x] **Repetitive Action Blocking:** Hard-coded interceptors prevent the VLM from entering infinite loops.
- [x] **Resilience Engineering:** Built-in API Rate Limit handling (429 Exponential Backoff) and bulletproof RegEx parsing for malformed VLM outputs.
- [x] **7 Complex Test Environments:** Including Kanban boards, nested setting tabs, IDE simulators, and random popup injections.

## 🔮 Next Steps: Stage 2 (Real-World Density & Tiny-ML)
We are currently generating massive trajectory datasets to transition from API reliance to local, 0-latency execution.

1. **Tiny-ML Behavioral Cloning:** We are using the collected JSON spatial memory logs to train a local Random Forest / XGBoost model. This model will act as a lightning-fast "Muscle Memory" cache—if the system recognizes a familiar UI layout, the local model will instantly execute the action, bypassing the VLM entirely.
2. **Extreme Density Testing:** Moving away from synthetic HTML environments to real-world platforms like **Amazon** and **Gmail** to test microscopic 10px hyperlinks and overlapping carousels.
3. **Advanced State Retention:** Implementing `COPY` and `PASTE` commands to force the VLM to maintain short-term working memory over multiple turns.

## 🛠️ Usage
Ensure you have the required credentials file (`convertionalai-d8da9e4d43dd.json`) in the root directory.

```bash
pip install -r requirements.txt
python benchmark_engine.py
```
> The script will prompt you for the number of test batches. Once started, sit back and watch the AI take control. **Press `ESC` to kill the engine at any time.**
