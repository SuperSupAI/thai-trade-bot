#!/usr/bin/env python
"""
ทดสอบว่าทุนเริ่มต้น (10000/20000/50000/80000/100000 บาท) มีผลต่อผลตอบแทน% หรือไม่
ใช้สูตรปัจจุบันของ webull_bot: E3 TrendMACD entry + TP12/SL15 exit + 10 ไม้ (เงินต่อไม้ = ทุน/10)

สมมติฐาน: ถ้าทุนต่อไม้เล็กเกินไป (ซื้อหุ้นแพงไม่ได้แม้ 1 หุ้น) ผลตอบแทน% จะเริ่มต่างจากทุนใหญ่
เพราะพลาดสัญญาณจากหุ้นราคาแพงไปเงียบๆ (เจอปรากฏการณ์นี้มาแล้วตอนทดสอบ 10,000 บาท/ไม้ vs 2,000 บาท/ไม้)
"""
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from universe import US_STOCKS

CAPITAL_LEVELS = [10_000, 20_000, 50_000, 80_000, 100_000]
SLOTS = 10


def main():
    data = teo.load_data()
    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    test_dates = all_dates[-252:]  # ปีล่าสุด
    bh = teo.buy_hold_return(prep, test_dates)
    print(f"หน้าต่างทดสอบ: {test_dates[0].date()} → {test_dates[-1].date()} · B&H เฉลี่ย {bh:+.1f}%")
    print(f"สูตร: E3 TrendMACD + TP12/SL15 + {SLOTS} ไม้ (เงินต่อไม้ = ทุน/{SLOTS})\n")

    rows = []
    for capital in CAPITAL_LEVELS:
        teo.CAPITAL_THB = capital  # override module-level constant ก่อนเรียก simulate()
        m = teo.simulate(prep, syms_order, test_dates, "E3 TrendMACD", exits["TP12/SL15"], SLOTS)
        pos_size = capital / SLOTS
        rows.append(dict(ทุน_บาท=capital, เงินต่อไม้_บาท=round(pos_size), **m))
        print(f"ทุน {capital:>7,} บาท (ไม้ละ {pos_size:>7,.0f} บาท) → "
              f"ผลตอบแทน {m['ret_pct']:+6.1f}%  ·  win rate {m['wr']:5.1f}%  ·  "
              f"ไม้ {m['trades']:3d}  ·  พลาดเพราะเงินไม่พอ {m['skip']:3d}")

    df = pd.DataFrame(rows)
    df.to_csv("capital_sensitivity_results.csv", index=False)

    print("\n" + "=" * 80)
    print("สรุป")
    print("=" * 80)
    print(df.to_string(index=False))

    spread = df["ret_pct"].max() - df["ret_pct"].min()
    print(f"\nส่วนต่างผลตอบแทน% ระหว่างทุนน้อยสุด-มากสุด: {spread:.1f} percentage points")
    if spread < 1.0:
        print("→ ทุนเริ่มต้นแทบไม่มีผลเลย (เงินต่อไม้ทุกระดับซื้อหุ้นในสัญญาณได้ครบ)")
    else:
        print("→ ทุนเริ่มต้นมีผลจริง เพราะเงินต่อไม้เล็กบางระดับพลาดสัญญาณจากหุ้นราคาแพง (ดูคอลัมน์ skip)")


if __name__ == "__main__":
    main()
