#!/usr/bin/env python
"""
เดเทรด: cross-sectional intraday momentum breakout บนหุ้นไทย 75 ตัว
ทุกวันเทรด จัดอันดับหุ้นตาม "โมเมนตัมช่วงเช้า" (return จากราคาเปิด ถึงจุดตัดสินใจ) แล้วซื้อ top-N
ที่ราคา ณ จุดตัดสินใจ ถือจนปิดตลาด ขายหมด (ไม่ถือข้ามคืน = เดเทรดจริง) วนทุกวัน

SET เทรด 10:00-12:00 (เช้า) + 14:00-16:00 (บ่าย) = 6 แท่งชั่วโมง/วัน (10,11,12,14,15,16)
เทสสองแบบ decision point: "1ชม" (สัญญาณจากแท่ง 10:00 อย่างเดียว, เข้าราคาปิดแท่ง 10:00)
กับ "2ชม" (สัญญาณจากแท่ง 10:00+11:00, เข้าราคาปิดแท่ง 11:00)
"""
import pickle, sys
import pandas as pd
import statistics
sys.path.insert(0, ".")

CAPITAL_THB = 1_000_000
FEE = 0.002


def build_daily_frames(data):
    """แปลง {ticker: hourly OHLC df} -> {ticker: {date: hourly df ของวันนั้น}}"""
    out = {}
    for t, df in data.items():
        df = df.copy()
        df["date"] = df.index.date
        out[t] = {d: g for d, g in df.groupby("date")}
    return out


def run_daytrade(daily, all_days, top_n, signal_bars, entry_bar_idx, capital_thb=CAPITAL_THB, fee=FEE):
    """signal_bars: กี่แท่งแรกใช้คำนวณสัญญาณ (1 หรือ 2), entry_bar_idx: index ของแท่งที่เข้าซื้อ (0-based)"""
    equity = capital_thb
    trades, wins = 0, 0
    daily_rets = []
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
        scores.sort(key=lambda x: x[1], reverse=True)
        picks = scores[:top_n]
        if not picks:
            daily_rets.append(0.0)
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
        daily_rets.append(day_pnl / capital_thb)
    ret_pct = (equity / capital_thb - 1) * 100
    wr = (wins / trades * 100) if trades else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades, wr=round(wr, 1), daily_rets=daily_rets)


def main():
    with open("thai_hourly_ohlc_2y_cache.pkl", "rb") as f:
        data = pickle.load(f)
    daily = build_daily_frames(data)

    all_days = sorted(set().union(*[set(d.keys()) for d in daily.values()]))
    n = len(all_days)
    print(f"{len(daily)} ตัว, {n} วันเทรด ({all_days[0]} ถึง {all_days[-1]})")

    train_days = all_days[: int(n * 0.6)]
    valid_days = all_days[int(n * 0.6): int(n * 0.8)]
    test_days = all_days[int(n * 0.8):]

    for label, signal_bars, entry_idx in [("เข้าหลัง 1ชม (แท่ง10:00)", 1, 0),
                                            ("เข้าหลัง 2ชม (แท่ง10:00+11:00)", 2, 1)]:
        print(f"\n{'='*90}\n{label}\n{'='*90}")
        for top_n in [3, 5]:
            results = {}
            for period, days in [("ALL", all_days), ("TRAIN", train_days), ("VALID", valid_days),
                                   ("TEST", test_days)]:
                m = run_daytrade(daily, days, top_n, signal_bars, entry_idx)
                results[period] = m
            print(f"top_n={top_n}  ALL:{results['ALL']['ret_pct']:+9.1f}%(n={results['ALL']['trades']:5d}, "
                  f"wr={results['ALL']['wr']:.0f}%)  TRAIN:{results['TRAIN']['ret_pct']:+8.1f}%  "
                  f"VALID:{results['VALID']['ret_pct']:+8.1f}%  TEST:{results['TEST']['ret_pct']:+8.1f}%")

    with open("thai_daytrade_daily.pkl", "wb") as f:
        pickle.dump({"daily": daily, "all_days": all_days}, f)


if __name__ == "__main__":
    main()
