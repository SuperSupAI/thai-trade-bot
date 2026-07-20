#!/usr/bin/env python
"""
Screen หุ้นไทยในจักรวาล 75 ตัว หาตัวที่ profile "โต + คุณภาพดี" คล้าย GULF/NVDA ก่อนวิ่ง
(EPS growth สูง, ROE ดี, margin ดี, D/E ไม่หนักเกินไป) จากงบการเงินปัจจุบัน -- ไม่ใช่ backtest ย้อนหลัง
ไม่ใช่คำแนะนำซื้อ แสดงตัวเลขจากงบจริงล่าสุดเฉยๆ ให้ดูว่าตอนนี้มีตัวไหนหน้าตาเข้าเกณฑ์บ้าง
"""
import sys
import pandas as pd

sys.path.insert(0, ".")
from data_cache import get_cached_fundamentals
from universe import SECTORS

THAI_UNIVERSE = sorted({sym + ".BK" for stocks in SECTORS.values() for sym in stocks})


def main():
    rows = []
    for sym in THAI_UNIVERSE:
        f = get_cached_fundamentals(sym)
        if not f:
            continue
        rows.append(dict(
            หุ้น=sym.replace(".BK", ""),
            pe=f.get("pe_ratio"),
            roe=f.get("roe"),
            de=f.get("de_ratio"),
            gross_margin=f.get("gross_margin"),
            ebit_margin=f.get("ebit_margin"),
            eps_growth=f.get("eps_growth"),
            profit_margin=f.get("profit_margin"),
            market_cap=f.get("market_cap"),
        ))

    df = pd.DataFrame(rows)
    print(f"มีข้อมูล fundamentals จริง {len(df)}/{len(THAI_UNIVERSE)} ตัว\n")

    # เกณฑ์ growth+quality แบบ CANSLIM/GARP คร่าวๆ: EPS โตแรง + ROE ดี + margin ดี + หนี้ไม่หนัก
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
            print(f"{r['หุ้น']:8s} EPS growth {r['eps_growth']*100:+6.1f}%  ROE {r['roe']*100:5.1f}%  "
                  f"EBIT margin {r['ebit_margin']*100:5.1f}%  D/E {r['de']:.2f}  P/E {r['pe'] if pd.notna(r['pe']) else float('nan'):.1f}")
    else:
        print("ไม่มีตัวไหนผ่านเกณฑ์ทั้งหมดพร้อมกันตอนนี้")

    print("\n" + "=" * 100)
    print("Top 10 EPS growth สูงสุด (ไม่กรองอย่างอื่น) -- ดูภาพกว้างว่าใครโตแรงตอนนี้บ้าง")
    print("=" * 100)
    top_growth = df.dropna(subset=["eps_growth"]).sort_values("eps_growth", ascending=False).head(10)
    for _, r in top_growth.iterrows():
        roe_s = f"{r['roe']*100:.1f}%" if pd.notna(r["roe"]) else "N/A"
        print(f"{r['หุ้น']:8s} EPS growth {r['eps_growth']*100:+7.1f}%  ROE {roe_s:>7s}")

    df.to_csv("growth_quality_screen_results.csv", index=False)
    print("\nบันทึกไว้ที่ growth_quality_screen_results.csv")


if __name__ == "__main__":
    main()
