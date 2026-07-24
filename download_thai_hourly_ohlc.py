#!/usr/bin/env python
"""ดาวน์โหลด OHLCV รายชั่วโมงเต็ม (ไม่ใช่แค่ Close) ของหุ้นไทย 75 ตัว สำหรับออกแบบสูตรเดเทรด
(ต้องมี Open ของแท่งแรกในแต่ละวัน เพื่อรู้ราคาเปิดตลาดจริง และ Close ของแท่งสุดท้ายเพื่อรู้ราคาปิด)"""
import pickle, sys
sys.path.insert(0, "dr_momentum_bot")
from dr_universe import THAI_MOMENTUM_UNIVERSE
import yfinance as yf

def download(tickers, period="730d", interval="60m", min_rows=300):
    out = {}
    failed = []
    for i, t in enumerate(tickers):
        try:
            df = yf.download(t, period=period, interval=interval, progress=False, auto_adjust=True)
            if isinstance(df.columns, __import__("pandas").MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) >= min_rows:
                out[t] = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            else:
                failed.append(t)
        except Exception:
            failed.append(t)
        if (i + 1) % 15 == 0:
            print(f"  {i+1}/{len(tickers)}")
    return out, failed

data, failed = download(THAI_MOMENTUM_UNIVERSE)
print(f"\nสำเร็จ {len(data)}/{len(THAI_MOMENTUM_UNIVERSE)} ตัว")
if failed:
    print("ล้มเหลว:", failed)

with open("thai_hourly_ohlc_2y_cache.pkl", "wb") as f:
    pickle.dump(data, f)
print("บันทึกไว้ที่ thai_hourly_ohlc_2y_cache.pkl")
