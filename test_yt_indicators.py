#!/usr/bin/env python
"""
ทดสอบ 3 ระบบอินดิเคเตอร์จากคลิป YouTube ที่ user ส่งมา (หา win rate แบบไม่หลอกตัวเอง)
กติกาเดิม: TRAIN(60%)/VALID(20%)/TEST(20%) ตามเวลา, รายงานทุก combo ที่ลอง

ที่มาของแต่ละระบบ (ดึง caption+description จริงจากคลิปด้วย yt-dlp):
A) "RVI + MACD" (คลิป: ถ้าให้เลือกแค่ 2 อินดิเคเตอร์...)
   - RVI (Relative Vigor Index, len=10) ตัด Signal Line ขึ้น หลังจากเคยต่ำกว่า -0.22
   - ยืนยันด้วย MACD(fast=100, slow=200, signal=50) histogram เป็นบวก (เทรนด์ขาขึ้น)
   ต้นฉบับเป็น short ได้ด้วยแต่หุ้นทั่วไป short ยาก จึงทดสอบเฉพาะฝั่ง long

B) "Trend Ribbon + Hull Suite + SuperTrend" (คลิป: อินดิเคเตอร์นี้ใช้เป็นตัวหลักได้เลย)
   - Donchian-based Trend Ribbon length=30 (ต้นฉบับ 20->30) เป็นสีเขียว (close > mid)
   - Hull Suite length=60 (ต้นฉบับ 55->60), slope เป็นบวก
   - SuperTrend atr period=50 (ต้นฉบับ 10->50), atr multiplier=7.0 (ต้นฉบับ 3->7.0) เป็นขาขึ้น
   ต้นฉบับเล่นใน Time Frame Day เป็นตัวกรองเทรนด์ภาพใหญ่ ไม่ใช่จุดเข้าแม่นยำ

C) "RSI Bullish Divergence + EMA12x26 cross" (คลิป: 5 อินดิเคเตอร์ยอดฮิต)
   - เกิด RSI(14) bullish divergence (ราคาทำ New Low แต่ RSI ไม่ทำ New Low ตาม) ในช่วง 20 วันหลังสุด
   - ยืนยันด้วย EMA12 ตัด EMA26 ขึ้น (สัญญาณ "เขียวแรก" ตามที่คลิปอธิบาย) ภายใน 5 วันหลังจากนั้น
"""
import itertools
import sys
import numpy as np
import pandas as pd
import yfinance as yf

FEE = 0.002


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def rvi(o, h, l, c, length=10):
    num = (c - o + 2 * (c.shift(1) - o.shift(1)) + 2 * (c.shift(2) - o.shift(2)) + (c.shift(3) - o.shift(3))) / 6
    den = (h - l + 2 * (h.shift(1) - l.shift(1)) + 2 * (h.shift(2) - l.shift(2)) + (h.shift(3) - l.shift(3))) / 6
    r = num.rolling(length).mean() / den.rolling(length).mean().replace(0, np.nan)
    sig = (r + 2 * r.shift(1) + 2 * r.shift(2) + r.shift(3)) / 6
    return r, sig


def macd_hist(c, fast, slow, sig):
    line = ema(c, fast) - ema(c, slow)
    signal = ema(line, sig)
    return line - signal


