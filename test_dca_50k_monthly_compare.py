#!/usr/bin/env python
"""
เทียบ DCA 10 ปี "เดือนละ 50,000 บาท" (ต่างจาก test_dca_50k_yearly_compare.py ที่เป็นปีละ 50,000)
รวมเงินลงทุนตลอด 10 ปี = 50,000 x 12 x 10 = 6,000,000 บาท ระหว่าง:
  A) RMF S&P500 (K-US500XRMF proxy: SPY) — คืนภาษี 25%, fee 0.54%/ปี
  B) RMF blend 40/30/20/10 (S&P500/Nasdaq100/ทอง/จีน) ตามสัดส่วนที่ปรับ RMF_Policy ไปแล้ว — คืนภาษี 25%
  C) SPY ตรงๆ ไม่ลดหย่อนภาษี (fee ~0.03%)
  D/E) DR Momentum Top-3/5 (21 หุ้น mega-cap ที่มี DR จริงบน SET) — ไม่มีภาษีเลย, rebalance รายเดือน

หมายเหตุ: ลิมิตลดหย่อนภาษี RMF+SSF+PVD จริงตามกฎหมายอยู่ที่ 500,000 บาท/ปี — เดือนละ 50,000 บาท x 12
เดือน = 600,000 บาท/ปี **เกินลิมิตไป 100,000 บาท/ปี** ส่วนเกินนี้จะไม่ได้สิทธิ์ลดหย่อนจริง (คำนวณแยกไว้ด้านล่าง)
"""
import sys
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")

MONTHLY_THB = 50_000
N_YEARS = 10
N_MONTHS = N_YEARS * 12
RMF_ANNUAL_CAP_THB = 500_000  # ลิมิตลดหย่อนภาษีรวม RMF+SSF+PVD ตามกฎหมายจริง
TAX_MULT = 1 / (1 - 0.25)
RMF_FEE = 0.0054
SPY_FEE = 0.0003
FEE_DR = 0.002
THB_PER_USD = 35.5

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


def monthly_inject_indices(dates, n_months):
    """หา index ของวันแรกของแต่ละเดือน (วันซื้อ DCA) เดือนละ 1 ครั้ง"""
    idx = [0]
    cur_ym = (dates[0].year, dates[0].month)
    for i, d in enumerate(dates):
        ym = (d.year, d.month)
        if ym != cur_ym:
            idx.append(i)
            cur_ym = ym
        if len(idx) >= n_months:
            break
    return idx


def sim_index_dca_monthly(close, monthly_thb, fee_rate, n_months):
    monthly_usd = monthly_thb / THB_PER_USD
    dates = close.index
    inject_idx = monthly_inject_indices(dates, n_months)
    inject_set = set(inject_idx)
    shares = 0.0
    total_invested = 0.0
    last_year_marker = dates[0].year
    for i, dt in enumerate(dates):
        if i in inject_set:
            price = float(close.iloc[i])
            shares += monthly_usd / price
            total_invested += monthly_thb
        if dt.year != last_year_marker:
            shares *= (1 - fee_rate)
            last_year_marker = dt.year
        if i >= inject_idx[-1] and i > inject_idx[-1] + 25:
            pass  # เลยเดือนสุดท้ายที่ฉีดเงินไปแล้ว ปล่อยให้ราคาวิ่งต่อจนจบข้อมูล
    final_value = shares * float(close.iloc[-1]) * THB_PER_USD
    return final_value, total_invested


def sim_blend_dca_monthly(closes_dict, weights, monthly_thb, fee_rate, n_months):
    monthly_usd = monthly_thb / THB_PER_USD
    common_idx = None
    for c in closes_dict.values():
        common_idx = c.index if common_idx is None else common_idx.intersection(c.index)
    common_idx = common_idx.sort_values()
    closes_dict = {k: v.reindex(common_idx).ffill() for k, v in closes_dict.items()}
    inject_idx = monthly_inject_indices(common_idx, n_months)
    inject_set = set(inject_idx)

    shares = {sym: 0.0 for sym in weights}
    total_invested = 0.0
    last_year_marker = common_idx[0].year
    for i, dt in enumerate(common_idx):
        if i in inject_set:
            for sym, w in weights.items():
                price = float(closes_dict[sym].iloc[i])
                shares[sym] += (monthly_usd * w) / price
            total_invested += monthly_thb
        if dt.year != last_year_marker:
            for sym in shares:
                shares[sym] *= (1 - fee_rate)
            last_year_marker = dt.year
    final_value = sum(shares[sym] * float(closes_dict[sym].iloc[-1]) for sym in shares) * THB_PER_USD
    return final_value, total_invested


