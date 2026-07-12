#!/usr/bin/env python
"""
หาจุดเข้าที่เหมาะกับ "หุ้นคะแนนสูง" (fundamental 4-5/5) โดยเฉพาะ — เพราะสูตร EMA Stack+NewHigh
เดิมให้ผลแค่กลางๆ กับกลุ่มนี้ (win rate 35.1%, กำไรเฉลี่ย ~0%) ลองเทียบจุดเข้าหลายแบบ
(ออกคงที่ = EMA30<EMA50+TP15% เพื่อเทียบแฟร์ๆ) เฉพาะหุ้นกลุ่มคะแนนสูงที่หาไว้ก่อนหน้า
"""
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, ".")
from safe_fetch import safe_download_one

CUT = 0.08
YEARS = 5

HIGH_SCORE_STOCKS = ["ADVANC", "AMATA", "BH", "COM7", "DELTA", "GLOBAL", "GPSC", "HMPRO",
                     "ITC", "KTC", "MTC", "OSP", "SAT", "SCCC", "SPRC", "TIDLOR", "TOP", "TVO"]


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def prep(close):
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    macd = ema(close, 12) - ema(close, 26)
    r = rsi(close)
    yr_high_252 = close.rolling(252, min_periods=60).max()
    yr_high_126 = close.rolling(126, min_periods=60).max()

    entries = {
        "EMA Stack + NewHigh 1y (เดิม)": (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50)
            & (e50 > e100) & (e100 > e200) & (close >= yr_high_252),
        "EMA Stack ล้วนๆ (ไม่ต้อง NewHigh)": (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50)
            & (e50 > e100) & (e100 > e200),
        "EMA Stack + NewHigh 6m": (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50)
            & (e50 > e100) & (e100 > e200) & (close >= yr_high_126),
        "Pullback ใน uptrend (Close>EMA200, EMA50>EMA200, ราคาแตะ EMA50 ±2%)":
            (close > e200) & (e50 > e200) & (close.sub(e50).abs() / e50 < 0.02),
        "Default หลวม (Close>EMA200 + MACD>0)": (close > e200) & (macd > 0),
        "RSI ย่อในเทรนด์ขึ้น (Close>EMA200, RSI 35-55)": (close > e200) & (r > 35) & (r < 55),
    }
    return dict(c=close.values, e30=e30.values, e50=e50.values,
               entries={k: v.fillna(False).values for k, v in entries.items()})


def sim_trades(P, cond):
    c = P["c"]; e30, e50 = P["e30"], P["e50"]
    n = len(c)
    held, ep = 0.0, 0.0
    trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            reason = None
            if chg <= -CUT:
                reason = "SL"
            elif chg >= 0.15:
                reason = "TP"
            elif e30[i] < e50[i]:
                reason = "EXIT"
            if reason:
                trades.append(chg)
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]
    return trades


def report(label, rets):
    if not rets:
        print(f"{label}: ไม่มีไม้")
        return
    wins = sum(1 for r in rets if r > 0)
    print(f"{label}: {len(rets)} ไม้ · win rate {wins/len(rets)*100:.1f}% · "
          f"กำไรเฉลี่ย {np.mean(rets)*100:+.1f}% · median {np.median(rets)*100:+.1f}%")


def main():
    print(f"โหลดราคา 5 ปีของหุ้นคะแนนสูง {len(HIGH_SCORE_STOCKS)} ตัว...")
    data = {}
    for s in HIGH_SCORE_STOCKS:
        c = safe_download_one(s + ".BK", YEARS)
        if c is not None and len(c) > 300:
            data[s] = c
    print(f"ใช้ได้ {len(data)} ตัว\n")

    entry_keys = list(prep(next(iter(data.values())))["entries"].keys())
    print("เปรียบเทียบจุดเข้าต่างๆ (ออกคงที่: SL-8% / TP+15% / EMA30<EMA50)")
    print("=" * 100)
    for key in entry_keys:
        all_rets = []
        for close in data.values():
            P = prep(close)
            all_rets += sim_trades(P, P["entries"][key])
        report(key, all_rets)


if __name__ == "__main__":
    main()
