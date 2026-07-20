#!/usr/bin/env python
"""
เทียบ DCA 10 ปี "ปีละ 50,000 บาท" (แทน 200,000 บาทที่เคยเทสก่อนหน้า) ระหว่าง:
  A) RMF S&P500 (K-US500XRMF proxy: SPY) — คืนภาษี 25%, fee 0.54%/ปี
  B) RMF blend 40/30/20/10 (S&P500/Nasdaq100/ทอง/จีน) ตามสัดส่วนที่ปรับ RMF_Policy ไปแล้ว — คืนภาษี 25%
  C) SPY ตรงๆ ไม่ลดหย่อนภาษี (fee ~0.03%)
  D) DR Momentum Top-3 (21 หุ้น mega-cap ที่มี DR จริงบน SET) — ไม่มีภาษีเลย, rebalance รายเดือน

วิธี RMF: ประมาณผลตอบแทนจากตัวคูณภาษี 1/(1-0.25)=1.333 บนมูลค่าสุดท้ายของดัชนีเดียวกัน (fee หักตามจริง)
ตามระเบียบวิธีที่ใช้ใน test_dca_3way_compare.py / test_rmf_blend_10_portfolios.py ก่อนหน้านี้
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")

ANNUAL_THB = 50_000
N_YEARS = 10
TAX_MULT = 1 / (1 - 0.25)  # RMF คืนภาษี 25%
RMF_FEE = 0.0054
SPY_FEE = 0.0003
FEE_DR = 0.002  # ค่าคอมฯ ซื้อขายหุ้นไทย/DR โดยประมาณต่อข้าง
THB_PER_USD = 35.5  # อัตราแลกเปลี่ยนสมมติคงที่ (ตามที่ใช้ในสคริปต์ก่อนหน้า test_exit_optimization.py)
ANNUAL_USD = ANNUAL_THB / THB_PER_USD  # หุ้น/กองทุน US ราคาเป็น USD ต้องแปลงก่อนซื้อ

DR_COVERED = ["AAPL", "MSFT", "JPM", "V", "UNH", "KO", "CSCO", "CRM", "GS", "JNJ",
              "DIS", "NKE", "GOOGL", "AMZN", "META", "NVDA", "PFE", "COST", "PEP", "ADBE", "LULU"]


def load_close(sym, years=10):
    df = yf.download(sym, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
    if df is None or df.empty:
        return None
    c = df["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.dropna()


def annual_inject_indices(dates, n_years):
    """หา index ของวันแรกของแต่ละปี (วันซื้อ DCA) ปีละ 1 ครั้ง"""
    idx = [0]
    cur_year = dates[0].year
    for i, d in enumerate(dates):
        if d.year != cur_year:
            idx.append(i)
            cur_year = d.year
        if len(idx) >= n_years:
            break
    return idx


def sim_index_dca(close, annual_thb, fee_rate, years):
    """DCA เข้าดัชนีเดียว (ราคาเป็น USD) หัก fee รายปีแบบทบต้น คืนมูลค่าสุดท้าย (บาท) และเงินต้นรวม (บาท)"""
    annual_usd = annual_thb / THB_PER_USD
    dates = close.index
    inject_idx = annual_inject_indices(dates, years)
    shares = 0.0
    total_invested = 0.0
    last_year_marker = dates[0].year
    for i, dt in enumerate(dates):
        if i in inject_idx:
            price = float(close.iloc[i])
            shares += annual_usd / price
            total_invested += annual_thb
        if dt.year != last_year_marker:
            shares *= (1 - fee_rate)  # หัก fee ปีละครั้ง (ทบต้น) — trigger แค่วันแรกที่ปีเปลี่ยน
            last_year_marker = dt.year
    final_value = shares * float(close.iloc[-1]) * THB_PER_USD
    return final_value, total_invested


def sim_blend_dca(closes_dict, weights, annual_thb, fee_rate, years):
    """DCA เข้าพอร์ตผสมหลายกอง (ราคาเป็น USD ทั้งหมด) ตามสัดส่วน weights rebalance ตอนฉีดเงินใหม่ทุกปี"""
    annual_usd = annual_thb / THB_PER_USD
    common_idx = None
    for c in closes_dict.values():
        common_idx = c.index if common_idx is None else common_idx.intersection(c.index)
    common_idx = common_idx.sort_values()
    closes_dict = {k: v.reindex(common_idx).ffill() for k, v in closes_dict.items()}
    inject_idx = annual_inject_indices(common_idx, years)

    shares = {sym: 0.0 for sym in weights}
    total_invested = 0.0
    last_year_marker = common_idx[0].year
    for i, dt in enumerate(common_idx):
        if i in inject_idx:
            for sym, w in weights.items():
                price = float(closes_dict[sym].iloc[i])
                shares[sym] += (annual_usd * w) / price
            total_invested += annual_thb
        if dt.year != last_year_marker:
            for sym in shares:
                shares[sym] *= (1 - fee_rate)
            last_year_marker = dt.year
    final_value = sum(shares[sym] * float(closes_dict[sym].iloc[-1]) for sym in shares) * THB_PER_USD
    return final_value, total_invested


def sim_dr_momentum_dca(closes, annual_thb, top_n, formation=252, skip=21, rebalance_every=21, years=10):
    """DCA เข้ากลยุทธ์ momentum แบบ cross-sectional (ราคาอ้างอิง USD) พร้อมฉีดเงินใหม่ปีละครั้ง (แปลงเป็น USD
    ตอนซื้อ), rebalance รายเดือน, ไม่มีภาษี — คืนมูลค่าสุดท้ายแปลงกลับเป็นบาท"""
    annual_usd = annual_thb / THB_PER_USD
    syms = list(closes.keys())
    common_idx = None
    for c in closes.values():
        common_idx = c.index if common_idx is None else common_idx.intersection(c.index)
    common_idx = sorted(common_idx)
    price = {s: closes[s].reindex(common_idx).ffill() for s in syms}
    n = len(common_idx)
    inject_idx = set(annual_inject_indices(common_idx, years))

    cash = 0.0
    shares = {s: 0.0 for s in syms}
    total_invested = 0.0
    start = formation + skip
    for i in range(start, n):
        if i in inject_idx:
            cash += annual_usd
            total_invested += annual_thb
        if (i - start) % rebalance_every == 0:
            scores = {}
            for s in syms:
                p_now = price[s].iloc[i - skip]
                p_form = price[s].iloc[i - formation]
                if p_form > 0:
                    scores[s] = p_now / p_form - 1
            ranked = sorted(scores, key=lambda k: -scores[k])[:top_n]
            port_value = cash + sum(shares[s] * float(price[s].iloc[i]) for s in syms)
            port_value *= (1 - FEE_DR)  # ค่าคอมฯ ตอน rebalance (ขายเก่า+ซื้อใหม่)
            target_each = port_value / top_n
            new_shares = {s: 0.0 for s in syms}
            for s in ranked:
                new_shares[s] = target_each / float(price[s].iloc[i])
            shares = new_shares
            cash = 0.0
    final_value = (cash + sum(shares[s] * float(price[s].iloc[-1]) for s in syms)) * THB_PER_USD
    return final_value, total_invested


def main():
    print(f"ดาวน์โหลดราคา 10 ปี (SPY, IXN, GLD, {len(DR_COVERED)} หุ้น DR mega-cap)...")
    spy = load_close("SPY")
    ixn = load_close("IXN")   # proxy K-GTECHRMF (เทคโลก)
    gld = load_close("GLD")   # proxy K-GDRMF (ทองคำ)
    fxi = load_close("FXI")   # proxy K-CHINARMF (จีน)
    dr_closes = {}
    for s in DR_COVERED:
        c = load_close(s)
        if c is not None and len(c) > 400:
            dr_closes[s] = c
    print(f"ใช้ได้ {len(dr_closes)}/{len(DR_COVERED)} หุ้น DR mega-cap\n")

    results = []

    # A) RMF S&P500
    v, inv = sim_index_dca(spy, ANNUAL_THB, RMF_FEE, N_YEARS)
    v_rmf = v * TAX_MULT
    results.append(("A) RMF S&P500 (K-US500XRMF)", v_rmf, inv))

    # B) RMF blend 40/30/20/10
    weights = {"SPY": 0.40, "IXN": 0.30, "GLD": 0.20, "FXI": 0.10}
    v, inv = sim_blend_dca({"SPY": spy, "IXN": ixn, "GLD": gld, "FXI": fxi}, weights, ANNUAL_THB, RMF_FEE, N_YEARS)
    v_blend = v * TAX_MULT
    results.append(("B) RMF blend 40/30/20/10", v_blend, inv))

    # C) SPY ตรงๆ ไม่ลดหย่อน
    v, inv = sim_index_dca(spy, ANNUAL_THB, SPY_FEE, N_YEARS)
    results.append(("C) SPY ตรงๆ (ไม่ลดหย่อนภาษี)", v, inv))

    # D) DR Momentum Top-3
    v, inv = sim_dr_momentum_dca(dr_closes, ANNUAL_THB, top_n=3, years=N_YEARS)
    results.append(("D) DR Momentum Top-3 (21 mega-cap)", v, inv))

    # E) DR Momentum Top-5 (เผื่อเทียบความเสี่ยงกระจุกน้อยกว่า)
    v, inv = sim_dr_momentum_dca(dr_closes, ANNUAL_THB, top_n=5, years=N_YEARS)
    results.append(("E) DR Momentum Top-5", v, inv))

    print(f"{'ทาง':45s} {'เงินลงทุนรวม':>15s} {'มูลค่าสุดท้าย':>15s} {'กำไร':>10s} {'ผลตอบแทน':>10s}")
    print("=" * 100)
    for label, final_v, invested in results:
        profit_pct = (final_v / invested - 1) * 100
        print(f"{label:45s} {invested:15,.0f} {final_v:15,.0f} {final_v-invested:10,.0f} {profit_pct:9.1f}%")

    df = pd.DataFrame([dict(label=l, final_value=v, invested=i, profit_pct=(v/i-1)*100) for l, v, i in results])
    df.to_csv("dca_50k_yearly_compare.csv", index=False)
    print("\nบันทึกไว้ที่ dca_50k_yearly_compare.csv")


if __name__ == "__main__":
    main()
