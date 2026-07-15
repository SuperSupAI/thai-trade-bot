#!/usr/bin/env python
"""
คำถาม: ถ้าเอา 10,000 บาทใส่บอทจริงช่วงครึ่งปีหลัง 2026 ควรรันสูตรไหน?
ครึ่งปีหลัง 2026 ยังไม่เกิดขึ้นจริง (future) — ใช้ 6 เดือนล่าสุดที่มีข้อมูลจริงเป็น proxy แทน

ทุน 10,000 บาท (~$282) เล็กกว่าที่เคยทดสอบเยอะ (เดิมทดสอบที่ 100,000 บาท 5-10 ไม้)
จากผลทดสอบ capital sensitivity ก่อนหน้า: ทุนเล็กต้อง "ไม้น้อยลง" ไม่ใช่ "ไม้เท่าเดิมแต่งบเล็กลง"
ถึงจะซื้อหุ้นได้จริง — ทดสอบ 1/2/3 ไม้ เทียบ 3 สูตรผู้ท้าชิง:
  S1) webull_bot ปัจจุบัน: E3 TrendMACD entry + TP12%/SL15% (ปลอดภัยสุด, ผ่าน bear-market test แล้ว)
  S2) E4 entry (Close>EMA200) + TP12%/SL15% (จากรอบ 2 — win rate สูงกว่า, ยังมีเพดานกำไร)
  S3) E4 entry + Exit F (ไม่มีเพดานกำไร, hard SL -20%) — ตัวที่ชนะ SPY 10 ปี แต่ win rate ต่ำมาก
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals, sim_entry
from test_beat_spy_v2 import sim_e4_trendexit
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
SPY_CACHE_FILE = "spy_10y_cache.pkl"
CAPITAL_THB = 10_000
THB_PER_USD = teo.THB_PER_USD


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    with open(SPY_CACHE_FILE, "rb") as f:
        spy = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()
    xcfg = exits["TP12/SL15"]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    dates_6m = all_dates[-126:]  # ~6 เดือนเทรดล่าสุด (proxy สำหรับครึ่งปีหลัง 2026)
    print(f"ช่วงทดสอบ (proxy 6 เดือนล่าสุด): {dates_6m[0].date()} → {dates_6m[-1].date()} ({len(dates_6m)} วัน)")
    print(f"ทุน {CAPITAL_THB:,} บาท (~${CAPITAL_THB/THB_PER_USD:,.0f})\n")

    spy_seg = spy.reindex(dates_6m).ffill().dropna()
    spy_ret = (spy_seg.iloc[-1] / spy_seg.iloc[0] - 1) * 100
    print(f"SPY B&H ช่วงเดียวกัน: {spy_ret:+.1f}%\n")

    rows = []
    for slots in [1, 2, 3]:
        m1 = sim_entry(prep, syms_order, dates_6m, "E3 TrendMACD", xcfg, rank_by_momentum=False,
                       capital_thb=CAPITAL_THB, target_slots=slots)
        m2 = sim_entry(prep, syms_order, dates_6m, "E4_Simple200", xcfg, rank_by_momentum=False,
                       capital_thb=CAPITAL_THB, target_slots=slots)
        m3 = sim_e4_trendexit(prep, syms_order, dates_6m, target_slots=slots, capital_thb=CAPITAL_THB)

        for label, m in [("S1 webull_bot ปัจจุบัน (E3+TP12/SL15)", m1),
                         ("S2 E4+TP12/SL15", m2),
                         ("S3 E4+ExitF (ไม่มีเพดานกำไร)", m3)]:
            rows.append(dict(สูตร=label, ไม้เป้าหมาย=slots, ret_pct=m["ret_pct"], trades=m["trades"], wr=m["wr"]))
            print(f"{label:38s} {slots} ไม้ → {m['ret_pct']:+6.1f}%  ·  ไม้ {m['trades']:3d}  ·  win rate {m['wr']:5.1f}%")

    df = pd.DataFrame(rows)
    df.to_csv("10k_h2_2026_results.csv", index=False)
    print("\n" + "=" * 70)
    print("เรียงจากดีสุด → แย่สุด")
    print("=" * 70)
    print(df.sort_values("ret_pct", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
