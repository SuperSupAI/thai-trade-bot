#!/usr/bin/env python
"""
เทียบผลตอบแทน B&H 10 ปี ของ RMF กสิกรหลายกอง (ไม่ใช่แค่ S&P500) — ใช้ ETF ที่ใกล้เคียงเป็น proxy
เพราะไม่มีข้อมูล NAV กองทุนไทยย้อนหลังตรงๆ ผ่าน yfinance

กองที่ทดสอบ (proxy ETF -> กองกสิกร):
  SPY  -> K-US500XRMF   (S&P500 สหรัฐฯ)
  QQQ  -> K-USXNDQRMF   (Nasdaq100 เทคโนโลยีสหรัฐฯ)
  MCHI -> K-CHINARMF    (หุ้นจีน)
  INDA -> K-INDIARMF    (หุ้นอินเดีย)
  EWJ  -> K-JPRMF       (หุ้นญี่ปุ่น)
  VGK  -> K-EURMF       (หุ้นยุโรป)
  VNM  -> K-VIETNAMRMF  (หุ้นเวียดนาม)
  GLD  -> K-GDRMF       (ทองคำ)
  ACWI -> K-WORLDXRMF   (หุ้นทั่วโลก MSCI ACWI)
  IXN  -> K-GTECHRMF    (เทคโนโลยีทั่วโลก)

ใช้กรอบเดิม: จ่ายจริง 200,000 บาท/ปี x 10 ปี -> ได้คืนภาษี 25% -> ลงทุนได้จริง 266,667 บาท/ปี
หัก RMF fee โดยประมาณ 0.54%/ปี ทุกกอง (ของจริงอาจต่างกันตามกอง โดยเฉพาะกองที่ active/เกิดใหม่)
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
import test_exit_optimization as teo

N_YEARS = 10
TAX_RATE = 0.25
RMF_FEE = 0.0054
ANNUAL_OUT_OF_POCKET_THB = 200_000
THB_PER_USD = teo.THB_PER_USD

FUNDS = [
    ("SPY", "K-US500XRMF (S&P500 สหรัฐฯ)"),
    ("QQQ", "K-USXNDQRMF (Nasdaq100 เทค สหรัฐฯ)"),
    ("MCHI", "K-CHINARMF (หุ้นจีน)"),
    ("INDA", "K-INDIARMF (หุ้นอินเดีย)"),
    ("EWJ", "K-JPRMF (หุ้นญี่ปุ่น)"),
    ("VGK", "K-EURMF (หุ้นยุโรป)"),
    ("VNM", "K-VIETNAMRMF (หุ้นเวียดนาม)"),
    ("GLD", "K-GDRMF (ทองคำ)"),
    ("ACWI", "K-WORLDXRMF (หุ้นทั่วโลก)"),
    ("IXN", "K-GTECHRMF (เทคโนโลยีทั่วโลก)"),
]


def load_cached_or_download(ticker):
    cache_file = f"{ticker.lower()}_10y_cache.pkl"
    import os
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    c = safe_download_one(ticker, N_YEARS)
    if c is not None:
        with open(cache_file, "wb") as f:
            pickle.dump(c, f)
    return c


def sim_rmf_dca(close, all_dates, inject_idx):
    rmf_annual_invested_thb = ANNUAL_OUT_OF_POCKET_THB / (1 - TAX_RATE)
    inject_usd = rmf_annual_invested_thb / THB_PER_USD
    seg = close.reindex(all_dates).ffill()
    shares = 0.0
    equity = []
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            price = float(seg.iloc[i])
            if not np.isnan(price) and price > 0:
                shares += inject_usd / price
        equity.append(shares * float(seg.iloc[i]) if not np.isnan(seg.iloc[i]) else equity[-1] if equity else 0)
    yrs_elapsed = np.array([(all_dates[i] - all_dates[0]).days / 365.25 for i in range(len(all_dates))])
    fee_decay = (1 - RMF_FEE) ** yrs_elapsed
    return np.array(equity) * fee_decay


def main():
    print(f"โหลดข้อมูล {len(FUNDS)} กอง (proxy ETF, {N_YEARS} ปี)...")
    data = {}
    for ticker, label in FUNDS:
        c = load_cached_or_download(ticker)
        if c is not None and len(c) > 500:
            data[ticker] = c
            print(f"  {ticker}: OK ({len(c)} วัน, {c.index[0].date()} -> {c.index[-1].date()})")
        else:
            print(f"  {ticker}: โหลดไม่ได้ ข้าม")

    all_dates = sorted(set().union(*[c.index for c in data.values()]))
    n = len(all_dates)
    inject_idx = [min(i * 252, n - 1) for i in range(N_YEARS)]
    total_out_of_pocket = ANNUAL_OUT_OF_POCKET_THB * N_YEARS

    print(f"\nช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"จ่ายจริง {ANNUAL_OUT_OF_POCKET_THB:,} บาท/ปี x {N_YEARS} ปี = {total_out_of_pocket:,} บาทรวม "
          f"(ลงทุนได้จริงในกองปีละ {ANNUAL_OUT_OF_POCKET_THB/(1-TAX_RATE):,.0f} บาท จากการคืนภาษี 25%)\n")

    rows = []
    for ticker, label in FUNDS:
        if ticker not in data:
            continue
        eq = sim_rmf_dca(data[ticker], all_dates, inject_idx)
        final_thb = eq[-1] * THB_PER_USD
        profit = final_thb - total_out_of_pocket
        ret_pct = (final_thb / total_out_of_pocket - 1) * 100
        rows.append(dict(ticker=ticker, กอง=label, final_thb=round(final_thb), profit_thb=round(profit), ret_pct=round(ret_pct, 1)))

    df = pd.DataFrame(rows).sort_values("ret_pct", ascending=False)
    print("=" * 100)
    print("อันดับผลตอบแทน RMF-DCA แต่ละกอง (200,000 บาท/ปี x 10 ปี, รวมข้อได้เปรียบภาษี 25%)")
    print("=" * 100)
    print(df.to_string(index=False))
    df.to_csv("rmf_multi_fund_compare_results.csv", index=False)
    print("\nบันทึกไว้ที่ rmf_multi_fund_compare_results.csv")


if __name__ == "__main__":
    main()
