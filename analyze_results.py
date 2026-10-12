import gspread
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

plt.style.use('ggplot')
sns.set_theme(style="whitegrid")

def clean_time(x):
    try:
        return float(str(x).replace('ms', '').strip())
    except Exception:
        return None

def run_analysis():
    print("[INFO] Connecting to Google Sheets...")
    try:
        gc = gspread.service_account(filename='convertionalai-d8da9e4d43dd.json')
        sh = gc.open_by_key('1eJ5PPHPvCbedRuLo-u1Wk9IYL6OdkJf36pzy87KuynY')
        
        # 1. Load Synthetic Data (Sheet1)
        ws_synth = sh.sheet1
        data_synth = ws_synth.get_all_values()
        df_synth = pd.DataFrame(data_synth[1:], columns=data_synth[0]) if len(data_synth) > 1 else pd.DataFrame()
        
        # 2. Load Live Web Data (Live_Web_Benchmark)
        df_live = pd.DataFrame()
        try:
            ws_live = sh.worksheet('Live_Web_Benchmark')
            data_live = ws_live.get_all_values()
            if len(data_live) > 1:
                df_live = pd.DataFrame(data_live[1:], columns=data_live[0])
        except Exception as e:
            print(f"[WARN] Could not load Live_Web_Benchmark worksheet: {e}")
            
    except Exception as e:
        print(f"[ERROR] Error connecting to Google Sheets: {e}")
        return

    # Process Synthetic Data
    has_synth = not df_synth.empty
    if has_synth:
        df_synth['Total Time (ms)'] = df_synth['Latency'].apply(clean_time)
        df_synth['Steps'] = pd.to_numeric(df_synth['Total Steps'], errors='coerce')
        def extract_ui(scenario):
            match = re.search(r'\[(.*?)\]', str(scenario))
            return match.group(1) if match else 'Unknown'
        df_synth['UI File'] = df_synth['Task'].apply(extract_ui)
        print(f"[INFO] Loaded {len(df_synth)} synthetic records from Sheet1.")

    # Process Live Web Data
    has_live = not df_live.empty
    if has_live:
        df_live['Total Time (ms)'] = df_live['Total Latency'].apply(clean_time)
        df_live['Page Load (ms)'] = df_live['Page Load Latency'].apply(clean_time)
        df_live['VLM Latency (ms)'] = df_live['VLM Latency'].apply(clean_time)
        df_live['Steps'] = pd.to_numeric(df_live['Total Steps'], errors='coerce')
        print(f"[INFO] Loaded {len(df_live)} live web records from Live_Web_Benchmark.")

    # --- Charts Generation ---

    # 1. Baseline Synthetic Charts (if present)
    if has_synth:
        plt.figure(figsize=(8, 5))
        status_counts = df_synth['Status'].value_counts()
        colors = ['#2ecc71' if s == 'PASSED' else '#e74c3c' for s in status_counts.index]
        sns.barplot(x=status_counts.index, y=status_counts.values, hue=status_counts.index, palette=colors, legend=False)
        plt.title('Synthetic HTML Pass Rate (Baseline)')
        plt.ylabel('Number of Tests')
        plt.savefig('analysis_pass_rate.png', bbox_inches='tight')
        plt.close()

        passed_synth = df_synth[df_synth['Status'] == 'PASSED'].copy()
        if not passed_synth.empty:
            plt.figure(figsize=(10, 6))
            sns.histplot(passed_synth['Total Time (ms)'], bins=20, kde=True, color='#3498db')
            plt.title('Synthetic Latency Distribution (ms)')
            plt.axvline(passed_synth['Total Time (ms)'].mean(), color='r', linestyle='--', label=f"Mean: {passed_synth['Total Time (ms)'].mean():.1f}ms")
            plt.legend()
            plt.savefig('analysis_latency.png', bbox_inches='tight')
            plt.close()

    # 2. Comparative & Live Web Charts
    if has_synth and has_live:
        # Comparison Pass Rate Bar Chart
        plt.figure(figsize=(8, 5))
        synth_pass_pct = (df_synth['Status'] == 'PASSED').mean() * 100
        live_pass_pct = (df_live['Status'] == 'PASSED').mean() * 100
        
        comp_df = pd.DataFrame({
            'Environment': ['Synthetic HTML (Sheet 1)', 'Live Web (Sheet 2)'],
            'Pass Rate (%)': [synth_pass_pct, live_pass_pct]
        })
        sns.barplot(x='Environment', y='Pass Rate (%)', data=comp_df, hue='Environment', palette=['#3498db', '#e67e22'], legend=False)
        plt.title('VLM Success Rate: Synthetic vs. Live Web')
        plt.ylim(0, 105)
        for i, val in enumerate([synth_pass_pct, live_pass_pct]):
            plt.text(i, val + 2, f"{val:.1f}%", ha='center', fontweight='bold')
        plt.savefig('analysis_comparison_pass_rate.png', bbox_inches='tight')
        plt.close()

    if has_live:
        # Live Web Success Rate by Platform
        plt.figure(figsize=(10, 5))
        platform_success = df_live.groupby('Platform')['Status'].apply(lambda x: (x == 'PASSED').mean() * 100).sort_values(ascending=False)
        sns.barplot(x=platform_success.index, y=platform_success.values, hue=platform_success.index, palette='viridis', legend=False)
        plt.title('Live Web Success Rate by Platform (%)')
        plt.ylabel('Success Rate (%)')
        plt.ylim(0, 105)
        for i, val in enumerate(platform_success.values):
            plt.text(i, val + 2, f"{val:.1f}%", ha='center', fontweight='bold')
        plt.savefig('analysis_live_platform_success.png', bbox_inches='tight')
        plt.close()

        # Error Classification Breakdown
        plt.figure(figsize=(10, 5))
        err_counts = df_live['Error Classification'].value_counts()
        sns.barplot(x=err_counts.index, y=err_counts.values, hue=err_counts.index, palette='mako', legend=False)
        plt.title('Live Web Error Taxonomy Breakdown')
        plt.ylabel('Occurrences')
        plt.xticks(rotation=30)
        plt.savefig('analysis_error_breakdown.png', bbox_inches='tight')
        plt.close()

    # --- Markdown Summary Report ---
    report_lines = ["# 📊 Autonomous VLM Benchmark Report\n"]
    
    if has_synth:
        passed_synth = df_synth[df_synth['Status'] == 'PASSED']
        synth_rate = (df_synth['Status'] == 'PASSED').mean() * 100
        synth_latency = passed_synth['Total Time (ms)'].mean() if not passed_synth.empty else 0
        report_lines.append(f"""## 🧪 1. Synthetic HTML Baseline (Sheet 1)
- **Total Tests**: {len(df_synth)}
- **Success Rate**: {synth_rate:.1f}%
- **Average Completion Time**: {synth_latency:.1f} ms
- **Average Steps**: {passed_synth['Steps'].mean():.1f}
""")

    if has_live:
        passed_live = df_live[df_live['Status'] == 'PASSED']
        live_rate = (df_live['Status'] == 'PASSED').mean() * 100
        live_tot_lat = passed_live['Total Time (ms)'].mean() if not passed_live.empty else 0
        live_page_lat = passed_live['Page Load (ms)'].mean() if not passed_live.empty else 0
        live_vlm_lat = passed_live['VLM Latency (ms)'].mean() if not passed_live.empty else 0
        
        report_lines.append(f"""## 🌐 2. Live Web Benchmark (Sheet 2: `Live_Web_Benchmark`)
- **Total Live Tests**: {len(df_live)}
- **Overall Live Success Rate**: {live_rate:.1f}%
- **Average Total Duration**: {live_tot_lat:.1f} ms
  - *Page Load & Stabilization*: {live_page_lat:.1f} ms
  - *Gemini 2.5 Flash Inference*: {live_vlm_lat:.1f} ms
- **Average Steps per Live Task**: {passed_live['Steps'].mean():.1f}

### 🏢 Platform Performance:
""")
        plat_grouped = df_live.groupby('Platform')['Status'].apply(lambda x: (x == 'PASSED').mean() * 100)
        for p, r in plat_grouped.items():
            report_lines.append(f"- **{p}**: {r:.1f}%\n")

        report_lines.append("""
### ⚠️ Error Classification Breakdown:
""")
        err_counts = df_live['Error Classification'].value_counts()
        for e, cnt in err_counts.items():
            report_lines.append(f"- **{e}**: {cnt} occurrences\n")

    if has_synth and has_live:
        report_lines.append(f"""
## ⚖️ 3. Comparative Analysis (Synthetic vs. Live Web)
| Metric | Synthetic HTML (Sheet 1) | Live Web (Sheet 2) | Variance / Delta |
| :--- | :---: | :---: | :---: |
| **Pass Rate** | {synth_rate:.1f}% | {live_rate:.1f}% | {live_rate - synth_rate:+.1f}% |
| **Average Latency** | {synth_latency:.1f} ms | {live_tot_lat:.1f} ms | {live_tot_lat - synth_latency:+.1f} ms |
""")

    with open('analysis_report.md', 'w', encoding='utf-8') as f:
        f.writelines(report_lines)

    print("[SUCCESS] Analysis complete! Updated analysis_report.md and comparison charts.")

if __name__ == "__main__":
    run_analysis()
