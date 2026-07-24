#!/usr/bin/env python
"""
เทส cross-sectional momentum หุ้นไทย 75 ตัว แบบรีบาลานซ์ถี่ขึ้น -- รายสัปดาห์ (REBAL=5 วันเทรด)
เทียบกับ baseline รายเดือนเดิม (REBAL=21) และรายสองสัปดาห์ (REBAL=10) ใช้ formation=126 ที่พิสูจน์แล้วว่า
ดีสุดสำหรับหุ้นไทย (ต่างจาก DR ที่ formation=252) -- เช็คค่าธรรมเนียมกินทุนไปพร้อมกันด้วย
"""
import pickle, sys
sys.path.insert(0, ".")

FORMATION, SKIP, TOP_N = 126, 21, 3
CAPITAL_THB = 1_000_000
FEE = 0.002


def sim(prep_close, syms_order, test_dates, top_n, rebal, capital_thb=CAPITAL_THB, fee=FEE):
    cash = capital_thb
    positions = {}
    trades_count, wins = 0, 0
    entry_px = {}
    rebal_dates = test_dates[::rebal]

    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            close = prep_close[sym]
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
                close = prep_close[sym]
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
                close = prep_close[sym]
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
        close = prep_close[sym]
        px = float(close.loc[last_dt]) if last_dt in close.index else float(close.iloc[-1])
        val += qty * px
    ret_pct = (val / capital_thb - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def main():
    with open("thai_stocks_10y_cache.pkl", "rb") as f:
        data = pickle.load(f)
    syms_order = list(data.keys())
    all_dates = sorted(set().union(*[data[s].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]
    dates_2022 = [d for d in all_dates if d.year == 2022]
    print(f"{len(syms_order)} ตัว, {n} วันเทรด ({all_dates[0].date()} ถึง {all_dates[-1].date()})")

    for rebal_label, rebal in [("รายเดือน (เดิม, REBAL=21)", 21), ("ราย 2 สัปดาห์ (REBAL=10)", 10),
                                ("รายสัปดาห์ (REBAL=5)", 5)]:
        n_rebal = len(all_dates[::rebal])
        fee_floor = ((1 - FEE) ** 2) ** n_rebal * 100
        print(f"\n{'='*90}\n{rebal_label} -- จำนวนรอบรีบาลานซ์ตลอด {n} วัน = {n_rebal} รอบ "
              f"(พื้นค่าธรรมเนียมถ้าไม่มี edge = เหลือ {fee_floor:.1f}% ของทุน)\n{'='*90}")
        for top_n in [3, 5]:
            results = {}
            for period, dates in [("ALL", all_dates), ("TRAIN", train_dates), ("VALID", valid_dates),
                                   ("TEST", test_dates_), ("2022", dates_2022)]:
                m = sim(data, syms_order, dates, top_n, rebal)
                results[period] = m
            print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+9.1f}%(n={results['ALL']['trades']:4d}, "
                  f"wr={results['ALL']['wr']:.0f}%)  TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  "
                  f"VALID:{results['VALID']['ret_pct']:+8.1f}%  TEST:{results['TEST']['ret_pct']:+8.1f}%  "
                  f"2022:{results['2022']['ret_pct']:+8.1f}%")


if __name__ == "__main__":
    main()
