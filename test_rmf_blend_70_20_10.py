#!/usr/bin/env python
"""
เทียบพอร์ตผสม RMF 70% S&P500 + 20% ทองคำ + 10% อินเดีย เทียบกับถือ K-US500XRMF ล้วน 100%
DCA ปีละ 200,000 บาท x 10 ปี (จ่ายจริงเท่ากัน ได้คืนภาษี 25% เหมือนกันทั้งคู่ เพราะเป็น RMF ทั้งคู่)
หัก fee 0.54%/ปีทุกกอง (สมมติเท่ากันเพื่อเทียบง่าย ของจริงอาจต่างกันตามกอง)

รายงาน: ผลตอบแทนสุดท้าย, กำไร, และ risk metrics (volatility, max drawdown) เทียบกัน
เพื่อดูว่าการกระจายช่วยลดความผันผวน/max drawdown ได้แค่ไหน แลกกับผลตอบแทนที่อาจลดลง
"""
import pickle
import numpy as np
import pandas as pd

N_YEARS = 10
TAX_RATE = 0.25
FEE = 0.0054
ANNUAL_OUT_OF_POCKET_THB = 200_000
THB_PER_USD = 35.5

WEIGHTS = {"SPY": 0.70, "GLD": 0.20, "INDA": 0.10}
LABELS = {"SPY": "K-US500XRMF (S&P500)", "GLD": "K-GDRMF (ทองคำ)", "INDA": "K-INDIARMF (อินเดีย)"}


def load(ticker):
    with open(f"{ticker.lower()}_10y_cache.pkl", "rb") as f:
        return pickle.load(f)


def sim_blend_dca(px, all_dates, inject_idx, weights):
    """DCA เข้าหลายกองตามสัดส่วน weights ในทุกรอบเติมเงิน แต่ละกองหัก fee ของตัวเองแยกกัน"""
    rmf_annual_invested_thb = ANNUAL_OUT_OF_POCKET_THB / (1 - TAX_RATE)
    shares = {t: 0.0 for t in weights}
    equity_by_fund = {t: [] for t in weights}
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            for t, w in weights.items():
                inject_usd = (rmf_annual_invested_thb * w) / THB_PER_USD
                price = float(px[t].iloc[i])
                if not np.isnan(price) and price > 0:
                    shares[t] += inject_usd / price
        for t in weights:
            price = float(px[t].iloc[i])
            val = shares[t] * price if not np.isnan(price) else (equity_by_fund[t][-1] if equity_by_fund[t] else 0.0)
            equity_by_fund[t].append(val)

    yrs_elapsed = np.array([(all_dates[i] - all_dates[0]).days / 365.25 for i in range(len(all_dates))])
    fee_decay = (1 - FEE) ** yrs_elapsed
    total = np.zeros(len(all_dates))
    for t in weights:
        total += np.array(equity_by_fund[t]) * fee_decay
    return total


def risk_metrics(equity_thb):
    eq = pd.Series(equity_thb)
    daily_ret = eq.pct_change().dropna()
    ann_vol = daily_ret.std() * np.sqrt(252) * 100
    roll_max = eq.cummax()
    dd = (eq / roll_max - 1) * 100
    max_dd = dd.min()
    return ann_vol, max_dd


def main():
    tickers = list(WEIGHTS.keys())
    data = {t: load(t) for t in tickers}
    all_dates = sorted(set().union(*[c.index for c in data.values()]))
    px = pd.DataFrame({t: data[t].reindex(all_dates).ffill() for t in tickers})
    n = len(all_dates)
    inject_idx = [min(i * 252, n - 1) for i in range(N_YEARS)]
    total_out_of_pocket = ANNUAL_OUT_OF_POCKET_THB * N_YEARS

    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"จ่ายจริงปีละ {ANNUAL_OUT_OF_POCKET_THB:,} บาท x {N_YEARS} ปี = {total_out_of_pocket:,} บาทรวม "
          f"(ลงทุนได้จริงปีละ {ANNUAL_OUT_OF_POCKET_THB/(1-TAX_RATE):,.0f} บาท จากคืนภาษี 25%)\n")

    # Blend 70/20/10
    blend_eq_usd = sim_blend_dca(px, all_dates, inject_idx, WEIGHTS)
    blend_eq_thb = blend_eq_usd * THB_PER_USD

    # Pure SPY 100%
    pure_eq_usd = sim_blend_dca(px, all_dates, inject_idx, {"SPY": 1.0})
    pure_eq_thb = pure_eq_usd * THB_PER_USD

    blend_vol, blend_dd = risk_metrics(blend_eq_thb)
    pure_vol, pure_dd = risk_metrics(pure_eq_thb)

    rows = [
        ("พอร์ตผสม 70% SPY + 20% ทอง + 10% อินเดีย", blend_eq_thb[-1], blend_vol, blend_dd),
        ("K-US500XRMF ล้วน 100% (S&P500)", pure_eq_thb[-1], pure_vol, pure_dd),
    ]

    print("=" * 100)
    print(f"{'แผน':45s}{'มูลค่าสุดท้าย':>16s}{'กำไร':>15s}{'ผลตอบแทน':>10s}{'ผันผวน/ปี':>12s}{'max drawdown':>14s}")
    print("=" * 100)
    for label, final_thb, vol, mdd in rows:
        profit = final_thb - total_out_of_pocket
        ret_pct = (final_thb / total_out_of_pocket - 1) * 100
        print(f"{label:45s}{final_thb:>16,.0f}{profit:>+15,.0f}{ret_pct:>+9.1f}%{vol:>11.1f}%{mdd:>13.1f}%")

    diff_final = blend_eq_thb[-1] - pure_eq_thb[-1]
    diff_vol = pure_vol - blend_vol
    diff_dd = pure_dd - blend_dd
    print(f"\nพอร์ตผสมได้ผลตอบแทนน้อยกว่าล้วน S&P500 อยู่ {abs(diff_final):,.0f} บาท "
          f"({'น้อยกว่า' if diff_final < 0 else 'มากกว่า'}) "
          f"แต่ผันผวนต่อปีต่ำกว่า {diff_vol:.1f} จุด% และ max drawdown ตื้นกว่า {diff_dd:.1f} จุด%")

    out = pd.DataFrame({"date": all_dates, "blend_70_20_10_thb": blend_eq_thb, "pure_spy_thb": pure_eq_thb})
    out.to_csv("rmf_blend_70_20_10_equity_curve.csv", index=False)
    print("\nบันทึก equity curve ไว้ที่ rmf_blend_70_20_10_equity_curve.csv")


if __name__ == "__main__":
    main()
