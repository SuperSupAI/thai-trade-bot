#!/usr/bin/env python
"""
เปรียบเทียบ 3 อย่างในช่วง 1 ปีล่าสุด (SET100):
  1) หุ้นที่ Buy & Hold ได้กำไรสูงสุด (ถือตัวเดียวยาวทั้งปี)
  2) หุ้นที่ Buy & Hold ขาดทุน/กำไรต่ำสุด (ถือตัวเดียวยาวทั้งปี)
  3) กลยุทธ์หมุนเงิน 1 ไม้ (เข้า: EMA Stack + New High / ออก: EMA30<EMA50 + TP15%)
     — พอออกจากตัวหนึ่ง เงินจะถูกโยกไปเข้าตัวถัดไปที่มีสัญญาณทันที (ไม่ถือเงินสดเฉยๆ)
     พร้อม log ละเอียดว่าออกตัวไหน เข้าตัวไหนต่อ วันที่เท่าไหร่

หมายเหตุ: ใช้ 2 ปีของข้อมูลราคาต่อหุ้น (ปีแรกไว้คำนวณ EMA200/New-High lookback,
ปีหลังไว้ประเมินผลจริง) กันสัญญาณเข้าผิดเพราะ EMA ยังไม่นิ่งตอนต้นช่วงที่ทดสอบ
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one

CUT = 0.08
LOOKBACK_YEARS = 2   # โหลด 2 ปี — ปีแรกไว้ warm-up EMA/breakout, ปีหลังไว้เทสจริง


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def prep(close, breakout_days=252):
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    cond = (stack & broke).fillna(False)
    return dict(c=close.values, idx=close.index, e30=e30.values, e50=e50.values, cond=cond.values)


def sim_trades(P, eval_start_i):
    """จำลองเข้า/ออกจากสัญญาณ แต่ 'นับ' เฉพาะไม้ที่เข้าตั้งแต่ eval_start_i เป็นต้นไป (1 ปีล่าสุด)"""
    c = P["c"]; e30, e50, cond = P["e30"], P["e50"], P["cond"]
    n = len(c)
    held, ep, entry_i = 0.0, 0.0, None
    trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            reason = None
            if chg <= -CUT:
                reason = "SL -8%"
            elif chg >= 0.15:
                reason = "TP +15%"
            elif e30[i] < e50[i]:
                reason = "EMA30<EMA50"
            if reason:
                trades.append(dict(entry_i=entry_i, exit_i=i, pnl=chg, reason=reason))
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]; entry_i = i
    return [t for t in trades if t["entry_i"] >= eval_start_i]


def main():
    print("โหลดข้อมูล SET100 (2 ปี — ปีแรก warm-up, ปีหลังประเมินผลจริง)...")
    syms = group_symbols("SET100 (ทั้งหมด)")
    data = {}
    for s in syms:
        c = safe_download_one(s, LOOKBACK_YEARS)
        if c is not None and len(c) > 300:
            data[s] = c
    print(f"ใช้ได้ {len(data)} ตัว\n")

    # ── 1) Buy & Hold รายตัว 1 ปีล่าสุด ──
    bh_1y = {}
    for sym, close in data.items():
        cutoff = close.index[-1] - pd.DateOffset(years=1)
        sub = close[close.index >= cutoff]
        if len(sub) < 200:
            continue
        bh_1y[sym] = sub.iloc[-1] / sub.iloc[0] - 1

    best_sym = max(bh_1y, key=bh_1y.get)
    worst_sym = min(bh_1y, key=bh_1y.get)

    print("=" * 90)
    print("1) Buy & Hold รายตัว (ถือยาว 1 ปี) — สูงสุด vs ต่ำสุดใน SET100")
    print("=" * 90)
    print(f"กำไรสูงสุด: {best_sym.replace('.BK','')}  {bh_1y[best_sym]*100:+.1f}%")
    print(f"กำไรต่ำสุด: {worst_sym.replace('.BK','')}  {bh_1y[worst_sym]*100:+.1f}%")
    print(f"เฉลี่ยทั้งกลุ่ม ({len(bh_1y)} ตัว): {np.mean(list(bh_1y.values()))*100:+.1f}%\n")

    # ── 2) กลยุทธ์หมุนเงิน 1 ไม้ ในช่วง 1 ปีล่าสุด ──
    print("=" * 90)
    print("2) กลยุทธ์หมุนเงิน 1 ไม้ (เข้า: EMA Stack+NewHigh / ออก: EMA30<EMA50+TP15%) — 1 ปีล่าสุด")
    print("=" * 90)

    all_signals = []  # (entry_date, exit_date, sym, pnl, reason)
    for sym, close in data.items():
        P = prep(close)
        cutoff_date = close.index[-1] - pd.DateOffset(years=1)
        eval_start_i = int((close.index >= cutoff_date).argmax())
        for t in sim_trades(P, eval_start_i):
            entry_d = close.index[t["entry_i"]]
            exit_d = close.index[t["exit_i"]] if t["exit_i"] < len(close.index) else None
            all_signals.append(dict(sym=sym.replace(".BK", ""), entry=entry_d, exit=exit_d,
                                    pnl=t["pnl"], reason=t["reason"]))

    all_signals.sort(key=lambda x: x["entry"])

    # จำลองพอร์ต 1 ไม้: ไล่สัญญาณตามลำดับเวลา ถือได้ทีละตัว — สัญญาณไหนที่เข้ามาตอนมือไม่ว่าง (ยังถือตัวก่อนหน้าอยู่) ข้ามไป
    rotation_log = []
    cash_mult = 1.0
    t_cursor = None
    for s in all_signals:
        if t_cursor is not None and s["entry"] < t_cursor:
            continue  # ช่วงนี้มือไม่ว่าง (ถือไม้ก่อนหน้าอยู่) ข้ามสัญญาณนี้ไป
        rotation_log.append(s)
        cash_mult *= (1 + s["pnl"])
        t_cursor = s["exit"] if s["exit"] is not None else s["entry"]

    print(f"จำนวนไม้ที่หมุนเข้า-ออกได้ในปีนี้: {len(rotation_log)}")
    print(f"ผลตอบแทนรวม (ทบต้นตามลำดับไม้จริง): {(cash_mult-1)*100:+.1f}%\n")
    print("รายละเอียดการหมุนไม้ (ออกตัวไหน → เข้าตัวไหนต่อ):")
    for i, s in enumerate(rotation_log, 1):
        exit_str = s["exit"].date() if s["exit"] is not None else "ยังถือ"
        print(f"  ไม้ {i}: {s['sym']:6s}  เข้า {s['entry'].date()}  ออก {exit_str} "
              f"({s['reason']})  กำไร {s['pnl']*100:+.1f}%")

    print(f"\nเทียบ: Buy&Hold ตัวดีสุด {best_sym.replace('.BK','')} = {bh_1y[best_sym]*100:+.1f}% "
          f"vs หมุนเงิน 1 ไม้ = {(cash_mult-1)*100:+.1f}% vs Buy&Hold ตัวแย่สุด "
          f"{worst_sym.replace('.BK','')} = {bh_1y[worst_sym]*100:+.1f}%")


if __name__ == "__main__":
    main()
