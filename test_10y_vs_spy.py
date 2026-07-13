#!/usr/bin/env python
"""
Backtest ย้อนหลัง 10 ปี: สูตร E3 TrendMACD + TP12/SL15 + ไม่จำกัดจำนวนไม้ (ใช้เงินทอนซื้อต่อ
จาก test_capital_reinvest_leftover.py) ทุนเริ่มต้น 100,000 บาท เทียบกับ SPY (S&P500) Buy & Hold
ช่วงเวลาเดียวกัน

โหลดข้อมูลใหม่ 10 ปี (cache แยกจากไฟล์เดิม เพราะยาวกว่า 4y/8y cache ที่มีอยู่)
"""
import os
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
from universe import US_STOCKS, US_MARKET_INDEX
import test_exit_optimization as teo
from test_capital_reinvest_leftover import simulate_reinvest

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
YEARS_DOWNLOAD = 10
CAPITAL_THB = 100_000
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD


def load_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
        print(f"ใช้ cache เดิม: {len(data)} ตัว ({CACHE_FILE})")
        return data
    print(f"โหลดหุ้น US {len(US_STOCKS)} ตัว ({YEARS_DOWNLOAD} ปี) — ใช้เวลานานกว่าปกติ...")
    data = {}
    for i, sym in enumerate(US_STOCKS):
        c = safe_download_one(sym, YEARS_DOWNLOAD)
        if c is not None and len(c) > 600:
            data[sym] = c
        if (i + 1) % 20 == 0:
            print(f"  โหลดแล้ว {i+1}/{len(US_STOCKS)}...")
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"ใช้ได้ {len(data)} ตัว (cache ไว้ที่ {CACHE_FILE})")
    return data


def load_spy():
    if os.path.exists(SPY_CACHE_FILE):
        with open(SPY_CACHE_FILE, "rb") as f:
            return pickle.load(f)
    print(f"โหลด {US_MARKET_INDEX} ({YEARS_DOWNLOAD} ปี)...")
    spy = safe_download_one(US_MARKET_INDEX, YEARS_DOWNLOAD)
    with open(SPY_CACHE_FILE, "wb") as f:
        pickle.dump(spy, f)
    return spy


def cagr_maxdd(equity_series):
    eq = pd.Series(equity_series)
    yrs = len(eq) / 252
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0
    maxdd = (eq / eq.cummax() - 1).min()
    return cagr * 100, maxdd * 100


def main():
    data = load_data()
    spy = load_spy()
    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบเต็ม: {all_dates[0].date()} → {all_dates[-1].date()} ({len(all_dates)} วันเทรด)\n")

    print(f"รันสูตร E3 TrendMACD + TP12/SL15 (ไม่จำกัดไม้) ทุน {CAPITAL_THB:,} บาท บน 10 ปีเต็ม...")
    m = simulate_reinvest(prep, syms_order, all_dates, "E3 TrendMACD", exits["TP12/SL15"], TARGET_SLOTS, CAPITAL_THB)

    # ต้องคำนวณ equity curve เองใหม่ (simulate_reinvest คืนแค่ summary) — เรียกแบบ manual เพื่อเก็บ equity
    capital_usd = CAPITAL_THB / THB_PER_USD
    pos_size = capital_usd / TARGET_SLOTS
    cash = capital_usd
    positions = {}
    equity = []
    FEE = teo.FEE
    xcfg = exits["TP12/SL15"]
    for dt in all_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            if chg <= -xcfg["sl"] or (xcfg["tp"] is not None and chg >= xcfg["tp"]):
                cash += pos["qty"] * price * (1 - FEE)
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
        equity.append(val)

    strat_cagr, strat_maxdd = cagr_maxdd(equity)
    strat_final_usd = equity[-1]
    strat_ret_pct = (strat_final_usd / capital_usd - 1) * 100

    # SPY Buy & Hold ช่วงเดียวกัน
    spy_seg = spy[(spy.index >= all_dates[0]) & (spy.index <= all_dates[-1])]
    spy_eq = (spy_seg / spy_seg.iloc[0] * capital_usd).values
    spy_cagr, spy_maxdd = cagr_maxdd(spy_eq)
    spy_ret_pct = (spy_eq[-1] / capital_usd - 1) * 100

    print("\n" + "=" * 90)
    print(f"ผลตอบแทน 10 ปี — ทุนเริ่มต้น {CAPITAL_THB:,} บาท")
    print("=" * 90)
    print(f"{'':30s}{'กลยุทธ์ (E3+TP12/SL15)':>25s}{'SPY Buy & Hold':>25s}")
    print(f"{'ผลตอบแทนรวม':30s}{strat_ret_pct:>+24.1f}%{spy_ret_pct:>+24.1f}%")
    print(f"{'CAGR ต่อปี':30s}{strat_cagr:>+24.1f}%{spy_cagr:>+24.1f}%")
    print(f"{'Max Drawdown':30s}{strat_maxdd:>+24.1f}%{spy_maxdd:>+24.1f}%")
    print(f"{'มูลค่าสุดท้าย (บาท)':30s}{strat_final_usd*THB_PER_USD:>+24,.0f}{spy_eq[-1]*THB_PER_USD:>+24,.0f}")
    print(f"{'จำนวนไม้ (กลยุทธ์)':30s}{m['trades']:>25d}")
    print(f"{'Win rate (กลยุทธ์)':30s}{m['wr']:>24.1f}%")

    result = pd.DataFrame({
        "date": all_dates,
        "strategy_equity_thb": np.array(equity) * THB_PER_USD,
        "spy_equity_thb": spy_eq * THB_PER_USD,
    })
    result.to_csv("10y_vs_spy_equity_curve.csv", index=False)
    print("\nบันทึก equity curve รายวันไว้ที่ 10y_vs_spy_equity_curve.csv")


if __name__ == "__main__":
    main()
