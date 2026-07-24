#!/usr/bin/env python
"""
Robust rolling-window: momentum top3 รายชั่วโมง vs equal-weight buy&hold บนหุ้นไทย 75 ตัว
หน้าต่าง ~500 แท่งชั่วโมง (~2.5 เดือน) เลื่อนทีละ 100 แท่ง (~2-3 สัปดาห์) ทั่วประวัติศาสตร์ 2 ปี
"""
import pickle, sys
import statistics
sys.path.insert(0, ".")
from test_thai_hourly_momentum import sim, FORMATION, SKIP, REBAL

with open("thai_hourly_2y_cache.pkl", "rb") as f:
    data = pickle.load(f)
syms_order = list(data.keys())
all_dates = sorted(set().union(*[data[s].index for s in syms_order]))
n = len(all_dates)

WINDOW = 500
STEP = 100
windows = []
start = 0
while start + WINDOW <= n:
    windows.append(all_dates[start:start + WINDOW])
    start += STEP
print(f"ทั้งหมด {len(windows)} หน้าต่าง (~{WINDOW} แท่ง/หน้าต่าง)")

def bh_ret(dates):
    total = 0
    for s in syms_order:
        c = data[s]
        avail = c.reindex(dates).dropna()
        if len(avail) < 2:
            continue
        total += float(avail.iloc[-1]) / float(avail.iloc[0])
    return (total / len(syms_order) - 1) * 100

for top_n in [3, 5]:
    wins, diffs = 0, []
    for w in windows:
        r_mom = sim(data, syms_order, w, top_n)["ret_pct"]
        r_bh = bh_ret(w)
        diff = r_mom - r_bh
        diffs.append(diff)
        if r_mom > r_bh:
            wins += 1
    n_win = len(windows)
    third = n_win // 3
    early, mid, late = diffs[:third], diffs[third:2*third], diffs[2*third:]
    print(f"\ntop_n={top_n}: momentum ชนะ buy&hold {wins}/{n_win} หน้าต่าง ({100*wins/n_win:.0f}%), "
          f"เฉลี่ย {sum(diffs)/len(diffs):+.1f}pp, median {statistics.median(diffs):+.1f}pp")
    print(f"  ช่วงต้น: {sum(early)/len(early):+.1f}pp ({sum(1 for d in early if d>0)}/{len(early)} ชนะ)")
    print(f"  ช่วงกลาง: {sum(mid)/len(mid):+.1f}pp ({sum(1 for d in mid if d>0)}/{len(mid)} ชนะ)")
    print(f"  ช่วงล่าสุด: {sum(late)/len(late):+.1f}pp ({sum(1 for d in late if d>0)}/{len(late)} ชนะ)")
