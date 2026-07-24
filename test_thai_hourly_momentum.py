#!/usr/bin/env python
"""
เทส cross-sectional momentum บนราคารายชั่วโมง (60m) ของหุ้นไทย 75 ตัว ย้อนหลัง ~2 ปี (yfinance)
ใช้สูตรเดียวกับที่ backtest รายวันมาตลอด (formation/skip/rebal) แต่หน่วยเป็น "แท่งชั่วโมง" แทน "วันเทรด"
FORMATION=252/SKIP=21/REBAL=21 แท่งชั่วโมง (~40 วันเทรด lookback, ~4 วัน skip, รีบาลานซ์ทุก ~4 วัน)
"""
import pickle, sys
import pandas as pd
sys.path.insert(0, ".")

FORMATION, SKIP, REBAL, TOP_N = 252, 21, 21, 3
CAPITAL_THB = 1_000_000
FEE = 0.002


def sim(price_lookup, syms_order, test_dates, top_n, capital_thb=CAPITAL_THB, fee=FEE):
    cash = capital_thb
    positions = {}
    trades_count, wins = 0, 0
    entry_px = {}

    for dt in test_dates[::REBAL]:
        scores = []
        for sym in syms_order:
            close = price_lookup[sym]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            if i < FORMATION:
                continue
            p_now = close.iloc[i - SKIP]
            p_form = close.iloc[i - FORMATION]
            if p_form > 0:
                scores.append((sym, p_now / p_form - 1))
        scores.sort(key=lambda x: x[1], reverse=True)
        target = set(s for s, _ in scores[:top_n])

        for sym in list(positions):
            if sym not in target:
                close = price_lookup[sym]
                if dt in close.index:
                    price = float(close.loc[dt])
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
                price = float(close.loc[dt])
                qty = (budget_each * (1 - fee)) / price
                if qty <= 0:
                    continue
                cash -= qty * price * (1 + fee)
                positions[sym] = qty
                entry_px[sym] = price

    last_dt = test_dates[-1]
    val = cash
    for sym, qty in positions.items():
        close = price_lookup[sym]
        px = float(close.loc[last_dt]) if last_dt in close.index else float(close.iloc[-1])
        val += qty * px
    ret_pct = (val / capital_thb - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def main():
    with open("thai_hourly_2y_cache.pkl", "rb") as f:
        data = pickle.load(f)

    syms_order = list(data.keys())
    print(f"{len(syms_order)} ตัว มีข้อมูลราคารายชั่วโมง")

    all_dates = sorted(set().union(*[data[s].index for s in syms_order]))
    n = len(all_dates)
    print(f"ทั้งหมด {n} แท่งชั่วโมง ({all_dates[0]} ถึง {all_dates[-1]})")
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"\nTRAIN: {train_dates[0]} ถึง {train_dates[-1]} ({len(train_dates)} แท่ง)")
    print(f"VALID: {valid_dates[0]} ถึง {valid_dates[-1]} ({len(valid_dates)} แท่ง)")
    print(f"TEST:  {test_dates_[0]} ถึง {test_dates_[-1]} ({len(test_dates_)} แท่ง)")

    print(f"\n{'='*80}\ncross-sectional momentum รายชั่วโมง (F={FORMATION}/skip={SKIP}/rebal={REBAL} แท่ง)\n{'='*80}")
    for top_n in [3, 5]:
        results = {}
        for period, dates in [("ALL", all_dates), ("TRAIN", train_dates), ("VALID", valid_dates),
                               ("TEST", test_dates_)]:
            m = sim(data, syms_order, dates, top_n)
            results[period] = m
        print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+9.1f}%(n={results['ALL']['trades']:4d})  "
              f"TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  VALID:{results['VALID']['ret_pct']:+8.1f}%  "
              f"TEST:{results['TEST']['ret_pct']:+8.1f}%")

    # เทียบ buy&hold เท่าๆ กันทุกตัว (equal-weight) เป็น benchmark
    bh_val = 0
    for s in syms_order:
        c = data[s]
        bh_val += (1/len(syms_order)) * capital_ratio(c)
    print(f"\nBuy&Hold equal-weight ALL: {(bh_val-1)*100:+.1f}%")


def capital_ratio(close):
    return float(close.iloc[-1]) / float(close.iloc[0])


if __name__ == "__main__":
    main()
