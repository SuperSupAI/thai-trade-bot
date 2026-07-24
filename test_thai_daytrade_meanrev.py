#!/usr/bin/env python
"""
เดเทรดแบบ mean-reversion: ซื้อหุ้นที่ "แพ้มากสุด" ช่วงเช้า (แทนที่จะไล่ซื้อตัวที่ชนะ)
ใช้ infra เดียวกับ test_thai_daytrade_orb.py แค่กลับทิศทางเลือก (bottom-N แทน top-N)
"""
import pickle, sys
sys.path.insert(0, ".")
from test_thai_daytrade_orb import build_daily_frames, CAPITAL_THB, FEE


def run_daytrade_reversal(daily, all_days, top_n, signal_bars, entry_bar_idx, capital_thb=CAPITAL_THB, fee=FEE):
    equity = capital_thb
    trades, wins = 0, 0
    for day in all_days:
        scores = []
        for t, days_map in daily.items():
            g = days_map.get(day)
            if g is None or len(g) <= entry_bar_idx:
                continue
            day_open = float(g["Open"].iloc[0])
            sig_close = float(g["Close"].iloc[signal_bars - 1])
            if day_open <= 0:
                continue
            scores.append((t, sig_close / day_open - 1, g))
        scores.sort(key=lambda x: x[1])  # จากน้อยไปมาก -- เอา "แพ้มากสุด" ก่อน
        picks = scores[:top_n]
        if not picks:
            continue
        budget_each = equity / len(picks)
        day_pnl = 0.0
        for t, sig_ret, g in picks:
            entry_px = float(g["Close"].iloc[entry_bar_idx])
            exit_px = float(g["Close"].iloc[-1])
            if entry_px <= 0:
                continue
            qty = (budget_each * (1 - fee)) / entry_px
            proceeds = qty * exit_px * (1 - fee)
            cost = qty * entry_px * (1 + fee)
            day_pnl += proceeds - cost
            trades += 1
            if exit_px > entry_px:
                wins += 1
        equity += day_pnl
    ret_pct = (equity / capital_thb - 1) * 100
    wr = (wins / trades * 100) if trades else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades, wr=round(wr, 1))


def main():
    with open("thai_hourly_ohlc_2y_cache.pkl", "rb") as f:
        data = pickle.load(f)
    daily = build_daily_frames(data)
    all_days = sorted(set().union(*[set(d.keys()) for d in daily.values()]))
    n = len(all_days)
    train_days = all_days[: int(n * 0.6)]
    valid_days = all_days[int(n * 0.6): int(n * 0.8)]
    test_days = all_days[int(n * 0.8):]

    for label, signal_bars, entry_idx in [("เข้าหลัง 1ชม", 1, 0), ("เข้าหลัง 2ชม", 2, 1)]:
        print(f"\n{'='*90}\nMean-reversion: ซื้อตัว 'แพ้มากสุด' ช่วงเช้า -- {label}\n{'='*90}")
        for top_n in [3, 5]:
            results = {}
            for period, days in [("ALL", all_days), ("TRAIN", train_days), ("VALID", valid_days),
                                   ("TEST", test_days)]:
                m = run_daytrade_reversal(daily, days, top_n, signal_bars, entry_idx)
                results[period] = m
            print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+9.1f}%(n={results['ALL']['trades']:5d}, "
                  f"wr={results['ALL']['wr']:.0f}%)  TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  "
                  f"VALID:{results['VALID']['ret_pct']:+8.1f}%  TEST:{results['TEST']['ret_pct']:+8.1f}%")


if __name__ == "__main__":
    main()
