#!/usr/bin/env python
"""
Out-of-Sample test (จับ overfitting)
- แบ่งข้อมูลแต่ละหุ้น: Train (อดีต 65%) / Test (อนาคต 35% ที่ไม่เคยเห็น)
- Optimize: หา combo ที่ดีสุดบน Train (5 entry × 5 exit)
- นำ combo นั้นไปเทสต์บน Test → ดูว่ายังดีอยู่ไหม
- ถ้า Train ดี แต่ Test แย่ = overfit
"""
import numpy as np
import pandas as pd
import yfinance as yf
from universe import group_symbols

FEE = 0.002

EXITS = [
    ("SL-8%+EMA50", -0.08, None, 50),
    ("SL-5%+EMA200", -0.05, None, 200),
    ("SL-10%", -0.10, None, None),
    ("SL-3%+EMA50", -0.03, None, 50),
    ("TP15%+SL-8%", -0.08, 0.15, None),
]


def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def indicators(close):
    df = pd.DataFrame({"close": close})
    for n in (10, 20, 50, 200):
        df[f"ema{n}"] = ema(close, n)
    df["rsi"] = rsi(close); df["macd"] = ema(close, 12) - ema(close, 26)
    df["entries"] = None
    ent = {
        "EMA10>50>200+MACD": (df.ema10 > df.ema50) & (df.ema50 > df.ema200) & (df.macd > 0),
        "EMA20>50>200": (df.ema20 > df.ema50) & (df.ema50 > df.ema200),
        "Close>EMA50+MACD": (df.close > df.ema50) & (df.macd > 0),
        "Close>EMA200+RSI>50": (df.close > df.ema200) & (df.rsi > 50),
        "RSI30-70+EMA10>50": (df.rsi > 30) & (df.rsi < 70) & (df.ema10 > df.ema50),
    }
    return df, ent


def sim(c, cond, e50, e200, sl, tp, trail):
    ret = np.zeros(len(c)); ret[1:] = c[1:] / c[:-1] - 1
    held, ep, eq = 0.0, 0.0, 1.0
    for i in range(len(c)):
        r = held * ret[i]; ft = 0.0
        if held > 0:
            chg = c[i] / ep - 1; ex = False
            if chg <= sl: ex = True
            elif tp is not None and chg >= tp: ex = True
            elif trail == 50 and e50[i] == e50[i] and c[i] < e50[i]: ex = True
            elif trail == 200 and e200[i] == e200[i] and c[i] < e200[i]: ex = True
            if ex: ft = FEE; held = 0
        else:
            if cond[i]: ft = FEE; held = 1.0; ep = c[i]
        eq *= (1 + r - ft)
    return eq - 1


def main():
    syms = group_symbols("SET100 (ทั้งหมด)")
    print(f"Out-of-Sample test · {len(syms)} ตัว · Train 65% / Test 35%\n" + "=" * 70)

    rows = []
    for sym in syms:
        try:
            d = yf.download(sym, period="8y", interval="1d", auto_adjust=True, progress=False)
            if d is None or len(d) < 500:
                continue
            close = d["Close"]; close = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
            close = close.dropna()
            df, ent = indicators(close)
            n = len(df); split = int(n * 0.65)
            e50 = df.ema50.values; e200 = df.ema200.values; c = df.close.values

            # optimize บน train
            best, best_ret = None, -9
            for ename, es in ent.items():
                ev = es.values
                for xn, sl, tp, tr in EXITS:
                    tr_ret = sim(c[:split], ev[:split], e50[:split], e200[:split], sl, tp, tr)
                    if tr_ret > best_ret:
                        best_ret, best = tr_ret, (ename, xn, sl, tp, tr, ev)
            ename, xn, sl, tp, tr, ev = best

            # เทสต์บน test (unseen)
            oos = sim(c[split:], ev[split:], e50[split:], e200[split:], sl, tp, tr)
            oos_bh = c[-1] / c[split] - 1
            rows.append(dict(Stock=sym.replace(".BK", ""), combo=f"{ename} | {xn}",
                             IS=round(best_ret * 100, 1), OOS=round(oos * 100, 1),
                             OOS_BH=round(oos_bh * 100, 1), beat=oos > oos_bh))
        except Exception:
            pass

    res = pd.DataFrame(rows)
    if res.empty:
        print("no data"); return
    res = res.sort_values("OOS", ascending=False).reset_index(drop=True)
    res.to_csv("scan_oos.csv", index=False)

    n = len(res)
    print("\nTOP 12 (เรียงตาม OOS):")
    print(res.head(12).to_string(index=False))
    print("\n" + "=" * 70)
    print(f"หุ้นที่ทดสอบ: {n}")
    print(f"  ผลตอบแทนเฉลี่ย In-Sample (อดีต ที่ optimize) : {res['IS'].mean():+.1f}%")
    print(f"  ผลตอบแทนเฉลี่ย Out-of-Sample (อนาคต unseen)  : {res['OOS'].mean():+.1f}%")
    print(f"  ผลตอบแทนเฉลี่ย B&H (ช่วง Test)               : {res['OOS_BH'].mean():+.1f}%")
    print(f"  ชนะ B&H ในช่วง Test : {res['beat'].sum()} / {n}  ({res['beat'].mean()*100:.0f}%)")
    drop = res['IS'].mean() - res['OOS'].mean()
    print(f"\n  ช่องว่าง IS − OOS = {drop:+.1f}%  (ยิ่งมาก = ยิ่ง overfit)")
    print("→ บันทึก scan_oos.csv")


if __name__ == "__main__":
    main()
