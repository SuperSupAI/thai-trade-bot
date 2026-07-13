#!/usr/bin/env python
"""
ทดสอบเงื่อนไข "ออก" แบบแบ่งไม้ (scale out) + ขยับ stop loss หลายแบบ เทียบกับ baseline
(TP12%/SL15% ขายหมดทีเดียว) — เป้าหมาย: ลดปัญหา TP ตายตัวจำกัดกำไรตอนหุ้นวิ่งแรงต่อเนื่อง
(ที่ทำให้แพ้ SPY ในรอบ 10 ปี) โดยยังคุมความเสี่ยงด้วย SL/trailing เหมือนเดิม

Entry: E3 TrendMACD (เหมือนเดิม) · Position sizing: ไม่จำกัดไม้ ใช้เงินทอนซื้อต่อ (target 10 ไม้)
ทดสอบบนหน้าต่าง 1 ปีล่าสุดก่อน (เร็ว, ใช้ cache 4y เดิม) — ถ้าตัวไหนดูดีค่อยเอาไปเทส 10 ปีต่อ

เงื่อนไขที่ทดสอบ:
  A) Baseline: TP12%/SL15% ขายหมดทีเดียว (ของเดิม)
  B) 50/50 + Trail 8%: ขาย 50% ที่ +10% แล้ว trail ที่เหลือด้วย -8% จาก peak (ไม่มี TP2 ตายตัว)
  C) 50/50 + Breakeven stop + ratchet: ขาย 50% ที่ +10% แล้วขยับ stop ไปที่ breakeven
     (และขยับตามทุก +10% ที่ทำได้เพิ่ม ล็อกกำไรไว้เรื่อยๆ)
  D) 1/3-1/3-1/3: ขาย 33% ที่ +8%, ขาย 33% ที่ +15%, ที่เหลือ trail -10% จาก peak
  E) Pure trail (ไม่มี TP ตายตัว): SL เริ่มต้น -15% แล้ว trail -10% จาก peak ทันทีที่กำไร
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from universe import US_STOCKS

CAPITAL_THB = 100_000
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.15


def sim_variant(prep, syms_order, test_dates, variant, capital_thb=CAPITAL_THB, target_slots=TARGET_SLOTS):
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / target_slots
    cash = capital_usd
    positions = {}   # sym -> dict(qty, entry_price, peak, stage, stop)
    closed_trades = []  # แต่ละรายการ = pnl% ของ "ก้อนที่ขาย" ครั้งนั้น (ไม่ใช่ทั้งไม้)
    full_exits = 0
    wins_full = 0

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            pos["peak"] = max(pos.get("peak", price), price)

            sell_frac, reason, exit_all = 0.0, None, False

            if variant == "A_baseline":
                if chg <= -0.15:
                    sell_frac, reason, exit_all = 1.0, "SL-15%", True
                elif chg >= 0.12:
                    sell_frac, reason, exit_all = 1.0, "TP+12%", True

            elif variant == "B_5050_trail8":
                if pos["stage"] == 0:
                    if chg <= -HARD_SL:
                        sell_frac, reason, exit_all = 1.0, "SL-15%", True
                    elif chg >= 0.10:
                        sell_frac, reason = 0.5, "ขาย50%@+10%"
                        pos["stage"] = 1
                else:
                    if price <= pos["peak"] * (1 - 0.08):
                        sell_frac, reason, exit_all = 1.0, "Trail-8%จาก peak", True

            elif variant == "C_5050_breakeven_ratchet":
                if pos["stage"] == 0:
                    if chg <= -HARD_SL:
                        sell_frac, reason, exit_all = 1.0, "SL-15%", True
                    elif chg >= 0.10:
                        sell_frac, reason = 0.5, "ขาย50%@+10%"
                        pos["stage"] = 1
                        pos["stop"] = pos["entry_price"]  # ขยับ stop ไป breakeven
                else:
                    # ratchet: ทุกๆ +10% ที่ทำได้เพิ่มจาก peak ให้ขยับ stop ตาม (ล็อกกำไรเพิ่ม)
                    locked_pct = ((pos["peak"] / pos["entry_price"] - 1) // 0.10) * 0.10 - 0.10
                    new_stop = pos["entry_price"] * (1 + max(0, locked_pct))
                    pos["stop"] = max(pos["stop"], new_stop)
                    if price <= pos["stop"]:
                        sell_frac, reason, exit_all = 1.0, f"Stop@{(pos['stop']/pos['entry_price']-1)*100:+.0f}%", True

            elif variant == "D_thirds":
                if pos["stage"] == 0:
                    if chg <= -HARD_SL:
                        sell_frac, reason, exit_all = 1.0, "SL-15%", True
                    elif chg >= 0.08:
                        sell_frac, reason = 1/3, "ขาย1/3@+8%"
                        pos["stage"] = 1
                elif pos["stage"] == 1:
                    if chg <= -HARD_SL:
                        sell_frac, reason, exit_all = 1.0, "SL-15%", True
                    elif chg >= 0.15:
                        sell_frac, reason = 0.5, "ขาย1/3ที่2@+15%"  # 0.5 ของที่เหลือ = 1/3 ของเดิม
                        pos["stage"] = 2
                else:
                    if price <= pos["peak"] * (1 - 0.10):
                        sell_frac, reason, exit_all = 1.0, "Trail-10%จาก peak", True

            elif variant == "E_pure_trail":
                if chg <= -HARD_SL:
                    sell_frac, reason, exit_all = 1.0, "SL-15%", True
                elif chg > 0 and price <= pos["peak"] * (1 - 0.10):
                    sell_frac, reason, exit_all = 1.0, "Trail-10%จาก peak", True

            if sell_frac > 0:
                qty_sold = pos["qty"] * sell_frac if not exit_all else pos["qty"]
                proceeds = qty_sold * price * (1 - FEE)
                cash += proceeds
                pnl_pct = price / pos["entry_price"] - 1
                closed_trades.append(pnl_pct)
                pos["qty"] -= qty_sold
                if exit_all or pos["qty"] < 1e-9:
                    full_exits += 1
                    if pnl_pct > 0:
                        wins_full += 1
                    del positions[sym]

        # เปิดไม้ใหม่ (ไม่จำกัดจำนวน ใช้เงินทอนซื้อต่อ)
        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E3 TrendMACD"].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=float(qty), entry_price=price, peak=price, stage=0, stop=0.0)

    val = cash
    for sym, pos in positions.items():
        series = prep[sym]["close"]
        px = float(series.iloc[-1])
        val += pos["qty"] * px

    ret_pct = (val / capital_usd - 1) * 100
    wr_full = (wins_full / full_exits * 100) if full_exits else float("nan")
    return dict(ret_pct=round(ret_pct, 1), full_exits=full_exits, wr_full_exit=round(wr_full, 1),
               partial_events=len(closed_trades))


def main():
    data = teo.load_data()
    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    test_dates = all_dates[-252:]
    bh = teo.buy_hold_return(prep, test_dates)
    print(f"หน้าต่างทดสอบ: {test_dates[0].date()} → {test_dates[-1].date()} · B&H เฉลี่ยหุ้น US {bh:+.1f}%")
    print(f"ทุน {CAPITAL_THB:,} บาท · entry E3 TrendMACD · ไม่จำกัดไม้ (target {TARGET_SLOTS})\n")

    variants = ["A_baseline", "B_5050_trail8", "C_5050_breakeven_ratchet", "D_thirds", "E_pure_trail"]
    labels = {
        "A_baseline": "A) Baseline: TP12%/SL15% ขายหมดทีเดียว",
        "B_5050_trail8": "B) 50% @+10% แล้ว trail ที่เหลือ -8% จาก peak",
        "C_5050_breakeven_ratchet": "C) 50% @+10% ขยับ stop ไป breakeven + ratchet ทุก+10%",
        "D_thirds": "D) 1/3 @+8%, 1/3 @+15%, เหลือ trail -10% จาก peak",
        "E_pure_trail": "E) ไม่มี TP ตายตัว: SL-15% + trail -10% จาก peak ทันทีที่กำไร",
    }

    rows = []
    for v in variants:
        m = sim_variant(prep, syms_order, test_dates, v)
        rows.append(dict(variant=labels[v], **m))
        print(f"{labels[v]:55s} → ผลตอบแทน {m['ret_pct']:+7.1f}%  ·  ไม้ที่ปิดหมด {m['full_exits']:4d}  ·  "
              f"win rate (ไม้ปิดหมด) {m['wr_full_exit']:5.1f}%  ·  เหตุการณ์ขาย (รวม partial) {m['partial_events']:4d}")

    df = pd.DataFrame(rows)
    df.to_csv("scaleout_variants_results.csv", index=False)
    print("\nบันทึกไว้ที่ scaleout_variants_results.csv")


if __name__ == "__main__":
    main()
