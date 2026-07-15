#!/usr/bin/env python
"""
เทียบพอร์ตผสม RMF 10 แบบ (รวมจีนด้วย) เทียบกับถือ K-US500XRMF ล้วน 100%
DCA ปีละ 200,000 บาท x 10 ปี ได้คืนภาษี 25% เท่ากันทุกแบบ (สมมติทุกกองเป็น RMF, fee 0.54%/ปีเท่ากันหมด)
"""
import pickle
import numpy as np
import pandas as pd

N_YEARS = 10
TAX_RATE = 0.25
FEE = 0.0054
ANNUAL_OUT_OF_POCKET_THB = 200_000
THB_PER_USD = 35.5

LABELS = {
    "SPY": "S&P500", "QQQ": "Nasdaq100", "MCHI": "จีน", "INDA": "อินเดีย",
    "EWJ": "ญี่ปุ่น", "VGK": "ยุโรป", "VNM": "เวียดนาม", "GLD": "ทองคำ",
    "ACWI": "หุ้นโลก", "IXN": "เทคโลก",
}

PORTFOLIOS = [
    ("1) SPY 100%", {"SPY": 1.00}),
    ("2) SPY 90% + ทอง 10%", {"SPY": 0.90, "GLD": 0.10}),
    ("3) SPY 80% + ทอง 20%", {"SPY": 0.80, "GLD": 0.20}),
    ("4) SPY 70% + ทอง 20% + อินเดีย 10%", {"SPY": 0.70, "GLD": 0.20, "INDA": 0.10}),
    ("5) SPY 70% + ทอง 20% + จีน 10%", {"SPY": 0.70, "GLD": 0.20, "MCHI": 0.10}),
    ("6) SPY 60% + ทอง 20% + อินเดีย 10% + จีน 10%", {"SPY": 0.60, "GLD": 0.20, "INDA": 0.10, "MCHI": 0.10}),
    ("7) SPY 50% + หุ้นโลก 30% + ทอง 20%", {"SPY": 0.50, "ACWI": 0.30, "GLD": 0.20}),
    ("8) หุ้นโลก 60% + ทอง 20% + อินเดีย 20% (ไม่กระจุกสหรัฐฯ)", {"ACWI": 0.60, "GLD": 0.20, "INDA": 0.20}),
    ("9) SPY 40% + Nasdaq 30% + ทอง 20% + จีน 10% (เทคหนัก)", {"SPY": 0.40, "QQQ": 0.30, "GLD": 0.20, "MCHI": 0.10}),
    ("10) SPY 25% + จีน 25% + อินเดีย 25% + ทอง 25% (equal-weight)", {"SPY": 0.25, "MCHI": 0.25, "INDA": 0.25, "GLD": 0.25}),
    ("11) SPY 50% + อินเดีย 30% + ทอง 20% (เอียงอินเดียหนัก)", {"SPY": 0.50, "INDA": 0.30, "GLD": 0.20}),
    ("12) SPY 40% + อินเดีย 20% + เวียดนาม 20% + ทอง 20% (เอียงอินเดีย+เวียดนาม)", {"SPY": 0.40, "INDA": 0.20, "VNM": 0.20, "GLD": 0.20}),
    ("13) SPY 60% + อินเดีย 20% + เวียดนาม 10% + ทอง 10%", {"SPY": 0.60, "INDA": 0.20, "VNM": 0.10, "GLD": 0.10}),
    ("14) อินเดีย 40% + เวียดนาม 20% + ทอง 20% + SPY 20% (เอียง EM หนักสุด)", {"INDA": 0.40, "VNM": 0.20, "GLD": 0.20, "SPY": 0.20}),
]


def load(ticker):
    with open(f"{ticker.lower()}_10y_cache.pkl", "rb") as f:
        return pickle.load(f)


def sim_blend_dca(px, all_dates, inject_idx, weights):
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
    all_tickers = sorted(set().union(*[set(w.keys()) for _, w in PORTFOLIOS]))
    data = {t: load(t) for t in all_tickers}
    all_dates_raw = sorted(set().union(*[c.index for c in data.values()]))
    px_raw = pd.DataFrame({t: data[t].reindex(all_dates_raw).ffill() for t in all_tickers})
    # ตัดวันแรกๆ ที่บางกองยังไม่มีราคา (ffill ไม่มีอะไรให้ fill ย้อนหลัง) ออก
    # เพื่อไม่ให้วันแรกของ DCA เป็น NaN/0 แล้วทำให้ equity curve ผิดเพี้ยน
    first_valid = px_raw.dropna(how="any").index[0]
    all_dates = [d for d in all_dates_raw if d >= first_valid]
    px = px_raw.loc[all_dates]
    n = len(all_dates)
    inject_idx = [min(i * 252, n - 1) for i in range(N_YEARS)]
    total_out_of_pocket = ANNUAL_OUT_OF_POCKET_THB * N_YEARS

    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"จ่ายจริงปีละ {ANNUAL_OUT_OF_POCKET_THB:,} บาท x {N_YEARS} ปี = {total_out_of_pocket:,} บาทรวม\n")

    rows = []
    curves = {"date": all_dates}
    for name, weights in PORTFOLIOS:
        weight_str = " + ".join(f"{LABELS[t]} {w*100:.0f}%" for t, w in weights.items())
        eq_thb = sim_blend_dca(px, all_dates, inject_idx, weights) * THB_PER_USD
        curves[name] = eq_thb
        vol, mdd = risk_metrics(eq_thb)
        final = eq_thb[-1]
        profit = final - total_out_of_pocket
        ret_pct = (final / total_out_of_pocket - 1) * 100
        rows.append(dict(พอร์ต=name, สัดส่วน=weight_str, final_thb=round(final), profit_thb=round(profit),
                          ret_pct=round(ret_pct, 1), vol_pct=round(vol, 1), max_dd_pct=round(mdd, 1)))

    pd.DataFrame(curves).to_csv("rmf_blend_all_equity_curves.csv", index=False)

    df = pd.DataFrame(rows)
    print("=" * 130)
    print("เรียงตามผลตอบแทน (สูง -> ต่ำ)")
    print("=" * 130)
    df_sorted = df.sort_values("ret_pct", ascending=False)
    for _, r in df_sorted.iterrows():
        print(f"{r['พอร์ต']:50s} ผลตอบแทน {r['ret_pct']:>+7.1f}%  มูลค่า {r['final_thb']:>12,.0f} บาท  "
              f"vol/ปี {r['vol_pct']:>5.1f}%  max DD {r['max_dd_pct']:>6.1f}%")

    print("\n" + "=" * 130)
    print("เรียงตาม max drawdown ตื้นสุด (เสี่ยงน้อยสุด -> เสี่ยงมากสุด)")
    print("=" * 130)
    df_sorted2 = df.sort_values("max_dd_pct", ascending=False)
    for _, r in df_sorted2.iterrows():
        print(f"{r['พอร์ต']:50s} max DD {r['max_dd_pct']:>6.1f}%  ผลตอบแทน {r['ret_pct']:>+7.1f}%  vol/ปี {r['vol_pct']:>5.1f}%")

    df.to_csv("rmf_blend_10_portfolios_results.csv", index=False)
    print("\nบันทึกไว้ที่ rmf_blend_10_portfolios_results.csv")


if __name__ == "__main__":
    main()
