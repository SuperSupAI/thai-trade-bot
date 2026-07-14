#!/usr/bin/env python
"""รายละเอียดเต็มของ E4+Exit F 5 ไม้ (ตัวชนะ SPY) — log ทุกไม้ + ติดตามจำนวนไม้ที่ถือจริงแต่ละวัน"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 100_000
TARGET_SLOTS = 5
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.20


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))

    capital_usd = CAPITAL_THB / THB_PER_USD
    pos_size = capital_usd / TARGET_SLOTS
    cash = capital_usd
    positions = {}
    trades = []
    n_positions_series = []

    for dt in all_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            ema200 = float(P["emas"][200].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1

            exit_now, reason = False, None
            if chg <= -HARD_SL:
                exit_now, reason = True, "Hard SL -20%"
            elif price < ema200:
                exit_now, reason = True, "หลุด EMA200"

            if exit_now:
                proceeds = pos["qty"] * price * (1 - FEE)
                cash += proceeds
                trades.append(dict(
                    symbol=sym, entry_date=pos["entry_date"], entry_price=pos["entry_price"],
                    exit_date=dt, exit_price=price, reason=reason,
                    pnl_pct=round(chg * 100, 1),
                    pnl_usd=round(proceeds - pos["qty"] * pos["entry_price"] * (1 + FEE), 2),
                    hold_days=(dt - pos["entry_date"]).days,
                    qty=pos["qty"],
                ))
                del positions[sym]

        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E4_Simple200"].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=qty, entry_price=price, entry_date=dt)

        n_positions_series.append(len(positions))

    val = cash
    open_positions = []
    for sym, pos in positions.items():
        last_price = float(prep[sym]["close"].iloc[-1])
        val += pos["qty"] * last_price
        open_positions.append(dict(symbol=sym, entry_date=pos["entry_date"], entry_price=pos["entry_price"],
                                   last_price=last_price, unrealized_pct=round((last_price/pos["entry_price"]-1)*100, 1)))

    trades_df = pd.DataFrame(trades)
    trades_df.to_csv("e4_exitf_5slots_all_trades.csv", index=False)

    n_pos = pd.Series(n_positions_series)
    print(f"ช่วงทดสอบ: {all_dates[0].date()} → {all_dates[-1].date()} ({len(all_dates)} วันเทรด)")
    print(f"ทุนเริ่มต้น {CAPITAL_THB:,} บาท · เงินต่อไม้เป้าหมาย {pos_size*THB_PER_USD:,.0f} บาท (ทุน/{TARGET_SLOTS})\n")

    print("=" * 80)
    print("จำนวนไม้ที่ถือจริงแต่ละวัน (ไม่ได้ล็อกที่ 5 ตายตัว — เป็นแค่ 'เงินต่อไม้เป้าหมาย')")
    print("=" * 80)
    print(f"เฉลี่ย {n_pos.mean():.1f} ไม้ · สูงสุด {n_pos.max()} ไม้ · ต่ำสุด {n_pos.min()} ไม้ · "
          f"มัธยฐาน {n_pos.median():.0f} ไม้")

    wins = trades_df[trades_df.pnl_pct > 0]
    losses = trades_df[trades_df.pnl_pct <= 0]
    print("\n" + "=" * 80)
    print(f"สถิติไม้ที่ปิดแล้วทั้งหมด: {len(trades_df)} ไม้")
    print("=" * 80)
    print(f"ชนะ {len(wins)} ไม้ ({len(wins)/len(trades_df)*100:.1f}%) · แพ้ {len(losses)} ไม้ ({len(losses)/len(trades_df)*100:.1f}%)")
    print(f"กำไรเฉลี่ยไม้ที่ชนะ: {wins.pnl_pct.mean():+.1f}% (มัธยฐาน {wins.pnl_pct.median():+.1f}%)")
    print(f"ขาดทุนเฉลี่ยไม้ที่แพ้: {losses.pnl_pct.mean():+.1f}% (มัธยฐาน {losses.pnl_pct.median():+.1f}%)")
    print(f"ถือยาวสุด (ไม้ที่ชนะ): {wins.hold_days.max()} วัน · ถือเฉลี่ย (ชนะ): {wins.hold_days.mean():.0f} วัน")
    print(f"ถือเฉลี่ย (แพ้): {losses.hold_days.mean():.0f} วัน")
    print(f"เหตุออก: {trades_df.reason.value_counts().to_dict()}")

    print("\n" + "=" * 80)
    print("TOP 15 ไม้ที่กำไรสูงสุด (ตัวที่ทำให้กลยุทธ์นี้ชนะ SPY)")
    print("=" * 80)
    top15 = trades_df.sort_values("pnl_pct", ascending=False).head(15)
    print(top15[["symbol", "entry_date", "entry_price", "exit_date", "exit_price", "pnl_pct", "hold_days", "reason"]].to_string(index=False))

    print("\n" + "=" * 80)
    print("TOP 10 ไม้ที่ขาดทุนหนักสุด")
    print("=" * 80)
    bot10 = trades_df.sort_values("pnl_pct").head(10)
    print(bot10[["symbol", "entry_date", "entry_price", "exit_date", "exit_price", "pnl_pct", "hold_days", "reason"]].to_string(index=False))

    print("\n" + "=" * 80)
    print("หุ้นที่เข้าเทรดบ่อยสุด 10 อันดับ (นับทุกครั้งที่เข้า)")
    print("=" * 80)
    print(trades_df.symbol.value_counts().head(10).to_string())

    if open_positions:
        print("\n" + "=" * 80)
        print(f"ไม้ที่ยังถืออยู่ตอนจบ ({len(open_positions)} ตัว)")
        print("=" * 80)
        print(pd.DataFrame(open_positions).to_string(index=False))

    final_thb = val * THB_PER_USD
    print(f"\nมูลค่าสุดท้าย: {final_thb:,.0f} บาท (ผลตอบแทน {(val/capital_usd-1)*100:+.1f}%)")
    print("บันทึกทุกไม้ไว้ที่ e4_exitf_5slots_all_trades.csv")


if __name__ == "__main__":
    main()
