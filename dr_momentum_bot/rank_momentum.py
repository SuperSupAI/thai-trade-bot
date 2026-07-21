#!/usr/bin/env python
"""
คำนวณอันดับ cross-sectional momentum ของ DR universe -- สูตรเดียวกับที่ backtest ไว้ทั้งเซสชัน
(formation 12 เดือน, skip 1 เดือน, ไม่มี overlay เพราะพิสูจน์แล้วว่า overlay overfit)
ดึงราคาหุ้นแม่ผ่าน yfinance (ตรงกับวิธี backtest ทุกอัน ไม่ใช่ราคา DR บน SET)
"""
import sys

sys.path.insert(0, "..")
sys.path.insert(0, ".")
from safe_fetch import safe_download_many
from dr_universe import DR_COVERED_EXPANDED

FORMATION = 252  # ~12 เดือนเทรด
SKIP = 21        # ~1 เดือน skip period


def fetch_prices(tickers=DR_COVERED_EXPANDED, years=2):
    """ดึงราคาแค่ ~2 ปีย้อนหลังพอ (เกินพอสำหรับ formation 252 วัน) ไม่ต้องดึง 10 ปีเหมือนตอน backtest"""
    print(f"ดึงราคา {len(tickers)} ตัว ({years} ปีย้อนหลัง) ...")
    data = safe_download_many(tickers, years=years, min_rows=FORMATION + SKIP + 5)
    missing = [t for t in tickers if t not in data]
    if missing:
        print(f"⚠️ ดึงราคาไม่ได้/ข้อมูลไม่พอ: {missing}")
    return data


def rank_top_n(price_data, top_n=3):
    """คืน list of (ticker, momentum_score) เรียงจากมากไปน้อย top_n ตัวแรก"""
    scores = []
    for ticker, close in price_data.items():
        if len(close) < FORMATION + SKIP:
            continue
        p_now = float(close.iloc[-SKIP])
        p_form = float(close.iloc[-FORMATION])
        if p_form <= 0:
            continue
        score = p_now / p_form - 1
        scores.append((ticker, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]


def main():
    data = fetch_prices()
    ranked = rank_top_n(data, top_n=3)
    print("\nอันดับ momentum ปัจจุบัน (top 3):")
    for ticker, score in ranked:
        print(f"  {ticker:8s}  momentum(12mo skip1mo) = {score*100:+.1f}%")
    return ranked


if __name__ == "__main__":
    main()
