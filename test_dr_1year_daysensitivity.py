#!/usr/bin/env python
"""
(1) Backtest cross-sectional momentum บน DR universe (21 หุ้น) ย้อนหลัง 1 ปีเต็ม
(2) เช็คว่า "วันที่เริ่ม/รีบาลานซ์" มีผลต่อผลตอบแทนแค่ไหน -- เลื่อนจุดเริ่ม rebalance cycle
    ทีละ 1 วันตลอด 21 วัน (ครบ 1 รอบเดือน) แล้วดูการกระจายตัวของผลตอบแทน 1 ปี
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum_dr_universe import DR_COVERED
from test_cross_sectional_momentum import FORMATION, SKIP, REBAL, sim_cross_sectional_momentum

CAPITAL_THB = 10_000
CACHE_FILE = "us_close_10y_cache.pkl"
DR_RATIO = 0.01  # ยืนยันแล้วจาก NVDA80/AAPL01/META01/GOOGL01/GSUS06/CSCO06/JNJ03 -- 1 หน่วย DR = 0.01 หุ้น


def sim_with_offset(prep, syms_order, test_dates, top_n, offset, capital_thb=CAPITAL_THB):
    """เหมือน sim_cross_sectional_momentum เดิม แต่เลื่อนจุดเริ่ม rebalance ไป offset วัน
    ใช้ราคาต่อหน่วย DR จริง (ราคาหุ้นเต็ม x 0.01) ไม่ใช่ราคาหุ้นเต็ม เพื่อให้ whole-unit rounding ถูกต้อง"""
    import test_cross_sectional_momentum as csm
    capital_usd = capital_thb / csm.THB_PER_USD
    cash = capital_usd
    positions = {}
    trades_count, wins = 0, 0
    rebal_dates = test_dates[offset::REBAL]

    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            P = prep[sym]
            close = P["close"]
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
                P = prep[sym]
                if dt in P["close"].index:
                    price_dr = float(P["close"].loc[dt]) * DR_RATIO
                    cash += positions[sym] * price_dr * (1 - csm.FEE)
                    trades_count += 1
                    del positions[sym]

        new_syms = [s for s in target_syms if s not in positions]
        if new_syms:
            budget_each = cash / len(new_syms)
            for sym in new_syms:
                P = prep[sym]
                if dt not in P["close"].index:
                    continue
                price_dr = float(P["close"].loc[dt]) * DR_RATIO
                qty = int((budget_each * (1 - csm.FEE)) / price_dr)
                if qty < 1:
                    continue
                cash -= qty * price_dr * (1 + csm.FEE)
                positions[sym] = qty

    last_dt = test_dates[-1]
    val = cash
    for sym, qty in positions.items():
        P = prep[sym]
        series = P["close"]
        px = float(series.loc[last_dt]) * DR_RATIO if last_dt in series.index else float(series.iloc[-1]) * DR_RATIO
        val += qty * px
    ret_pct = (val / capital_usd - 1) * 100
    return ret_pct, trades_count


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in DR_COVERED if s in prep]
    all_dates = sorted(set().union(*[prep[s]["close"].index for s in syms_order]))

    year_dates = all_dates[-252:]
    print(f"=== (1) Backtest 1 ปีเต็ม: {year_dates[0].date()} -> {year_dates[-1].date()} ===")
    print(f"ทุน {CAPITAL_THB:,} บาท (ใช้ราคาต่อหน่วย DR จริง = ราคาหุ้น x 0.01)\n")
    for top_n in [3, 5, 10]:
        ret_pct, trades = sim_with_offset(prep, syms_order, year_dates, top_n, offset=0, capital_thb=CAPITAL_THB)
        print(f"top_n={top_n:2d}: {ret_pct:+7.1f}%  ไม้ {trades:3d}")

    print(f"\n=== (2) ผลตอบแทน 1 ปี ถ้าเลื่อนวันเริ่ม rebalance ไปทีละวัน (offset 0-20 จาก 21 วันในรอบ) ===")
    for top_n in [3, 5]:
        print(f"\ntop_n={top_n}:")
        rets = []
        for offset in range(21):
            ret_pct, trades = sim_with_offset(prep, syms_order, year_dates, top_n, offset, capital_thb=CAPITAL_THB)
            rets.append(ret_pct)
            print(f"  เริ่มวันที่ {offset:2d} ของรอบ: {ret_pct:+7.2f}%  ({trades} ไม้)")
        rets = np.array(rets)
        print(f"  --> เฉลี่ย {rets.mean():+.2f}%  min {rets.min():+.2f}%  max {rets.max():+.2f}%  "
              f"ส่วนเบี่ยงเบนมาตรฐาน {rets.std():.2f} จุด%  ช่วงห่างสุด (max-min) {rets.max()-rets.min():.2f} จุด%")


if __name__ == "__main__":
    main()
