#!/usr/bin/env python
"""
เทียบ tracking error จริงของ DR ไทยกับดัชนีต้นทาง โดยใช้ราคาย้อนหลังจริงที่ยาวที่สุดที่มี:
  SP50001.BK (DR ติดตาม Hang Seng S&P500 ETF) vs SPY -- มีข้อมูลตั้งแต่ 2024-10-22 เท่านั้น (~1.7 ปี, จดทะเบียนไม่นาน)
  NDX01.BK   (DR ติดตาม ChinaAMC Nasdaq100 ETF) vs QQQ -- มีข้อมูลตั้งแต่ 2022-05-06 (~4.2 ปี)
หมายเหตุ: DR ซื้อขายเป็นเงินบาท ต้นทางเป็น USD -- ส่วนต่างจึงรวมทั้ง (1) ค่าธรรมเนียมกอง (2) ผลกระทบอัตราแลกเปลี่ยน
(3) ราคาซื้อขายจริงบน SET อาจเบี่ยงจาก NAV (premium/discount) ไม่ได้แยกองค์ประกอบให้ในที่นี้
"""
import numpy as np
import pandas as pd
import yfinance as yf

PAIRS = [
    ("SP50001.BK", "SPY", "SP50001 (DR ติดตาม S&P500) vs SPY"),
    ("NDX01.BK", "QQQ", "NDX01 (DR ติดตาม Nasdaq100) vs QQQ"),
]


def get_close(ticker):
    d = yf.download(ticker, period="max", progress=False)["Close"]
    if isinstance(d, pd.DataFrame):
        d = d.iloc[:, 0]
    d = d.dropna()
    d.index = pd.to_datetime(d.index).tz_localize(None)
    return d


def main():
    for dr_ticker, idx_ticker, label in PAIRS:
        dr = get_close(dr_ticker)
        idx = get_close(idx_ticker)

        common = dr.index.intersection(idx.index)
        dr_c = dr.loc[common]
        idx_c = idx.loc[common]

        dr_norm = dr_c / dr_c.iloc[0]
        idx_norm = idx_c / idx_c.iloc[0]

        dr_ret_total = float(dr_norm.iloc[-1] - 1) * 100
        idx_ret_total = float(idx_norm.iloc[-1] - 1) * 100
        gap = dr_ret_total - idx_ret_total

        dr_daily = dr_c.pct_change().dropna()
        idx_daily = idx_c.pct_change().dropna()
        common2 = dr_daily.index.intersection(idx_daily.index)
        corr = dr_daily.loc[common2].corr(idx_daily.loc[common2])

        diff_series = dr_norm - idx_norm  # ส่วนต่างสะสม (normalized)
        tracking_vol = (dr_daily.loc[common2] - idx_daily.loc[common2]).std() * np.sqrt(252) * 100

        n_days = len(common)
        n_years = n_days / 252

        print("=" * 90)
        print(label)
        print("=" * 90)
        print(f"ช่วงข้อมูลที่ overlap กันจริง: {common[0].date()} -> {common[-1].date()} "
              f"({n_days} วัน, ~{n_years:.1f} ปี)")
        print(f"ผลตอบแทนสะสม {dr_ticker}: {dr_ret_total:+.1f}%   {idx_ticker}: {idx_ret_total:+.1f}%   "
              f"ส่วนต่าง (tracking gap): {gap:+.1f} percentage point")
        dr_ann = (float(dr_norm.iloc[-1]) ** (1 / n_years) - 1) * 100 if n_years > 0 else float("nan")
        idx_ann = (float(idx_norm.iloc[-1]) ** (1 / n_years) - 1) * 100 if n_years > 0 else float("nan")
        print(f"correlation รายวัน: {corr:.3f}")
        print(f"tracking error (annualized vol ของส่วนต่างผลตอบแทนรายวัน): {tracking_vol:.2f}%/ปี")
        print(f"ผลตอบแทนเฉลี่ยต่อปี: {dr_ticker} {dr_ann:+.2f}%/ปี vs {idx_ticker} {idx_ann:+.2f}%/ปี "
              f"(ส่วนต่าง {dr_ann-idx_ann:+.2f} จุด%/ปี)\n")


if __name__ == "__main__":
    main()
