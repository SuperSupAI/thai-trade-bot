#!/usr/bin/env python
"""
ต่อยอดจาก test_news_volume_pocpullback.py: เพิ่มมิติ "โทนข่าว" (บวก/ลบ) ไม่ใช่แค่จำนวน
ใช้ trades เดิมที่หาไว้แล้วใน news_volume_vs_winloss.csv (ไม่ต้อง backtest ใหม่)
ดึง GDELT mode=timelinetone (ค่าเฉลี่ย sentiment ต่อวัน, บวก=ข่าวดี ลบ=ข่าวลบ) ในช่วง 3 วันก่อนเข้าไม้
เทียบ tone เฉลี่ยของไม้ชนะ vs ไม้แพ้
"""
import time
import requests
import pandas as pd

STOCKS_NAME = {"TSLA": "Tesla", "NVDA": "Nvidia", "AAPL": "Apple", "AMD": "AMD", "NFLX": "Netflix"}
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def gdelt_news_tone(query, start_dt, end_dt, max_retries=5):
    params = {
        "query": query,
        "mode": "timelinetone",
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
                vals = [pt.get("value") for pt in series if pt.get("value") is not None]
                return sum(vals) / len(vals) if vals else None
            except Exception:
                return None
        time.sleep(8 + attempt * 4)
    return None


def main():
    df = pd.read_csv("news_volume_vs_winloss.csv", parse_dates=["entry_date"])
    tones = []
    for _, row in df.iterrows():
        name = STOCKS_NAME[row["symbol"]]
        start = row["entry_date"] - pd.Timedelta(days=3)
        end = row["entry_date"] + pd.Timedelta(days=1)
        tone = gdelt_news_tone(name, start, end)
        print(f"{row['symbol']} {row['entry_date'].date()} win={row['win']} news_count={row['news_count']} avg_tone_3d={tone}")
        tones.append(tone)
        time.sleep(6)

    df["avg_tone_3d"] = tones
    df.to_csv("news_tone_vs_winloss.csv", index=False)

    df_ok = df.dropna(subset=["avg_tone_3d"])
    print(f"\n=== สรุปโทนข่าว (ใช้ได้ {len(df_ok)}/{len(df)} ไม้) ===")
    if not df_ok.empty:
        win_tone = df_ok[df_ok.win]["avg_tone_3d"]
        loss_tone = df_ok[~df_ok.win]["avg_tone_3d"]
        print(f"ไม้ชนะ (n={len(win_tone)}): tone เฉลี่ย = {win_tone.mean():.3f}, median = {win_tone.median():.3f}")
        print(f"ไม้แพ้  (n={len(loss_tone)}): tone เฉลี่ย = {loss_tone.mean():.3f}, median = {loss_tone.median():.3f}")
        pos_news = df_ok[df_ok["avg_tone_3d"] > 0]
        neg_news = df_ok[df_ok["avg_tone_3d"] <= 0]
        if len(pos_news) > 0:
            print(f"\nกลุ่มข่าว 'บวก' ก่อนเข้าไม้ (n={len(pos_news)}): win rate = {(pos_news.win.mean()*100):.1f}%")
        if len(neg_news) > 0:
            print(f"กลุ่มข่าว 'ลบ' ก่อนเข้าไม้ (n={len(neg_news)}): win rate = {(neg_news.win.mean()*100):.1f}%")
    print("\nบันทึกไว้ที่ news_tone_vs_winloss.csv")


if __name__ == "__main__":
    main()
