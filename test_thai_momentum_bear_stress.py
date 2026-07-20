#!/usr/bin/env python
"""
Stress test cross-sectional momentum บนหุ้นไทย 75 ตัว ผ่านตลาดหมีจริง 2 ครั้ง (ตามธรรมเนียม stress test
ของโปรเจกต์): 2020 (COVID crash) และ 2022 (Fed ขึ้นดอกเบี้ยแรง/ตลาดหุ้นทั่วโลกร่วง)
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from test_thai_cross_sectional_momentum import sim_cross_sectional_momentum_thb, FORMATION, SKIP, REBAL

CACHE_FILE = "thai_stocks_10y_cache.pkl"
CAPITAL_THB = 1_000_000


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    syms_order = sorted(data.keys())
    all_dates = sorted(set().union(*[c.index for c in data.values()]))

    periods = {
        "2020 เต็มปี (COVID crash)": [d for d in all_dates if d.year == 2020],
        "2022 เต็มปี (Fed ขึ้นดอกเบี้ย)": [d for d in all_dates if d.year == 2022],
    }

    rows = []
    for label, dates in periods.items():
        if not dates:
            print(f"{label}: ไม่มีข้อมูลในช่วงนี้")
            continue
        print(f"\n{'='*90}")
        print(f"{label}: {dates[0].date()} -> {dates[-1].date()} ({len(dates)} วัน)")
        print(f"{'='*90}")
        for top_n in [3, 5, 10]:
            m = sim_cross_sectional_momentum_thb(data, syms_order, dates, top_n, capital_thb=CAPITAL_THB)
            print(f"top_n={top_n:2d}: {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:3d}  WR {m['wr']:5.1f}%")
            rows.append(dict(period=label, top_n=top_n, **m))

    # เทียบ B&H equal-weight ทั้งตลาดในช่วงเดียวกัน เป็น baseline
    print(f"\n{'='*90}")
    print("เทียบ Buy&Hold equal-weight ทั้งตลาด (baseline)")
    print(f"{'='*90}")
    for label, dates in periods.items():
        if not dates:
            continue
        rets = []
        for sym in syms_order:
            close = data[sym]
            c = close.reindex(dates).ffill().dropna()
            if len(c) < 2:
                continue
            rets.append(float(c.iloc[-1] / c.iloc[0] - 1))
        if rets:
            avg = sum(rets) / len(rets) * 100
            print(f"{label}: B&H เฉลี่ยเท่ากันทุกตัว = {avg:+.1f}%")
            rows.append(dict(period=label, top_n="B&H_all", ret_pct=round(avg, 1), trades=0, wr=float("nan")))

    pd.DataFrame(rows).to_csv("thai_momentum_bear_stress_results.csv", index=False)
    print("\nบันทึกไว้ที่ thai_momentum_bear_stress_results.csv")


if __name__ == "__main__":
    main()
