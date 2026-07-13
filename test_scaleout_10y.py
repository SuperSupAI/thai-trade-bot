#!/usr/bin/env python
"""
เอาแบบ B (50/50+trail8%) และ C (50/50+breakeven+ratchet) จาก test_scaleout_variants.py
ไปทดสอบเต็ม 10 ปี ทุนก้อนเดียว 100,000 บาท เทียบกับ SPY B&H และ baseline A (TP12/SL15)
เดิมที่เคยเทสไว้แล้ว (test_10y_vs_spy.py): A = +227.4% (327,366 บาท) · SPY = +315.3% (415,317 บาท)
ใช้ cache 10 ปีเดิม (us_close_10y_cache.pkl, spy_10y_cache.pkl) ไม่ต้องโหลดใหม่
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_scaleout_variants import sim_variant
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
CAPITAL_THB = 100_000
THB_PER_USD = teo.THB_PER_USD

# ผลเดิมที่เทสไว้แล้วรอบก่อน (test_10y_vs_spy.py) — เอามาโชว์เทียบกันในตารางเดียว
KNOWN_RESULTS = {
    "SPY Buy & Hold": dict(ret_pct=315.3, final_thb=415_317),
    "A) Baseline TP12%/SL15% (เดิม)": dict(ret_pct=227.4, final_thb=327_366),
}


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"ใช้ cache เดิม: {len(data)} หุ้น")

    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบเต็ม: {all_dates[0].date()} → {all_dates[-1].date()} ({len(all_dates)} วันเทรด)")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท · entry E3 TrendMACD · ไม่จำกัดไม้ (target 10)\n")

    rows = []
    for key, label in [("SPY Buy & Hold", None), ("A) Baseline TP12%/SL15% (เดิม)", None)]:
        m = KNOWN_RESULTS[key]
        rows.append(dict(variant=key, ret_pct=m["ret_pct"], final_thb=m["final_thb"]))
        print(f"{key:45s} → ผลตอบแทน {m['ret_pct']:+7.1f}%  ·  มูลค่าสุดท้าย {m['final_thb']:>10,} บาท  (ผลเดิม)")

    for v, label in [("B_5050_trail8", "B) 50%@+10% + trail -8% จาก peak"),
                     ("C_5050_breakeven_ratchet", "C) 50%@+10% + breakeven + ratchet")]:
        m = sim_variant(prep, syms_order, all_dates, v, capital_thb=CAPITAL_THB, target_slots=10)
        final_thb = CAPITAL_THB * (1 + m["ret_pct"] / 100)
        rows.append(dict(variant=label, ret_pct=m["ret_pct"], final_thb=round(final_thb),
                         full_exits=m["full_exits"], wr_full_exit=m["wr_full_exit"]))
        print(f"{label:45s} → ผลตอบแทน {m['ret_pct']:+7.1f}%  ·  มูลค่าสุดท้าย {final_thb:>10,.0f} บาท  ·  "
              f"ไม้ปิดหมด {m['full_exits']:4d}  ·  win rate {m['wr_full_exit']:5.1f}%")

    df = pd.DataFrame(rows)
    df.to_csv("scaleout_10y_vs_spy_results.csv", index=False)

    print("\n" + "=" * 80)
    print("สรุปเรียงจากดีสุด → แย่สุด")
    print("=" * 80)
    print(df.sort_values("ret_pct", ascending=False)[["variant", "ret_pct", "final_thb"]].to_string(index=False))


if __name__ == "__main__":
    main()
