#!/usr/bin/env python
"""
ทดสอบสูตร "EMA Stack + New High" (เข้า) / "EMA30<EMA50" ± TP15% (ออก) กับหุ้นอเมริกา
แทนหุ้นไทย — yfinance ให้ข้อมูลหุ้น US ครบและแม่นกว่ามาก (ปรับ split/ปันผลถูกต้อง,
ไม่มีปัญหา delisted/rate-limit เท่าหุ้นไทย) ใช้กลุ่ม Dow 30 + หุ้นใหญ่บาง sector เพิ่มเติม
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf

CUT = 0.08
YEARS = 15

# Dow 30 + หุ้นใหญ่เพิ่มเติมบาง sector (เทค/พลังงาน/สุขภาพ) ให้กระจายหลากหลายกว่าดัชนีเดียว
US_STOCKS = [
    "AAPL", "MSFT", "JPM", "V", "PG", "UNH", "HD", "MRK", "KO", "CSCO",
    "CVX", "MCD", "CRM", "WMT", "AXP", "IBM", "GS", "CAT", "HON", "AMGN",
    "BA", "MMM", "TRV", "JNJ", "DIS", "NKE", "VZ", "DOW", "INTC", "WBA",
    "GOOGL", "AMZN", "META", "NVDA", "XOM", "PFE", "T", "COST", "PEP", "ADBE",
]


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def prep(close, breakout_days=252):
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    cond = (stack & broke).fillna(False)
    return dict(c=close.values, idx=close.index, e30=e30.values, e50=e50.values, cond=cond.values)


def sim_trades(P, use_tp15):
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


def report(label, rets):
    if not rets:
        print(f"{label}: ไม่มีไม้")
        return
    wins = sum(1 for r in rets if r > 0)
    print(f"{label}: {len(rets)} ไม้ · win rate {wins/len(rets)*100:.1f}% · "
          f"กำไรเฉลี่ย {np.mean(rets)*100:+.1f}% · median {np.median(rets)*100:+.1f}%")


def load_data():
    data = {}
    for s in US_STOCKS:
        try:
            df = yf.download(s, period=f"{YEARS}y", interval="1d", auto_adjust=True, progress=False)
            if df is None or df.empty:
                continue
            c = df["Close"]
            if isinstance(c, pd.DataFrame):
                c = c.iloc[:, 0]
            c = c.dropna()
            if len(c) > 300:
                data[s] = c
        except Exception:
            pass
    return data


def main():
    print(f"โหลดข้อมูลหุ้น US {len(US_STOCKS)} ตัว ({YEARS} ปี)...")
    data = load_data()
    print(f"ใช้ได้ {len(data)} ตัว\n")

    spy = yf.download("SPY", period=f"{YEARS}y", interval="1d", auto_adjust=True, progress=False)["Close"]
    if isinstance(spy, pd.DataFrame):
        spy = spy.iloc[:, 0]
    bh_rets = []
    for s, close in data.items():
        bh_rets.append(close.iloc[-1] / close.iloc[0] - 1)
    print(f"Buy & Hold เฉลี่ยทั้งกลุ่ม ({YEARS} ปี): {np.mean(bh_rets)*100:+.1f}%")
    print(f"SPY (S&P500 ETF) B&H: {(spy.iloc[-1]/spy.iloc[0]-1)*100:+.1f}%\n")

    for use_tp15, exit_label in [(False, "EMA30<EMA50 (ไม่มี TP15%)"), (True, "EMA30<EMA50 + TP15%")]:
        print("=" * 90)
        print(f"สูตร: {exit_label} — หุ้น US, {YEARS} ปี")
        print("=" * 90)

        all_trades = []
        for close in data.values():
            P = prep(close)
            for t in sim_trades(P, use_tp15):
                all_trades.append((close.index[t["entry_i"]], t["pnl"]))

        report("รวมทั้งหมด", [p for _, p in all_trades])

        all_trades.sort(key=lambda x: x[0])
        n = len(all_trades)
        if n >= 20:
            half = n // 2
            report(f"ครึ่งแรก ({all_trades[0][0].date()}..{all_trades[half-1][0].date()})",
                   [p for _, p in all_trades[:half]])
            report(f"ครึ่งหลัง ({all_trades[half][0].date()}..{all_trades[-1][0].date()})",
                   [p for _, p in all_trades[half:]])
        print()


if __name__ == "__main__":
    main()