def sim_dr_momentum_dca_monthly(closes, monthly_thb, top_n, formation=252, skip=21, rebalance_every=21, n_months=120):
    monthly_usd = monthly_thb / THB_PER_USD
    syms = list(closes.keys())
    common_idx = None
    for c in closes.values():
        common_idx = c.index if common_idx is None else common_idx.intersection(c.index)
    common_idx = sorted(common_idx)
    price = {s: closes[s].reindex(common_idx).ffill() for s in syms}
    n = len(common_idx)
    inject_idx = set(monthly_inject_indices(common_idx, n_months))

    cash = 0.0
    shares = {s: 0.0 for s in syms}
    total_invested = 0.0
    start = formation + skip
    for i in range(start, n):
        if i in inject_idx:
            cash += monthly_usd
            total_invested += monthly_thb
        if (i - start) % rebalance_every == 0:
            scores = {}
            for s in syms:
                p_now = price[s].iloc[i - skip]
                p_form = price[s].iloc[i - formation]
                if p_form > 0:
                    scores[s] = p_now / p_form - 1
            ranked = sorted(scores, key=lambda k: -scores[k])[:top_n]
            port_value = cash + sum(shares[s] * float(price[s].iloc[i]) for s in syms)
            port_value *= (1 - FEE_DR)
            target_each = port_value / top_n
            new_shares = {s: 0.0 for s in syms}
            for s in ranked:
                new_shares[s] = target_each / float(price[s].iloc[i])
            shares = new_shares
            cash = 0.0
    final_value = (cash + sum(shares[s] * float(price[s].iloc[-1]) for s in syms)) * THB_PER_USD
    return final_value, total_invested


def main():
    print(f"ดาวน์โหลดราคา 10 ปี (SPY, IXN, GLD, FXI, {len(DR_COVERED)} หุ้น DR mega-cap)...")
    spy = load_close("SPY")
    ixn = load_close("IXN")
    gld = load_close("GLD")
    fxi = load_close("FXI")
    dr_closes = {}
    for s in DR_COVERED:
        c = load_close(s)
        if c is not None and len(c) > 400:
            dr_closes[s] = c
    print(f"ใช้ได้ {len(dr_closes)}/{len(DR_COVERED)} หุ้น DR mega-cap\n")

    results = []

    v, inv = sim_index_dca_monthly(spy, MONTHLY_THB, RMF_FEE, N_MONTHS)
    results.append(("A) RMF S&P500 (K-US500XRMF)", v * TAX_MULT, inv))

    weights = {"SPY": 0.40, "IXN": 0.30, "GLD": 0.20, "FXI": 0.10}
    v, inv = sim_blend_dca_monthly({"SPY": spy, "IXN": ixn, "GLD": gld, "FXI": fxi}, weights, MONTHLY_THB, RMF_FEE, N_MONTHS)
    results.append(("B) RMF blend 40/30/20/10", v * TAX_MULT, inv))

    v, inv = sim_index_dca_monthly(spy, MONTHLY_THB, SPY_FEE, N_MONTHS)
    results.append(("C) SPY ตรงๆ (ไม่ลดหย่อนภาษี)", v, inv))

    v, inv = sim_dr_momentum_dca_monthly(dr_closes, MONTHLY_THB, top_n=3, n_months=N_MONTHS)
    results.append(("D) DR Momentum Top-3 (21 mega-cap)", v, inv))

    v, inv = sim_dr_momentum_dca_monthly(dr_closes, MONTHLY_THB, top_n=5, n_months=N_MONTHS)
    results.append(("E) DR Momentum Top-5", v, inv))

    print(f"{'ทาง':45s} {'เงินลงทุนรวม':>15s} {'มูลค่าสุดท้าย':>15s} {'กำไร':>12s} {'ผลตอบแทน':>10s}")
    print("=" * 105)
    for label, final_v, invested in results:
        profit_pct = (final_v / invested - 1) * 100
        print(f"{label:45s} {invested:15,.0f} {final_v:15,.0f} {final_v-invested:12,.0f} {profit_pct:9.1f}%")

    over_cap_per_year = MONTHLY_THB * 12 - RMF_ANNUAL_CAP_THB
    print(f"\n⚠️ หมายเหตุ: เดือนละ {MONTHLY_THB:,} บาท x 12 = {MONTHLY_THB*12:,.0f} บาท/ปี "
          f"แต่ลิมิตลดหย่อน RMF+SSF+PVD จริงคือ {RMF_ANNUAL_CAP_THB:,.0f} บาท/ปี")
    print(f"   ส่วนเกิน {over_cap_per_year:,.0f} บาท/ปี จะไม่ได้สิทธิ์ลดหย่อนภาษี (ตัวเลข A/B ด้านบนคำนวณ")
    print(f"   ตัวคูณภาษีจากเงินลงทุนทั้งหมด ซึ่งจริงๆ แล้วสูงเกินจริงไปเล็กน้อยสำหรับส่วนที่เกินลิมิต)")

    df = pd.DataFrame([dict(label=l, final_value=v, invested=i, profit_pct=(v/i-1)*100) for l, v, i in results])
    df.to_csv("dca_50k_monthly_compare.csv", index=False)
    print("\nบันทึกไว้ที่ dca_50k_monthly_compare.csv")


if __name__ == "__main__":
    main()
