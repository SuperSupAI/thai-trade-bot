#!/usr/bin/env python
"""
เทียบ DCA 10 ปี: เติมเงินปีละ 200,000 บาท (รวม 2,000,000 บาทตลอด 10 ปี)
  A) ซื้อ SPY (S&P500) เก็บยาว ไม่ทำอะไร
  B) เอาเงินไปเทรดด้วยสูตร E3 TrendMACD + TP12/SL15 (ไม่จำกัดไม้ ใช้เงินทอนซื้อต่อ)
ใช้ cache ข้อมูล 10 ปีเดิม (us_close_10y_cache.pkl, spy_10y_cache.pkl)
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
ANNUAL_INJECTION_THB = 200_000
N_INJECTIONS = 10
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    with open(SPY_CACHE_FILE, "rb") as f:
        spy = pickle.load(f)
    print(f"ใช้ cache เดิม: {len(data)} หุ้น + SPY")

    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()
    xcfg = exits["TP12/SL15"]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    n = len(all_dates)
    inject_idx = [min(i * 252, n - 1) for i in range(N_INJECTIONS)]  # วันที่เติมเงินแต่ละปี (~ทุก 252 วันเทรด)
    inject_usd = ANNUAL_INJECTION_THB / THB_PER_USD
    print(f"ช่วงทดสอบ: {all_dates[0].date()} → {all_dates[-1].date()} ({n} วันเทรด)")
    print(f"เติมเงิน {ANNUAL_INJECTION_THB:,} บาท/ปี × {N_INJECTIONS} ครั้ง = "
          f"{ANNUAL_INJECTION_THB*N_INJECTIONS:,} บาท รวม (~{inject_usd*N_INJECTIONS:,.0f} USD)")
    print(f"วันที่เติมเงิน (index): {[all_dates[i].date().isoformat() for i in inject_idx]}\n")

    # ── A) SPY DCA ──
    spy_seg = spy.reindex(all_dates).ffill()
    shares = 0.0
    spy_equity = []
    total_invested_usd = 0.0
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            price = float(spy_seg.iloc[i])
            shares += inject_usd / price
            total_invested_usd += inject_usd
        spy_equity.append(shares * float(spy_seg.iloc[i]))
    spy_final = spy_equity[-1]

    # ── B) กลยุทธ์ DCA ──
    cash = 0.0
    positions = {}
    total_capital_injected = 0.0
    strat_equity = []
    trades_count = 0
    wins = 0
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            cash += inject_usd
            total_capital_injected += inject_usd
        pos_size = total_capital_injected / TARGET_SLOTS  # ขนาดไม้เป้าหมาย ขยับตามทุนที่เติมเข้ามาแล้ว

        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            if chg <= -xcfg["sl"] or chg >= xcfg["tp"]:
                cash += pos["qty"] * price * (1 - FEE)
                trades_count += 1
                if chg > 0:
                    wins += 1
                del positions[sym]

        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E3 TrendMACD"].loc[dt]):
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
        strat_equity.append(val)
    strat_final = strat_equity[-1]

    total_invested_thb = total_invested_usd * THB_PER_USD
    spy_final_thb = spy_final * THB_PER_USD
    strat_final_thb = strat_final * THB_PER_USD

    print("=" * 90)
    print(f"ผล DCA 10 ปี — เติมเงิน {ANNUAL_INJECTION_THB:,} บาท/ปี รวม {total_invested_thb:,.0f} บาท")
    print("=" * 90)
    print(f"{'':28s}{'SPY (ซื้อสะสมทุกปี)':>28s}{'กลยุทธ์ (เติมทุนทุกปี)':>28s}")
    print(f"{'มูลค่าสุดท้าย (บาท)':28s}{spy_final_thb:>28,.0f}{strat_final_thb:>28,.0f}")
    print(f"{'กำไรสุทธิ (บาท)':28s}{spy_final_thb-total_invested_thb:>+28,.0f}{strat_final_thb-total_invested_thb:>+28,.0f}")
    print(f"{'ผลตอบแทนเทียบทุนที่ใส่':28s}{(spy_final_thb/total_invested_thb-1)*100:>+27.1f}%{(strat_final_thb/total_invested_thb-1)*100:>+27.1f}%")
    print(f"{'จำนวนไม้ (กลยุทธ์)':28s}{'':>28s}{trades_count:>28d}")
    print(f"{'Win rate (กลยุทธ์)':28s}{'':>28s}{(wins/trades_count*100 if trades_count else 0):>27.1f}%")

    result = pd.DataFrame({"date": all_dates, "spy_equity_thb": np.array(spy_equity)*THB_PER_USD,
                           "strategy_equity_thb": np.array(strat_equity)*THB_PER_USD})
    result.to_csv("dca_10y_vs_spy_equity_curve.csv", index=False)
    print("\nบันทึก equity curve รายวันไว้ที่ dca_10y_vs_spy_equity_curve.csv")


if __name__ == "__main__":
    main()
