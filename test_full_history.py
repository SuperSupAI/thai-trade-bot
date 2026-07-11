#!/usr/bin/env python
"""
รันการทดสอบสูตร "EMA Stack + New High" (เข้า) / "EMA30<EMA50" ± TP15% (ออก) ซ้ำ
โดยใช้ข้อมูลจริง 50 ปี (1975-2025) จาก data/archive_close.csv แทนการดึง yfinance 5 ปี

ข้อควรระวัง: ราคาในไฟล์นี้เป็นราคาดิบ ไม่ได้ปรับ split/ปันผล เหมือน yfinance auto_adjust=True
ผลตอบแทนต่อไม้ (โดยเฉพาะไม้เก่าๆ ที่มี split) อาจไม่แม่นเป๊ะ 100% แต่สถิติภาพรวม (win rate,
ทิศทางเทียบ regime ต่างๆ) ยังใช้อ้างอิงได้ เพราะ EMA/breakout signal คำนวณจากราคาต่อเนื่องเดียวกัน
"""
import numpy as np
import pandas as pd

CUT = 0.08
CLOSE_PATH = "data/archive_close.csv"


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


def main():
    close_df = pd.read_csv(CLOSE_PATH, index_col=0, parse_dates=True)
    set_close = close_df["SET"].dropna()
    stock_cols = [c for c in close_df.columns if c != "SET"]
    print(f"หุ้นทั้งหมด {len(stock_cols)} ตัว · SET Index {len(set_close)} วัน "
          f"({set_close.index.min().date()} .. {set_close.index.max().date()})\n")

    set_e200 = ema(set_close, 200)
    set_regime = (set_close > set_e200)

    for use_tp15, exit_label in [(False, "EMA30<EMA50 (ไม่มี TP15%)"), (True, "EMA30<EMA50 + TP15%")]:
        print("=" * 90)
        print(f"สูตร: {exit_label} — ข้อมูลเต็ม 50 ปี")
        print("=" * 90)

        all_trades = []          # (entry_date, pnl)
        for col in stock_cols:
            close = close_df[col].dropna()
            if len(close) < 300:
                continue
            P = prep(close)
            for t in sim_trades(P, use_tp15):
                all_trades.append((close.index[t["entry_i"]], t["pnl"]))

        report("รวมทั้งหมด (ทุกช่วงเวลา ทุกหุ้น)", [p for _, p in all_trades])

        # แบ่งเป็น 4 ช่วงเวลาเท่าๆ กัน (ตามจำนวนไม้ เรียงตามวันที่เข้า) เช็คความสม่ำเสมอข้ามยุค
        all_trades.sort(key=lambda x: x[0])
        n = len(all_trades)
        if n >= 40:
            q = n // 4
            for qi in range(4):
                seg = all_trades[qi*q: (qi+1)*q] if qi < 3 else all_trades[qi*q:]
                dates = [d for d, _ in seg]
                label = f"ช่วงที่ {qi+1}/4 ({dates[0].date()}..{dates[-1].date()})" if dates else f"ช่วงที่ {qi+1}/4"
                report(label, [p for _, p in seg])

        # แบ่งตาม SET regime (เหนือ/ต่ำกว่า EMA200 ของตัวเอง) ด้วยข้อมูล 50 ปี
        up_rets, down_rets = [], []
        for d, p in all_trades:
            aligned = set_regime.reindex([d], method="ffill")
            if aligned.isna().all():
                continue
            (up_rets if aligned.iloc[0] else down_rets).append(p)
        print()
        report("SET > EMA200 (ตลาดใหญ่ขาขึ้น)", up_rets)
        report("SET < EMA200 (ตลาดใหญ่ขาลง/ย่อ)", down_rets)
        print()


if __name__ == "__main__":
    main()
