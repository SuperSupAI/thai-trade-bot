#!/usr/bin/env python
"""
รัน cross-sectional momentum ใหม่ จำกัด universe เหลือแค่ 21 หุ้นที่มี DR ซื้อขายได้จริงบน SET
(เช็คจากรายชื่อ DR จริง ณ 19 ม.ค. 2026 เทียบกับ US_STOCKS 77 ตัวเดิม)
ผลลัพธ์นี้ = ผลตอบแทนที่ "เป็นไปได้จริง" ถ้าซื้อผ่าน DR แทนหุ้นสหรัฐฯ ตรงๆ (ไม่มีภาษีเลย)
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum import sim_cross_sectional_momentum

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000

DR_COVERED = ["AAPL", "MSFT", "JPM", "V", "UNH", "KO", "CSCO", "CRM", "GS", "JNJ",
              "DIS", "NKE", "GOOGL", "AMZN", "META", "NVDA", "PFE", "COST", "PEP", "ADBE", "LULU"]


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in DR_COVERED if s in prep]
    print(f"หุ้นที่มี DR และมีข้อมูลราคา: {len(syms_order)}/{len(DR_COVERED)} ตัว -> {syms_order}\n")

    all_dates = sorted(set().union(*[prep[s]["close"].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"ทั้งชุด: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"TRAIN: {train_dates[0].date()} -> {train_dates[-1].date()}")
    print(f"VALID: {valid_dates[0].date()} -> {valid_dates[-1].date()}")
    print(f"TEST : {test_dates_[0].date()} -> {test_dates_[-1].date()}")
    print(f"ทุนก้อนเดียวรีเซ็ตใหม่ทุกช่วง {CAPITAL_THB:,} บาท (ไม่มีภาษีเลยเพราะเป็น DR)\n")

    rows = []
    print("=" * 100)
    print(f"{'top_n':>6s}  {'ALL 10 ปี':>26s}  {'TRAIN':>26s}  {'VALID':>26s}  {'TEST':>26s}")
    print("=" * 100)
    for top_n in [3, 5, 10]:
        m_all = sim_cross_sectional_momentum(prep, syms_order, all_dates, top_n, capital_thb=CAPITAL_THB)
        m_train = sim_cross_sectional_momentum(prep, syms_order, train_dates, top_n, capital_thb=CAPITAL_THB)
        m_valid = sim_cross_sectional_momentum(prep, syms_order, valid_dates, top_n, capital_thb=CAPITAL_THB)
        m_test = sim_cross_sectional_momentum(prep, syms_order, test_dates_, top_n, capital_thb=CAPITAL_THB)

        def fmt(m):
            return f"{m['ret_pct']:+7.1f}% (n={m['trades']:3d},WR{m['wr']:5.1f}%)"

        print(f"{top_n:>6d}  {fmt(m_all):>26s}  {fmt(m_train):>26s}  {fmt(m_valid):>26s}  {fmt(m_test):>26s}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(top_n=top_n, period=period, **m))

    print("\n=== เทียบกับ RMF หลังภาษี (+320.8%) และเวอร์ชั่นหุ้นสหรัฐฯ 76 ตัวเต็ม (ALL=+4,479.6% pretax) ===")
    pd.DataFrame(rows).to_csv("cross_sectional_momentum_dr_universe_results.csv", index=False)
    print("บันทึกไว้ที่ cross_sectional_momentum_dr_universe_results.csv")


if __name__ == "__main__":
    main()
