#!/usr/bin/env python
"""
ต่อยอดจาก test_capital_sensitivity.py — วัดว่า "เงินว่าง" (ไม่ได้ลงทุน) อยู่กี่ % ของเวลา
ในแต่ละระดับทุน (10000/20000/50000/80000/100000 บาท) ด้วยสูตรเดียวกัน
(E3 TrendMACD + TP12/SL15 + 10 ไม้)

วัด 2 มุม:
  - % เงินสดเฉลี่ย (เทียบมูลค่าพอร์ตรวม) ตลอดช่วงทดสอบ — ยิ่งสูง = เงินว่างเยอะ
  - % วันที่มีช่องไม้ว่าง (ไม่ครบ 10 ไม้) — ยิ่งสูง = โอกาสลงทุนไม่ถูกใช้เต็มที่
"""
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from universe import US_STOCKS

CAPITAL_LEVELS = [10_000, 20_000, 50_000, 80_000, 100_000]
SLOTS = 10
FEE = teo.FEE
THB_PER_USD = teo.THB_PER_USD


def simulate_with_idle(prep, syms_order, test_dates, entry_key, exit_cfg, slots, capital_thb):
    """เหมือน teo.simulate() แต่บันทึกสัดส่วนเงินสด/ช่องว่างในแต่ละวันเพิ่มด้วย"""
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / slots
    cash = capital_usd
    positions = {}
    trades = []
    skipped_price = 0
    equity = []
    cash_pct_series = []
    slots_used_series = []
    trail_n = exit_cfg["trail_ema"]

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            exit_now = False
            if chg <= -exit_cfg["sl"]:
                exit_now = True
            elif exit_cfg["tp"] is not None and chg >= exit_cfg["tp"]:
                exit_now = True
            elif trail_n and price < float(P["emas"][trail_n].loc[dt]):
                exit_now = True
            if exit_now:
                cash += pos["qty"] * price * (1 - FEE)
                trades.append(chg - 2 * FEE)
                del positions[sym]

        if len(positions) < slots:
            for sym in syms_order:
                if len(positions) >= slots:
                    break
                if sym in positions or sym not in prep:
                    continue
                P = prep[sym]
                if dt not in P["close"].index or not bool(P["entries"][entry_key].loc[dt]):
                    continue
                price = float(P["close"].loc[dt])
                budget = min(pos_size, cash)
                qty = int((budget * (1 - FEE)) / price)
                if qty < 1:
                    skipped_price += 1
                    continue
                cash -= qty * price * (1 + FEE)
                positions[sym] = dict(qty=qty, entry_price=price)

        val = cash
        for sym, pos in positions.items():
            series = prep[sym]["close"]
            px = float(series.loc[dt]) if dt in series.index else float(series[series.index <= dt].iloc[-1])
            val += pos["qty"] * px
        equity.append(val)
        cash_pct_series.append(cash / val * 100 if val > 0 else 100.0)
        slots_used_series.append(len(positions))

    eq = pd.Series(equity)
    final = eq.iloc[-1] if len(eq) else capital_usd
    wins = sum(1 for t in trades if t > 0)
    cash_pct = pd.Series(cash_pct_series)
    slots_used = pd.Series(slots_used_series)
    return dict(
        trades=len(trades),
        wr=round(wins / len(trades) * 100, 1) if trades else float("nan"),
        ret_pct=round((final / capital_usd - 1) * 100, 1),
        skip=skipped_price,
        avg_cash_pct=round(cash_pct.mean(), 1),
        pct_days_slots_not_full=round((slots_used < slots).mean() * 100, 1),
        avg_slots_used=round(slots_used.mean(), 1),
        pct_days_zero_positions=round((slots_used == 0).mean() * 100, 1),
    )


def main():
    data = teo.load_data()
    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    test_dates = all_dates[-252:]
    print(f"หน้าต่างทดสอบ: {test_dates[0].date()} → {test_dates[-1].date()}")
    print(f"สูตร: E3 TrendMACD + TP12/SL15 + {SLOTS} ไม้\n")

    rows = []
    for capital in CAPITAL_LEVELS:
        m = simulate_with_idle(prep, syms_order, test_dates, "E3 TrendMACD", exits["TP12/SL15"], SLOTS, capital)
        rows.append(dict(ทุน_บาท=capital, **m))
        print(f"ทุน {capital:>7,} บาท → ผลตอบแทน {m['ret_pct']:+6.1f}%  ·  "
              f"เงินสดเฉลี่ย {m['avg_cash_pct']:5.1f}%  ·  "
              f"วันที่ช่องไม้ไม่เต็ม {m['pct_days_slots_not_full']:5.1f}%  ·  "
              f"ไม้เฉลี่ยที่ถือ {m['avg_slots_used']:4.1f}/{SLOTS}  ·  "
              f"วันไม่ถือเลย {m['pct_days_zero_positions']:5.1f}%")

    df = pd.DataFrame(rows)
    df.to_csv("capital_idle_time_results.csv", index=False)
    print("\n" + "=" * 100)
    print(df.to_string(index=False))
    print("\nบันทึกไว้ที่ capital_idle_time_results.csv")


if __name__ == "__main__":
    main()
