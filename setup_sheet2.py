import gspread
import traceback

import time

def initialize_sheet2():
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[INFO] Connecting to Google Sheets (Attempt {attempt}/{max_retries})...")
            gc = gspread.service_account(filename="convertionalai-d8da9e4d43dd.json")
            spreadsheet_id = "1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY"
            sh = gc.open_by_key(spreadsheet_id)
            
            sheet_titles = [ws.title for ws in sh.worksheets()]
            target_title = "Live_Web_Benchmark"
            
            headers = [
                "Test ID",
                "Batch ID",
                "Timestamp",
                "Platform",
                "Task",
                "Page Load Latency",
                "VLM Latency",
                "Total Latency",
                "Status",
                "Error Classification",
                "Action Chain",
                "Total Steps"
            ]
            
            if target_title not in sheet_titles:
                print(f"[INFO] Creating new worksheet '{target_title}'...")
                ws = sh.add_worksheet(title=target_title, rows=1000, cols=20)
                ws.append_row(headers)
                print(f"[SUCCESS] Created worksheet '{target_title}' with 12 structured headers!")
            else:
                print(f"[INFO] Worksheet '{target_title}' already exists. Checking header...")
                ws = sh.worksheet(target_title)
                existing_headers = ws.row_values(1)
                if not existing_headers:
                    ws.append_row(headers)
                    print(f"[SUCCESS] Appended headers to existing '{target_title}'.")
                else:
                    print(f"[INFO] Existing headers: {existing_headers}")
                    
            print("[INFO] Available worksheets now:", [w.title for w in sh.worksheets()])
            return True
        except Exception as e:
            print(f"[WARN] Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                sleep_time = attempt * 2
                print(f"[INFO] Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                print("[ERROR] Max retries reached. Stacktrace:")
                traceback.print_exc()
                return False

if __name__ == "__main__":
    initialize_sheet2()
