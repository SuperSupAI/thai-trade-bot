#!/usr/bin/env python
"""
เทส cross-sectional momentum (12mo formation, skip 1mo, rebalance รายเดือน) แยกทีละประเทศ
ในสกุลเงินท้องถิ่น (ไม่แปลงเป็น USD/THB เพราะ momentum score เป็น ratio ไม่ขึ้นกับสกุลเงิน)
เทียบว่า "สูตรเดียวกัน" ที่ได้ผลกับหุ้นไทย/สหรัฐฯ ใช้ได้ผลกับตลาดอื่นด้วยไหม
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")

FORMATION, SKIP, REBAL = 252, 21, 21
TOP_N_LIST = [3, 5]

BASKETS = {
    "ญี่ปุ่น (14 ตัว)": "japan_dr_10y_cache.pkl",
    "ฮ่องกง/จีน (16 ตัว)": "hk_china_dr_10y_cache.pkl",
    "สิงคโปร์ (8 ตัว)": "singapore_dr_10y_cache.pkl",
}


def sim(price_lookup, syms_order, test_dates, top_n, fee=0.002):
    cash = 1.0  # ทำงานเป็นสัดส่วนของทุนตั้งต้น (ไม่ต้องแปลงสกุลเงิน)
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
    ret_pct = (val - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def main():
    rows = []
    for label, cache_file in BASKETS.items():
        with open(cache_file, "rb") as f:
            price_lookup = pickle.load(f)
        syms_order = list(price_lookup.keys())
        print(f"\n{'='*100}\n{label}\n{'='*100}")

        all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
        n = len(all_dates)
        train_dates = all_dates[: int(n * 0.6)]
        valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
        test_dates_ = all_dates[int(n * 0.8):]
        dates_2022 = [d for d in all_dates if d.year == 2022]

        for top_n in TOP_N_LIST:
            results = {}
            for period, dates in [("ALL", all_dates), ("TRAIN", train_dates), ("VALID", valid_dates),
                                   ("TEST", test_dates_), ("2022", dates_2022)]:
                m = sim(price_lookup, syms_order, dates, top_n)
                results[period] = m
                rows.append(dict(market=label, top_n=top_n, period=period, **m))
            print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+8.1f}%(n={results['ALL']['trades']:3d})  "
                  f"TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  VALID:{results['VALID']['ret_pct']:+8.1f}%  "
                  f"TEST:{results['TEST']['ret_pct']:+8.1f}%  2022:{results['2022']['ret_pct']:+8.1f}%  "
                  f"WR:{results['ALL']['wr']:.0f}%")

    pd.DataFrame(rows).to_csv("momentum_per_country_results.csv", index=False)
    print("\nบันทึกไว้ที่ momentum_per_country_results.csv")


if __name__ == "__main__":
    main()
