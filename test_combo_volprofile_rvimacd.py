#!/usr/bin/env python
"""
ทดสอบรวม (combo) Volume Profile "POC Pullback Bounce" + RVI+MACD(100,200,50)
เข้าเฉพาะเมื่อสัญญาณทั้ง 2 ระบบ "ตรงกันในวันเดียวกัน" เท่านั้น (AND condition)
เทียบกับแต่ละระบบเดี่ยวๆ บนชุดข้อมูลเดียวกัน (หุ้น US เต็ม 77 ตัว เพราะเป็นตลาดเดียวที่มี edge จริง)
กติกาเดิม: TRAIN(60%)/VALID(20%)/TEST(20%) ตามเวลา, รายงานทุก combo
"""
import itertools
import sys
import numpy as np
import pandas as pd
import yfinance as yf

FEE = 0.002
WINDOW = 60
NBINS = 24
VA_PCT = 0.70


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def macd_hist(c, fast, slow, sig):
    line = ema(c, fast) - ema(c, slow)
    signal = ema(line, sig)
    return line - signal


def rvi(o, h, l, c, length=10):
    num = (c - o + 2 * (c.shift(1) - o.shift(1)) + 2 * (c.shift(2) - o.shift(2)) + (c.shift(3) - o.shift(3))) / 6
    den = (h - l + 2 * (h.shift(1) - l.shift(1)) + 2 * (h.shift(2) - l.shift(2)) + (h.shift(3) - l.shift(3))) / 6
    r = num.rolling(length).mean() / den.rolling(length).mean().replace(0, np.nan)
    sig = (r + 2 * r.shift(1) + 2 * r.shift(2) + r.shift(3)) / 6
    return r, sig


def rolling_volume_profile(close, volume, window=WINDOW, nbins=NBINS, va_pct=VA_PCT):
    n = len(close)
    poc = np.full(n, np.nan)
    c = close.values; v = volume.values
    for i in range(window, n):
        seg_c = c[i - window:i]; seg_v = v[i - window:i]
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
    return pd.Series(poc, index=close.index)


def prep(o, h, l, c, v):
    e200 = ema(c, 200)
    poc = rolling_volume_profile(c, v)
    prev_poc = poc.shift(1)
    near_poc = (c.sub(prev_poc).abs() / prev_poc < 0.015)
    was_above_poc_recent = (c.shift(2) > poc.shift(2)) | (c.shift(3) > poc.shift(3))
    vp_entry = near_poc & was_above_poc_recent & (c > e200) & (c > c.shift(1))

    r, sig = rvi(o, h, l, c)
    r_prev = r.shift(1)
    hist_slow = macd_hist(c, 100, 200, 50)
    rvi_entry = (r_prev <= sig.shift(1)) & (r > sig) & (r.shift(1).rolling(15).min() < -0.22) & (hist_slow > 0)

    combo_entry = vp_entry & rvi_entry

    entries = {
        "VolProfile POC Pullback (เดี่ยว)": vp_entry,
        "RVI+MACD (เดี่ยว)": rvi_entry,
        "COMBO: ทั้งคู่ตรงกัน": combo_entry,
    }
    return dict(c=c.values, entries={k: vv.fillna(False).values for k, vv in entries.items()})


EXIT_GRID = [(tp, sl) for tp in (0.05, 0.08, 0.10, 0.15) for sl in (0.05, 0.08, 0.10)]


def sim(c, cond, tp, sl):
    n = len(c); held, ep = 0.0, 0.0; trades = []
    for i in range(n):
        if held > 0:
            chg = c[i] / ep - 1
            if chg <= -sl or chg >= tp:
                trades.append(chg); held = 0
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


def load_ohlcv(sym, years):
    try:
        df = yf.download(sym, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 400:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        o, h, l, c, v = (df[k].dropna() for k in ("Open", "High", "Low", "Close", "Volume"))
        idx = o.index
        for s in (h, l, c, v):
            idx = idx.intersection(s.index)
        return o.loc[idx], h.loc[idx], l.loc[idx], c.loc[idx], v.loc[idx]
    except Exception:
        return None


def load_market(label, syms, years):
    print(f"  โหลด {label}: {len(syms)} สัญลักษณ์ ({years} ปี)...")
    data = []
    for s in syms:
        r = load_ohlcv(s, years)
        if r is None:
            continue
        o, h, l, c, v = r
        data.append(prep(o, h, l, c, v))
    print(f"  ใช้ได้ {len(data)} ตัว")
    return data


def run_market(label, data_p):
    if not data_p:
        print(f"\n{'='*100}\n{label}: ไม่มีข้อมูลพอ\n{'='*100}")
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
                & (res.valid_n >= 30) & (res.test_n >= 30)]
    print(f"\nผ่านเกณฑ์ (valid WR>=55%, test WR>=52%, กำไรเฉลี่ยบวกทั้งคู่, ไม้>=30 -- ลดเกณฑ์ n เพราะ COMBO สัญญาณจะเกิดยากขึ้นมาก): {len(passed)} combo")
    if not passed.empty:
        print(passed.sort_values("test_wr", ascending=False).to_string(index=False))
    else:
        print("ไม่มี combo ไหนผ่านครบทุกเกณฑ์")

    print("\nทุก combo เรียงตาม entry แล้วตาม test_wr:")
    print(res.sort_values(["entry", "test_wr"], ascending=[True, False]).to_string(index=False))
    return res, passed


def main():
    sys.path.insert(0, ".")
    from universe import US_STOCKS
    us_syms = list(US_STOCKS)
    us_data = load_market(f"หุ้น US เต็ม ({len(us_syms)} ตัว)", us_syms, 10)
    us_res, us_passed = run_market("ตลาด US - COMBO Volume Profile + RVI/MACD", us_data)
    if not us_res.empty:
        us_res.to_csv("combo_volprofile_rvimacd_us_all_combos.csv", index=False)
    print("\nบันทึกไว้ที่ combo_volprofile_rvimacd_us_all_combos.csv")


if __name__ == "__main__":
    main()
