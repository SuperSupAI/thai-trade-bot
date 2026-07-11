#!/usr/bin/env python
"""
เปรียบเทียบผลของกลยุทธ์ EMA Stack + New High (เข้า) / EMA30<EMA50 (ออก, ทั้งแบบมี/ไม่มี TP15%)
แยกตามว่า "วันนั้น" ดัชนี SET อยู่เหนือ หรือ ต่ำกว่า EMA200 ของตัวเอง (เป็น regime filter)
เพื่อดูว่ากลยุทธ์นี้พึ่งพาทิศทางตลาดใหญ่แค่ไหน — ถ้าทำงานได้เฉพาะตอน SET>EMA200 (ตลาดขาขึ้น)
แปลว่า "ไม่ใช้เงื่อนไข SET" อาจเสี่ยงกว่าที่คิด เพราะเข้าได้แม้ตลาดใหญ่กำลังขาลง
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one

CUT = 0.08
YEARS = 5


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def prep(close, breakout_days=252):
    df = pd.DataFrame({"c": close})
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    cond = (stack & broke).fillna(False)
    return dict(c=close.values, idx=close.index, e30=e30.values, e50=e50.values, cond=cond.values)


def sim_trades(P, use_tp15):
    """คืน list ของ dict {entry_i, exit_i, pnl} — ไม่บังคับปิดไม้ที่ยังถืออยู่ (ตัดทิ้งจากสถิติ)"""
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
                trades.append(dict(entry_i=entry_i, exit_i=i, pnl=chg))
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]; entry_i = i
    return trades


def main():
    print("โหลด SET Index (5 ปี) เพื่อคำนวณ regime (SET>EMA200 หรือ <EMA200)...")
    set_close = safe_download_one("^SET.BK", YEARS)
    set_e200 = ema(set_close, 200)
    set_regime = (set_close > set_e200)  # True = SET อยู่เหนือ EMA200 ของตัวเอง (ตลาดใหญ่ขาขึ้น)

    print("โหลดข้อมูล SET100 (5 ปี)...")
    syms = group_symbols("SET100 (ทั้งหมด)")
    data = {}
    for s in syms:
        c = safe_download_one(s, YEARS)
        if c is not None and len(c) > 300:
            data[s] = c
    print(f"ใช้ได้ {len(data)} ตัว\n")

    for use_tp15, label in [(False, "EMA30<EMA50 (ไม่มี TP15%)"), (True, "EMA30<EMA50 + TP15%")]:
        print("=" * 90)
        print(f"สูตร: {label}")
        print("=" * 90)

        buckets = {"SET > EMA200 (ตลาดใหญ่ขาขึ้น)": [], "SET < EMA200 (ตลาดใหญ่ขาลง/ย่อ)": []}
        for close in data.values():
            P = prep(close)
            trades = sim_trades(P, use_tp15)
            regime_aligned = set_regime.reindex(close.index).ffill()
            for t in trades:
                entry_date = close.index[t["entry_i"]]
                if entry_date not in regime_aligned.index:
                    continue
                is_up = regime_aligned.loc[entry_date]
                if pd.isna(is_up):
                    continue
                key = "SET > EMA200 (ตลาดใหญ่ขาขึ้น)" if is_up else "SET < EMA200 (ตลาดใหญ่ขาลง/ย่อ)"
                buckets[key].append(t["pnl"])

        for key, rets in buckets.items():
            if not rets:
                print(f"{key}: ไม่มีไม้")
                continue
            wins = sum(1 for r in rets if r > 0)
            print(f"{key}: {len(rets)} ไม้ · win rate {wins/len(rets)*100:.1f}% · "
                  f"กำไรเฉลี่ย {np.mean(rets)*100:+.1f}% · median {np.median(rets)*100:+.1f}%")
        print()


if __name__ == "__main__":
    main()
