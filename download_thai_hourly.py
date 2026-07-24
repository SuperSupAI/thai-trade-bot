#!/usr/bin/env python
"""ดาวน์โหลดราคารายชั่วโมง (interval=60m) ย้อนหลัง ~2 ปี ของหุ้นไทย 75 ตัว จาก yfinance
(yfinance ให้ hourly ได้ไกลสุด 730 วัน ต่างจาก Settrade Sandbox ที่มีแค่ ~85 วันและเป็นราคาจำลอง)"""
import pickle, sys
sys.path.insert(0, "dr_momentum_bot")
from dr_universe import THAI_MOMENTUM_UNIVERSE
import yfinance as yf

def download_hourly(tickers, period="730d", interval="60m", min_rows=300):
    out = {}
    failed = []
    for i, t in enumerate(tickers):
        try:
            df = yf.download(t, period=period, interval=interval, progress=False, auto_adjust=True)
            if len(df) >= min_rows:
                close = df["Close"]
                if hasattr(close, "iloc") and close.ndim == 2:
                    close = close.iloc[:, 0]
                out[t] = close.dropna()
            else:
                failed.append(t)
        except Exception as e:
            failed.append(t)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(tickers)}")
    return out, failed

data, failed = download_hourly(THAI_MOMENTUM_UNIVERSE)
print(f"\nสำเร็จ {len(data)}/{len(THAI_MOMENTUM_UNIVERSE)} ตัว")
if failed:
    print("ล้มเหลว/ข้อมูลไม่พอ:", failed)

with open("thai_hourly_2y_cache.pkl", "wb") as f:
    pickle.dump(data, f)
print("บันทึกไว้ที่ thai_hourly_2y_cache.pkl")
