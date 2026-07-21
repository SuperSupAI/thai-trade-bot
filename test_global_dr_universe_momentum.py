#!/usr/bin/env python
"""
เทส cross-sectional momentum บน "Global DR universe" -- รวม DR ทุกประเทศที่ซื้อขายได้จริงบน SET
(สหรัฐฯ 47 + ญี่ปุ่น 14 + ฮ่องกง/จีน 16 + สิงคโปร์ 8 = 85 ตัว) เทียบกับสูตรเดิมที่ใช้แค่ DR สหรัฐฯ 47 ตัว
แปลงทุกสกุลเงินเป็น THB เทียบเท่า (อัตราคงที่ ณ ปัจจุบัน เหมือนที่ใช้ THB_PER_USD=35.5 มาตลอดทั้งโปรเจกต์)
เพื่อให้จัดสรรงบซื้อข้ามสกุลเงินได้ถูกต้อง (momentum score เป็น ratio ไม่ขึ้นกับสกุลเงินอยู่แล้ว
แต่การจัดสรรเงินสด/ถือพอร์ตรวมข้ามตลาดต้องแปลงเป็นหน่วยเดียวกันก่อน)
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_dr_universe_expanded_comparison import DR_COVERED_EXPANDED

FORMATION, SKIP, REBAL = 252, 21, 21
CAPITAL_THB = 1_000_000
FEE = 0.002
THB_PER_USD = teo.THB_PER_USD          # 35.5
THB_PER_JPY = 35.5 / 162.489
THB_PER_HKD = 35.5 / 7.8401
THB_PER_SGD = 35.5 / 1.29081


def load_converted(cache_file, thb_rate):
    with open(cache_file, "rb") as f:
        data = pickle.load(f)
    return {sym: series * thb_rate for sym, series in data.items()}


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
    with open("us_close_10y_cache.pkl", "rb") as f:
        us_data = pickle.load(f)
    prep = teo.precompute(us_data)
    prep = add_extra_signals(prep)
    us_syms = [s for s in DR_COVERED_EXPANDED if s in prep]
    us_price_lookup = {s: prep[s]["close"] * THB_PER_USD for s in us_syms}

    japan_lookup = load_converted("japan_dr_10y_cache.pkl", THB_PER_JPY)
    hk_lookup = load_converted("hk_china_dr_10y_cache.pkl", THB_PER_HKD)
    sg_lookup = load_converted("singapore_dr_10y_cache.pkl", THB_PER_SGD)

    global_lookup = {}
    global_lookup.update(us_price_lookup)
    global_lookup.update(japan_lookup)
    global_lookup.update(hk_lookup)
    global_lookup.update(sg_lookup)

    rows = []
    for label, syms_order in [("DR สหรัฐฯ เดิม (47 ตัว)", list(us_price_lookup.keys())),
                               ("DR ทั่วโลก (85 ตัว: US+ญี่ปุ่น+ฮ่องกง/จีน+สิงคโปร์)", list(global_lookup.keys()))]:
        price_lookup = global_lookup if "ทั่วโลก" in label else us_price_lookup
        print(f"\n{'='*100}\n{label}\n{'='*100}")

        all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
        n = len(all_dates)
        train_dates = all_dates[: int(n * 0.6)]
        valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
        test_dates_ = all_dates[int(n * 0.8):]
        dates_2022 = [d for d in all_dates if d.year == 2022]

        for top_n in [3, 5]:
            results = {}
            for period, dates in [("ALL", all_dates), ("TRAIN", train_dates), ("VALID", valid_dates),
                                   ("TEST", test_dates_), ("2022", dates_2022)]:
                m = sim(price_lookup, syms_order, dates, top_n)
                results[period] = m
                rows.append(dict(universe=label, top_n=top_n, period=period, **m))
            print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+8.1f}%(n={results['ALL']['trades']:3d})  "
                  f"TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  VALID:{results['VALID']['ret_pct']:+8.1f}%  "
                  f"TEST:{results['TEST']['ret_pct']:+8.1f}%  2022:{results['2022']['ret_pct']:+8.1f}%")

    pd.DataFrame(rows).to_csv("global_dr_universe_momentum_results.csv", index=False)
    print("\nบันทึกไว้ที่ global_dr_universe_momentum_results.csv")


if __name__ == "__main__":
    main()
