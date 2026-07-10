#!/usr/bin/env python
"""
Walk-Forward Optimization — ทดสอบแบบโกงตัวเองไม่ได้
- optimize บนหน้าต่าง 3 ปี (เลือก combo ที่ "median ทั้งกลุ่ม" ดีสุด — ไม่ fit รายตัว)
- เอา combo นั้นเทรด "ปีถัดไป" ที่ไม่เคยเห็น
- เลื่อนหน้าต่างทีละปี → ร้อยผลปี unseen ต่อกัน
เกณฑ์ (ตั้งก่อนรัน): ชนะ B&H+SET · กำไรกระจายหลายปี · ใช้ได้ ≥50% ของหุ้น · gap<30%
"""
import numpy as np
import pandas as pd
import yfinance as yf
from universe import group_symbols

FEE = 0.002
TRAIN_Y, START, END = 3, 2018, 2025   # หน้าต่างเทรน 3 ปี · เทสต์ 2021..2025


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def prep(close):
    """คืน dict ของ arrays: close, entry signals (bool), trailing refs"""
    df = pd.DataFrame({"c": close})
    e10, e20, e50, e200 = (ema(close, n) for n in (10, 20, 50, 200))
    r = rsi(close); macd = ema(close, 12) - ema(close, 26)
    hh20 = close.rolling(20).max().shift(1)
    hh55 = close.rolling(55).max().shift(1)
    tr = close.diff().abs()               # proxy ATR (มีแต่ close)
    atr = tr.rolling(14).mean()
    ent = {
        "EMA10>50>200+MACD": (e10 > e50) & (e50 > e200) & (macd > 0),
        "EMA20>50>200":      (e20 > e50) & (e50 > e200),
        "Close>EMA50+MACD":  (close > e50) & (macd > 0),
        "Close>EMA200+RSI>50": (close > e200) & (r > 50),
        "RSI30-70+EMA10>50": (r > 30) & (r < 70) & (e10 > e50),
        "Breakout20+MACD":   (close > hh20) & (macd > 0),
        "Breakout55":        (close > hh55),
    }
    return dict(c=close.values, idx=close.index,
                ent={k: v.fillna(False).values for k, v in ent.items()},
                e20=e20.values, e50=e50.values, e200=e200.values, atr=atr.values)


# (ชื่อ, SL, TP, trail)  trail: 'e20'/'e50'/'e200'/'atr2'/'atr3'/None
EXITS = [
    ("SL-8%+EMA50",  -0.08, None, "e50"),
    ("SL-5%+EMA200", -0.05, None, "e200"),
    ("SL-8%+EMA20",  -0.08, None, "e20"),
    ("SL-10%",       -0.10, None, None),
    ("TP15%+SL-8%",  -0.08, 0.15, None),
    ("TP25%+SL-8%",  -0.08, 0.25, None),
    ("ATR3trail+SL-8%", -0.08, None, "atr3"),
]


def sim(P, a, b, ekey, sl, tp, trail):
    """จำลองช่วง [a,b) คืนผลตอบแทนรวม"""
    c = P["c"]; cond = P["ent"][ekey]
    e20, e50, e200, atr = P["e20"], P["e50"], P["e200"], P["atr"]
    held, ep, eq, peak = 0.0, 0.0, 1.0, 0.0
    wins = tot = 0
    for i in range(a + 1, b):
        r = held * (c[i] / c[i - 1] - 1); ft = 0.0
        if held > 0:
            peak = max(peak, c[i])
            chg = c[i] / ep - 1; ex = False
            if chg <= sl: ex = True
            elif tp is not None and chg >= tp: ex = True
            elif trail == "e20" and e20[i] == e20[i] and c[i] < e20[i]: ex = True
            elif trail == "e50" and e50[i] == e50[i] and c[i] < e50[i]: ex = True
            elif trail == "e200" and e200[i] == e200[i] and c[i] < e200[i]: ex = True
            elif trail == "atr3" and atr[i] == atr[i] and c[i] < peak - 3 * atr[i]: ex = True
            if ex:
                tot += 1; wins += 1 if chg > 0 else 0
                ft = FEE; held = 0
        else:
            if cond[i]:
                ft = FEE; held = 1.0; ep = c[i]; peak = c[i]
        eq *= (1 + r - ft)
    return eq - 1, tot, wins


