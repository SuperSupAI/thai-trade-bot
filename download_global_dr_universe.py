#!/usr/bin/env python
"""
ดาวน์โหลดราคาย้อนหลัง 10 ปีของหุ้นที่มี DR บน SET จากประเทศอื่นๆ นอกจากสหรัฐฯ
(ญี่ปุ่น, ฮ่องกง/จีน, สิงคโปร์) -- เจอจากการหาข้อมูล DR ล่าสุด ก.ค. 2026 (Finnomena/Yuanta)
เก็บแยกไฟล์แคชต่อประเทศ (คนละสกุลเงิน คนละ trading calendar) ไม่ปนกับ us_close_10y_cache.pkl
"""
import pickle
import sys

sys.path.insert(0, ".")
from safe_fetch import safe_download_many

JAPAN_TICKERS = {
    "7203.T": "Toyota", "6758.T": "Sony", "9984.T": "SoftBank", "8306.T": "MUFG",
    "8316.T": "SMFG", "8001.T": "Itochu", "8058.T": "Mitsubishi Corp", "6861.T": "Keyence",
    "8035.T": "Tokyo Electron", "9983.T": "Fast Retailing", "7974.T": "Nintendo",
    "8136.T": "Sanrio", "6857.T": "Advantest", "7267.T": "Honda",
}

HK_CHINA_TICKERS = {
    "0700.HK": "Tencent", "1810.HK": "Xiaomi", "3690.HK": "Meituan", "1211.HK": "BYD",
    "1024.HK": "Kuaishou", "9618.HK": "JD.com", "9888.HK": "Baidu", "1398.HK": "ICBC",
    "0941.HK": "China Mobile", "0857.HK": "PetroChina", "2318.HK": "Ping An",
    "9999.HK": "NetEase", "2899.HK": "Zijin Mining", "0981.HK": "SMIC",
    "0175.HK": "Geely", "0388.HK": "HKEX",
}

SINGAPORE_TICKERS = {
    "D05.SI": "DBS", "U11.SI": "UOB", "C6L.SI": "Singapore Airlines", "Z74.SI": "Singtel",
    "S68.SI": "SGX", "U96.SI": "Sembcorp", "S63.SI": "ST Engineering", "V03.SI": "Venture Corp",
}

BASKETS = {
    "japan_dr_10y_cache.pkl": JAPAN_TICKERS,
    "hk_china_dr_10y_cache.pkl": HK_CHINA_TICKERS,
    "singapore_dr_10y_cache.pkl": SINGAPORE_TICKERS,
}


def main():
    for cache_file, tickers in BASKETS.items():
        print(f"\n{'='*80}\n{cache_file}: {len(tickers)} ตัว -> {list(tickers.keys())}\n{'='*80}")

        def progress(i, n):
            print(f"  {i}/{n}")

        data = safe_download_many(list(tickers.keys()), years=10, min_rows=210, progress_cb=progress)
        print(f"ดาวน์โหลดสำเร็จ: {len(data)}/{len(tickers)} ตัว")
        failed = [s for s in tickers if s not in data]
        if failed:
            print(f"ล้มเหลว/ข้อมูลไม่พอ: {failed}")
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        print(f"บันทึกไว้ที่ {cache_file}")


if __name__ == "__main__":
    main()
