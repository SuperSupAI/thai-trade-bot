#!/usr/bin/env python
"""Robust rolling-window: DR รายวัน (REBAL=1) และรายสัปดาห์ (REBAL=5) vs รายเดือนเดิม (REBAL=21)"""
import pickle, sys
import statistics
sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
sys.path.insert(0, "dr_momentum_bot")
from dr_universe import DR_COVERED_EXPANDED, get_dr_symbol
from test_dr_daily_weekly_rebalance import sim

with open("us_close_10y_cache.pkl", "rb") as f:
    data = pickle.load(f)
prep = teo.precompute(data)
prep = add_extra_signals(prep)
confirmed = [t for t in DR_COVERED_EXPANDED if get_dr_symbol(t)[0]]
syms_order = [s for s in confirmed if s in prep]
all_dates = sorted(set().union(*[prep[s]["close"].index for s in syms_order]))
n = len(all_dates)

WINDOW_DAYS = 504
STEP_DAYS = 42
windows = []
start = 0
while start + WINDOW_DAYS <= n:
    windows.append(all_dates[start:start + WINDOW_DAYS])
    start += STEP_DAYS
print(f"ทั้งหมด {len(windows)} หน้าต่าง")

for challenger_label, challenger_rebal in [("รายวัน (REBAL=1)", 1), ("รายสัปดาห์ (REBAL=5)", 5)]:
    print(f"\n{'#'*90}\n{challenger_label} vs รายเดือนเดิม (REBAL=21)\n{'#'*90}")
    for top_n in [3, 5]:
        wins, diffs = 0, []
        for w in windows:
            r_challenger = sim(prep, syms_order, w, top_n, rebal=challenger_rebal)["ret_pct"]
            r_monthly = sim(prep, syms_order, w, top_n, rebal=21)["ret_pct"]
            diff = r_challenger - r_monthly
            diffs.append(diff)
            if r_challenger > r_monthly:
                wins += 1
        n_win = len(windows)
        third = n_win // 3
        early, mid, late = diffs[:third], diffs[third:2*third], diffs[2*third:]
        print(f"\ntop_n={top_n}: {challenger_label} ชนะรายเดือน {wins}/{n_win} หน้าต่าง ({100*wins/n_win:.0f}%), "
              f"เฉลี่ย {sum(diffs)/len(diffs):+.1f}pp, median {statistics.median(diffs):+.1f}pp")
        print(f"  ช่วงต้น: {sum(early)/len(early):+.1f}pp ({sum(1 for d in early if d>0)}/{len(early)} ชนะ)")
        print(f"  ช่วงกลาง: {sum(mid)/len(mid):+.1f}pp ({sum(1 for d in mid if d>0)}/{len(mid)} ชนะ)")
        print(f"  ช่วงล่าสุด: {sum(late)/len(late):+.1f}pp ({sum(1 for d in late if d>0)}/{len(late)} ชนะ)")
