#!/usr/bin/env python
"""
สร้างชุดข้อมูลราคาปิด/ปริมาณซื้อขายย้อนหลัง 50 ปี (1975-2025) จาก set-archive_EOD_1970-LAST.zip
(ไฟล์ EOD รายวันของตลาดหลักทรัพย์ฯ ทุกหลักทรัพย์ — ไม่ต้องพึ่ง yfinance เลย ไม่มี rate-limit/segfault)

หมายเหตุสำคัญ: ราคาในไฟล์นี้เป็นราคาดิบ (ไม่ได้ปรับ split/เงินปันผลแบบหุ้น เหมือนที่ yfinance
auto_adjust=True ทำให้) — ใช้สำหรับ "งานวิจัย/ทดสอบสูตรระยะยาว" เป็นหลัก ไม่ใช้ปนกับ
data/*.csv ที่แอปจริงใช้ (ซึ่งเป็นราคาปรับแล้วจาก yfinance) เพราะจะทำให้ราคาสะดุดที่รอยต่อ

Output: data/archive_close.csv, data/archive_volume.csv (index=วันที่, columns=ticker ไม่มี .BK)
ครอบคลุม SET100 (จาก universe.SECTORS) + ดัชนี SET เอง (ticker "SET" ในไฟล์)
"""
import io
import re
import sys
import zipfile
import pandas as pd

sys.path.insert(0, ".")
from universe import SECTORS

ZIP_PATH = "set-archive_EOD_1970-LAST.zip"
OUT_CLOSE = "data/archive_close.csv"
OUT_VOLUME = "data/archive_volume.csv"

TARGET = sorted({s for lst in SECTORS.values() for s in lst}) + ["SET"]
TARGET_SET = set(TARGET)

DATE_RE = re.compile(r"set-history_EOD_(\d{4}-\d{2}-\d{2})\.csv$")


def main():
    z = zipfile.ZipFile(ZIP_PATH)
    names = [n for n in z.namelist() if n.endswith(".csv")]
    print(f"ไฟล์รายวันทั้งหมด {len(names)} ไฟล์ · เป้าหมาย {len(TARGET)} ticker: {TARGET[:5]}...")

    close_rows = {}   # date -> {ticker: close}
    vol_rows = {}
    bad_files = []
    for i, name in enumerate(names, 1):
        m = DATE_RE.search(name)
        if not m:
            continue
        date = m.group(1)
        try:
            with z.open(name) as f:
                df = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8", errors="ignore"))
            df.columns = [c.strip("<>") for c in df.columns]
            df = df[df["TICKER"].isin(TARGET_SET)]
        except Exception as e:
            bad_files.append((name, str(e)))
            continue
        if df.empty:
            continue
        close_rows[date] = dict(zip(df["TICKER"], df["CLOSE"]))
        vol_rows[date] = dict(zip(df["TICKER"], df["VOL"]))
        if i % 2000 == 0:
            print(f"  ...{i}/{len(names)}")

    if bad_files:
        print(f"\nไฟล์เสีย/อ่านไม่ได้ {len(bad_files)} ไฟล์ (ข้ามไป):")
        for n, err in bad_files[:20]:
            print(f"  {n}: {err}")

    close_df = pd.DataFrame(close_rows).T
    vol_df = pd.DataFrame(vol_rows).T
    close_df.index = pd.to_datetime(close_df.index)
    vol_df.index = pd.to_datetime(vol_df.index)
    close_df = close_df.sort_index()
    vol_df = vol_df.sort_index()

    close_df.to_csv(OUT_CLOSE)
    vol_df.to_csv(OUT_VOLUME)
    print(f"\nบันทึก {OUT_CLOSE} · {OUT_VOLUME}")
    print(f"ช่วงวันที่: {close_df.index.min().date()} .. {close_df.index.max().date()} · แถว {len(close_df)}")
    have = close_df.notna().sum().sort_values(ascending=False)
    print(f"\nจำนวนวันที่มีราคาต่อ ticker (10 อันดับแรก):\n{have.head(10)}")
    missing = [t for t in TARGET if t not in close_df.columns]
    if missing:
        print(f"\nticker ที่ไม่พบเลยในไฟล์: {missing}")


if __name__ == "__main__":
    main()
