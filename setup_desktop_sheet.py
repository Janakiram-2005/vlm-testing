"""
SETUP GOOGLE SHEET FOR DESKTOP + WEB BENCHMARK
==============================================
Creates a dedicated worksheet 'Desktop_Web_Benchmark' in the project Google Spreadsheet
to independently track and evaluate cross-boundary OS + Web agent runs.
"""

import sys
import time
import datetime
import traceback
import gspread

# Reconfigure stdout/stderr for Unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

SPREADSHEET_ID = "1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY"
CREDENTIALS_FILE = "convertionalai-d8da9e4d43dd.json"
SHEET_TITLE = "Desktop_Web_Benchmark"

HEADERS = [
    "Test ID",
    "Batch ID",
    "Timestamp",
    "Scenario ID",
    "Environment Type",
    "Goal Task",
    "Primary Driver",
    "Status",
    "Total Steps",
    "Total Latency (ms)",
    "Action Chain",
    "Window Transition Sequence",
    "Teacher Interventions",
    "Dataset Sample ID"
]

def initialize_desktop_sheet():
    print(f"📊 Connecting to Google Sheets (Spreadsheet ID: {SPREADSHEET_ID})...")
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    sh = gc.open_by_key(SPREADSHEET_ID)

    existing_sheets = [ws.title for ws in sh.worksheets()]
    print(f"• Current Worksheets: {existing_sheets}")

    if SHEET_TITLE not in existing_sheets:
        print(f"✨ Creating new dedicated worksheet: '{SHEET_TITLE}'...")
        ws = sh.add_worksheet(title=SHEET_TITLE, rows=1000, cols=len(HEADERS) + 4)
        ws.append_row(HEADERS)
        print(f"✅ Successfully created '{SHEET_TITLE}' with {len(HEADERS)} structured headers!")
    else:
        print(f"ℹ️ Worksheet '{SHEET_TITLE}' already exists. Verifying headers...")
        ws = sh.worksheet(SHEET_TITLE)
        current_headers = ws.row_values(1)
        if not current_headers:
            ws.append_row(HEADERS)
            print(f"✅ Appended headers to empty worksheet '{SHEET_TITLE}'.")
        else:
            print(f"✅ Headers verified: {len(current_headers)} columns present.")

    all_sheets = [ws.title for ws in sh.worksheets()]
    print(f"• Updated Worksheets: {all_sheets}")
    return ws

def log_desktop_test(
    scenario_id: str,
    env_type: str,
    goal: str,
    driver: str,
    status: str,
    total_steps: int,
    latency_ms: float,
    action_chain: list,
    window_seq: list,
    teacher_interventions: int,
    sample_id: str = "N/A",
    batch_id: str = "Batch-01"
):
    """Logs a single cross-boundary run to Desktop_Web_Benchmark."""
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(SHEET_TITLE)

        all_vals = ws.get_all_values()
        test_num = max(1, len(all_vals))
        test_id = f"DW-{test_num:03d}"

        chain_str = " -> ".join(action_chain) if action_chain else "None"
        win_str = " -> ".join(window_seq) if window_seq else "Desktop"

        row = [
            test_id,
            batch_id,
            datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            scenario_id,
            env_type,
            goal,
            driver,
            status,
            total_steps,
            f"{round(latency_ms, 2)}ms",
            chain_str,
            win_str,
            teacher_interventions,
            sample_id
        ]

        ws.append_row(row)
        print(f"📋 [SHEET LOGGED] Successfully added row {test_id} ({status}) to '{SHEET_TITLE}'")
        return test_id
    except Exception as e:
        print(f"⚠️ Sheet logging notice: {e}")
        return None

if __name__ == "__main__":
    initialize_desktop_sheet()
