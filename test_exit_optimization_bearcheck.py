#!/usr/bin/env python
"""
เช็คความทนทานของผู้ชนะจาก grid search (E3 TrendMACD + Trail EMA100 + 10 ไม้) กับสูตรเทียบอื่นๆ
บนหน้าต่างเวลาที่ยังไม่เคยทดสอบเลย — ใช้ข้อมูลที่มี (cache 4 ปี) แบ่งได้ 4 หน้าต่างไม่ทับกัน:
  W1 2022-07-11 → 2023-07-11  (ตลาดยังผันผวนหนักจากดอกเบี้ยขึ้น + เพิ่งพ้นจุดต่ำสุด ต.ค. 2022)
  W2 2023-07-12 → 2024-07-11
  W3 2024-07-12 → 2025-07-15  (TRAIN เดิม)
  W4 2025-07-16 → 2026-07-10  (TEST เดิม)
เน้น W1/W2 ที่ยังไม่เคยดูเลยตอน optimize — โดยเฉพาะ W1 ที่ใกล้เคียงช่วงตลาดขาลง/ผันผวนที่สุดที่มีข้อมูล
"""
import sys
import pandas as pd

sys.path.insert(0, ".")
from test_exit_optimization import load_data, precompute, simulate, buy_hold_return, build_exit_grid
from universe import US_STOCKS

CHECK_COMBOS = [
    ("E3 TrendMACD", "Trail EMA100", 10, "ผู้ชนะจาก grid search (train+test +17%)"),
    ("E3 TrendMACD", "TP12/SL15", 10, "อันดับ 2 จาก grid search"),
    ("E1 StackNewHigh", "TP5/SL10", 10, "สูตรบอทปัจจุบัน (E1+TP5/SL10)"),
    ("E1 StackNewHigh", "Trail EMA50", 10, "trailing แบบเดิมที่เคยดูรอบก่อน"),
]


def main():
    data = load_data()
    prep = precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    windows = {
        "W1 2022-23 (ผันผวน/เพิ่งพ้นจุดต่ำสุด)": all_dates[0:252],
        "W2 2023-24": all_dates[252:504],
        "W3 2024-25 (TRAIN เดิม)": all_dates[504:756],
        "W4 2025-26 (TEST เดิม)": all_dates[756:],
    }

    rows = []
    for wname, dates in windows.items():
        if len(dates) < 100:
            continue
        bh = buy_hold_return(prep, dates)
        print(f"\n{wname}: {dates[0].date()} → {dates[-1].date()} · B&H {bh:+.1f}%")
        for entry_key, exit_name, slots, label in CHECK_COMBOS:
            m = simulate(prep, syms_order, dates, entry_key, exits[exit_name], slots)
            rows.append(dict(window=wname, bh=bh, combo=label, entry=entry_key, exit=exit_name,
                             slots=slots, **m))
            print(f"  {label:45s} → ret {m['ret_pct']:+6.1f}%  wr {m['wr']:5.1f}%  "
                  f"maxdd {m['maxdd_pct']:6.1f}%  trades {m['trades']:3d}")

    df = pd.DataFrame(rows)
    df.to_csv("exit_optimization_bearcheck_results.csv", index=False)

    print("\n" + "=" * 100)
    print("สรุป: ผลตอบแทนแต่ละคอมโบ ข้ามทั้ง 4 หน้าต่าง (แถว = คอมโบ, คอลัมน์ = หน้าต่างเวลา)")
    print("=" * 100)
    pivot = df.pivot_table(values="ret_pct", index="combo", columns="window", aggfunc="first")
    pivot["เฉลี่ย"] = pivot.mean(axis=1).round(1)
    pivot["แย่สุด"] = pivot.min(axis=1)
    print(pivot.round(1).to_string())


if __name__ == "__main__":
    main()
