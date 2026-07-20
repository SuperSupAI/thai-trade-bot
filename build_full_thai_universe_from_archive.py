#!/usr/bin/env python
"""
แปลง archive รายวัน (set-history_EOD_YYYY-MM-DD.csv, ไฟล์ละ 1 วัน ทุกหุ้นในตลาด) ให้เป็น
dict {ticker: pd.Series close} แบบเดียวกับ cache อื่นๆ ในโปรเจกต์ -- ครอบคลุม ~10 ปีล่าสุดที่มีข้อมูล
(archive มีถึงแค่ 2025-12-30) เร็วกว่าดาวน์โหลดทีละตัวผ่าน yfinance มาก เพราะเป็นไฟล์ในเครื่องอยู่แล้ว
"""
import glob
import os
import pickle
import pandas as pd

ARCHIVE_DIR = r"set-archive_EOD_1970-LAST (1)\set-archive_EOD_1970-LAST"
OUT_FILE = "thai_all_stocks_archive_10y_cache.pkl"
START_DATE = "2015-12-30"  # ~10 ปีก่อนวันสุดท้ายที่มีข้อมูล (2025-12-30)


SPLIT_RATIOS = [1/2, 1/3, 1/4, 1/5, 1/10, 1/20, 1/25, 1/50, 1/100, 2, 3, 4, 5, 10, 20, 25, 50, 100]


def adjust_splits(s, jump_threshold=0.5, tolerance=0.15):
    """ตรวจจับวันที่ราคากระโดดผิดปกติ (>jump_threshold) แล้วเช็คว่าใกล้เคียงอัตราส่วนแตกพาร์มาตรฐานไหม
    (1:2, 1:5, 1:10 ฯลฯ) ถ้าใช่ ปรับราคาก่อนวันนั้นทั้งหมดให้ต่อเนื่องกับหลังแตกพาร์ (คูณด้วยอัตราส่วน)
    ถ้าไม่ตรงอัตราส่วนใดๆ เลย (ต่างเกิน tolerance) ถือว่าน่าสงสัยเป็น data error -- คืน None ให้ตัดทิ้ง"""
    s = s.sort_index().copy()
    ret = s.pct_change()
    jump_dates = ret[ret.abs() > jump_threshold].index.tolist()
    for d in jump_dates:
        idx = s.index.get_loc(d)
        if idx == 0:
            continue
        price_before = s.iloc[idx - 1]
        price_after = s.iloc[idx]
        if price_before <= 0:
            return None
        ratio = price_after / price_before
        closest = min(SPLIT_RATIOS, key=lambda c: abs(c - ratio))
        if abs(closest - ratio) / closest > tolerance:
            return None  # ไม่ตรงอัตราส่วนแตกพาร์มาตรฐานใดๆ -- น่าจะเป็น data error จริง ตัดทิ้ง
        s.iloc[:idx] = s.iloc[:idx] * closest
    return s


def main():
    pattern = os.path.join(ARCHIVE_DIR, "set-history_EOD_*.csv")
    files = sorted(glob.glob(pattern))
    files = [f for f in files if os.path.basename(f).replace("set-history_EOD_", "").replace(".csv", "") >= START_DATE]
    print(f"ไฟล์ที่จะอ่าน (ตั้งแต่ {START_DATE}): {len(files)} ไฟล์")

    dfs = []
    for i, f in enumerate(files):
        try:
            df = pd.read_csv(f, usecols=["<TICKER>", "<DTYYYYMMDD>", "<CLOSE>"])
        except Exception:
            continue
        df.columns = ["ticker", "date", "close"]
        dfs.append(df)
        if (i + 1) % 500 == 0:
            print(f"  อ่านแล้ว {i+1}/{len(files)} ไฟล์...")

    print("รวมข้อมูลทั้งหมด...")
    all_df = pd.concat(dfs, ignore_index=True)
    all_df["date"] = pd.to_datetime(all_df["date"], format="%Y%m%d")
    print(f"รวม {len(all_df):,} แถว, หุ้นทั้งหมด {all_df['ticker'].nunique():,} ตัว")

    print("Pivot เป็น wide format ต่อหุ้น...")
    wide = all_df.pivot_table(index="date", columns="ticker", values="close", aggfunc="last")

    INDEX_NAMES = {"SET", "SET50", "SET100", "sSET", "mai", "SETCLMV", "SETESG", "SETHD",
                   "SETTHSI", "SETWB", "SETIB", "SETIBSI"}

    data = {}
    skipped_short = 0
    skipped_notstock = 0
    skipped_baddata = 0
    for ticker in wide.columns:
        # ตัด ticker พิเศษที่ไม่ใช่หุ้นสามัญ (ดัชนีกลุ่มอุตสาหกรรม ขึ้นต้นด้วย !/$ , ดัชนีตลาดหลัก)
        if not ticker[0].isalnum() or ticker in INDEX_NAMES:
            skipped_notstock += 1
            continue

        raw = wide[ticker]
        s = pd.to_numeric(raw, errors="coerce").dropna()
        s = s[s > 0]
        if len(s) < 1200:  # ต้องมีข้อมูลอย่างน้อย ~5 ปี ถึงจะพอสำหรับ formation period 252 วัน + มีที่ทดสอบ
            skipped_short += 1
            continue

        # ปรับราคาย้อนหลังสำหรับหุ้นที่แตกพาร์จริง (ไม่ใช่แค่ตัดทิ้ง) -- คืน None ถ้าดูเหมือน data error จริง
        adjusted = adjust_splits(s)
        if adjusted is None:
            skipped_baddata += 1
            continue

        data[ticker] = adjusted

    print(f"ใช้ได้จริง: {len(data)} ตัว")
    print(f"  ตัดเพราะไม่ใช่หุ้นสามัญ (ดัชนี/กลุ่มอุตสาหกรรม): {skipped_notstock}")
    print(f"  ตัดเพราะข้อมูลสั้นเกินไป (<1200 วัน): {skipped_short}")
    print(f"  ตัดเพราะราคากระโดดผิดปกติ >70%/วัน (สงสัย split/data error ไม่ได้ปรับย้อนหลัง): {skipped_baddata}")

    with open(OUT_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"บันทึกไว้ที่ {OUT_FILE}")


if __name__ == "__main__":
    main()
