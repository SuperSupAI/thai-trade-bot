#!/usr/bin/env python
"""
Robust rolling-window test: 95 เดิม vs 153 ขยาย (95+58 ใหม่จากลิสต์ DR สหรัฐฯ เต็มที่ผู้ใช้ส่งมา)
ใช้หน้าต่าง 2 ปีเหลื่อมกันทั่วประวัติศาสตร์ ตามระเบียบวิธีที่ใช้มาตลอดในโปรเจกต์นี้
"""
import pickle, sys
import pandas as pd
sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum import sim_cross_sectional_momentum
sys.path.insert(0, "dr_momentum_bot")
from dr_universe import DR_COVERED_EXPANDED as DR_95

NEW_64 = ['ABNB', 'AFRM', 'ALAB', 'AMGN', 'AMKR', 'ANET', 'APLD', 'APP', 'AXP', 'BA', 'BKSY', 'BRK-B',
          'CAT', 'CDNS', 'CIEN', 'COIN', 'COST', 'CRDO', 'CRSP', 'CRWV', 'DASH', 'DG', 'EL', 'EXPE',
          'FN', 'FSLR', 'FWONK', 'GEV', 'GFS', 'GLW', 'GOOG', 'GRAB', 'IBM', 'INTC', 'IONQ', 'MPWR',
          'MRAM', 'NBIS', 'NET', 'NKE', 'NVTS', 'OKLO', 'ON', 'ONDS', 'OXY', 'PLAB', 'PG', 'PWR',
          'STX', 'SHOP', 'SMR', 'SOFI', 'STM', 'SYM', 'SNPS', 'TER', 'TRV', 'TSEM', 'USAR', 'V',
          'VRT', 'VST', 'WMT']
NEW_UNIQUE = [t for t in NEW_64 if t not in set(DR_95)]
DR_153 = DR_95 + NEW_UNIQUE

with open("us_close_10y_cache.pkl", "rb") as f:
    data = pickle.load(f)
prep = teo.precompute(data)
prep = add_extra_signals(prep)

TOP_N = 3
WINDOW_DAYS = 504   # ~2 ปีเทรด
STEP_DAYS = 42      # เลื่อนทีละ ~2 เดือน

def run(syms_full, dates):
    syms_order = [s for s in syms_full if s in prep]
    m = sim_cross_sectional_momentum(prep, syms_order, dates, TOP_N, 1_000_000)
    return m["ret_pct"]

all_dates_95 = sorted(set().union(*[prep[s]["close"].index for s in DR_95 if s in prep]))
all_dates_153 = sorted(set().union(*[prep[s]["close"].index for s in DR_153 if s in prep]))
# ใช้วันที่ร่วมกันทั้งสอง universe (intersection) เพื่อเทียบ apples-to-apples ในหน้าต่างเดียวกันทุกครั้ง
common_dates = sorted(set(all_dates_95) & set(all_dates_153))

n = len(common_dates)
windows = []
start = 0
while start + WINDOW_DAYS <= n:
    windows.append(common_dates[start:start + WINDOW_DAYS])
    start += STEP_DAYS

print(f"ทั้งหมด {len(windows)} หน้าต่าง (แต่ละหน้าต่าง ~{WINDOW_DAYS} วันเทรด, เลื่อนทีละ {STEP_DAYS} วัน)")

rows = []
wins_153 = 0
diffs = []
for idx, w in enumerate(windows):
    r95 = run(DR_95, w)
    r153 = run(DR_153, w)
    diff = r153 - r95
    diffs.append(diff)
    if r153 > r95:
        wins_153 += 1
    rows.append(dict(window=idx, start=w[0], end=w[-1], ret_95=r95, ret_153=r153, diff=diff))

df = pd.DataFrame(rows)
df.to_csv("dr_153_rolling_robust_results.csv", index=False)

n_win = len(windows)
print(f"\n153 ขยาย ชนะ 95 เดิม: {wins_153}/{n_win} หน้าต่าง ({100*wins_153/n_win:.0f}%)")
print(f"outperformance เฉลี่ย: {sum(diffs)/len(diffs):+.1f}pp")
import statistics
print(f"outperformance median: {statistics.median(diffs):+.1f}pp")

third = n_win // 3
early = diffs[:third]
mid = diffs[third:2*third]
late = diffs[2*third:]
print(f"\nช่วงต้น ({len(early)} หน้าต่าง): เฉลี่ย {sum(early)/len(early):+.1f}pp, ชนะ {sum(1 for d in early if d>0)}/{len(early)}")
print(f"ช่วงกลาง ({len(mid)} หน้าต่าง): เฉลี่ย {sum(mid)/len(mid):+.1f}pp, ชนะ {sum(1 for d in mid if d>0)}/{len(mid)}")
print(f"ช่วงล่าสุด ({len(late)} หน้าต่าง): เฉลี่ย {sum(late)/len(late):+.1f}pp, ชนะ {sum(1 for d in late if d>0)}/{len(late)}")

print("\n" + "="*80)
print("เช็คซ้ำที่ top_n=5")
print("="*80)
TOP_N = 5
def run5(syms_full, dates):
    syms_order = [s for s in syms_full if s in prep]
    m = sim_cross_sectional_momentum(prep, syms_order, dates, TOP_N, 1_000_000)
    return m["ret_pct"]

wins_153_5 = 0
diffs5 = []
for w in windows:
    r95 = run5(DR_95, w)
    r153 = run5(DR_153, w)
    diff = r153 - r95
    diffs5.append(diff)
    if r153 > r95:
        wins_153_5 += 1

print(f"top_n=5: 153 ขยาย ชนะ 95 เดิม: {wins_153_5}/{n_win} หน้าต่าง ({100*wins_153_5/n_win:.0f}%)")
print(f"outperformance เฉลี่ย: {sum(diffs5)/len(diffs5):+.1f}pp, median: {statistics.median(diffs5):+.1f}pp")
third5_e, third5_m, third5_l = diffs5[:third], diffs5[third:2*third], diffs5[2*third:]
print(f"ช่วงต้น: เฉลี่ย {sum(third5_e)/len(third5_e):+.1f}pp, ชนะ {sum(1 for d in third5_e if d>0)}/{len(third5_e)}")
print(f"ช่วงกลาง: เฉลี่ย {sum(third5_m)/len(third5_m):+.1f}pp, ชนะ {sum(1 for d in third5_m if d>0)}/{len(third5_m)}")
print(f"ช่วงล่าสุด: เฉลี่ย {sum(third5_l)/len(third5_l):+.1f}pp, ชนะ {sum(1 for d in third5_l if d>0)}/{len(third5_l)}")
