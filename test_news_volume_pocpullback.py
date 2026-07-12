#!/usr/bin/env python
"""
เช็คว่า "จำนวนข่าว" ก่อนเกิดสัญญาณ Volume Profile POC Pullback (TP5%/SL10%) มีผลต่อการแพ้ชนะหรือไม่
วิธี: หาไม้เทรดจริง (ทั้งที่ชนะและแพ้) ของหุ้น US ที่ข่าวลงเยอะ (TSLA, NVDA, AAPL, AMD, NFLX)
แล้วนับจำนวนข่าวใน 3 วันก่อนวันเข้าไม้ (ผ่าน GDELT DOC 2.0 API ฟรี ไม่ต้องสมัคร, ครอบคลุมข่าวตั้งแต่ก.พ. 2017)
เทียบค่าเฉลี่ยจำนวนข่าวของไม้ที่ "ชนะ" กับ "แพ้"

ข้อจำกัด: GDELT rate limit ~1 request/5 วินาที (แชร์ทั้งโลก) จึงทดสอบแค่ไม่กี่หุ้น/ไม้เพื่อไม่ให้ใช้เวลานานเกินไป
"""
import time
import requests
import yfinance as yf
import pandas as pd
import sys

sys.path.insert(0, ".")
import test_volume_profile as vp

STOCKS = {"TSLA": "Tesla", "NVDA": "Nvidia", "AAPL": "Apple", "AMD": "AMD", "NFLX": "Netflix"}
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def gdelt_news_count(query, start_dt, end_dt, max_retries=5):
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
    }
    for attempt in range(max_retries):
        try:
            r = requests.get(GDELT_URL, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        except Exception:
            time.sleep(8)
            continue
        if r.status_code == 200:
            try:
                data = r.json()
                series = data.get("timeline", [{}])[0].get("data", [])
                return sum(pt.get("value", 0) for pt in series)
            except Exception:
                return None
        time.sleep(8 + attempt * 4)
    return None


def get_trades(sym):
    df = yf.download(sym, period="10y", interval="1d", auto_adjust=True, progress=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    close = df["Close"].dropna()
    vol = df["Volume"].dropna()
    idx = close.index.intersection(vol.index)
    close, vol = close.loc[idx], vol.loc[idx]
    P = vp.prep(close, vol)
    cond = P["entries"]["POC Pullback Bounce"]
    c = P["c"]

    trades = []
    held = False; ep = 0.0; entry_i = 0
    for i in range(len(c)):
        if held:
            chg = c[i] / ep - 1
            if chg <= -0.10 or chg >= 0.05:
                trades.append(dict(entry_date=close.index[entry_i], exit_date=close.index[i], win=bool(chg > 0)))
                held = False
        else:
            if cond[i]:
                held = True; ep = c[i]; entry_i = i
    # ตัดไม้ก่อน 2017-06 ออก เพราะ GDELT DOC API ครอบคลุมข่าวตั้งแต่ราวก.พ. 2017 เท่านั้น (early period ข้อมูลไม่ครบ)
    return [t for t in trades if t["entry_date"] >= pd.Timestamp("2017-06-01")]


def main():
    rows = []
    for sym, name in STOCKS.items():
        print(f"=== {sym} ({name}) ===")
        trades = get_trades(sym)
        print(f"  ไม้เทรดหลัง 2017-06: {len(trades)}")
        for t in trades:
            start = t["entry_date"] - pd.Timedelta(days=3)
            end = t["entry_date"] + pd.Timedelta(days=1)
            cnt = gdelt_news_count(name, start, end)
            print(f"  {t['entry_date'].date()} win={t['win']} news_count_3d={cnt}")
            rows.append(dict(symbol=sym, entry_date=t["entry_date"], win=t["win"], news_count=cnt))
            time.sleep(6)  # เคารพ rate limit ของ GDELT

    df = pd.DataFrame(rows)
    df.to_csv("news_volume_vs_winloss.csv", index=False)
    df_ok = df.dropna(subset=["news_count"])
    print(f"\n=== สรุปทั้งหมด (ใช้ได้ {len(df_ok)}/{len(df)} ไม้ ที่ดึงข่าวสำเร็จ) ===")
    if not df_ok.empty:
        win_news = df_ok[df_ok.win]["news_count"]
        loss_news = df_ok[~df_ok.win]["news_count"]
        print(f"ไม้ชนะ (n={len(win_news)}): news count เฉลี่ย = {win_news.mean():.1f}, median = {win_news.median():.1f}")
        print(f"ไม้แพ้  (n={len(loss_news)}): news count เฉลี่ย = {loss_news.mean():.1f}, median = {loss_news.median():.1f}")
    print("\nบันทึกไว้ที่ news_volume_vs_winloss.csv")


if __name__ == "__main__":
    main()
