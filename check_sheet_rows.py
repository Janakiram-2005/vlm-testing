import gspread
import json

gc = gspread.service_account(filename='convertionalai-d8da9e4d43dd.json')
sh = gc.open_by_key('1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY')
ws = sh.worksheet('Live_Web_Benchmark')
rows = ws.get_all_records()
print(f"Total records in Sheet 2: {len(rows)}")

for r in rows:
    test_id = r.get('Test ID', '')
    platform = r.get('Platform', '')
    status = r.get('Status', '')
    err = r.get('Error Classification', '')
    task = r.get('Task', '')
    chain = r.get('Action Chain', '')
    steps = r.get('Total Steps', '')
    vlm_lat = r.get('VLM Latency (ms)', '')
    print(f"[{test_id}] {platform} | Status: {status} | Error: {err} | Steps: {steps} | VLM Lat: {vlm_lat}")
    print(f"   Task: {task}")
    print(f"   Chain: {chain}")
    print("-" * 60)
