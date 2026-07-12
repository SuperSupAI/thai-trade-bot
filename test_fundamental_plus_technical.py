#!/usr/bin/env python
"""
เอาหุ้นที่คะแนน Fundamental Screener สูง (4-5/5) vs ต่ำ (0-2/5) มารันสูตรเทคนิคเดิม
(เข้า: EMA Stack + New High / ออก: EMA30<EMA50 + TP15%) เทียบกันว่า win rate/ผลตอบแทน
ต่างกันไหม — ทดสอบสมมติฐานว่า "กรองด้วยงบการเงินก่อน แล้วค่อยจับจังหวะเข้าด้วยเทคนิค" ดีกว่า
ใช้เทคนิคอย่างเดียวหรือเปล่า

ข้อจำกัดสำคัญที่ต้องรู้ก่อนเชื่อผล: คะแนน fundamental มาจาก "ข้อมูลปัจจุบัน" (snapshot วันนี้)
แต่ไม้เทรดที่ทดสอบมาจาก "5 ปีที่ผ่านมา" — เท่ากับใช้ความรู้วันนี้ (ว่าหุ้นนี้งบดี/แย่) ไปตัดสิน
เทรดในอดีต ซึ่งเป็น look-ahead bias รูปแบบหนึ่ง (หุ้นที่งบดีวันนี้ อาจงบแย่เมื่อ 3 ปีก่อนก็ได้)
ผลจึงตีความได้แค่ "ถ้าเลือกหุ้นจากงบดีที่สุด ณ วันนี้ แล้วย้อนเทสด้วยเทคนิคเดิม จะได้ผลแบบนี้"
ไม่ใช่ "กลยุทธ์ผสมงบ+เทคนิคที่ใช้ได้จริงแบบ point-in-time"
"""
import json
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one

CUT = 0.08
YEARS = 5
FUND_PATH = "data/fundamentals.json"


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def prep(close, breakout_days=252):
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    cond = (stack & broke).fillna(False)
    return dict(c=close.values, e30=e30.values, e50=e50.values, cond=cond.values)


def sim_trades(P):
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
            elif chg >= 0.15:
                reason = "TP"
            elif e30[i] < e50[i]:
                reason = "EXIT"
            if reason:
                trades.append(chg)
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]; entry_i = i
    return trades


def score_stock(f):
    roe = f.get('roe'); eps_g = f.get('eps_growth'); de = f.get('de_ratio')
    ebit_m = f.get('ebit_margin'); pe = f.get('pe_ratio')
    score = 0
    score += 1 if (roe is not None and roe > 0.15) else 0
    score += 1 if (eps_g is not None and eps_g > 0.10) else 0
    score += 1 if (de is not None and de < 1.0) else 0
    score += 1 if (ebit_m is not None and ebit_m > 0.10) else 0
    score += 1 if (pe is not None and 0 < pe < 25) else 0
    return score


def report(label, rets):
    if not rets:
        print(f"{label}: ไม่มีไม้")
        return
    wins = sum(1 for r in rets if r > 0)
    print(f"{label}: {len(rets)} ไม้ · win rate {wins/len(rets)*100:.1f}% · "
          f"กำไรเฉลี่ย {np.mean(rets)*100:+.1f}% · median {np.median(rets)*100:+.1f}%")


def main():
    with open(FUND_PATH, encoding="utf-8") as f:
        funds = json.load(f)

    syms = group_symbols("SET100 (ทั้งหมด)")
    scores = {}
    for s in syms:
        f = funds.get(s)
        if f:
            scores[s] = score_stock(f)

    high = [s for s, sc in scores.items() if sc >= 4]
    low = [s for s, sc in scores.items() if sc <= 1]
    mid = [s for s, sc in scores.items() if 2 <= sc <= 3]
    print(f"หุ้นคะแนนสูง (4-5/5): {len(high)} ตัว — {[s.replace('.BK','') for s in high]}")
    print(f"หุ้นคะแนนต่ำ (0-1/5): {len(low)} ตัว — {[s.replace('.BK','') for s in low]}")
    print(f"หุ้นคะแนนกลาง (2-3/5): {len(mid)} ตัว\n")

    print("โหลดราคา 5 ปีของทั้ง 3 กลุ่ม...")
    data = {}
    for s in high + low + mid:
        c = safe_download_one(s, YEARS)
        if c is not None and len(c) > 300:
            data[s] = c
    print(f"ใช้ได้ {len(data)} ตัว\n")

    for label, syms_group in [("คะแนนสูง (4-5/5)", high), ("คะแนนกลาง (2-3/5)", mid), ("คะแนนต่ำ (0-1/5)", low)]:
        all_rets = []
        for s in syms_group:
            close = data.get(s)
            if close is None:
                continue
            P = prep(close)
            all_rets += sim_trades(P)
        print("=" * 80)
        report(f"กลุ่ม {label}", all_rets)


if __name__ == "__main__":
    main()
