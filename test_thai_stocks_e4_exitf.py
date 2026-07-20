#!/usr/bin/env python
"""
ทดสอบสูตร E4+ExitF (เหมือนที่ใช้กับหุ้นสหรัฐฯ) กับหุ้นไทยรายตัวแทน -- คำถาม: ถ้าจับหุ้นแบบ DELTA
(ที่เคยพุ่งแรงมากช่วง 2019-2022) ได้ จะพลิกให้ "เล่นรายตัว" ชนะ RMF ได้จริงไหม? และเป็นเพราะกฎ
เข้า-ออกจับได้เอง (ไม่ใช่ hindsight) หรือแค่โชคหุ้นตัวเดียว?

ใช้ universe หุ้นไทยขนาดใหญ่สภาพคล่องสูงจาก SECTORS ใน universe.py (~65 ตัว รวม DELTA.BK)
กำไรหุ้นไทยไม่โดนภาษี capital gain เลย (ขายผ่านตลาดหลักทรัพย์) -- ต่างจากหุ้นสหรัฐฯ ที่โดนตอนโอนเงินกลับ
"""
import pickle
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from universe import SECTORS
from safe_fetch import safe_download_one

CACHE_FILE = "thai_stocks_10y_cache.pkl"
CAPITAL_THB = 1_000_000
FEE = teo.FEE
HARD_SL = 0.20
YEARS = 10

THAI_UNIVERSE = sorted({sym + ".BK" for stocks in SECTORS.values() for sym in stocks})


def load_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    print(f"โหลดหุ้นไทย {len(THAI_UNIVERSE)} ตัว ({YEARS} ปี)...")
    data = {}
    for i, sym in enumerate(THAI_UNIVERSE):
        c = safe_download_one(sym, YEARS)
        if c is not None and len(c) > 600:
            data[sym] = c
        if (i + 1) % 20 == 0:
            print(f"  โหลดแล้ว {i+1}/{len(THAI_UNIVERSE)}...")
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"ใช้ได้ {len(data)}/{len(THAI_UNIVERSE)} ตัว")
    return data


def sim_e4_exitf_thb(prep, syms_order, test_dates, target_slots, capital_thb, exclude=None):
    """เหมือน sim_e4_trendexit เดิม แต่เป็นเงินบาทตรงๆ ไม่ต้องแปลง USD"""
    pos_size = capital_thb / target_slots
    cash = capital_thb
    positions = {}
    trade_log = []
    exclude = exclude or set()

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
                trade_log.append(dict(sym=sym, entry=pos["entry_price"], exit=price, chg_pct=chg * 100,
                                       entry_date=pos["entry_date"], exit_date=dt))
                del positions[sym]

        for sym in syms_order:
            if sym in exclude or cash < 1:
                continue
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E4_Simple200"].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=qty, entry_price=price, entry_date=dt)

    val = cash
    for sym, pos in positions.items():
        val += pos["qty"] * float(prep[sym]["close"].iloc[-1])
    ret_pct = (val / capital_thb - 1) * 100
    wins = sum(1 for t in trade_log if t["chg_pct"] > 0)
    wr = (wins / len(trade_log) * 100) if trade_log else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=len(trade_log), wr=round(wr, 1), trade_log=trade_log,
                open_positions=len(positions))


def main():
    data = load_data()
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in THAI_UNIVERSE if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"\nช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}  หุ้นที่ใช้ได้ {len(syms_order)} ตัว")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท\n")

    if "DELTA.BK" in prep:
        d = prep["DELTA.BK"]["close"]
        delta_bh = (float(d.iloc[-1]) / float(d.iloc[0]) - 1) * 100
        print(f"DELTA.BK เดี่ยวๆ (Buy&Hold 10 ปีเต็ม): {delta_bh:+.1f}%\n")

    for slots in [5, 10, 20]:
        m = sim_e4_exitf_thb(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        delta_trades = [t for t in m["trade_log"] if t["sym"] == "DELTA.BK"]
        delta_chgs = ", ".join("{:+.0f}%".format(t["chg_pct"]) for t in delta_trades)
        extra = f" ({delta_chgs})" if delta_trades else ""
        print(f"E4+ExitF หุ้นไทย ({slots:2d} ไม้): {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:4d}  WR {m['wr']:5.1f}%  "
              f"ค้าง {m['open_positions']} ไม้  |  DELTA.BK ถูกเทรด {len(delta_trades)} ครั้ง{extra}")

    print()
    # เทียบ "มี DELTA" vs "ไม่มี DELTA" ที่ 5 ไม้ เพื่อแยกผลคุณูปการของหุ้นตัวเดียว
    m_with = sim_e4_exitf_thb(prep, syms_order, all_dates, target_slots=5, capital_thb=CAPITAL_THB)
    m_without = sim_e4_exitf_thb(prep, syms_order, all_dates, target_slots=5, capital_thb=CAPITAL_THB,
                                  exclude={"DELTA.BK"})
    print("=" * 90)
    print(f"เทียบผลกระทบของ DELTA.BK ตัวเดียว (5 ไม้):")
    print(f"  มี DELTA ในจักรวาลหุ้น:    {m_with['ret_pct']:+7.1f}%")
    print(f"  ไม่มี DELTA (ตัดออก):     {m_without['ret_pct']:+7.1f}%")
    print(f"  ผลต่างจาก DELTA ตัวเดียว: {m_with['ret_pct']-m_without['ret_pct']:+7.1f} percentage point")

    # Buy&Hold ตะกร้าเท่าน้ำหนักทั้งหมด เทียบ baseline
    bh_rets = []
    for sym in syms_order:
        c = prep[sym]["close"]
        bh_rets.append(float(c.iloc[-1]) / float(c.iloc[0]) - 1)
    bh_avg = np.mean(bh_rets) * 100
    print(f"\nBuy&Hold ตะกร้าหุ้นไทยทั้งหมด (equal-weight เฉลี่ยรายตัว): {bh_avg:+.1f}%")


if __name__ == "__main__":
    main()
