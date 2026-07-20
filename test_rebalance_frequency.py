#!/usr/bin/env python
"""
ทดสอบว่าความถี่ rebalance (REBAL) แบบไหนดีที่สุด -- เทียบ 5 (รายสัปดาห์), 10 (ราย 2 สัปดาห์),
21 (รายเดือน, ค่าเดิม), 42 (ราย 2 เดือน), 63 (รายไตรมาส) วัน บนทั้ง DR universe (21 mega-cap สหรัฐฯ)
และหุ้นไทย (75 ตัว) เต็ม 10 ปี พร้อมเช็ค TRAIN/VALID/TEST เพื่อความเสถียร
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum_dr_universe import DR_COVERED

FORMATION, SKIP = 252, 21
CAPITAL_THB = 1_000_000
DR_RATIO = 0.01
TOP_N = 5
FREQS = [5, 10, 21, 42, 63]


def sim_momentum(price_lookup, syms_order, test_dates, top_n, rebal, capital_thb, fee, thb_per_usd=None, dr_ratio=1.0):
    """price_lookup: dict sym -> pd.Series close. ถ้า thb_per_usd=None ถือว่าราคาบาทตรงๆ (หุ้นไทย)"""
    capital_base = capital_thb / thb_per_usd if thb_per_usd else capital_thb
    cash = capital_base
    positions = {}
    trades_count, wins = 0, 0
    entry_px = {}
    rebal_dates = test_dates[::rebal]

    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            close = price_lookup[sym]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            if i < FORMATION:
                continue
            p_now = close.iloc[i - SKIP]
            p_start = close.iloc[i - FORMATION]
            if p_start <= 0:
                continue
            scores.append((sym, p_now / p_start - 1))
        scores.sort(key=lambda x: x[1], reverse=True)
        target = set(s for s, _ in scores[:top_n])

        for sym in list(positions):
            if sym not in target:
                close = price_lookup[sym]
                if dt in close.index:
                    price = float(close.loc[dt]) * dr_ratio
                    cash += positions[sym] * price * (1 - fee)
                    trades_count += 1
                    if price > entry_px[sym]:
                        wins += 1
                    del positions[sym]

        new_syms = [s for s in target if s not in positions]
        if new_syms:
            budget_each = cash / len(new_syms)
            for sym in new_syms:
                close = price_lookup[sym]
                if dt not in close.index:
                    continue
                price = float(close.loc[dt]) * dr_ratio
                qty = int((budget_each * (1 - fee)) / price)
                if qty < 1:
                    continue
                cash -= qty * price * (1 + fee)
                positions[sym] = qty
                entry_px[sym] = price

    last_dt = test_dates[-1]
    val = cash
    for sym, qty in positions.items():
        close = price_lookup[sym]
        px = float(close.loc[last_dt]) * dr_ratio if last_dt in close.index else float(close.iloc[-1]) * dr_ratio
        val += qty * px
    ret_pct = (val / capital_base - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def run_universe(name, price_lookup, syms_order, thb_per_usd, dr_ratio, fee):
    all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"\n{'='*100}")
    print(f"{name}  (ทั้งชุด {all_dates[0].date()} -> {all_dates[-1].date()}, top_n={TOP_N})")
    print(f"{'='*100}")
    print(f"{'REBAL':>6s}  {'ALL 10ปี':>22s}  {'TRAIN':>22s}  {'VALID':>22s}  {'TEST':>22s}")
    rows = []
    for rebal in FREQS:
        m_all = sim_momentum(price_lookup, syms_order, all_dates, TOP_N, rebal, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
        m_train = sim_momentum(price_lookup, syms_order, train_dates, TOP_N, rebal, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
        m_valid = sim_momentum(price_lookup, syms_order, valid_dates, TOP_N, rebal, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
        m_test = sim_momentum(price_lookup, syms_order, test_dates_, TOP_N, rebal, CAPITAL_THB, fee, thb_per_usd, dr_ratio)

        def fmt(m):
            return f"{m['ret_pct']:+7.1f}%(n={m['trades']:3d})"

        days_label = {5: "5(สัปดาห์)", 10: "10(2สัปดาห์)", 21: "21(เดือน)", 42: "42(2เดือน)", 63: "63(ไตรมาส)"}[rebal]
        print(f"{days_label:>14s}  {fmt(m_all):>22s}  {fmt(m_train):>22s}  {fmt(m_valid):>22s}  {fmt(m_test):>22s}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(universe=name, rebal=rebal, period=period, **m))
    return rows


def main():
    all_rows = []

    with open("us_close_10y_cache.pkl", "rb") as f:
        us_data = pickle.load(f)
    prep = teo.precompute(us_data)
    prep = add_extra_signals(prep)
    dr_syms = [s for s in DR_COVERED if s in prep]
    dr_price_lookup = {s: prep[s]["close"] for s in dr_syms}
    all_rows += run_universe("DR universe (21 mega-cap สหรัฐฯ, ไม่มีภาษี)", dr_price_lookup, dr_syms,
                              thb_per_usd=teo.THB_PER_USD, dr_ratio=DR_RATIO, fee=teo.FEE)

    with open("thai_stocks_10y_cache.pkl", "rb") as f:
        thai_data = pickle.load(f)
    thai_syms = sorted(thai_data.keys())
    all_rows += run_universe("หุ้นไทย (75 ตัว, ไม่มีภาษี)", thai_data, thai_syms,
                              thb_per_usd=None, dr_ratio=1.0, fee=0.002)

    pd.DataFrame(all_rows).to_csv("rebalance_frequency_results.csv", index=False)
    print("\nบันทึกไว้ที่ rebalance_frequency_results.csv")


if __name__ == "__main__":
    main()
