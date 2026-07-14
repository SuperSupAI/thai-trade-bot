#!/usr/bin/env python
"""เทียบ E4+Exit F (5 ไม้) กับ SPY เฉพาะ "ปีนี้" — ทั้งแบบปีปฏิทิน 2026 (YTD) และแบบย้อนหลัง 1 ปีล่าสุด"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_beat_spy_v2 import sim_e4_trendexit
from universe import US_STOCKS, US_MARKET_INDEX

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
CAPITAL_THB = 100_000
THB_PER_USD = teo.THB_PER_USD


def spy_ret(spy, dates):
    seg = spy.reindex(dates).ffill().dropna()
    if len(seg) < 2:
        return float("nan")
    return round((seg.iloc[-1] / seg.iloc[0] - 1) * 100, 1)


def report(label, prep, syms_order, dates, spy):
    if len(dates) < 5:
        print(f"{label}: ข้อมูลสั้นไป ข้าม")
        return
    m = sim_e4_trendexit(prep, syms_order, dates, target_slots=5, capital_thb=CAPITAL_THB)
    s_ret = spy_ret(spy, dates)
    print(f"\n{'='*70}\n{label}: {dates[0].date()} → {dates[-1].date()} ({len(dates)} วัน)\n{'='*70}")
    print(f"SPY B&H:          {s_ret:+7.1f}%")
    print(f"E4+ExitF 5 ไม้:    {m['ret_pct']:+7.1f}%  ·  ไม้ {m['trades']:4d}  ·  win rate {m['wr']:5.1f}%")
    diff = m['ret_pct'] - s_ret
    print(f"ส่วนต่าง: {diff:+.1f} percentage points {'(กลยุทธ์ชนะ)' if diff > 0 else '(SPY ชนะ)'}")


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    with open(SPY_CACHE_FILE, "rb") as f:
        spy = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))

    # ปีปฏิทิน 2026 (YTD)
    dates_2026 = [d for d in all_dates if d.year == 2026]
    report("ปีนี้ (2026 YTD, ม.ค.-ก.ค.)", prep, syms_order, dates_2026, spy)

    # ย้อนหลัง 1 ปีล่าสุด (rolling)
    dates_trailing = all_dates[-252:]
    report("ย้อนหลัง 1 ปีล่าสุด (rolling 252 วัน)", prep, syms_order, dates_trailing, spy)


if __name__ == "__main__":
    main()
