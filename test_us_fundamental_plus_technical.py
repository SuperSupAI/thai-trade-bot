#!/usr/bin/env python
"""
เอาหุ้น US มาให้คะแนน Fundamental Screener (เกณฑ์เดียวกับหุ้นไทย) แล้วแบ่งกลุ่มคะแนนสูง/กลาง/ต่ำ
รันสูตรเทคนิคเดิม (เข้า: EMA Stack + New High / ออก: EMA30<EMA50 + TP15%) เทียบกัน

ข้อจำกัดเดียวกับฝั่งหุ้นไทย: คะแนน fundamental เป็นข้อมูลปัจจุบัน แต่ไม้เทรดมาจากอดีต 15 ปี
เป็น look-ahead bias — ตีความได้แค่ทิศทางกว้างๆ ไม่ใช่กลยุทธ์ point-in-time จริง
"""
import numpy as np
import pandas as pd
import yfinance as yf

CUT = 0.08
YEARS = 15

# รวมหุ้น mega-cap + mid/small-cap จากการทดสอบก่อนหน้า ให้ได้ตัวอย่างกว้างขึ้น
US_STOCKS = [
    "AAPL", "MSFT", "JPM", "V", "PG", "UNH", "HD", "MRK", "KO", "CSCO",
    "CVX", "MCD", "CRM", "WMT", "AXP", "IBM", "GS", "CAT", "HON", "AMGN",
    "BA", "MMM", "TRV", "JNJ", "DIS", "NKE", "VZ", "DOW", "INTC",
    "GOOGL", "AMZN", "META", "NVDA", "XOM", "PFE", "T", "COST", "PEP", "ADBE",
    "DKS", "RH", "WSM", "ULTA", "DECK", "CROX", "FIVE", "BURL", "YETI",
    "ETSY", "WING", "CAKE", "PLNT", "TXT", "CHRW", "HUN", "JBLU", "GNTX",
    "POOL", "FOXF", "OMCL", "MASI", "BLKB", "SAM", "RRC", "CIEN", "ZBRA", "ENPH",
    "FSLR", "CRSP", "EXPE", "NCLH", "RCL", "CCL", "LULU", "DPZ", "CMG", "WEN",
]


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


def score_stock(info):
    roe = info.get('returnOnEquity')
    eps_g = info.get('earningsGrowth')
    de_raw = info.get('debtToEquity')
    de = (de_raw / 100) if de_raw is not None else None
    ebit_m = info.get('operatingMargins')
    pe = info.get('trailingPE')
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
    print(f"ดึง fundamentals หุ้น US {len(US_STOCKS)} ตัว...")
    scores = {}
    for s in US_STOCKS:
        try:
            info = yf.Ticker(s).info
            if info:
                scores[s] = score_stock(info)
        except Exception:
            pass
    print(f"ได้ข้อมูล {len(scores)} ตัว\n")

    high = [s for s, sc in scores.items() if sc >= 4]
    low = [s for s, sc in scores.items() if sc <= 1]
    mid = [s for s, sc in scores.items() if 2 <= sc <= 3]
    print(f"คะแนนสูง (4-5/5): {len(high)} ตัว — {high}")
    print(f"คะแนนต่ำ (0-1/5): {len(low)} ตัว — {low}")
    print(f"คะแนนกลาง (2-3/5): {len(mid)} ตัว\n")

    print(f"โหลดราคา {YEARS} ปีของทั้ง 3 กลุ่ม...")
    data = {}
    for s in high + low + mid:
        try:
            df = yf.download(s, period=f"{YEARS}y", interval="1d", auto_adjust=True, progress=False)
            if df is None or df.empty:
                continue
            c = df["Close"]
            if isinstance(c, pd.DataFrame):
                c = c.iloc[:, 0]
            c = c.dropna()
            if len(c) > 300:
                data[s] = c
        except Exception:
            pass
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
