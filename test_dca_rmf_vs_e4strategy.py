#!/usr/bin/env python
"""
เทียบ DCA 10 ปี: จ่ายออกจากกระเป๋าปีละ 200,000 บาทเท่ากันทั้ง 2 ทาง
  A) RMF (K-US500XRMF-style): 200,000 บาท จ่ายจริง → ได้คืนภาษี 25% → ลงทุนได้จริง 266,667 บาท/ปี
     ในกองอ้างอิง S&P500 หักค่าธรรมเนียม 0.54%/ปี (ไม่รวมผลกระทบค่าเงิน THB/USD)
  B) สูตร E4+ExitF ของเราเอง (Close>EMA200 เข้า, ไม่มีเพดานกำไร, SL -20%): 200,000 บาท/ปี ลงทุนตรง
     ไม่มีการลดหย่อนภาษี (ไม่ใช่กองทุนจดทะเบียน RMF)
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_beat_spy_v2 import sim_e4_trendexit
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
ANNUAL_OUT_OF_POCKET_THB = 200_000
N_YEARS = 10
TAX_RATE = 0.25
RMF_FEE = 0.0054
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE


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
    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()} ({n} วันเทรด)")
    print(f"จ่ายออกจากกระเป๋าจริงปีละ {ANNUAL_OUT_OF_POCKET_THB:,} บาท x {N_YEARS} ปี "
          f"= {ANNUAL_OUT_OF_POCKET_THB*N_YEARS:,} บาทรวม (ต้นทุนจริงเท่ากันทั้ง 2 ทาง)\n")

    # ===== A) RMF: ได้คืนภาษี 25% ทุกปี -> ลงทุนได้มากกว่าที่จ่ายจริง =====
    rmf_invest_per_year_thb = ANNUAL_OUT_OF_POCKET_THB / (1 - TAX_RATE)
    inject_usd_rmf = rmf_invest_per_year_thb / THB_PER_USD
    print(f"RMF: จ่ายจริง {ANNUAL_OUT_OF_POCKET_THB:,} บาท/ปี -> ได้คืนภาษี 25% -> ลงทุนได้จริง "
          f"{rmf_invest_per_year_thb:,.0f} บาท/ปี ({inject_usd_rmf:,.0f} USD)")

    spy_seg = spy.reindex(all_dates).ffill()
    shares = 0.0
    rmf_equity = []
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            price = float(spy_seg.iloc[i])
            shares += inject_usd_rmf / price
        rmf_equity.append(shares * float(spy_seg.iloc[i]))
    # หัก RMF fee 0.54%/ปี: ประมาณคร่าวๆ ด้วยการคูณ equity curve ทั้งเส้นด้วย decay factor
    # ตามเวลาที่ผ่านไปนับจากวันแรก (ไม่ได้แยกตามอายุของเงินแต่ละก้อนที่ทยอยเติมเข้ามา แต่ผลใกล้เคียงพอ)
    yrs_elapsed = np.array([(all_dates[i] - all_dates[0]).days / 365.25 for i in range(n)])
    fee_decay = (1 - RMF_FEE) ** yrs_elapsed
    rmf_equity_net = np.array(rmf_equity) * fee_decay
    rmf_final_usd = rmf_equity_net[-1]

    # ===== B) สูตร E4+ExitF: ลงทุนตรง 200,000 บาท/ปี (ไม่มีลดหย่อน) =====
    inject_usd_strat = ANNUAL_OUT_OF_POCKET_THB / THB_PER_USD
    print(f"สูตร E4+ExitF: ลงทุนตรง {ANNUAL_OUT_OF_POCKET_THB:,} บาท/ปี ({inject_usd_strat:,.0f} USD) ไม่มีลดหย่อนภาษี\n")

    cash = 0.0
    positions = {}
    total_injected_usd = 0.0
    strat_equity = []
    trades_count, wins = 0, 0
    exits = teo.build_exit_grid()
    HARD_SL = 0.20
    for i, dt in enumerate(all_dates):
        if i in inject_idx:
            cash += inject_usd_strat
            total_injected_usd += inject_usd_strat
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
        strat_equity.append(val)
    strat_final_usd = strat_equity[-1]

    total_out_of_pocket_thb = ANNUAL_OUT_OF_POCKET_THB * N_YEARS
    rmf_final_thb = rmf_final_usd * THB_PER_USD
    strat_final_thb = strat_final_usd * THB_PER_USD

    print("=" * 80)
    print(f"ผล DCA 10 ปี -- จ่ายจริงเท่ากัน {total_out_of_pocket_thb:,} บาท (ปีละ {ANNUAL_OUT_OF_POCKET_THB:,})")
    print("=" * 80)
    print(f"{'':30s}{'A) RMF S&P500 (+25% คืนภาษี)':>32s}{'B) สูตร E4+ExitF (ไม่ลดหย่อน)':>32s}")
    print(f"{'มูลค่าสุดท้าย (บาท)':30s}{rmf_final_thb:>32,.0f}{strat_final_thb:>32,.0f}")
    print(f"{'กำไรสุทธิ (บาท)':30s}{rmf_final_thb-total_out_of_pocket_thb:>+32,.0f}{strat_final_thb-total_out_of_pocket_thb:>+32,.0f}")
    print(f"{'ผลตอบแทนเทียบทุนจ่ายจริง':30s}{(rmf_final_thb/total_out_of_pocket_thb-1)*100:>+31.1f}%{(strat_final_thb/total_out_of_pocket_thb-1)*100:>+31.1f}%")
    print(f"{'จำนวนไม้ (สูตร B)':30s}{'':>32s}{trades_count:>32d}")
    print(f"{'win rate (สูตร B)':30s}{'':>32s}{(wins/trades_count*100 if trades_count else 0):>31.1f}%")

    result = pd.DataFrame({"date": all_dates, "rmf_equity_thb": rmf_equity_net * THB_PER_USD,
                           "strategy_equity_thb": np.array(strat_equity) * THB_PER_USD})
    result.to_csv("dca_rmf_vs_e4strategy_equity_curve.csv", index=False)
    print("\nบันทึก equity curve รายวันไว้ที่ dca_rmf_vs_e4strategy_equity_curve.csv")


if __name__ == "__main__":
    main()
