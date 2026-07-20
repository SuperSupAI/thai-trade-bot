#!/usr/bin/env python
"""
เทียบ DR universe เดิม (21 ตัว) vs ที่ขยายใหม่ (~47 ตัว, เจอเพิ่มจากการหาข้อมูล DR ล่าสุด ก.ค. 2026)
ใช้ momentum baseline ล้วนๆ (ไม่มี overlay -- เพิ่งพิสูจน์ไปว่า overlay overfit ใช้จริงไม่ได้)
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum import sim_cross_sectional_momentum
from test_cross_sectional_momentum_dr_universe import DR_COVERED as DR_COVERED_OLD

DR_COVERED_NEW_ADDED = [
    "ABBV", "AMD", "AVGO", "BAC", "BDX", "BKNG", "BRK-B", "EL", "ISRG", "LLY",
    "MA", "MELI", "MU", "MNST", "MS", "NDAQ", "NFLX", "ORCL", "PANW", "PLTR",
    "RBLX", "SBUX", "SNOW", "SPOT", "TSLA", "UBER",
]
DR_COVERED_EXPANDED = DR_COVERED_OLD + DR_COVERED_NEW_ADDED

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)

    rows = []
    for label, syms_full in [("DR เดิม (21 ตัว)", DR_COVERED_OLD),
                              ("DR ขยายใหม่ (47 ตัว)", DR_COVERED_EXPANDED)]:
        syms_order = [s for s in syms_full if s in prep]
        print(f"\n{'='*100}")
        print(f"{label}: {len(syms_order)}/{len(syms_full)} ตัวมีข้อมูลราคา")
        print(f"{'='*100}")

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
                m = sim_cross_sectional_momentum(prep, syms_order, dates, top_n, CAPITAL_THB)
                results[period] = m
                rows.append(dict(universe=label, top_n=top_n, period=period, **m))
            print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+8.1f}%(n={results['ALL']['trades']:3d})  "
                  f"TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  VALID:{results['VALID']['ret_pct']:+8.1f}%  "
                  f"TEST:{results['TEST']['ret_pct']:+8.1f}%  2022:{results['2022']['ret_pct']:+8.1f}%")

    pd.DataFrame(rows).to_csv("dr_universe_expanded_comparison_results.csv", index=False)
    print("\nบันทึกไว้ที่ dr_universe_expanded_comparison_results.csv")


if __name__ == "__main__":
    main()
