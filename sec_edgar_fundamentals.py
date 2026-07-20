#!/usr/bin/env python
"""
ดึงงบการเงินย้อนหลังแบบ point-in-time จริงของหุ้นสหรัฐฯ ผ่าน SEC EDGAR API (ฟรี, ทางการ, ไม่ต้องขอ key)
เก็บ "วันที่ยื่นจริง" (filed date) ไว้ด้วย เพื่อใช้สร้าง backtest ที่ไม่มี look-ahead bias

Rate limit ของ SEC: 10 requests/วินาที ทั่วโดเมน sec.gov/data.sec.gov ต้องใส่ User-Agent ที่มีอีเมลจริง
"""
import json
import os
import time
import requests

HEADERS = {"User-Agent": "thai-trade-bot-research contact@example.com"}
TICKER_CIK_CACHE = "sec_ticker_cik_map.json"
FACTS_CACHE_DIR = "sec_facts_cache"
CONCEPTS = ["Revenues", "NetIncomeLoss", "EarningsPerShareDiluted",
            "StockholdersEquity", "OperatingIncomeLoss", "Liabilities"]
REQUEST_DELAY = 0.12  # ~8 req/sec ให้เผื่อ margin จากลิมิต 10/sec


def get_ticker_cik_map():
    if os.path.exists(TICKER_CIK_CACHE):
        with open(TICKER_CIK_CACHE, encoding="utf-8") as f:
            return json.load(f)
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=15)
    r.raise_for_status()
    raw = r.json()
    cik_map = {v["ticker"]: str(v["cik_str"]).zfill(10) for v in raw.values()}
    with open(TICKER_CIK_CACHE, "w", encoding="utf-8") as f:
        json.dump(cik_map, f)
    return cik_map


def fetch_concept(cik, tag, unit_hint=None):
    """คืน list ของ dict {end, val, filed, form, fp} เรียงตามวันที่ end -- เอาเฉพาะ 10-K (รายปี, fp=FY)"""
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    d = r.json()
    units = d.get("units", {})
    unit_key = unit_hint or next(iter(units), None)
    if unit_key is None or unit_key not in units:
        return None
    entries = units[unit_key]
    annual = [e for e in entries if e.get("form") == "10-K" and e.get("fp") == "FY" and "end" in e and "filed" in e]
    # กันข้อมูลซ้ำจากการยื่นแก้ย้อนหลัง (restatement เช่นตอนแตกพาร์) -- เอาแค่ "ยื่นครั้งแรกสุด" ต่อช่วงเวลา end
    dedup = {}
    for e in annual:
        key = e["end"]
        if key not in dedup or e["filed"] < dedup[key]["filed"]:
            dedup[key] = e
    return sorted(dedup.values(), key=lambda x: x["end"])


def fetch_all_facts(symbol, cik):
    cache_file = os.path.join(FACTS_CACHE_DIR, f"{symbol}.json")
    out = {}
    if os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as f:
            out = json.load(f)
    missing = [tag for tag in CONCEPTS if tag not in out]
    if not missing:
        return out
    for tag in missing:
        series = fetch_concept(cik, tag)
        out[tag] = series if series else []
        time.sleep(REQUEST_DELAY)
    os.makedirs(FACTS_CACHE_DIR, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


def fetch_universe(symbols):
    cik_map = get_ticker_cik_map()
    results = {}
    missing = []
    for i, sym in enumerate(symbols):
        cik = cik_map.get(sym)
        if not cik:
            missing.append(sym)
            continue
        results[sym] = fetch_all_facts(sym, cik)
        if (i + 1) % 10 == 0:
            print(f"  ดึงแล้ว {i+1}/{len(symbols)}...")
    if missing:
        print(f"หา CIK ไม่เจอ ({len(missing)} ตัว): {missing}")
    return results


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from universe import US_STOCKS
    print(f"ดึง SEC EDGAR facts {len(US_STOCKS)} หุ้น (มี cache ต่อตัวใน {FACTS_CACHE_DIR}/)...")
    data = fetch_universe(US_STOCKS)
    print(f"เสร็จ {len(data)} ตัว")