def hull(c, n):
    wma_half = c.rolling(n // 2).apply(lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum(), raw=True)
    wma_full = c.rolling(n).apply(lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum(), raw=True)
    raw = 2 * wma_half - wma_full
    sqrt_n = max(int(np.sqrt(n)), 1)
    hma = raw.rolling(sqrt_n).apply(lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum(), raw=True)
    return hma


def donchian_mid(h, l, n):
    return (h.rolling(n).max() + l.rolling(n).min()) / 2


def supertrend(h, l, c, period, mult):
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (h + l) / 2
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    st = pd.Series(index=c.index, dtype=float)
    dirn = pd.Series(index=c.index, dtype=int)
    st.iloc[0] = upper.iloc[0]; dirn.iloc[0] = 1
    for i in range(1, len(c)):
        if pd.isna(atr.iloc[i]):
            st.iloc[i] = st.iloc[i - 1]; dirn.iloc[i] = dirn.iloc[i - 1]
            continue
        if c.iloc[i] > st.iloc[i - 1]:
            dirn.iloc[i] = 1
        elif c.iloc[i] < st.iloc[i - 1]:
            dirn.iloc[i] = -1
        else:
            dirn.iloc[i] = dirn.iloc[i - 1]
        if dirn.iloc[i] == 1:
            st.iloc[i] = max(lower.iloc[i], st.iloc[i - 1]) if dirn.iloc[i - 1] == 1 else lower.iloc[i]
        else:
            st.iloc[i] = min(upper.iloc[i], st.iloc[i - 1]) if dirn.iloc[i - 1] == -1 else upper.iloc[i]
    return dirn


def bullish_divergence(c, r, lookback=20, within=20):
    """True ถ้าราคาทำ New Low ในช่วง lookback วัน แต่ RSI ไม่ทำ New Low ตาม (higher low)"""
    price_ll = c <= c.rolling(lookback, min_periods=lookback).min()
    rsi_higher = r > r.rolling(lookback, min_periods=lookback).min() + 2  # ต้องสูงกว่า low เดิมพอสมควร ไม่ใช่ noise
    div = (price_ll & rsi_higher).fillna(False)
    return div.rolling(within, min_periods=1).max().astype(bool)


def prep(o, h, l, c):
    r, sig = rvi(o, h, l, c)
    r_prev = r.shift(1)
    hist_slow = macd_hist(c, 100, 200, 50)
    a_entry = (r_prev <= sig.shift(1)) & (r > sig) & (r.shift(1).rolling(15).min() < -0.22) & (hist_slow > 0)

    dmid = donchian_mid(h, l, 30)
    hma = hull(c, 60)
    st_dir = supertrend(h, l, c, 50, 7.0)
    b_entry = (c > dmid) & (hma > hma.shift(2)) & (st_dir == 1) & \
              ((c.shift(1) <= dmid.shift(1)) | (hma.shift(1) <= hma.shift(3)) | (st_dir.shift(1) == -1))

    rr = rsi(c, 14)
    div = bullish_divergence(c, rr, lookback=20, within=20)
    e12, e26 = ema(c, 12), ema(c, 26)
    cross_up = (e12.shift(1) <= e26.shift(1)) & (e12 > e26)
    c_entry = div & cross_up

    entries = {
        "RVI+MACD(100,200,50)": a_entry,
        "TrendRibbon+HullSuite+SuperTrend": b_entry,
        "RSI Divergence+EMA12x26": c_entry,
    }
    return dict(c=c.values, entries={k: v.fillna(False).values for k, v in entries.items()})


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


def load_ohlc(sym, years):
    try:
        df = yf.download(sym, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 400:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        o, h, l, c = df["Open"].dropna(), df["High"].dropna(), df["Low"].dropna(), df["Close"].dropna()
        idx = o.index.intersection(h.index).intersection(l.index).intersection(c.index)
        return o.loc[idx], h.loc[idx], l.loc[idx], c.loc[idx]
    except Exception:
        return None


def load_market(label, syms, years):
    print(f"  โหลด {label}: {len(syms)} สัญลักษณ์ ({years} ปี)...")
    data = []
    for s in syms:
        r = load_ohlc(s, years)
        if r is None:
            continue
        o, h, l, c = r
        data.append(prep(o, h, l, c))
    print(f"  ใช้ได้ {len(data)} ตัว")
    return data


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
    sys.path.insert(0, ".")
    from universe import group_symbols, US_STOCKS
    th_syms = group_symbols("SET100 (ทั้งหมด)")
    us_syms = list(US_STOCKS)

    th_data = load_market(f"หุ้นไทย เต็ม ({len(th_syms)} ตัว)", th_syms, 10)
    us_data = load_market(f"หุ้น US เต็ม ({len(us_syms)} ตัว)", us_syms, 10)

    th_res, th_passed = run_market("ตลาดไทย - YT Indicators", th_data)
    us_res, us_passed = run_market("ตลาด US - YT Indicators", us_data)

    if not th_res.empty:
        th_res.to_csv("yt_indicators_thai_all_combos.csv", index=False)
    if not us_res.empty:
        us_res.to_csv("yt_indicators_us_all_combos.csv", index=False)
    print("\nบันทึกทุก combo ที่ลองไว้ที่ yt_indicators_thai_all_combos.csv / yt_indicators_us_all_combos.csv")


if __name__ == "__main__":
    main()
