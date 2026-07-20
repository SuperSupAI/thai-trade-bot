#!/usr/bin/env python
"""
รอบ 2 ของ hard cap: (1) เพิ่ม cap=1,2 (กระจุกสุดขั้ว) (2) เช็คความเสถียรด้วย TRAIN/VALID/TEST split
เพราะรอบแรก cap=3 ชนะ (+327.9%) แต่ n=68 ไม้เท่านั้น + ผลไม่ mono­tonic (cap=5 แย่กว่า cap=3 และ cap=8)
-- ต้องเช็คว่าเป็น edge จริงหรือแค่โชคหุ้นตัวเดียวในช่วงใดช่วงหนึ่ง
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_hardcap_positions import sim_hardcap
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000
CAPS = [1, 2, 3, 5, 8, 10, 15, 20]


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    n = len(all_dates)

    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates = all_dates[int(n * 0.8):]

    print(f"ทั้งชุด: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"TRAIN: {train_dates[0].date()} -> {train_dates[-1].date()} ({len(train_dates)} วัน)")
    print(f"VALID: {valid_dates[0].date()} -> {valid_dates[-1].date()} ({len(valid_dates)} วัน)")
    print(f"TEST : {test_dates[0].date()} -> {test_dates[-1].date()} ({len(test_dates)} วัน)")
    print(f"ทุนก้อนเดียวรีเซ็ตใหม่ทุกช่วง {CAPITAL_THB:,} บาท\n")

    rows = []
    print("=" * 100)
    print(f"{'cap':>4s}  {'ALL 10 ปี':>28s}  {'TRAIN (6 ปีแรก)':>28s}  {'VALID (2 ปีถัดมา)':>28s}  {'TEST (2 ปีสุดท้าย)':>28s}")
    print("=" * 100)
    for cap in CAPS:
        m_all = sim_hardcap(prep, syms_order, all_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        m_train = sim_hardcap(prep, syms_order, train_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        m_valid = sim_hardcap(prep, syms_order, valid_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        m_test = sim_hardcap(prep, syms_order, test_dates, max_positions=cap, capital_thb=CAPITAL_THB)

        def fmt(m):
            return f"{m['ret_pct']:+7.1f}% (n={m['trades']:3d}, WR{m['wr']:5.1f}%)"

        print(f"{cap:>4d}  {fmt(m_all):>28s}  {fmt(m_train):>28s}  {fmt(m_valid):>28s}  {fmt(m_test):>28s}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(cap=cap, period=period, **m))

    pd.DataFrame(rows).to_csv("hardcap_positions_v2_stability_results.csv", index=False)
    print("\nบันทึกไว้ที่ hardcap_positions_v2_stability_results.csv")


if __name__ == "__main__":
    main()
