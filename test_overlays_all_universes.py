#!/usr/bin/env python
"""
เทียบ Baseline vs #4 Trend Filter Overlay vs #2v2 Regime-Aware (breadth-based) ย้อนหลัง 10 ปีเต็ม
ทดสอบครบ 3 universe: หุ้นไทย (75 ตัว), DR mega-cap (21 ตัวที่มี DR จริง), หุ้นเมกาสหรัฐฯ เต็ม (76 ตัว ไม่จำกัดแค่ DR)
"""
import pickle
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum_dr_universe import DR_COVERED
from universe import US_STOCKS

FORMATION, SKIP, REBAL = 252, 21, 21
CAPITAL_THB = 1_000_000
RISK_OFF_EXPOSURE = 0.50
BREADTH_THRESHOLD = 0.40


def momentum_score(close, i):
    if i < FORMATION:
        return None
    p_now = close.iloc[i - SKIP]
    p_start = close.iloc[i - FORMATION]
    if p_start <= 0:
        return None
    return p_now / p_start - 1


def compute_avg_ema200_ratio(price_lookup, syms_order):
    all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
    ratios = pd.DataFrame(index=all_dates)
    for sym in syms_order:
        close = price_lookup[sym].reindex(all_dates).ffill()
        ema200 = close.ewm(span=200, adjust=False).mean()
        ratios[sym] = close / ema200
    return ratios.mean(axis=1)


def compute_breadth_series(price_lookup, ema200_lookup, syms_order):
    all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
    above = pd.DataFrame(index=all_dates)
    for sym in syms_order:
        close = price_lookup[sym].reindex(all_dates).ffill()
        ema200 = ema200_lookup[sym].reindex(all_dates).ffill()
        above[sym] = (close > ema200).astype(float)
    return above.mean(axis=1)


def sim(price_lookup, syms_order, test_dates, top_n, mode, signal_series, capital_thb, fee, thb_per_usd, dr_ratio):
    capital_base = capital_thb / thb_per_usd if thb_per_usd else capital_thb
    cash = capital_base
    positions = {}
    trades_count, wins = 0, 0
    entry_px = {}

    def pv(dt):
        v = cash
        for s, q in positions.items():
            c = price_lookup[s]
            if dt in c.index:
                v += q * float(c.loc[dt]) * dr_ratio
        return v

    for dt in test_dates[::REBAL]:
        target_fraction = 1.0
        if mode != "baseline" and signal_series is not None and dt in signal_series.index:
            sig = signal_series.loc[dt]
            if mode == "trend_filter" and sig < 1.0:
                target_fraction = RISK_OFF_EXPOSURE
            elif mode == "regime_breadth" and sig < BREADTH_THRESHOLD:
                target_fraction = RISK_OFF_EXPOSURE

        scores = []
        for sym in syms_order:
            close = price_lookup[sym]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            sc = momentum_score(close, i)
            if sc is not None:
                scores.append((sym, sc))
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

        total_val = pv(dt)
        invest_budget_total = total_val * target_fraction
        held_val = sum(positions[s] * float(price_lookup[s].loc[dt]) * dr_ratio
                        for s in positions if dt in price_lookup[s].index)
        remaining_budget = max(0, invest_budget_total - held_val)
        new_syms = [s for s in target if s not in positions]
        if new_syms and remaining_budget > 1:
            budget_each = remaining_budget / len(new_syms)
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
    val = pv(last_dt)
    ret_pct = (val / capital_base - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def run_universe(label, price_lookup, syms_order, thb_per_usd, dr_ratio, fee, top_ns):
    all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]
    dates_2022 = [d for d in all_dates if d.year == 2022]

    print(f"\n{'='*105}")
    print(f"{label}  ({len(syms_order)} ตัว, {all_dates[0].date()} -> {all_dates[-1].date()})")
    print(f"{'='*105}")

    ema200_lookup = {s: price_lookup[s].ewm(span=200, adjust=False).mean() for s in syms_order}
    trend_signal = compute_avg_ema200_ratio(price_lookup, syms_order)
    breadth_signal = compute_breadth_series(price_lookup, ema200_lookup, syms_order)

    rows = []
    for top_n in top_ns:
        print(f"\n--- top_n = {top_n} ---")
        for mode, sig, mlabel in [("baseline", None, "Baseline"),
                                   ("trend_filter", trend_signal, "#4 Trend Filter"),
                                   ("regime_breadth", breadth_signal, "#2v2 Regime Breadth")]:
            results = {}
            for period, dates in [("ALL", all_dates), ("TRAIN", train_dates), ("VALID", valid_dates),
                                   ("TEST", test_dates_), ("2022", dates_2022)]:
                m = sim(price_lookup, syms_order, dates, top_n, mode, sig, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
                results[period] = m
                rows.append(dict(universe=label, top_n=top_n, mode=mlabel, period=period, **m))
            print(f"{mlabel:22s} ALL:{results['ALL']['ret_pct']:+8.1f}%  TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  "
                  f"VALID:{results['VALID']['ret_pct']:+8.1f}%  TEST:{results['TEST']['ret_pct']:+8.1f}%  "
                  f"2022:{results['2022']['ret_pct']:+8.1f}%")
    return rows


def main():
    all_rows = []

    # 1) DR mega-cap (21 ตัว, tax-free, DR ratio 0.01)
    with open("us_close_10y_cache.pkl", "rb") as f:
        us_data = pickle.load(f)
    prep = teo.precompute(us_data)
    prep = add_extra_signals(prep)
    dr_syms = [s for s in DR_COVERED if s in prep]
    dr_price_lookup = {s: prep[s]["close"] for s in dr_syms}
    all_rows += run_universe("DR mega-cap (21 ตัว, ไม่มีภาษี)", dr_price_lookup, dr_syms,
                              teo.THB_PER_USD, 0.01, teo.FEE, [3, 5])

    # 2) หุ้นเมกาสหรัฐฯ เต็ม (76 ตัว, โดนภาษีถ้าเทรดตรง แต่ตัวเลขนี้เป็น pretax)
    us_syms = [s for s in US_STOCKS if s in prep]
    us_price_lookup = {s: prep[s]["close"] for s in us_syms}
    all_rows += run_universe("หุ้นเมกาสหรัฐฯ เต็ม (76 ตัว, pretax)", us_price_lookup, us_syms,
                              teo.THB_PER_USD, 1.0, teo.FEE, [3, 5])

    # 3) หุ้นไทย (75 ตัว, ไม่มีภาษี)
    with open("thai_stocks_10y_cache.pkl", "rb") as f:
        thai_data = pickle.load(f)
    thai_syms = sorted(thai_data.keys())
    all_rows += run_universe("หุ้นไทย (75 ตัว, ไม่มีภาษี)", thai_data, thai_syms,
                              None, 1.0, 0.002, [3, 5])

    pd.DataFrame(all_rows).to_csv("overlays_all_universes_results.csv", index=False)
    print("\nบันทึกไว้ที่ overlays_all_universes_results.csv")


if __name__ == "__main__":
    main()
