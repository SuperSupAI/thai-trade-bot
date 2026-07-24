#!/usr/bin/env python
"""Robust rolling-window: รีบาลานซ์รายสัปดาห์ (REBAL=5) vs รายเดือนเดิม (REBAL=21) หุ้นไทย 75 ตัว"""
import pickle, sys
import statistics
sys.path.insert(0, ".")
from test_thai_weekly_rebalance import sim, FORMATION, SKIP

with open("thai_stocks_10y_cache.pkl", "rb") as f:
    data = pickle.load(f)
syms_order = list(data.keys())
all_dates = sorted(set().union(*[data[s].index for s in syms_order]))
n = len(all_dates)

WINDOW_DAYS = 504  # ~2 ปีเทรด (เหมือน rolling-window test อื่นๆ ในโปรเจกต์นี้)
STEP_DAYS = 42
windows = []
start = 0
while start + WINDOW_DAYS <= n:
    windows.append(all_dates[start:start + WINDOW_DAYS])
    start += STEP_DAYS
print(f"ทั้งหมด {len(windows)} หน้าต่าง")

for top_n in [3, 5]:
    wins, diffs = 0, []
    for w in windows:
        r_weekly = sim(data, syms_order, w, top_n, rebal=5)["ret_pct"]
        r_monthly = sim(data, syms_order, w, top_n, rebal=21)["ret_pct"]
        diff = r_weekly - r_monthly
        diffs.append(diff)
        if r_weekly > r_monthly:
            wins += 1
    n_win = len(windows)
    third = n_win // 3
    early, mid, late = diffs[:third], diffs[third:2*third], diffs[2*third:]
    print(f"\ntop_n={top_n}: รายสัปดาห์ ชนะ รายเดือน {wins}/{n_win} หน้าต่าง ({100*wins/n_win:.0f}%), "
          f"เฉลี่ย {sum(diffs)/len(diffs):+.1f}pp, median {statistics.median(diffs):+.1f}pp")
    print(f"  ช่วงต้น: {sum(early)/len(early):+.1f}pp ({sum(1 for d in early if d>0)}/{len(early)} ชนะ)")
    print(f"  ช่วงกลาง: {sum(mid)/len(mid):+.1f}pp ({sum(1 for d in mid if d>0)}/{len(mid)} ชนะ)")
    print(f"  ช่วงล่าสุด: {sum(late)/len(late):+.1f}pp ({sum(1 for d in late if d>0)}/{len(late)} ชนะ)")
