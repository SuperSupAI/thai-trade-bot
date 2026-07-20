#!/usr/bin/env python
"""
Cross-sectional momentum บน universe หุ้นไทยเต็ม 809 ตัว (จาก archive EOD) เทียบกับ 75 ตัวเดิม (SECTORS)
เต็ม 10 ปี + TRAIN/VALID/TEST + stress test 2022 + เช็คว่ามี "DELTA ตัวใหม่" ที่ universe เดิมไม่เคยจับไหม
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from test_thai_cross_sectional_momentum import sim_cross_sectional_momentum_thb, FORMATION, SKIP, REBAL

CAPITAL_THB = 1_000_000


def run_full_backtest(data, syms_order, label):
    all_dates = sorted(set().union(*[data[s].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"\n{'='*100}")
    print(f"{label}  ({len(syms_order)} หุ้น, {all_dates[0].date()} -> {all_dates[-1].date()})")
    print(f"{'='*100}")
    rows = []
    for top_n in [3, 5, 10]:
        m_all = sim_cross_sectional_momentum_thb(data, syms_order, all_dates, top_n, capital_thb=CAPITAL_THB)
        m_train = sim_cross_sectional_momentum_thb(data, syms_order, train_dates, top_n, capital_thb=CAPITAL_THB)
        m_valid = sim_cross_sectional_momentum_thb(data, syms_order, valid_dates, top_n, capital_thb=CAPITAL_THB)
        m_test = sim_cross_sectional_momentum_thb(data, syms_order, test_dates_, top_n, capital_thb=CAPITAL_THB)

        def fmt(m):
            return f"{m['ret_pct']:+8.1f}%(WR{m['wr']:5.1f}%,n={m['trades']})"

        print(f"top_n={top_n:2d}  ALL:{fmt(m_all)}  TRAIN:{fmt(m_train)}  VALID:{fmt(m_valid)}  TEST:{fmt(m_test)}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(universe=label, top_n=top_n, period=period, **m))

    # stress test 2022
    dates_2022 = [d for d in all_dates if d.year == 2022]
    print(f"\n2022 เต็มปี (stress test):")
    for top_n in [3, 5, 10]:
        m = sim_cross_sectional_momentum_thb(data, syms_order, dates_2022, top_n, capital_thb=CAPITAL_THB)
        print(f"  top_n={top_n:2d}: {m['ret_pct']:+7.1f}%  WR {m['wr']:5.1f}%")
        rows.append(dict(universe=label, top_n=top_n, period="2022_stress", **m))

    return rows


def main():
    with open("thai_all_stocks_archive_10y_cache.pkl", "rb") as f:
        full_data = pickle.load(f)
    with open("thai_stocks_10y_cache.pkl", "rb") as f:
        old_data = pickle.load(f)
        old_data = {k.replace(".BK", ""): v for k, v in old_data.items()}

    full_syms = sorted(full_data.keys())
    old_syms = sorted(old_data.keys())

    all_rows = []
    all_rows += run_full_backtest(old_data, old_syms, "เดิม 75 ตัว (SECTORS)")
    all_rows += run_full_backtest(full_data, full_syms, "ใหม่ 809 ตัว (archive เต็มตลาด)")

    # เช็คว่าหุ้นตัวไหนติด top 5 บ่อยสุดใน universe ใหม่ ที่ไม่ได้อยู่ใน 75 ตัวเดิม
    print(f"\n{'='*100}")
    print("เช็คหุ้น 'ตัวใหม่' (ไม่อยู่ใน 75 ตัวเดิม) ที่ติด top 5 บ่อยที่สุดตลอด 10 ปี (universe 809 ตัว)")
    print(f"{'='*100}")
    all_dates = sorted(set().union(*[full_data[s].index for s in full_syms]))
    rebal_dates = all_dates[::REBAL]
    hit_count = {}
    hit_scores = {}
    for dt in rebal_dates:
        scores = []
        for sym in full_syms:
            close = full_data[sym]
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
        for sym, sc in scores[:5]:
            if sym not in old_syms:
                hit_count[sym] = hit_count.get(sym, 0) + 1
                hit_scores.setdefault(sym, []).append(sc)

    top_new = sorted(hit_count.items(), key=lambda x: -x[1])[:15]
    for sym, cnt in top_new:
        avg_score = sum(hit_scores[sym]) / len(hit_scores[sym]) * 100
        max_score = max(hit_scores[sym]) * 100
        print(f"  {sym:10s} ติด top5 {cnt:3d} ครั้ง  momentum เฉลี่ยตอนติด {avg_score:+7.1f}%  สูงสุด {max_score:+7.1f}%")

    pd.DataFrame(all_rows).to_csv("thai_momentum_full_universe_results.csv", index=False)
    print("\nบันทึกไว้ที่ thai_momentum_full_universe_results.csv")


if __name__ == "__main__":
    main()
