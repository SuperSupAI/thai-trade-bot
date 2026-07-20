#!/usr/bin/env python
"""
ทดสอบไอเดียใหม่ที่ต่างจาก 4 อันก่อนหน้า (ซึ่งล้วน "เพิ่มความซับซ้อน" แล้วแพ้): "target_slots" เดิมเป็นแค่
ตัวกำหนดงบต่อไม้ (ทุน/slots) ไม่ใช่เพดานจำนวนไม้จริง -- ทุนใหญ่ขึ้นเลยถือพร้อมกันได้หลายไม้ขึ้นมาก
(เจือจางออกจากการเดิมพันกระจุกตัว) ลองบังคับ "เพดานจำนวนไม้พร้อมกันจริงๆ" (hard cap) แทน ไม่ว่าทุนจะใหญ่แค่ไหน
ก็ห้ามถือเกิน N ไม้พร้อมกัน -- ทดสอบว่าการบังคับกระจุกตัวจริงๆ (ไม่ใช่แค่งบเจือจาง) ช่วยที่ทุน 1M บาทไหม
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_beat_spy_v2 import sim_e4_trendexit
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.20


def sim_hardcap(prep, syms_order, test_dates, max_positions, capital_thb=CAPITAL_THB):
    """เพดานจำนวนไม้พร้อมกันจริงๆ (ปฏิเสธสัญญาณใหม่ถ้าเต็มแล้ว) งบต่อไม้ = เงินสดคงเหลือ/(ที่ว่างเหลือ)"""
    capital_usd = capital_thb / THB_PER_USD
    cash = capital_usd
    positions = {}
    trades_count, wins = 0, 0

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            ema200 = float(P["emas"][200].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            if chg <= -HARD_SL or price < ema200:
                cash += pos["qty"] * price * (1 - FEE)
                trades_count += 1
                if chg > 0:
                    wins += 1
                del positions[sym]

        for sym in syms_order:
            if len(positions) >= max_positions or cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E4_Simple200"].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            slots_left = max_positions - len(positions)
            budget = min(cash / slots_left, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=qty, entry_price=price)

    val = cash
    for sym, pos in positions.items():
        val += pos["qty"] * float(prep[sym]["close"].iloc[-1])
    ret_pct = (val / capital_usd - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท\n")

    print("=== เทียบวิธีเดิม (budget-sizing, uncapped จำนวนไม้จริง) ===")
    rows = []
    for slots in [5, 10, 20]:
        m = sim_e4_trendexit(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        print(f"  target_slots={slots:2d} (งบ), ไม้จริงไม่จำกัด: {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:4d}  WR {m['wr']:5.1f}%")
        rows.append(dict(mode="budget_only", param=slots, **m))

    print("\n=== เทียบวิธีใหม่ (hard cap จำนวนไม้พร้อมกันจริงๆ) ===")
    for cap in [3, 5, 8, 10, 15]:
        m = sim_hardcap(prep, syms_order, all_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        print(f"  hard cap={cap:2d} ไม้ (บังคับจริง):        {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:4d}  WR {m['wr']:5.1f}%")
        rows.append(dict(mode="hard_cap", param=cap, **m))

    pd.DataFrame(rows).to_csv("hardcap_positions_results.csv", index=False)
    print("\nบันทึกไว้ที่ hardcap_positions_results.csv")


if __name__ == "__main__":
    main()
