#!/usr/bin/env python
"""
เทส universe ขยายจาก 95 -> 159 ตัว (เพิ่ม 64 ตัวใหม่จากลิสต์ DR สหรัฐฯ เต็ม 149 ตัวที่ผู้ใช้ส่งมา
เอาไปเทียบกับ 95 ตัวเดิม ทั้ง single-split และ robust rolling-window
"""
import pickle, sys
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
NEW_UNIQUE = [t for t in NEW_64 if t not in set(DR_95)]  # กัน dup (V/COST/NKE/EL/BRK-B ซ้ำกับ 95 เดิม)
DR_159 = DR_95 + NEW_UNIQUE

with open("us_close_10y_cache.pkl", "rb") as f:
    data = pickle.load(f)
prep = teo.precompute(data)
prep = add_extra_signals(prep)

for label, syms_full in [("95 เดิม", DR_95), (f"{len(DR_159)} ขยาย (95+{len(NEW_UNIQUE)} ใหม่ ไม่ซ้ำ)", DR_159)]:
    syms_order = [s for s in syms_full if s in prep]
    print(f"\n{'='*100}\n{label}: {len(syms_order)}/{len(syms_full)} มีข้อมูลราคา\n{'='*100}")

    all_dates = sorted(set().union(*[prep[s]["close"].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]
    dates_2022 = [d for d in all_dates if d.year == 2022]

    for top_n in [3, 5]:
        results = {}
        for period, dates in [("ALL", all_dates), ("TRAIN", train_dates), ("VALID", valid_dates),
                               ("TEST", test_dates_), ("2022", dates_2022)]:
            m = sim_cross_sectional_momentum(prep, syms_order, dates, top_n, 1_000_000)
            results[period] = m
        print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+9.1f}%  TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  "
              f"VALID:{results['VALID']['ret_pct']:+8.1f}%  TEST:{results['TEST']['ret_pct']:+8.1f}%  "
              f"2022:{results['2022']['ret_pct']:+8.1f}%")
