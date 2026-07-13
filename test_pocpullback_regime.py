#!/usr/bin/env python
"""
หา win rate ของ "POC Pullback Bounce" (จาก test_volume_profile.py) เฉพาะหุ้น US
แยกตามว่า "วันที่เข้าไม้" ตลาดใหญ่ (SPY) อยู่เหนือ หรือ ต่ำกว่า EMA200 ของตัวเอง
เพื่อดูว่ากลยุทธ์นี้ win rate เท่าไหร่ตอนตลาด US เป็นขาลง (SPY < EMA200)
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
from universe import US_STOCKS, US_MARKET_INDEX

YEARS = 10
WINDOW = 60
NBINS = 24
VA_PCT = 0.70
EXIT_GRID = [(tp, sl) for tp in (0.05, 0.08, 0.10, 0.15) for sl in (0.05, 0.08, 0.10)]
FEE = 0.002


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rolling_volume_profile(close, volume, window=WINDOW, nbins=NBINS, va_pct=VA_PCT):
    n = len(close)
    poc = np.full(n, np.nan)
    vah = np.full(n, np.nan)
    c = close.values
    v = volume.values
    for i in range(window, n):
        seg_c = c[i - window:i]
        seg_v = v[i - window:i]
        lo, hi = seg_c.min(), seg_c.max()
        if hi <= lo:
            continue
        edges = np.linspace(lo, hi, nbins + 1)
        idx = np.clip(np.digitize(seg_c, edges) - 1, 0, nbins - 1)
        vol_per_bin = np.zeros(nbins)
        for b, vv in zip(idx, seg_v):
            vol_per_bin[b] += vv
        centers = (edges[:-1] + edges[1:]) / 2
        poc[i] = centers[vol_per_bin.argmax()]
        total = vol_per_bin.sum()
        if total <= 0:
            continue
        order = sorted(range(nbins), key=lambda b: -vol_per_bin[b])
        acc = 0.0
        included = set()
        for b in order:
            acc += vol_per_bin[b]
            included.add(b)
            if acc >= va_pct * total:
                break
        va_bins = sorted(included)
        vah[i] = centers[va_bins[-1]]
    return pd.Series(poc, index=close.index), pd.Series(vah, index=close.index)


def prep(close, volume):
    e200 = ema(close, 200)
    poc, vah = rolling_volume_profile(close, volume)
    prev_poc = poc.shift(1)
    near_poc = (close.sub(prev_poc).abs() / prev_poc < 0.015)
    was_above_poc_recent = (close.shift(2) > poc.shift(2)) | (close.shift(3) > poc.shift(3))
    cond = (near_poc & was_above_poc_recent & (close > e200) & (close > close.shift(1))).fillna(False)
    return dict(c=close.values, idx=close.index, cond=cond.values)


def sim_trades(P, tp, sl):
    c, idx, cond = P["c"], P["idx"], P["cond"]
    n = len(c)
    held, ep, entry_i = 0.0, 0.0, None
    trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            if chg <= -sl or chg >= tp:
                trades.append(dict(entry_i=entry_i, pnl=chg - 2 * FEE))
                held = 0
        else:
            if cond[i]:
                held = 1.0; ep = c[i]; entry_i = i
    return trades


def main():
    print(f"โหลด {US_MARKET_INDEX} ({YEARS} ปี) เพื่อคำนวณ regime ตลาด US...")
    spy_close = safe_download_one(US_MARKET_INDEX, YEARS)
    spy_e200 = ema(spy_close, 200)
    spy_regime = spy_close > spy_e200  # True = SPY เหนือ EMA200 (ตลาด US ขาขึ้น)

    us_syms = list(US_STOCKS)
    print(f"โหลดหุ้น US: {len(us_syms)} ตัว ({YEARS} ปี)...")
    data = []
    for s in us_syms:
        df = safe_download_one(s, YEARS, with_volume=True)
        if df is None or len(df) <= 400:
            continue
        data.append(prep(df["close"], df["volume"]))
    print(f"ใช้ได้ {len(data)} ตัว\n")

    for tp, sl in EXIT_GRID:
        buckets = {"SPY > EMA200 (US ขาขึ้น)": [], "SPY < EMA200 (US ขาลง/ย่อ)": []}
        for P in data:
            trades = sim_trades(P, tp, sl)
            regime_aligned = spy_regime.reindex(P["idx"]).ffill()
            for t in trades:
                entry_date = P["idx"][t["entry_i"]]
                if entry_date not in regime_aligned.index:
                    continue
                is_up = regime_aligned.loc[entry_date]
                if pd.isna(is_up):
                    continue
                key = "SPY > EMA200 (US ขาขึ้น)" if is_up else "SPY < EMA200 (US ขาลง/ย่อ)"
                buckets[key].append(t["pnl"])

        print("=" * 90)
        print(f"POC Pullback Bounce · TP={tp:.0%} SL={sl:.0%}")
        print("=" * 90)
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
