#!/usr/bin/env python
"""
เทียบผลของกลยุทธ์ EMA Stack + New High (เข้า) / EMA30<EMA50 + TP15% (ออก) แยกตามว่า
ตอนเข้าไม้นั้น "กำไรบริษัท (Net Income) ปีล่าสุดที่มีงบ" โตขึ้นจากปีก่อนหน้า (YoY) หรือไม่

ข้อจำกัดสำคัญ: yfinance ให้งบการเงินย้อนหลังแค่รายปี (~4-5 ปี) ไม่ใช่รายไตรมาส (QoQ ได้แค่
4-5 ไตรมาสล่าสุด ไม่พอสร้าง time series ย้อนหลังคู่กับราคาหุ้น 5 ปี) เลยใช้ YoY (รายปี) แทน
สมมติว่างบปีนั้นเริ่ม "รู้" ได้ตั้งแต่ต้นปีถัดไป (เช่น งบปี 2023 ถือว่ารู้ได้ตั้งแต่ต้นปี 2024)
เพื่อไม่ให้ใช้ข้อมูลที่ยังไม่ประกาศจริง ณ วันเข้าไม้ (point-in-time correctness)
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one
from fundamental_backtest import get_fund_history

CUT = 0.08
YEARS = 5


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def prep(close, breakout_days=252):
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    cond = (stack & broke).fillna(False)
    return dict(c=close.values, idx=close.index, e30=e30.values, e50=e50.values, cond=cond.values)


def sim_trades(P, use_tp15=True):
    c = P["c"]; e30, e50, cond = P["e30"], P["e50"], P["cond"]
    n = len(c)
    held, ep, entry_i = 0.0, 0.0, None
    trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            reason = None
            if chg <= -CUT:
                reason = "SL"
            elif use_tp15 and chg >= 0.15:
                reason = "TP"
            elif e30[i] < e50[i]:
                reason = "EXIT"
            if reason:
                trades.append(dict(entry_i=entry_i, pnl=chg))
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]; entry_i = i
    return trades


def earnings_grew_yoy_asof(fund_df, entry_date):
    """คืน True/False/None — เช็คปีล่าสุดที่ 'รู้ได้แล้ว' ณ entry_date (ปีนั้น + 1 ผ่านไปแล้ว)
    ว่า net_income โตจากปีก่อนหน้าหรือไม่"""
    if fund_df is None or fund_df.empty:
        return None
    known = fund_df[fund_df["year"] + 1 <= entry_date.year]
    if len(known) < 2:
        return None
    latest, prior = known.iloc[-1], known.iloc[-2]
    ni_latest, ni_prior = latest.get("net_income"), prior.get("net_income")
    if pd.isna(ni_latest) or pd.isna(ni_prior) or ni_prior == 0:
        return None
    return ni_latest > ni_prior


def get_fund_history_with_ni(sym):
    """ต่อยอด get_fund_history เดิม (มี revenue/roe/opm/de) ให้มี net_income ด้วย"""
    try:
        t = yf.Ticker(sym)
        fin = t.financials
        if fin is None or fin.empty or "Net Income" not in fin.index:
            return None
        base = get_fund_history(sym)
        if base is None:
            return None
        ni_by_year = {}
        for col in fin.columns:
            ni = fin.loc["Net Income", col]
            if pd.notna(ni):
                ni_by_year[col.year] = ni
        base["net_income"] = base["year"].map(ni_by_year)
        return base
    except Exception:
        return None


def main():
    print("โหลดข้อมูลราคา SET100 (5 ปี)...")
    syms = group_symbols("SET100 (ทั้งหมด)")
    price_data = {}
    for s in syms:
        c = safe_download_one(s, YEARS)
        if c is not None and len(c) > 300:
            price_data[s] = c
    print(f"ใช้ได้ {len(price_data)} ตัว (ราคา)\n")

    print("โหลดงบการเงินรายปี (Net Income) ทีละหุ้น...")
    fund_data = {}
    for i, s in enumerate(price_data, 1):
        fund_data[s] = get_fund_history_with_ni(s)
        if i % 15 == 0:
            print(f"  ...{i}/{len(price_data)}")
    n_with_fund = sum(1 for v in fund_data.values() if v is not None)
    print(f"มีงบใช้ได้ {n_with_fund}/{len(price_data)} ตัว\n")

    buckets = {"กำไรโต YoY": [], "กำไรลด YoY": []}
    skipped_no_data = 0
    for sym, close in price_data.items():
        P = prep(close)
        trades = sim_trades(P, use_tp15=True)
        fund_df = fund_data.get(sym)
        for t in trades:
            entry_date = close.index[t["entry_i"]]
            grew = earnings_grew_yoy_asof(fund_df, entry_date)
            if grew is None:
                skipped_no_data += 1
                continue
            key = "กำไรโต YoY" if grew else "กำไรลด YoY"
            buckets[key].append(t["pnl"])

    print("=" * 90)
    print("ผลเปรียบเทียบ: เข้าไม้ตอนกำไรบริษัท (Net Income ปีล่าสุดที่รู้ได้) โตจากปีก่อน vs ลด")
    print("(สูตร: EMA Stack + New High เข้า / EMA30<EMA50 + TP15% ออก)")
    print("=" * 90)
    for key, rets in buckets.items():
        if not rets:
            print(f"{key}: ไม่มีไม้")
            continue
        wins = sum(1 for r in rets if r > 0)
        print(f"{key}: {len(rets)} ไม้ · win rate {wins/len(rets)*100:.1f}% · "
              f"กำไรเฉลี่ย {np.mean(rets)*100:+.1f}% · median {np.median(rets)*100:+.1f}%")
    print(f"\n(ข้ามไป {skipped_no_data} ไม้ เพราะไม่มีงบการเงินย้อนหลังพอเทียบ YoY ณ วันเข้า)")


if __name__ == "__main__":
    main()
