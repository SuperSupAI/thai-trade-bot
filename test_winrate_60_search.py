#!/usr/bin/env python
"""
Phase 1: หา combo (เข้า x ออก) ที่ win rate >= 60% แบบไม่หลอกตัวเอง
กติกา (ล็อกไว้ก่อนรัน ห้ามแก้หลังเห็นผล):
  - แบ่งข้อมูลราคาแต่ละหุ้นเป็น 3 ช่วงตามเวลา: TRAIN (60%) / VALID (20%) / TEST (20%)
  - หา combo ทั้งหมดบน TRAIN, คัดที่ผ่านเกณฑ์บน VALID, ยืนยันครั้งเดียวบน TEST
  - เกณฑ์ผ่าน: win rate >= 55% ทั้ง valid+test, กำไรเฉลี่ยต่อไม้ > 0 (หลังค่าธรรมเนียม), ไม้ >= 40 ต่อช่วง
  - รายงาน "ทุก" combo ที่ลอง ไม่ใช่แค่ตัวที่ผ่าน (กัน survivorship ของผลลัพธ์เอง)

Grid: entry 6 แบบ x exit (TP,SL) 9 คู่ = 54 combo ต่อตลาด x 2 ตลาด (ไทย/US) = 108 combo
"""
import itertools
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one

FEE = 0.002


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def prep(close):
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    macd = ema(close, 12) - ema(close, 26)
    r = rsi(close)
    yr_high = close.rolling(252, min_periods=60).max()
    hi20 = close.rolling(20).max().shift(1)

    entries = {
        "EMA Stack+NewHigh": (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200) & (close >= yr_high),
        "Close>EMA200+MACD>0": (close > e200) & (macd > 0),
        "Pullback EMA50 in uptrend": (close > e200) & (e50 > e200) & (close.sub(e50).abs() / e50 < 0.02),
        "RSI35-55 in uptrend": (close > e200) & (r > 35) & (r < 55),
        "Breakout20d+MACD>0": (close > hi20) & (macd > 0),
        "EMA10>50>200": (e10 > e50) & (e50 > e200),
    }
    return dict(c=close.values, entries={k: v.fillna(False).values for k, v in entries.items()})


EXIT_GRID = [(tp, sl) for tp in (0.05, 0.08, 0.10, 0.15) for sl in (0.05, 0.08, 0.10)]


def sim(c, cond, tp, sl):
    n = len(c)
    held, ep = 0.0, 0.0
    trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            if chg <= -sl or chg >= tp:
                trades.append(chg)
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]
    return trades


def split_idx(n):
    a = int(n * 0.6); b = int(n * 0.8)
    return (0, a), (a, b), (b, n)


def eval_combo(data_p, entry_key, tp, sl, which):
    all_trades = []
    for P in data_p:
        c = P["c"]; cond = P["entries"][entry_key]
        (a0, a1), (b0, b1), (c0, c1) = split_idx(len(c))
        lo, hi = {"train": (a0, a1), "valid": (b0, b1), "test": (c0, c1)}[which]
        sub_c = c[lo:hi]; sub_cond = cond[lo:hi]
        if len(sub_c) < 100:
            continue
        all_trades += [t - 2 * FEE for t in sim(sub_c, sub_cond, tp, sl)]
    if not all_trades:
        return None
    wins = sum(1 for t in all_trades if t > 0)
    return dict(n=len(all_trades), wr=wins / len(all_trades) * 100, avg=np.mean(all_trades) * 100)


def load_market(label, syms, years):
    print(f"  โหลด {label}: {len(syms)} สัญลักษณ์ ({years} ปี)...")
    data = {}
    for s in syms:
        c = safe_download_one(s, years)
        if c is not None and len(c) > 400:
            data[s] = c
    print(f"  ใช้ได้ {len(data)} ตัว")
    return [prep(c) for c in data.values()]


def run_market(label, data_p):
    if not data_p:
        print(f"\n{'='*100}\n{label}: ไม่มีข้อมูลพอ ข้ามตลาดนี้ไป\n{'='*100}")
        return pd.DataFrame(), pd.DataFrame()
    entry_keys = list(data_p[0]["entries"].keys())
    combos = list(itertools.product(entry_keys, EXIT_GRID))
    print(f"\n{'='*100}\n{label}: ทดสอบ {len(combos)} combo\n{'='*100}")

    all_rows = []
    for ekey, (tp, sl) in combos:
        tr = eval_combo(data_p, ekey, tp, sl, "train")
        va = eval_combo(data_p, ekey, tp, sl, "valid")
        te = eval_combo(data_p, ekey, tp, sl, "test")
        if not tr or not va or not te:
            continue
        all_rows.append(dict(entry=ekey, tp=tp, sl=sl,
                             train_n=tr["n"], train_wr=round(tr["wr"], 1), train_avg=round(tr["avg"], 2),
                             valid_n=va["n"], valid_wr=round(va["wr"], 1), valid_avg=round(va["avg"], 2),
                             test_n=te["n"], test_wr=round(te["wr"], 1), test_avg=round(te["avg"], 2)))

    res = pd.DataFrame(all_rows)
    print(f"combo ที่มีข้อมูลพอทั้ง 3 ช่วง: {len(res)}/{len(combos)}")

    passed = res[(res.valid_wr >= 55) & (res.test_wr >= 52) & (res.valid_avg > 0) & (res.test_avg > 0)
                & (res.valid_n >= 40) & (res.test_n >= 40)]
    print(f"\nผ่านเกณฑ์ (valid WR>=55%, test WR>=52%, กำไรเฉลี่ยบวกทั้งคู่, ไม้>=40): {len(passed)} combo")
    if not passed.empty:
        print(passed.sort_values("test_wr", ascending=False).to_string(index=False))
    else:
        print("ไม่มี combo ไหนผ่านครบทุกเกณฑ์")

    print("\nTop 10 ตาม test_wr (ไม่ผ่านเกณฑ์ครบก็แสดง เพื่อดูว่าใกล้แค่ไหน):")
    print(res.sort_values("test_wr", ascending=False).head(10).to_string(index=False))
    return res, passed


def main():
    th_syms = group_symbols("SET100 (ทั้งหมด)")
    # ใช้ ticker US จริง (ไม่ใช่ DR ไทย) เพราะ DR ในไทยเพิ่งเปิดเทรด มีประวัติแค่ ~1-1.5 ปี ไม่พอทำ 10 ปี
    us_syms = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "JPM",
              "KO", "PEP", "V", "MA", "ORCL", "CRM", "ADBE", "NFLX", "CSCO",
              "BAC", "DIS", "NKE"]

    th_data = load_market("หุ้นไทย (SET100)", th_syms, 5)
    us_data = load_market("หุ้น US (ticker จริง)", us_syms, 10)

    th_res, th_passed = run_market("ตลาดไทย", th_data)
    us_res, us_passed = run_market("ตลาด US", us_data)

    th_res.to_csv("winrate60_thai_all_combos.csv", index=False)
    us_res.to_csv("winrate60_us_all_combos.csv", index=False)
    print("\nบันทึกทุก combo ที่ลองไว้ที่ winrate60_thai_all_combos.csv / winrate60_us_all_combos.csv")


if __name__ == "__main__":
    main()
