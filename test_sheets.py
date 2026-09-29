import gspread
import datetime
import traceback

def test_connection():
    try:
        gc = gspread.service_account(filename="convertionalai-d8da9e4d43dd.json")
        spreadsheet_id = "1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY"
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        row = [str(datetime.datetime.now()), "TEST_MODEL", "Test_Scenario", "120ms", "PASSED", "100%", "$0.0001", "[100, 100]"]
        worksheet.append_row(row)
        print(f"SUCCESS: Wrote row to {sh.title}")
    except Exception as e:
        print("ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()