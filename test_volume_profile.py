#!/usr/bin/env python
"""
ทดสอบกลยุทธ์ Volume Profile หา win rate แบบไม่หลอกตัวเอง
กติกาเดียวกับ test_winrate_60_search.py: แบ่ง TRAIN(60%)/VALID(20%)/TEST(20%) ตามเวลา
หา combo ทั้งหมดบน TRAIN ไม่ได้ใช้เลือก, รายงานผลทุก combo ที่ลอง (กัน survivorship)

Volume Profile คืออะไร: แบ่งช่วงราคาย้อนหลัง N วัน (rolling window) เป็น bin แล้วรวม volume
ที่เทรดในแต่ละ bin ราคา -> ได้กราฟแท่งนอน (profile) บอกว่าราคาระดับไหน "มีคนซื้อขายเยอะที่สุด"
  - POC (Point of Control) = ราคา bin ที่ volume สูงสุด (แนวรับ/แนวต้านที่แข็งแรงสุด)
  - Value Area (VA) = ช่วงราคาที่รวม volume ได้ 70% ของทั้งหมด (สมมาตรรอบ POC)
    VAH = ขอบบน, VAL = ขอบล่าง
Entry ที่ทดสอบ (อิงตรรกะ volume profile จริง ไม่ใช่แค่ราคาเฉยๆ):
  1. Breakout เหนือ VAH + volume วันนั้นสูงกว่าเฉลี่ย -> ราคาหลุดโซนสมดุลขึ้นไปแบบมีแรงซื้อจริง
  2. Breakout เหนือ POC เดิม (ราคาที่แน่นที่สุด) + close > EMA200 (เทรนด์ขึ้น)
  3. Pullback กลับไปแตะ POC จากด้านบนแล้วเด้ง (ซื้อที่แนวรับ POC ในเทรนด์ขึ้น)
  4. Breakout เหนือ HVN (High Volume Node) ล่าสุดที่เคยเป็นแนวต้าน
"""
import itertools
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
from universe import group_symbols, US_STOCKS

FEE = 0.002
WINDOW = 60      # rolling window สำหรับสร้าง volume profile (วัน)
NBINS = 24       # จำนวน bin ราคาในแต่ละ profile
VA_PCT = 0.70    # Value Area ครอบคลุม 70% ของ volume


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rolling_volume_profile(close, volume, window=WINDOW, nbins=NBINS, va_pct=VA_PCT):
    """คืน POC, VAH, VAL ของแต่ละวัน (อิง window วันย้อนหลัง ไม่ล่วงรู้อนาคต)"""
    n = len(close)
    poc = np.full(n, np.nan)
    vah = np.full(n, np.nan)
    val = np.full(n, np.nan)
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
        poc_bin = vol_per_bin.argmax()
        poc[i] = centers[poc_bin]

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
        val[i] = centers[va_bins[0]]
    return pd.Series(poc, index=close.index), pd.Series(vah, index=close.index), pd.Series(val, index=close.index)


def prep(close, volume):
    e200 = ema(close, 200)
    avg_vol20 = volume.rolling(20).mean()
    poc, vah, val = rolling_volume_profile(close, volume)

    prev_poc = poc.shift(1)
    prev_vah = vah.shift(1)
    prev_close = close.shift(1)

    # ยอดเป็นแนวต้านที่เคยแตะแต่ผ่านไม่ได้ในช่วง window ก่อนหน้า (proxy HVN resistance = VAH เดิม)
    hvn_res = vah.shift(1).rolling(20).max()

    near_poc = (close.sub(prev_poc).abs() / prev_poc < 0.015)
    was_above_poc_recent = (close.shift(2) > poc.shift(2)) | (close.shift(3) > poc.shift(3))

    entries = {
        "VAH Breakout+Volume": (prev_close <= prev_vah) & (close > prev_vah) & (volume > avg_vol20 * 1.3),
        "POC Breakout+Uptrend": (prev_close <= prev_poc) & (close > prev_poc) & (close > e200),
        "POC Pullback Bounce": near_poc & was_above_poc_recent & (close > e200) & (close > close.shift(1)),
        "HVN Resistance Break": (prev_close <= hvn_res) & (close > hvn_res) & (close > e200),
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
    data = []
    for s in syms:
        df = safe_download_one(s, years, with_volume=True)
        if df is None or len(df) <= 400:
            continue
        data.append(prep(df["close"], df["volume"]))
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
    th_syms = group_symbols("SET100 (ทั้งหมด)")
    us_syms = list(US_STOCKS)

    th_data = load_market(f"หุ้นไทย (SET100 เต็ม {len(th_syms)} ตัว)", th_syms, 10)
    us_data = load_market(f"หุ้น US (เต็ม {len(us_syms)} ตัว)", us_syms, 10)

    th_res, th_passed = run_market("ตลาดไทย - Volume Profile", th_data)
    us_res, us_passed = run_market("ตลาด US - Volume Profile", us_data)

    if not th_res.empty:
        th_res.to_csv("volprofile_thai_all_combos.csv", index=False)
    if not us_res.empty:
        us_res.to_csv("volprofile_us_all_combos.csv", index=False)
    print("\nบันทึกทุก combo ที่ลองไว้ที่ volprofile_thai_all_combos.csv / volprofile_us_all_combos.csv")


if __name__ == "__main__":
    main()
