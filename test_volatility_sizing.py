#!/usr/bin/env python
"""
ทดสอบ volatility-based position sizing (risk parity แบบง่าย) บน E4+ExitF -- แทนที่จะให้ทุกไม้ได้งบ
เท่ากัน (ทุน/target_slots) ให้หุ้นที่แกว่งแรง (volatility สูง) ได้งบน้อยกว่า หุ้นนิ่งได้งบมากกว่า
เพื่อให้แต่ละ position มี "ความเสี่ยงเท่ากันโดยประมาณ" แทนที่จะมี "เงินเท่ากัน"

วิธีคำนวณ: budget_i = base_budget * clip(median_vol_ทั้งตลาด / vol_i(60วันล่าสุด ณ วันเข้า), 0.4, 2.5)
(cap ไว้กันไม่ให้หุ้นนิ่งมากๆ ได้งบเยอะเกินจนกระจุกตัว หรือหุ้นแกว่งแรงมากได้งบน้อยจนไม่มีความหมาย)
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
CAPITAL_THB = 1_000_000
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.20
VOL_LOOKBACK = 60
VOL_CAP_LOW, VOL_CAP_HIGH = 0.4, 2.5


def add_vol_signal(prep):
    for sym, P in prep.items():
        ret = P["close"].pct_change()
        vol = ret.rolling(VOL_LOOKBACK, min_periods=30).std()
        P["vol60"] = vol
    return prep


def sim_vol_sized(prep, syms_order, test_dates, target_slots, capital_thb=CAPITAL_THB):
    capital_usd = capital_thb / THB_PER_USD
    base_pos_size = capital_usd / target_slots
    cash = capital_usd
    positions = {}
    trades_count, wins = 0, 0

    for dt in test_dates:
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

        # หา median volatility ของหุ้นทั้งตลาด ณ วันนี้ (จากหุ้นที่มีค่า vol60 วันนี้)
        vols_today = []
        for sym in syms_order:
            P = prep[sym]
            if dt in P["vol60"].index:
                v = P["vol60"].loc[dt]
                if pd.notna(v) and v > 0:
                    vols_today.append(v)
        median_vol = float(np.median(vols_today)) if vols_today else None

        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E4_Simple200"].loc[dt]):
                continue
            v = P["vol60"].loc[dt] if dt in P["vol60"].index else None
            if median_vol is None or v is None or pd.isna(v) or v <= 0:
                budget = base_pos_size
            else:
                scale = np.clip(median_vol / v, VOL_CAP_LOW, VOL_CAP_HIGH)
                budget = base_pos_size * scale
            price = float(P["close"].loc[dt])
            budget = min(budget, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=qty, entry_price=price)

    val = cash
    for sym, pos in positions.items():
        val += pos["qty"] * float(prep[sym]["close"].iloc[-1])
    ret_pct = (val / capital_usd - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    prep = add_vol_signal(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท\n")

    rows = []
    for slots in [5, 10, 20]:
        m_old = sim_e4_trendexit(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        m_new = sim_vol_sized(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        print(f"{slots:2d} ไม้:")
        print(f"  E4 เดิม (งบเท่ากันทุกไม้):        {m_old['ret_pct']:+7.1f}%  ไม้ {m_old['trades']:4d}  WR {m_old['wr']:5.1f}%")
        print(f"  E4 + Volatility sizing:          {m_new['ret_pct']:+7.1f}%  ไม้ {m_new['trades']:4d}  WR {m_new['wr']:5.1f}%")
        rows.append(dict(slots=slots, variant="E4 เดิม", **m_old))
        rows.append(dict(slots=slots, variant="E4+VolSizing", **m_new))
        print()

    pd.DataFrame(rows).to_csv("volatility_sizing_results.csv", index=False)
    print("บันทึกไว้ที่ volatility_sizing_results.csv")


if __name__ == "__main__":
    main()
