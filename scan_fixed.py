#!/usr/bin/env python
"""
สแกน SET100 ด้วย "ชุดเงื่อนไขเดียว" (ไม่ cherry-pick) → ดูว่า robust จริงไหม
Entry: Close>EMA50 & MACD>0 · Exit: TP+15% / SL-8% (long-only, all-in)
เทียบทั้ง Buy&Hold ของหุ้นเอง และ SET Index
"""
import numpy as np
import pandas as pd
import yfinance as yf
from universe import group_symbols

FEE, TP, SL = 0.002, 0.15, -0.08


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def run(close):
    df = pd.DataFrame({"close": close})
    df["ema50"] = ema(close, 50)
    df["macd"] = ema(close, 12) - ema(close, 26)
    cond = ((df["close"] > df["ema50"]) & (df["macd"] > 0)).values
    c = df["close"].values
    ret = df["close"].pct_change().fillna(0).values
    held, ep, eq, trades = 0.0, 0.0, 1.0, []
    for i in range(len(df)):
        r = held * ret[i]; ft = 0.0
        if held > 0:
            chg = c[i] / ep - 1
            if chg <= SL or chg >= TP:
                trades.append(chg - 2 * FEE); ft = fee_ = FEE; held = 0
        else:
            if cond[i]:
                ft = FEE; held = 1.0; ep = c[i]
        eq *= (1 + r - ft)
    total = eq - 1
    bh = c[-1] / c[0] - 1
    wr = (sum(1 for t in trades if t > 0) / len(trades) * 100) if trades else 0
    return total, bh, len(trades), wr


def main():
    syms = group_symbols("SET100 (ทั้งหมด)")
    print(f"สแกน {len(syms)} ตัว · ชุดเดียว (Close>EMA50 & MACD>0 / TP+15% SL-8%)\n" + "=" * 70)

    # SET reference (5y)
    setdf = yf.download("^SET.BK", period="5y", interval="1d", auto_adjust=True, progress=False)
    set_ret = None
    if setdf is not None and len(setdf):
        sc = setdf["Close"]; sc = sc.iloc[:, 0] if isinstance(sc, pd.DataFrame) else sc
        set_ret = sc.dropna().iloc[-1] / sc.dropna().iloc[0] - 1

    rows = []
    for i, sym in enumerate(syms):
        try:
            df = yf.download(sym, period="5y", interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 250:
                continue
            close = df["Close"]; close = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
            close = close.dropna()
            total, bh, ntr, wr = run(close)
            rows.append(dict(Stock=sym.replace(".BK", ""), Ret=round(total * 100, 1),
                             BH=round(bh * 100, 1), beatBH=total > bh,
                             beatSET=(set_ret is not None and total > set_ret),
                             Trades=ntr, Win=round(wr)))
        except Exception:
            pass

    res = pd.DataFrame(rows).sort_values("Ret", ascending=False).reset_index(drop=True)
    res.to_csv("scan_fixed.csv", index=False)

    n = len(res)
    print(f"\nSET Index 5y: {set_ret*100:+.1f}%\n" if set_ret is not None else "")
    print("TOP 15:")
    print(res.head(15).to_string(index=False))
    print("\n" + "=" * 70)
    print(f"หุ้นที่ทดสอบ: {n}")
    print(f"  ชนะ Buy&Hold ตัวเอง : {res['beatBH'].sum()} / {n}  ({res['beatBH'].mean()*100:.0f}%)")
    if set_ret is not None:
        print(f"  ชนะ SET Index        : {res['beatSET'].sum()} / {n}  ({res['beatSET'].mean()*100:.0f}%)")
    print(f"  ผลตอบแทนเฉลี่ย (กลยุทธ์): {res['Ret'].mean():+.1f}%")
    print(f"  ผลตอบแทนเฉลี่ย (B&H)   : {res['BH'].mean():+.1f}%")
    print(f"\n→ บันทึก scan_fixed.csv")


if __name__ == "__main__":
    main()
