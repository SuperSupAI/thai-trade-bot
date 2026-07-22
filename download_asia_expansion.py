#!/usr/bin/env python
"""
ขยาย basket เอเชียจาก 38 ตัวเดิม (japan/hk_china/singapore_dr_10y_cache.pkl) เพิ่มตัวที่มั่นใจเรื่อง
ticker จริง จากลิสต์ DR เอเชีย 102 ตัวที่ผู้ใช้ paste มา -- ตัวที่ไม่มั่นใจ ticker แน่ชัด (เช่น IPO ใหม่มาก,
บริษัทเล็ก หา ticker ไม่ชัดเจน) คัดออกไปเลย ไม่เดา (กันบั๊กแบบ TEL/GOLD ก่อนหน้านี้)
เวียดนามไม่รวม เพราะ yfinance ไม่ค่อยรองรับหุ้นรายตัวบน HOSE (โปรเจกต์นี้เคยใช้แค่ ETF VNM แทน)
"""
import pickle, sys
sys.path.insert(0, ".")
from safe_fetch import safe_download_many

NEW_JAPAN = {
    "7936.T": "ASICS", "6146.T": "Disco", "6954.T": "FANUC", "6501.T": "Hitachi",
    "9766.T": "Konami", "4063.T": "Shin-Etsu Chemical", "3563.T": "Food & Life (Sushiro)",
}
NEW_HK_CHINA = {
    "9988.HK": "Alibaba", "9626.HK": "Bilibili", "300750.SZ": "CATL", "3968.HK": "China Merchants Bank",
    "1772.HK": "Ganfeng Lithium", "9698.HK": "GDS Holdings", "6690.HK": "Haier Smart Home",
    "3692.HK": "Hansoh Pharma", "1347.HK": "Hua Hong Semiconductor", "6618.HK": "JD Health",
    "3888.HK": "Kingsoft", "0992.HK": "Lenovo", "0300.HK": "Midea Group", "9633.HK": "Nongfu Spring",
    "9992.HK": "Pop Mart", "1177.HK": "Sino Biopharmaceutical", "2382.HK": "Sunny Optical",
    "2269.HK": "WuXi Biologics", "2359.HK": "WuXi AppTec", "9688.HK": "Zai Lab",
    "600519.SS": "Kweichow Moutai", "600900.SS": "China Yangtze Power", "002230.SZ": "iFlytek",
    "002371.SZ": "NAURA Technology", "1299.HK": "AIA Group", "2020.HK": "Anta Sports",
    "2238.HK": "GAC Group", "0020.HK": "SenseTime", "1698.HK": "Tencent Music", "9961.HK": "Trip.com",
    "9868.HK": "XPeng",
}
NEW_SINGAPORE = {
    "Y92.SI": "Thai Beverage",
}

def progress(i, n):
    print(f"  {i}/{n}")

for cache_file, new_tickers in [
    ("japan_dr_10y_cache.pkl", NEW_JAPAN),
    ("hk_china_dr_10y_cache.pkl", NEW_HK_CHINA),
    ("singapore_dr_10y_cache.pkl", NEW_SINGAPORE),
]:
    with open(cache_file, "rb") as f:
        existing = pickle.load(f)
    missing = [t for t in new_tickers if t not in existing]
    print(f"\n{'='*80}\n{cache_file}: เพิ่ม {len(missing)}/{len(new_tickers)} ตัวใหม่\n{'='*80}")
    if missing:
        results = safe_download_many(missing, years=10, min_rows=210, progress_cb=progress)
        print(f"สำเร็จ {len(results)}/{len(missing)}")
        failed = [t for t in missing if t not in results]
        if failed:
            print("ล้มเหลว/ข้อมูลไม่พอ:", failed)
        existing.update(results)
        with open(cache_file, "wb") as f:
            pickle.dump(existing, f)
    print(f"{cache_file} ตอนนี้มี {len(existing)} ตัว")
