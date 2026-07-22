#!/usr/bin/env python
"""
Robust rolling-window: 95 US เดิม vs 172 (US+เอเชียขยาย 77 ตัว) ใช้หน้าต่าง 2 ปีเหลื่อมกันทั่วประวัติศาสตร์
"""
import pickle, sys
import pandas as pd
import statistics
sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
sys.path.insert(0, "dr_momentum_bot")
from dr_universe import DR_COVERED_EXPANDED as DR_95
from test_asia_expansion_momentum import (sim, load_converted_mixed, THB_PER_USD, THB_PER_JPY,
                                            THB_PER_HKD, THB_PER_SGD, THB_PER_CNY)

with open("us_close_10y_cache.pkl", "rb") as f:
    us_data = pickle.load(f)
prep = teo.precompute(us_data)
prep = add_extra_signals(prep)
us_syms = [s for s in DR_95 if s in prep]
us_price_lookup = {s: prep[s]["close"] * THB_PER_USD for s in us_syms}

japan_lookup = load_converted_mixed("japan_dr_10y_cache.pkl", THB_PER_JPY, THB_PER_CNY)
hk_lookup = load_converted_mixed("hk_china_dr_10y_cache.pkl", THB_PER_HKD, THB_PER_CNY)
sg_lookup = load_converted_mixed("singapore_dr_10y_cache.pkl", THB_PER_SGD, THB_PER_CNY)
asia_lookup = {}
asia_lookup.update(japan_lookup); asia_lookup.update(hk_lookup); asia_lookup.update(sg_lookup)
global_lookup = dict(us_price_lookup); global_lookup.update(asia_lookup)

us_syms_order = list(us_price_lookup.keys())
global_syms_order = list(global_lookup.keys())

WINDOW_DAYS = 504
STEP_DAYS = 42

common_dates = sorted(
    set().union(*[us_price_lookup[s].index for s in us_syms_order]) &
    set().union(*[global_lookup[s].index for s in global_syms_order])
)
n = len(common_dates)
windows = []
start = 0
while start + WINDOW_DAYS <= n:
    windows.append(common_dates[start:start + WINDOW_DAYS])
    start += STEP_DAYS
print(f"ทั้งหมด {len(windows)} หน้าต่าง")

for top_n in [3, 5]:
    wins, diffs = 0, []
    for w in windows:
        r_us = sim(us_price_lookup, us_syms_order, w, top_n)["ret_pct"]
        r_gl = sim(global_lookup, global_syms_order, w, top_n)["ret_pct"]
        diff = r_gl - r_us
        diffs.append(diff)
        if r_gl > r_us:
            wins += 1
    n_win = len(windows)
    third = n_win // 3
    early, mid, late = diffs[:third], diffs[third:2*third], diffs[2*third:]
    print(f"\ntop_n={top_n}: US+เอเชีย ชนะ {wins}/{n_win} ({100*wins/n_win:.0f}%), "
          f"เฉลี่ย {sum(diffs)/len(diffs):+.1f}pp, median {statistics.median(diffs):+.1f}pp")
    print(f"  ช่วงต้น: {sum(early)/len(early):+.1f}pp ({sum(1 for d in early if d>0)}/{len(early)} ชนะ)")
    print(f"  ช่วงกลาง: {sum(mid)/len(mid):+.1f}pp ({sum(1 for d in mid if d>0)}/{len(mid)} ชนะ)")
    print(f"  ช่วงล่าสุด: {sum(late)/len(late):+.1f}pp ({sum(1 for d in late if d>0)}/{len(late)} ชนะ)")
