#!/usr/bin/env python
"""เช็คว่า E4+Exit F (5 ไม้, ผู้ชนะ SPY ตัวใหม่) ทนตลาดหมี 2022 ได้ไหม ก่อนเชื่อผล 10 ปีเต็ม"""
import pickle
import sys

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_beat_spy_v2 import sim_e4_trendexit
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))

    dates_2022 = [d for d in all_dates if d.year == 2022]
    bh_2022 = teo.buy_hold_return(prep, dates_2022)
    print(f"ปี 2022: {dates_2022[0].date()} → {dates_2022[-1].date()} · B&H เฉลี่ยหุ้น US {bh_2022:+.1f}%\n")

    for slots in [5, 10]:
        m = sim_e4_trendexit(prep, syms_order, dates_2022, slots)
        print(f"E4+ExitF {slots} ไม้ ปี 2022 เดี่ยว → {m['ret_pct']:+.1f}%  ·  ไม้ {m['trades']}  ·  win rate {m['wr']:.1f}%")

    # เช็คด้วยว่าปี 2022 เดี่ยวๆ (ไม่ต่อเนื่องจากปีก่อน) ต่างจากดู mark-to-market ระหว่างทางยังไง
    print("\n--- เช็ค equity curve ช่วงปี 2022 จากการรันต่อเนื่อง 10 ปี (mark-to-market ระหว่างทาง) ---")
    for slots in [5, 10]:
        capital_usd = 100_000 / teo.THB_PER_USD
        pos_size = capital_usd / slots
        cash = capital_usd
        positions = {}
        FEE = teo.FEE
        HARD_SL = 0.20
        equity_2022 = []
        for dt in all_dates:
            for sym in list(positions):
                P = prep[sym]
                if dt not in P["close"].index:
                    continue
                price = float(P["close"].loc[dt])
                ema200 = float(P["emas"][200].loc[dt])
                pos = positions[sym]
                chg = price / pos["entry_price"] - 1
                if chg <= -HARD_SL or price < ema200:
                    cash += pos["qty"] * price * (1 - FEE)
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
                positions[sym] = dict(qty=qty, entry_price=price)
            val = cash
            for sym, pos in positions.items():
                series = prep[sym]["close"]
                px = float(series.loc[dt]) if dt in series.index else float(series[series.index <= dt].iloc[-1])
                val += pos["qty"] * px
            if dt.year == 2022:
                equity_2022.append(val)
        if equity_2022:
            eq0, eq1 = equity_2022[0], equity_2022[-1]
            maxdd_2022 = min((v / max(equity_2022[:i+1]) - 1) for i, v in enumerate(equity_2022)) * 100
            print(f"{slots} ไม้: มูลค่าต้นปี 2022 (จาก equity สะสม) {eq0*teo.THB_PER_USD:,.0f} บาท → "
                  f"ปลายปี {eq1*teo.THB_PER_USD:,.0f} บาท ({(eq1/eq0-1)*100:+.1f}%) · MaxDD ในปีนี้ {maxdd_2022:.1f}%")


if __name__ == "__main__":
    main()
