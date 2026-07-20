#!/usr/bin/env python
"""
คำถาม: เล่นหุ้นรายตัว (สูตร E4+ExitF ของเราเอง ที่เคยชนะ SPY แบบก้อนเดียว) มีโอกาสชนะ RMF+คืนภาษี
"หลังภาษีจริง" ไหม? -- ใช้ทุนก้อนเดียว 1,000,000 บาท 10 ปี เหมือนการทดลองก่อนหน้า เพื่อเทียบกันตรงๆ

กำไรจากหุ้นสหรัฐฯ ที่เทรดเอง ก็โดนกฎการโอนเงินกลับไทยแบบเดียวกับซื้อ SPY ตรงๆ (ป.161/2566) -- ถ้าไม่โอน
เงินกลับไทยเลยระหว่างทาง (reinvest ในบัญชีต่างประเทศ) แล้วโอนกลับทีเดียวปีที่ 10 เหมือนสถานการณ์ D เดิม
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_beat_spy_v2 import sim_e4_trendexit
from universe import US_STOCKS
from test_aftertax_lumpsum_compare import thai_pit, ASSUMED_OTHER_INCOME_THB

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000
THB_PER_USD = teo.THB_PER_USD

# ผลลัพธ์ 5 ช่องทางจากรอบก่อน (หลังภาษีจริงแล้ว) เอามาเทียบตรงๆ
PRIOR_RESULTS = {
    "A) RMF (500k ลดหย่อนได้จริง) + ส่วนเกินกองทั่วไป": 320.8,
    "B) กองทุนทั่วไป K-USA-A style": 249.9,
    "C) DR (SP50001)": 279.4,
    "D) ซื้อ SPY ตรงๆ (หลังภาษีก้าวหน้า)": 222.4,
    "E) หุ้นไทย (THD proxy)": 33.6,
}


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))

    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท ({CAPITAL_THB/THB_PER_USD:,.0f} USD)\n")

    rows = []
    for slots in [5, 10, 20]:
        m = sim_e4_trendexit(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        rows.append((slots, m))

    print("=" * 100)
    for slots, m in rows:
        print(f"E4+ExitF ({slots} ไม้): ก่อนภาษี {m['ret_pct']:+.1f}%  ไม้ {m['trades']}  WR {m['wr']:.1f}%")
    print()

    # เอาผลลัพธ์แต่ละ config มาคิดภาษีหลังโอนเงินกลับปีที่ 10
    print("=" * 100)
    print("หลังภาษีจริง (โอนกำไรกลับไทยทีเดียวปีที่ 10 ตาม ป.161/2566 ซ้อนทับรายได้อื่นสมมติ "
          f"{ASSUMED_OTHER_INCOME_THB:,} บาท/ปี):")
    print("=" * 100)
    best_row = None
    for slots, m in rows:
        ret_pct = m["ret_pct"]
        pretax_final_thb = CAPITAL_THB * (1 + ret_pct / 100)
        gain = pretax_final_thb - CAPITAL_THB
        tax_on_gain = thai_pit(ASSUMED_OTHER_INCOME_THB + gain) - thai_pit(ASSUMED_OTHER_INCOME_THB)
        aftertax_final = pretax_final_thb - tax_on_gain
        aftertax_ret_pct = (aftertax_final / CAPITAL_THB - 1) * 100
        avg_tax_rate = tax_on_gain / gain * 100 if gain > 0 else 0
        print(f"E4+ExitF ({slots:2d} ไม้): ก่อนภาษี {ret_pct:+7.1f}%  ->  หลังภาษี {aftertax_ret_pct:+7.1f}%  "
              f"(กำไร {gain:,.0f} บาท ถูกภาษี {tax_on_gain:,.0f} บาท เฉลี่ย {avg_tax_rate:.1f}%)  "
              f"ไม้ {m['trades']:4d} · WR {m['wr']:.1f}%")
        if best_row is None or aftertax_ret_pct > best_row[1]:
            best_row = (slots, aftertax_ret_pct)

    print("\n" + "=" * 100)
    print("เทียบกับ 5 ช่องทางจากรอบก่อน (หลังภาษีจริงแล้วทั้งหมด):")
    print("=" * 100)
    all_compare = dict(PRIOR_RESULTS)
    all_compare[f"F) E4+ExitF เทรดเอง ({best_row[0]} ไม้ ดีสุด)"] = best_row[1]
    for label, ret in sorted(all_compare.items(), key=lambda x: -x[1]):
        marker = " <-- เล่นรายตัว" if "E4+ExitF" in label else ""
        print(f"{label:55s} {ret:+7.1f}%{marker}")


if __name__ == "__main__":
    main()
