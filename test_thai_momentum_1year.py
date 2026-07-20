#!/usr/bin/env python
"""
Cross-sectional momentum บนหุ้นไทย 75 ตัว ย้อนหลัง 1 ปีเต็ม ทุน 10,000 บาท
พร้อมแสดงว่าหุ้นตัวไหนถูกเลือกเข้าพอร์ตบ้างในแต่ละรอบ rebalance
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from test_thai_cross_sectional_momentum import sim_cross_sectional_momentum_thb, FORMATION, SKIP, REBAL

CACHE_FILE = "thai_stocks_10y_cache.pkl"
CAPITAL_THB = 10_000


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    syms_order = sorted(data.keys())
    all_dates = sorted(set().union(*[c.index for c in data.values()]))
    year_dates = all_dates[-252:]

    print(f"หุ้นไทยที่ใช้ได้: {len(syms_order)} ตัว")
    print(f"ช่วง 1 ปีล่าสุด: {year_dates[0].date()} -> {year_dates[-1].date()}")
    print(f"ทุน {CAPITAL_THB:,} บาท\n")

    print("=" * 90)
    print("ผลตอบแทน 1 ปี")
    print("=" * 90)
    for top_n in [3, 5, 10]:
        m = sim_cross_sectional_momentum_thb(data, syms_order, year_dates, top_n, capital_thb=CAPITAL_THB)
        print(f"top_n={top_n:2d}: {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:3d}  WR {m['wr']:5.1f}%")

    print("\n" + "=" * 90)
    print("หุ้นที่ถูกเลือกเข้า top 5 ในแต่ละรอบ rebalance ตลอด 1 ปีที่ผ่านมา")
    print("=" * 90)
    rebal_dates = year_dates[::REBAL]
    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            close = data[sym]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            if i < FORMATION:
                continue
            p_now = close.iloc[i - SKIP]
            p_start = close.iloc[i - FORMATION]
            if p_start <= 0:
                continue
            scores.append((sym, p_now / p_start - 1))
        scores.sort(key=lambda x: x[1], reverse=True)
        top5 = [f"{s.replace('.BK','')}({r*100:+.0f}%)" for s, r in scores[:5]]
        print(f"  {dt.date()}: {', '.join(top5)}")


if __name__ == "__main__":
    main()
