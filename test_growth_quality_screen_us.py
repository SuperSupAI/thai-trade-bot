#!/usr/bin/env python
"""
Screen หุ้นสหรัฐฯ ในจักรวาล US_STOCKS หา profile "โต + คุณภาพดี" เดียวกับที่ใช้กับหุ้นไทย
(EPS growth>15%, ROE>12%, EBIT margin>10%, D/E<1.5) จากงบการเงินปัจจุบัน -- ไม่ใช่ backtest ย้อนหลัง
ไม่มี cache ในเครื่อง (data/fundamentals.json เก็บแค่หุ้นไทย) ต้องดึงสดผ่าน yfinance
"""
import sys
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")
from universe import US_STOCKS


def fetch_fundamentals(sym):
    try:
        info = yf.Ticker(sym).info
    except Exception:
        return None
    if not info:
        return None
    de_raw = info.get("debtToEquity")
    return dict(
        symbol=sym,
        pe=info.get("trailingPE"),
        roe=info.get("returnOnEquity"),
        de=(de_raw / 100) if de_raw is not None else None,
        gross_margin=info.get("grossMargins"),
        ebit_margin=info.get("operatingMargins"),
        eps_growth=info.get("earningsGrowth"),
        profit_margin=info.get("profitMargins"),
        market_cap=info.get("marketCap"),
    )


def main():
    print(f"ดึง fundamentals สด {len(US_STOCKS)} หุ้น US...")
    rows = []
    for i, sym in enumerate(US_STOCKS):
        f = fetch_fundamentals(sym)
        if f:
            rows.append(f)
        if (i + 1) % 20 == 0:
            print(f"  ดึงแล้ว {i+1}/{len(US_STOCKS)}...")

    df = pd.DataFrame(rows)
    print(f"\nมีข้อมูล fundamentals จริง {len(df)}/{len(US_STOCKS)} ตัว\n")

    screened = df[
        (df["eps_growth"].fillna(-999) > 0.15) &
        (df["roe"].fillna(-999) > 0.12) &
        (df["ebit_margin"].fillna(-999) > 0.10) &
        (df["de"].fillna(999) < 1.5)
    ].copy()

    print("=" * 100)
    print("เกณฑ์: EPS growth > 15%, ROE > 12%, EBIT margin > 10%, D/E < 1.5 (จากงบล่าสุด ณ ปัจจุบัน)")
    print("=" * 100)
    if len(screened):
        screened = screened.sort_values("eps_growth", ascending=False)
        for _, r in screened.iterrows():
            de_s = f"{r['de']:.2f}" if pd.notna(r["de"]) else "N/A"
            pe_s = f"{r['pe']:.1f}" if pd.notna(r["pe"]) else "N/A"
            print(f"{r['symbol']:8s} EPS growth {r['eps_growth']*100:+7.1f}%  ROE {r['roe']*100:5.1f}%  "
                  f"EBIT margin {r['ebit_margin']*100:5.1f}%  D/E {de_s:>6s}  P/E {pe_s:>7s}")
    else:
        print("ไม่มีตัวไหนผ่านเกณฑ์ทั้งหมดพร้อมกันตอนนี้")

    print("\n" + "=" * 100)
    print("Top 15 EPS growth สูงสุด (ไม่กรองอย่างอื่น) -- ภาพกว้างว่าใครโตแรงตอนนี้บ้าง")
    print("=" * 100)
    top_growth = df.dropna(subset=["eps_growth"]).sort_values("eps_growth", ascending=False).head(15)
    for _, r in top_growth.iterrows():
        roe_s = f"{r['roe']*100:.1f}%" if pd.notna(r["roe"]) else "N/A"
        print(f"{r['symbol']:8s} EPS growth {r['eps_growth']*100:+8.1f}%  ROE {roe_s:>7s}")

    df.to_csv("growth_quality_screen_us_results.csv", index=False)
    print("\nบันทึกไว้ที่ growth_quality_screen_us_results.csv")


if __name__ == "__main__":
    main()
