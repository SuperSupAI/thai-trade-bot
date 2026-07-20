#!/usr/bin/env python
"""
เทส hypothesis "volume มาก่อนราคา" (Wyckoff accumulation) -- ช่วงที่ volume สูงผิดปกติ แต่ราคายัง
ไม่ค่อยขยับ (แปลว่ามีคนสะสมของเงียบๆ) ทำนายผลตอบแทน 3 เดือนข้างหน้าได้ดีกว่าค่าเฉลี่ยตลาดจริงไหม?

สัญญาณ "accumulation": vol_ratio = avg(volume 20 วันล่าสุด) / avg(volume 100 วันก่อนหน้านั้น) > 1.5
  (volume พุ่งขึ้นชัดเจนเทียบฐานเดิม) และ price_range = ผลตอบแทนราคาช่วง 20 วันล่าสุด อยู่ใน [-8%, +8%]
  (ราคายังไม่วิ่งไปไหน ไม่ใช่ volume ที่มากับการวิ่งไปแล้ว)
"""
import pickle
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import US_STOCKS
from safe_fetch import safe_download_one

CACHE_FILE = "us_close_volume_10y_cache.pkl"
FEE = 0.002
STEP = 63


def load_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    print(f"โหลดหุ้น US {len(US_STOCKS)} ตัว (ราคา+volume, 10 ปี)...")
    data = {}
    for i, sym in enumerate(US_STOCKS):
        d = safe_download_one(sym, 10, with_volume=True)
        if d is not None and len(d) > 600:
            data[sym] = d
        if (i + 1) % 20 == 0:
            print(f"  โหลดแล้ว {i+1}/{len(US_STOCKS)}...")
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"ใช้ได้ {len(data)}/{len(US_STOCKS)} ตัว")
    return data


def main():
    data = load_data()
    rows = []
    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or "close" not in df.columns or "volume" not in df.columns:
            continue
        close = df["close"]
        vol = df["volume"]
        n = len(close)
        for i in range(120, n - STEP, 21):  # เดินหน้าทุก ~1 เดือน
            recent_vol = vol.iloc[i - 20:i].mean()
            base_vol = vol.iloc[i - 120:i - 20].mean()
            if base_vol <= 0 or pd.isna(recent_vol) or pd.isna(base_vol):
                continue
            vol_ratio = recent_vol / base_vol
            price_chg_20d = float(close.iloc[i] / close.iloc[i - 20] - 1)
            fwd_ret = float(close.iloc[i + STEP] / close.iloc[i] - 1) - 2 * FEE

            accumulating = (vol_ratio > 1.5) and (-0.08 <= price_chg_20d <= 0.08)
            rows.append(dict(symbol=sym, idx=i, vol_ratio=vol_ratio, price_chg_20d=price_chg_20d,
                              fwd_ret=fwd_ret, accumulating=accumulating))

    df_all = pd.DataFrame(rows)
    print(f"\nรวม {len(df_all)} หุ้น-เดือน จาก {df_all['symbol'].nunique()} หุ้น\n")

    accum = df_all[df_all["accumulating"]]
    not_accum = df_all[~df_all["accumulating"]]

    def stats(d, label):
        if len(d) == 0:
            print(f"{label}: ไม่มีข้อมูล")
            return
        wr = (d["fwd_ret"] > 0).mean() * 100
        avg = d["fwd_ret"].mean() * 100
        median = d["fwd_ret"].median() * 100
        print(f"{label}: n={len(d)}  WR={wr:.1f}%  avg={avg:+.2f}%  median={median:+.2f}%")

    print("=" * 90)
    print("Signal: volume 20 วันล่าสุด > 1.5 เท่าของฐาน 100 วันก่อนหน้า + ราคานิ่ง (+/-8%)")
    print("=" * 90)
    stats(accum, "  Accumulating (volume พุ่ง+ราคานิ่ง)")
    stats(not_accum, "  อื่นๆ (ไม่เข้าเงื่อนไข)")
    stats(df_all, "  ทั้งชุด (baseline)")

    # เช็คแบบละเอียดขึ้น: แบ่ง vol_ratio เป็น quintile ดูว่า monotonic ไหม
    print("\n" + "=" * 90)
    print("แบ่ง vol_ratio เป็น 5 กลุ่ม (quintile) -- ดูว่า volume ยิ่งพุ่ง ผลตอบแทนยิ่งดีขึ้นเรื่อยๆ ไหม")
    print("=" * 90)
    df_all["vr_quintile"] = pd.qcut(df_all["vol_ratio"], 5, labels=["Q1 ต่ำสุด", "Q2", "Q3", "Q4", "Q5 สูงสุด"], duplicates="drop")
    for q in df_all["vr_quintile"].cat.categories:
        d = df_all[df_all["vr_quintile"] == q]
        stats(d, f"  {q}")

    df_all.to_csv("volume_accumulation_signal_results.csv", index=False)
    print("\nบันทึกไว้ที่ volume_accumulation_signal_results.csv")


if __name__ == "__main__":
    main()
