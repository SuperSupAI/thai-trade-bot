#!/usr/bin/env python
"""
ลอง optimize สูตร "EMA Stack + New High" (เข้า) / "EMA30<EMA50" (ออก) ให้ win rate สูงขึ้น
โดยไม่โกงตัวเอง: หา combo ที่ win rate ดีสุดบนครึ่งแรกของข้อมูล (train) แล้วเอาไปทดสอบ
ครึ่งหลังที่ไม่เคยเห็น (test) — ถ้า win rate ยังดีอยู่ในครึ่งหลังด้วย ถึงจะเชื่อได้ว่าไม่ใช่ fluke

ตัวแปรที่ลองปรับ:
  - breakout_days: กรอบเวลาที่ต้องทำ New High (126=6ด. / 252=1ปี / 378=1.5ปี / 504=2ปี)
  - entry_extra:   เงื่อนไขเข้าเพิ่มนอกจาก EMA stack — none / MACD>0 / RSI<70 (กันเข้าตอน overbought)
  - exit_rule:     'ema30_50' (เดิม) / 'ema20_50' (ไวกว่า) / 'ema10_30' (ไวมาก) /
                   'ema30_50_tp15' (เดิม+ขายทำกำไรอัตโนมัติที่ +15% ด้วย)
"""
import sys
import itertools
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one

CUT = 0.08
YEARS = 5


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def prep(close, breakout_days):
    df = pd.DataFrame({"c": close})
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    macd = ema(close, 12) - ema(close, 26)
    r = rsi(close)
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    return dict(c=close.values, e10=e10.values, e20=ema(close, 20).values, e30=e30.values,
                e50=e50.values, macd=macd.values, rsi=r.values,
                stack=stack.fillna(False).values, broke=broke.fillna(False).values)


def entry_cond(P, extra):
    base = P["stack"] & P["broke"]
    if extra == "none":
        return base
    if extra == "macd":
        return base & (P["macd"] > 0)
    if extra == "rsi70":
        return base & (P["rsi"] < 70)
    raise ValueError(extra)


def sim(P, cond, exit_rule):
    c = P["c"]; e20, e30, e50 = P["e20"], P["e30"], P["e50"]
    n = len(c)
    held, ep, eq = 0.0, 0.0, 1.0
    trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            reason = None
            if chg <= -CUT:
                reason = "SL"
            elif exit_rule == "ema30_50" and e30[i] < e50[i]:
                reason = "EXIT"
            elif exit_rule == "ema20_50" and e20[i] < e50[i]:
                reason = "EXIT"
            elif exit_rule == "ema10_30" and P["e10"][i] < e30[i]:
                reason = "EXIT"
            elif exit_rule == "ema30_50_tp15" and (e30[i] < e50[i] or chg >= 0.15):
                reason = "EXIT"
            if reason:
                trades.append(chg)
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]
    return trades


def load_data():
    syms = group_symbols("SET100 (ทั้งหมด)")
    data = {}
    for s in syms:
        c = safe_download_one(s, YEARS)
        if c is not None and len(c) > 300:
            data[s] = c
    return data


def main():
    print("โหลดข้อมูล SET100 (5 ปี)...")
    data = load_data()
    print(f"ใช้ได้ {len(data)} ตัว\n")

    breakout_opts = [126, 252, 378, 504]
    extra_opts = ["none", "macd", "rsi70"]
    exit_opts = ["ema30_50", "ema20_50", "ema10_30", "ema30_50_tp15"]
    combos = list(itertools.product(breakout_opts, extra_opts, exit_opts))
    print(f"ทดสอบ {len(combos)} combo บนครึ่งแรก (train) ของข้อมูลแต่ละหุ้น...\n")

    # ครึ่งแรก/ครึ่งหลังของแต่ละหุ้น (ใช้ index สัมพัทธ์ ไม่ใช่ absolute date เพราะแต่ละหุ้นความยาวต่างกันเล็กน้อย)
    def eval_split(which):
        results = {}
        for bd, extra, ex in combos:
            all_trades = []
            for close in data.values():
                a, b = (0, len(close) // 2) if which == "train" else (len(close) // 2, len(close))
                sub = close.iloc[a:b]
                if len(sub) < 260:
                    continue
                P = prep(sub, bd)
                cond = entry_cond(P, extra)
                all_trades += sim(P, cond, ex)
            if all_trades:
                wins = sum(1 for t in all_trades if t > 0)
                results[(bd, extra, ex)] = dict(n=len(all_trades), win_rate=wins / len(all_trades) * 100,
                                                 avg_ret=float(np.mean(all_trades) * 100))
        return results

    train_res = eval_split("train")
    test_res = eval_split("test")

    rows = []
    for key in combos:
        tr = train_res.get(key)
        te = test_res.get(key)
        if not tr or not te or tr["n"] < 15 or te["n"] < 15:
            continue
        bd, extra, ex = key
        rows.append(dict(breakout_d=bd, extra=extra, exit=ex,
                         train_n=tr["n"], train_wr=round(tr["win_rate"], 1), train_avg=round(tr["avg_ret"], 1),
                         test_n=te["n"], test_wr=round(te["win_rate"], 1), test_avg=round(te["avg_ret"], 1)))

    res = pd.DataFrame(rows).sort_values("train_wr", ascending=False)
    print("=" * 100)
    print("อันดับตาม win rate บน TRAIN (ครึ่งแรก) — เรียงจากมากไปน้อย")
    print("=" * 100)
    print(res.head(15).to_string(index=False))

    print("\n" + "=" * 100)
    print("baseline (สูตรเดิม: breakout=252, extra=none, exit=ema30_50) เทียบทั้ง train/test")
    print("=" * 100)
    base = res[(res.breakout_d == 252) & (res.extra == "none") & (res.exit == "ema30_50")]
    print(base.to_string(index=False) if not base.empty else "ไม่มีข้อมูลพอ")

    res.to_csv("optimize_win_rate.csv", index=False)
    print("\nบันทึกผลเต็มไปที่ optimize_win_rate.csv")


if __name__ == "__main__":
    main()
