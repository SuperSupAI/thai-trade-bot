#!/usr/bin/env python
"""
เทียบ DCA 10 ปี 3 ทาง ที่ 2 ระดับเงินต้นต่อปี (200,000 และ 600,000 บาท):
  A) RMF S&P500 (+25% คืนภาษี) หักค่าธรรมเนียม RMF 0.54%/ปี
  C) SPY ตรงๆ ไม่มีลดหย่อนภาษี (ค่าธรรมเนียม ETF ต่ำมาก ~0.03%/ปี) -- ไม่มี RMF wrapper
  B) สูตร E4+ExitF ของเราเอง ไม่มีลดหย่อนภาษี (เหมือนเดิม)
จ่ายออกจากกระเป๋าจริงเท่ากันทั้ง 3 ทางในแต่ละระดับ
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
N_YEARS = 10
TAX_RATE = 0.25
RMF_FEE = 0.0054
SPY_FEE = 0.0003
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.20


def sim_index_dca(spy_seg, all_dates, inject_idx, annual_thb_invested, fee_rate):
    """จำลอง DCA เข้าดัชนี (RMF หรือ SPY ตรง) พร้อมหัก fee รายปีแบบทบต้น"""
    inject_usd = annual_thb_invested / THB_PER_USD
    shares = 0.0
    equity = []
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            price = float(spy_seg.iloc[i])
            shares += inject_usd / price
        equity.append(shares * float(spy_seg.iloc[i]))
    yrs_elapsed = np.array([(all_dates[i] - all_dates[0]).days / 365.25 for i in range(len(all_dates))])
    fee_decay = (1 - fee_rate) ** yrs_elapsed
    return np.array(equity) * fee_decay


def sim_strategy_dca(prep, syms_order, all_dates, inject_idx, annual_thb_invested):
    inject_usd = annual_thb_invested / THB_PER_USD
    cash = 0.0
    positions = {}
    total_injected_usd = 0.0
    equity = []
    trades_count, wins = 0, 0
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            cash += inject_usd
            total_injected_usd += inject_usd
        pos_size = total_injected_usd / TARGET_SLOTS

        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            ema200 = float(P["emas"][200].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            if chg <= -HARD_SL or price < ema200:
                cash += pos["qty"] * price * (1 - FEE)
                trades_count += 1
                if chg > 0:
                    wins += 1
                del positions[sym]

        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E4_Simple200"].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=float(qty), entry_price=price)

        val = cash
        for sym, pos in positions.items():
            series = prep[sym]["close"]
            px = float(series.loc[dt]) if dt in series.index else float(series[series.index <= dt].iloc[-1])
            val += pos["qty"] * px
        equity.append(val)
    wr = (wins / trades_count * 100) if trades_count else 0.0
    return np.array(equity), trades_count, wr


def run_for_level(annual_out_of_pocket_thb, prep, syms_order, spy_seg, all_dates, inject_idx):
    total_out_of_pocket = annual_out_of_pocket_thb * N_YEARS
    rmf_annual_invested = annual_out_of_pocket_thb / (1 - TAX_RATE)

    rmf_eq = sim_index_dca(spy_seg, all_dates, inject_idx, rmf_annual_invested, RMF_FEE)
    spy_eq = sim_index_dca(spy_seg, all_dates, inject_idx, annual_out_of_pocket_thb, SPY_FEE)
    strat_eq, trades, wr = sim_strategy_dca(prep, syms_order, all_dates, inject_idx, annual_out_of_pocket_thb)

    rmf_final = rmf_eq[-1] * THB_PER_USD
    spy_final = spy_eq[-1] * THB_PER_USD
    strat_final = strat_eq[-1] * THB_PER_USD

    print("\n" + "=" * 90)
    print(f"เงินต้นปีละ {annual_out_of_pocket_thb:,} บาท x {N_YEARS} ปี = {total_out_of_pocket:,} บาทรวม")
    print("=" * 90)
    rows = [
        ("A) RMF S&P500 (+25% คืนภาษี, fee 0.54%)", rmf_final),
        ("C) SPY ตรงๆ (ไม่ลดหย่อน, fee ~0.03%)", spy_final),
        ("B) สูตร E4+ExitF (ไม่ลดหย่อน)", strat_final),
    ]
    for label, final_thb in rows:
        profit = final_thb - total_out_of_pocket
        ret_pct = (final_thb / total_out_of_pocket - 1) * 100
        print(f"{label:42s} มูลค่า {final_thb:>12,.0f} บาท  กำไร {profit:>+12,.0f} บาท  ผลตอบแทน {ret_pct:>+7.1f}%")
    print(f"สูตร B: {trades} ไม้ · win rate {wr:.1f}%")
    return rows


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    with open(SPY_CACHE_FILE, "rb") as f:
        spy = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    n = len(all_dates)
    inject_idx = [min(i * 252, n - 1) for i in range(N_YEARS)]
    spy_seg = spy.reindex(all_dates).ffill()
    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()} ({n} วันเทรด)")

    all_rows = []
    for level in [200_000, 600_000]:
        rows = run_for_level(level, prep, syms_order, spy_seg, all_dates, inject_idx)
        for label, final_thb in rows:
            all_rows.append(dict(annual_thb=level, variant=label, final_thb=round(final_thb)))

    df = pd.DataFrame(all_rows)
    df.to_csv("dca_3way_compare_results.csv", index=False)
    print("\nบันทึกไว้ที่ dca_3way_compare_results.csv")


if __name__ == "__main__":
    main()