def year_slice(idx, y0, y1):
    a = idx.searchsorted(pd.Timestamp(f"{y0}-01-01"))
    b = idx.searchsorted(pd.Timestamp(f"{y1}-01-01"))
    return a, b


def main():
    syms = group_symbols("SET100 (ทั้งหมด)")
    print(f"โหลดข้อมูล {len(syms)} ตัว (8 ปี)...")
    data = {}
    for s in syms:
        try:
            d = yf.download(s, period="9y", interval="1d", auto_adjust=True, progress=False)
            if d is None or len(d) < 1500:
                continue
            c = d["Close"]; c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
            data[s] = prep(c.dropna())
        except Exception:
            pass
    print(f"ใช้ได้ {len(data)} ตัว\n" + "=" * 78)

    sd = yf.download("^SET.BK", period="9y", interval="1d", auto_adjust=True, progress=False)
    sc = sd["Close"]; sc = sc.iloc[:, 0] if isinstance(sc, pd.DataFrame) else sc
    sc = sc.dropna()

    combos = [(e, x) for e in list(data.values())[0]["ent"] for x in EXITS]
    yearly, log = [], []
    for test_y in range(START + TRAIN_Y, END + 1):
        tr0, tr1 = test_y - TRAIN_Y, test_y
        # ── optimize บน train: median ของผลตอบแทนทั้งกลุ่ม ──
        best, best_med = None, -9
        for ekey, (xn, sl, tp, trail) in combos:
            rets = []
            for P in data.values():
                a, b = year_slice(P["idx"], tr0, tr1)
                if b - a < 300: continue
                rr, _, _ = sim(P, a, b, ekey, sl, tp, trail)
                rets.append(rr)
            if len(rets) >= 20:
                med = float(np.median(rets))
                if med > best_med:
                    best_med, best = med, (ekey, xn, sl, tp, trail)
        ekey, xn, sl, tp, trail = best

        # ── เทสต์ปี unseen ──
        strat, bh, nbeat, nst = [], [], 0, 0
        for P in data.values():
            a, b = year_slice(P["idx"], test_y, test_y + 1)
            if b - a < 150: continue
            rr, _, _ = sim(P, a, b, ekey, sl, tp, trail)
            bhr = P["c"][b - 1] / P["c"][a] - 1
            strat.append(rr); bh.append(bhr); nst += 1
            nbeat += 1 if rr > bhr else 0
        sa, sb = year_slice(sc.index, test_y, test_y + 1)
        set_r = float(sc.iloc[sb - 1] / sc.iloc[sa] - 1) if sb - sa > 50 else np.nan

        yearly.append(dict(Year=test_y, Combo=f"{ekey} | {xn}",
                           TrainMed=round(best_med * 100, 1),
                           Strat=round(np.mean(strat) * 100, 1),
                           BH=round(np.mean(bh) * 100, 1),
                           SET=round(set_r * 100, 1),
                           BeatBH=f"{nbeat}/{nst}"))

    res = pd.DataFrame(yearly)
    res.to_csv("walkforward.csv", index=False)
    print("\nผลรายปี (ปีที่ไม่เคยเห็นตอน optimize):")
    print(res.to_string(index=False))

    print("\n" + "=" * 78)
    g = lambda col: (1 + res[col] / 100).prod() - 1
    print(f"ผลรวมทบต้น 5 ปี unseen:  กลยุทธ์ {g('Strat')*100:+.1f}%  ·  B&H {g('BH')*100:+.1f}%  ·  SET {g('SET')*100:+.1f}%")
    print(f"เฉลี่ย/ปี:  กลยุทธ์ {res['Strat'].mean():+.1f}%  ·  B&H {res['BH'].mean():+.1f}%  ·  SET {res['SET'].mean():+.1f}%")
    print(f"เทียบเป้า 10%/เดือน = ต้องได้ +214%/ปี ทุกปี")
    print("→ บันทึก walkforward.csv")


if __name__ == "__main__":
    main()
