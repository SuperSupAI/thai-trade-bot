#!/usr/bin/env python
"""
ดึงข้อมูลราคา + fundamentals ของหุ้นกลุ่มหลัก (SET100 + SET Index) แล้วเก็บลงไฟล์ใน data/
รันวันละครั้งผ่าน GitHub Action (.github/workflows/update-data.yml) หลังตลาดปิด
แอป (app.py) จะโหลดจากไฟล์พวกนี้ก่อน — ไม่ต้องยิง yfinance สดทุกครั้งที่มีคนเปิดแอป
(ลดปัญหาโดน Yahoo rate-limit บน Streamlit Cloud)
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from universe import SECTORS
from safe_fetch import safe_download_one, safe_fetch_info

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
YEARS = 5
SET_SYMBOL = "^SET.BK"


def build_universe():
    """SET100 (จาก SECTORS) + SET Index — ไม่รวม SET Index ทั้งกลุ่ม ~900 ตัว (ใหญ่เกินไปสำหรับ cache รายวัน)"""
    syms = sorted({s for lst in SECTORS.values() for s in lst})
    return [s + ".BK" for s in syms] + [SET_SYMBOL]


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    universe = build_universe()
    print(f"อัปเดตข้อมูล {len(universe)} สัญลักษณ์ (ปี ย้อนหลัง {YEARS} ปี)...")

    prices, volumes, funds = {}, {}, {}
    for i, sym in enumerate(universe, 1):
        df = safe_download_one(sym, YEARS, with_volume=True)
        if df is not None and not df.empty:
            prices[sym] = df["close"]
            volumes[sym] = df["volume"]
        else:
            print(f"  [{i}/{len(universe)}] {sym}: ไม่มีข้อมูลราคา")

        if sym != SET_SYMBOL:
            info = safe_fetch_info(sym)
            if info:
                de_raw = info.get('debtToEquity')  # yfinance คืนเป็น % ไม่ใช่ ratio ตรงๆ (เช่น 60.6 = D/E 0.606)
                funds[sym] = {
                    'pe_ratio': info.get('trailingPE'),
                    'roe': info.get('returnOnEquity'),
                    'de_ratio': (de_raw / 100) if de_raw is not None else None,
                    'gross_margin': info.get('grossMargins'),
                    'ebit_margin': info.get('operatingMargins'),
                    'eps_growth': info.get('earningsGrowth'),
                    'profit_margin': info.get('profitMargins'),
                    'price': info.get('currentPrice'),
                    'market_cap': info.get('marketCap'),
                }

        if i % 10 == 0:
            print(f"  ...{i}/{len(universe)}")

    if not prices:
        print("ไม่มีข้อมูลราคาเลย — ยกเลิกการเขียนไฟล์ (กันเขียนทับ cache เดิมด้วยข้อมูลว่าง)")
        sys.exit(1)

    # ใช้ CSV แทน parquet — parquet ต้องพึ่ง pyarrow (C extension) ซึ่งเสี่ยง segfault บน
    # Python เวอร์ชันใหม่มากๆ ของ Streamlit Cloud (เจอปัญหานี้มาแล้วกับ yfinance/curl_cffi)
    price_df = pd.DataFrame(prices).sort_index()
    vol_df = pd.DataFrame(volumes).sort_index()
    price_df.to_csv(os.path.join(DATA_DIR, "prices.csv"))
    vol_df.to_csv(os.path.join(DATA_DIR, "volumes.csv"))
    with open(os.path.join(DATA_DIR, "fundamentals.json"), "w", encoding="utf-8") as f:
        json.dump(funds, f, ensure_ascii=False)
    with open(os.path.join(DATA_DIR, "updated_at.txt"), "w") as f:
        f.write(str(int(time.time())))

    print(f"บันทึกราคา {len(prices)}/{len(universe)} ตัว · fundamentals {len(funds)} ตัว → {DATA_DIR}")


if __name__ == "__main__":
    main()
