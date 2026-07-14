#!/usr/bin/env python
"""
สำรวจตลาดหุ้นประเทศอื่นๆ เทียบกับ SPY (US) — ใช้ ETF ดัชนีรายประเทศเป็นตัวแทน (Buy & Hold 10 ปี)
ช่วงเวลาเดียวกับที่เทส SPY มาตลอด (2016-07 ถึง 2026-07)
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one

YEARS = 10

MARKETS = {
    "🇺🇸 US (SPY)": "SPY",
    "🇯🇵 ญี่ปุ่น (EWJ)": "EWJ",
    "🇩🇪 เยอรมนี (EWG)": "EWG",
    "🇬🇧 อังกฤษ (EWU)": "EWU",
    "🇫🇷 ฝรั่งเศส (EWQ)": "EWQ",
    "🇨🇳 จีน (MCHI)": "MCHI",
    "🇭🇰 ฮ่องกง (EWH)": "EWH",
    "🇮🇳 อินเดีย (INDA)": "INDA",
    "🇰🇷 เกาหลีใต้ (EWY)": "EWY",
    "🇹🇼 ไต้หวัน (EWT)": "EWT",
    "🇻🇳 เวียดนาม (VNM)": "VNM",
    "🇹🇭 ไทย (THD)": "THD",
    "🇧🇷 บราซิล (EWZ)": "EWZ",
    "🇦🇺 ออสเตรเลีย (EWA)": "EWA",
    "🇨🇦 แคนาดา (EWC)": "EWC",
    "🌍 ตลาดเกิดใหม่รวม (EEM)": "EEM",
    "🌐 ทั่วโลกรวม (VT)": "VT",
}


def cagr_maxdd(series):
    yrs = len(series) / 252
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0
    maxdd = ((series / series.cummax() - 1).min()) * 100
    return cagr, maxdd


def main():
    print(f"ดาวน์โหลด ETF ดัชนีรายประเทศ {len(MARKETS)} ตลาด ({YEARS} ปี)...\n")
    rows = []
    for label, sym in MARKETS.items():
        c = safe_download_one(sym, YEARS)
        if c is None or len(c) < 200:
            print(f"  {label} ({sym}): โหลดไม่ได้ ข้าม")
            continue
        ret_pct = (c.iloc[-1] / c.iloc[0] - 1) * 100
        cagr, maxdd = cagr_maxdd(c)
        rows.append(dict(ตลาด=label, ticker=sym, ผลตอบแทนรวม=round(ret_pct, 1),
                         CAGR=round(cagr, 1), MaxDD=round(maxdd, 1),
                         ช่วงข้อมูล=f"{c.index[0].date()} - {c.index[-1].date()}"))
        print(f"  {label} ({sym}): {ret_pct:+.1f}% รวม · CAGR {cagr:+.1f}% · MaxDD {maxdd:.1f}%")

    df = pd.DataFrame(rows).sort_values("ผลตอบแทนรวม", ascending=False)
    df.to_csv("international_markets_10y.csv", index=False)

    print("\n" + "=" * 90)
    print("สรุปเรียงจากดีสุด → แย่สุด (Buy & Hold 10 ปี)")
    print("=" * 90)
    print(df[["ตลาด", "ผลตอบแทนรวม", "CAGR", "MaxDD"]].to_string(index=False))
    print("\nบันทึกไว้ที่ international_markets_10y.csv")


if __name__ == "__main__":
    main()
