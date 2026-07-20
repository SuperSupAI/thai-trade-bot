#!/usr/bin/env python
"""
ดาวน์โหลดราคาย้อนหลัง 10 ปีของหุ้นที่มี DR ซื้อขายจริงบน SET แต่ยังไม่มีในแคช
(เจอจากการหาข้อมูลล่าสุด ก.ค. 2026 -- ตลาด DR ไทยขยายจาก ~21 ตัวเป็น ~410 DR / ~45 underlying ไม่ซ้ำ)
เพิ่มเข้า us_close_10y_cache.pkl (ของเดิมไม่โดนทับ แค่เพิ่มตัวใหม่)
"""
import pickle
import sys

sys.path.insert(0, ".")
from safe_fetch import safe_download_many

CACHE_FILE = "us_close_10y_cache.pkl"

NEW_DR_TICKERS = [
    "ABBV", "AMD", "AVGO", "BAC", "BDX", "BKNG", "BRK-B", "EL", "ISRG", "LLY",
    "MA", "MELI", "MU", "MNST", "MS", "NDAQ", "NFLX", "ORCL", "PANW", "PLTR",
    "RBLX", "SBUX", "SNOW", "SPOT", "TSLA", "UBER",
]


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"แคชเดิม: {len(data)} ตัว")

    missing = [s for s in NEW_DR_TICKERS if s not in data]
    print(f"ต้องดาวน์โหลดเพิ่ม: {len(missing)} ตัว -> {missing}")

    def progress(i, n):
        print(f"  {i}/{n}")

    new_data = safe_download_many(missing, years=10, min_rows=210, progress_cb=progress)
    print(f"ดาวน์โหลดสำเร็จ: {len(new_data)}/{len(missing)} ตัว")
    failed = [s for s in missing if s not in new_data]
    if failed:
        print(f"ล้มเหลว/ข้อมูลไม่พอ: {failed}")

    data.update(new_data)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"บันทึกแคชใหม่: {len(data)} ตัว รวม -> {CACHE_FILE}")


if __name__ == "__main__":
    main()
