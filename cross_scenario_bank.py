"""
CROSS-BOUNDARY SCENARIO BANK (Desktop OS <-> Web Scenarios)
============================================================
Defines structured test scenarios that cross between the Windows desktop
environment and web browsers, as well as native desktop productivity apps.
Includes automated sandbox generation and fast state setups/teardowns.
"""

import os
import sys
import time
import subprocess
from typing import Dict, List, Any

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

USER_DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
SANDBOX_DIR = os.path.join(USER_DESKTOP, "VLM_SANDBOX")

def create_sample_pdf(file_path: str):
    """Creates a minimal valid PDF file without external heavy dependencies."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <<>> >> endobj\n"
        b"4 0 obj <</Length 68>> stream\n"
        b"BT /F1 24 Tf 100 700 Td (HEALVLM CROSS-BOUNDARY TEST INVOICE) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000219 00000 n \n"
        b"trailer <</Size 5 /Root 1 0 R>>\n"
        b"startxref\n"
        b"337\n"
        b"%%EOF\n"
    )
    with open(file_path, "wb") as f:
        f.write(pdf_content)

def create_sample_html(file_path: str):
    """Creates an interactive modern test HTML dashboard for web-desktop transitions."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>VLM Enterprise Portal</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
  .card { background: #1e293b; border-radius: 12px; padding: 30px; max-width: 650px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
  h1 { color: #38bdf8; margin-top: 0; }
  p { color: #94a3b8; line-height: 1.6; }
  .badge { background: #0369a1; color: #e0f2fe; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; }
  .btn { display: inline-block; background: #2563eb; color: #fff; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; margin-top: 20px; font-size: 15px; }
  .btn:hover { background: #1d4ed8; }
  .auth-token { background: #020617; border: 1px dashed #38bdf8; padding: 12px; border-radius: 6px; font-family: Consolas, monospace; color: #38bdf8; margin-top: 15px; font-size: 16px; text-align: center; }
</style>
</head>
<body>
<div class="card">
  <span class="badge">SECURE TRANSITION GATEWAY</span>
  <h1>Autonomous Cross-Boundary Portal</h1>
  <p>This page verified that the desktop agent successfully launched the web browser from the desktop environment.</p>
  <div class="auth-token" id="tokenField">AUTH-TOKEN-HEALVLM-9942</div>
  <button class="btn" id="confirmBtn" onclick="this.innerText='VERIFIED SUCCESSFUL!'; this.style.background='#16a34a';">Confirm Document Access</button>
</div>
</body>
</html>
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

def setup_sandbox() -> Dict[str, str]:
    """Generates the isolated desktop sandbox folder with test files."""
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    pdf_path = os.path.join(SANDBOX_DIR, "invoice_2026.pdf")
    html_path = os.path.join(SANDBOX_DIR, "company_portal.html")
    txt_path = os.path.join(SANDBOX_DIR, "session_notes.txt")

    if not os.path.exists(pdf_path):
        create_sample_pdf(pdf_path)
    if not os.path.exists(html_path):
        create_sample_html(html_path)
    if not os.path.exists(txt_path):
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("HEALVLM Desktop Notes Initial State\n")

    return {
        "sandbox_dir": SANDBOX_DIR,
        "pdf_path": pdf_path,
        "html_path": html_path,
        "txt_path": txt_path
    }

def get_scenarios() -> List[Dict[str, Any]]:
    """Returns curated cross-boundary and desktop benchmark scenarios."""
    fixtures = setup_sandbox()
    
    return [
        {
            "id": "cross_01_desktop_html_to_web",
            "name": "Desktop Folder HTML to Web Browser Gateway",
            "type": "DESKTOP_TO_WEB",
            "goal": "Open the VLM_SANDBOX folder, launch company_portal.html, and click the blue 'Confirm Document Access' button in the browser.",
            "target_app": "company_portal.html",
            "setup_shell": f'start "" "{fixtures["sandbox_dir"]}"',
            "cleanup_shell": 'taskkill /f /im chrome.exe /im brave.exe /im msedge.exe 2>nul; exit 0',
            "success_keyword": "company_portal"
        },
        {
            "id": "cross_02_desktop_pdf_reader",
            "name": "Desktop PDF Launch & Focus",
            "type": "DESKTOP_TO_WEB",
            "goal": "In the VLM_SANDBOX folder, locate invoice_2026.pdf and double-click it to open the document viewer.",
            "target_app": "invoice_2026.pdf",
            "setup_shell": f'start "" "{fixtures["sandbox_dir"]}"',
            "cleanup_shell": 'taskkill /f /im Acrobat.exe /im msedge.exe /im chrome.exe 2>nul; exit 0',
            "success_keyword": "invoice_2026"
        },
        {
            "id": "desktop_03_notepad_productivity",
            "name": "Native Notepad Autonomous Typing & Save",
            "type": "DESKTOP_APP_NOTEPAD",
            "goal": "Open Notepad, type 'HEALVLM Verified Autonomous Desktop Run', and save the file.",
            "target_app": "notepad.exe",
            "setup_shell": "taskkill /f /im notepad.exe 2>nul; start notepad.exe",
            "cleanup_shell": "taskkill /f /im notepad.exe 2>nul; exit 0",
            "success_keyword": "Notepad"
        },
        {
            "id": "desktop_04_mspaint_canvas_box",
            "name": "MS Paint Visual Spatial Box Drawing",
            "type": "DESKTOP_APP_PAINT",
            "goal": "Open MS Paint, select the Rectangle shape, and draw a bounding box across the central white canvas.",
            "target_app": "mspaint.exe",
            "setup_shell": "taskkill /f /im mspaint.exe 2>nul; start mspaint.exe",
            "cleanup_shell": "taskkill /f /im mspaint.exe 2>nul; exit 0",
            "success_keyword": "Paint"
        }
    ]

if __name__ == "__main__":
    fixtures = setup_sandbox()
    print("=" * 65)
    print("📁 VLM_SANDBOX TESTBED GENERATED")
    print(f"• Sandbox Directory: {fixtures['sandbox_dir']}")
    print(f"• Sample PDF       : {fixtures['pdf_path']}")
    print(f"• Sample Portal HTML: {fixtures['html_path']}")
    print("=" * 65)
    scenarios = get_scenarios()
    print(f"✅ Loaded {len(scenarios)} Cross-Boundary & Desktop Benchmark Scenarios.")
    for s in scenarios:
        print(f"  [{s['type']}] {s['id']}: {s['goal']}")
