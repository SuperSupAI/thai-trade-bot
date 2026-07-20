#!/usr/bin/env python
"""
ทดสอบ cross-sectional momentum (เหมือนเวอร์ชั่นหุ้นสหรัฐฯ ทุกอย่าง) กับหุ้นไทย 75 ตัว (universe เดียวกับ
test_thai_stocks_e4_exitf.py ซึ่งรวม DELTA.BK) เป็นเงินบาทตรงๆ ไม่ต้องแปลง USD
"""
import pickle
import os
import sys
import pandas as pd

sys.path.insert(0, ".")
from universe import SECTORS

CACHE_FILE = "thai_stocks_10y_cache.pkl"
CAPITAL_THB = 1_000_000
FEE = 0.002
FORMATION = 252
SKIP = 21
REBAL = 21


def sim_cross_sectional_momentum_thb(prep_close, syms_order, test_dates, top_n, capital_thb=CAPITAL_THB):
    cash = capital_thb
    positions = {}
    entry_prices = {}
    trades_count, wins = 0, 0
    rebal_dates = test_dates[::REBAL]

    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            close = prep_close[sym]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            if i < FORMATION:
                continue
            p_now_skip = close.iloc[i - SKIP]
            p_formation_start = close.iloc[i - FORMATION]
            if p_formation_start <= 0:
                continue
            scores.append((sym, p_now_skip / p_formation_start - 1))
        scores.sort(key=lambda x: x[1], reverse=True)
        target_syms = set(s for s, _ in scores[:top_n])

        for sym in list(positions):
            if sym not in target_syms:
                close = prep_close[sym]
                if dt in close.index:
                    price = float(close.loc[dt])
                    cash += positions[sym] * price * (1 - FEE)
                    trades_count += 1
                    if price > entry_prices[sym]:
                        wins += 1
                    del positions[sym]
                    del entry_prices[sym]

        new_syms = [s for s in target_syms if s not in positions]
        if new_syms:
            budget_each = cash / len(new_syms)
            for sym in new_syms:
                close = prep_close[sym]
                if dt not in close.index:
                    continue
                price = float(close.loc[dt])
                qty = int((budget_each * (1 - FEE)) / price)
                if qty < 1:
                    continue
                cash -= qty * price * (1 + FEE)
                positions[sym] = qty
                entry_prices[sym] = price

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
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    syms_order = sorted(data.keys())
    all_dates = sorted(set().union(*[c.index for c in data.values()]))
    n = len(all_dates)

    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"หุ้นไทยที่ใช้ได้: {len(syms_order)} ตัว")
    print(f"ทั้งชุด: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"TRAIN: {train_dates[0].date()} -> {train_dates[-1].date()}")
    print(f"VALID: {valid_dates[0].date()} -> {valid_dates[-1].date()}")
    print(f"TEST : {test_dates_[0].date()} -> {test_dates_[-1].date()}")
    print(f"ทุนก้อนเดียวรีเซ็ตใหม่ทุกช่วง {CAPITAL_THB:,} บาท\n")

    rows = []
    print("=" * 100)
    print(f"{'top_n':>6s}  {'ALL 10 ปี':>26s}  {'TRAIN':>26s}  {'VALID':>26s}  {'TEST':>26s}")
    print("=" * 100)
    for top_n in [5, 10, 20]:
        m_all = sim_cross_sectional_momentum_thb(data, syms_order, all_dates, top_n)
        m_train = sim_cross_sectional_momentum_thb(data, syms_order, train_dates, top_n)
        m_valid = sim_cross_sectional_momentum_thb(data, syms_order, valid_dates, top_n)
        m_test = sim_cross_sectional_momentum_thb(data, syms_order, test_dates_, top_n)

        def fmt(m):
            return f"{m['ret_pct']:+7.1f}% (n={m['trades']:3d},WR{m['wr']:5.1f}%)"

        print(f"{top_n:>6d}  {fmt(m_all):>26s}  {fmt(m_train):>26s}  {fmt(m_valid):>26s}  {fmt(m_test):>26s}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(top_n=top_n, period=period, **m))

    # ตรวจว่า DELTA.BK เคยติด top5 ไหม และเดือนไหนบ้าง
    print("\n=== เช็คว่า DELTA.BK เคยติด top 5 ไหม ===")
    rebal_dates = all_dates[::REBAL]
    delta_hits = []
    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            close = data[sym]
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
        top5 = [s for s, _ in scores[:5]]
        if "DELTA.BK" in top5:
            rank = top5.index("DELTA.BK") + 1
            score = dict(scores)["DELTA.BK"]
            delta_hits.append((dt, rank, score))
    print(f"DELTA.BK ติด top 5 ทั้งหมด {len(delta_hits)} ครั้ง จาก {len(rebal_dates)} รอบ rebalance")
    for dt, rank, score in delta_hits[:20]:
        print(f"  {dt.date()}  อันดับ {rank}  คะแนน momentum {score*100:+.0f}%")

    pd.DataFrame(rows).to_csv("thai_cross_sectional_momentum_results.csv", index=False)
    print("\nบันทึกไว้ที่ thai_cross_sectional_momentum_results.csv")


if __name__ == "__main__":
    main()
