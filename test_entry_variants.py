#!/usr/bin/env python
"""
ย้ายจากทดสอบ exit มาทดสอบ entry แทน — เพราะลอง exit มา 5 แบบแล้วก็ยังแพ้ SPY ทุกแบบ
สมมติฐาน: ปัญหาอาจไม่ใช่จุดออก แต่เป็นจุดเข้า/การเลือกหุ้นตอนสัญญาณชนกัน (พอร์ตกระจายไปหุ้นรองๆ
แทนที่จะกระจุกในหุ้นที่วิ่งแรงที่สุดแบบที่ S&P500 (market-cap weighted) ได้อานิสงส์)

เงื่อนไขเข้าที่ทดสอบ (ทุกแบบใช้ exit TP12%/SL15% เดิม ไม่จำกัดไม้ ไม่จำกัดจำนวน):
  E1 StackNewHigh : EMA เรียง 5>10>30>50>100>200 + New High รอบ 1 ปี (เข้มงวดสุด)
  E2 StackOnly    : EMA เรียงครบ ไม่ต้องรอ New High
  E3 TrendMACD    : Close>EMA200 & EMA10>EMA50 & EMA50>EMA200 & MACD>0 (baseline เดิม)
  E4 Simple200    : Close>EMA200 อย่างเดียว (หลวมสุด เข้าไวสุด)
  E5 E3+Momentum  : เงื่อนไขเข้าเหมือน E3 แต่ตอนสัญญาณชนกันหลายตัว "เลือกหุ้นโมเมนตัมแรงสุด
                    (ผลตอบแทน 3 เดือนย้อนหลังสูงสุด) ก่อน" แทนที่จะเรียงตามลำดับ list เฉยๆ

ทดสอบ 1 ปีก่อน (เร็ว, cache เดิม) แล้วเอาตัวที่ดีสุดไปเทียบ 10 ปีเต็มต่อ
"""
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from universe import US_STOCKS

CAPITAL_THB = 100_000
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
MOM_LOOKBACK = 63  # ~3 เดือนเทรด


def add_extra_signals(prep):
    for sym, P in prep.items():
        P["entries"]["E4_Simple200"] = (P["close"] > P["emas"][200]).fillna(False)
        P["mom63"] = P["close"].pct_change(MOM_LOOKBACK)
    return prep


def sim_entry(prep, syms_order, test_dates, entry_key, exit_cfg, rank_by_momentum=False,
              capital_thb=CAPITAL_THB, target_slots=TARGET_SLOTS):
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / target_slots
    cash = capital_usd
    positions = {}
    trades = []

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            if chg <= -exit_cfg["sl"] or chg >= exit_cfg["tp"]:
                cash += pos["qty"] * price * (1 - FEE)
                trades.append(chg)
                del positions[sym]

        candidates = []
        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"][entry_key].loc[dt]):
                continue
            candidates.append(sym)

        if rank_by_momentum:
            def mom_score(sym):
                P = prep[sym]
                if dt not in P["mom63"].index:
                    return -999
                v = P["mom63"].loc[dt]
                return v if pd.notna(v) else -999
            candidates.sort(key=mom_score, reverse=True)

        for sym in candidates:
            if cash < 1:
                break
            P = prep[sym]
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=qty, entry_price=price)

    val = cash
    for sym, pos in positions.items():
        px = float(prep[sym]["close"].iloc[-1])
        val += pos["qty"] * px
    ret_pct = (val / capital_usd - 1) * 100
    wins = sum(1 for t in trades if t > 0)
    wr = (wins / len(trades) * 100) if trades else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=len(trades), wr=round(wr, 1))


def main():
    data = teo.load_data()
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()
    xcfg = exits["TP12/SL15"]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    test_dates = all_dates[-252:]
    bh = teo.buy_hold_return(prep, test_dates)
    print(f"หน้าต่างทดสอบ: {test_dates[0].date()} → {test_dates[-1].date()} · B&H เฉลี่ยหุ้น US {bh:+.1f}%")
    print(f"exit: TP12%/SL15% (คงเดิมทุกแบบ) · ทุน {CAPITAL_THB:,} บาท\n")

    variants = [
        ("E1 StackNewHigh", "E1 StackNewHigh", False),
        ("E2 StackOnly", "E2 StackOnly", False),
        ("E3 TrendMACD (baseline)", "E3 TrendMACD", False),
        ("E4 Simple (Close>EMA200)", "E4_Simple200", False),
        ("E5 E3 + เรียงตามโมเมนตัม 3 เดือน", "E3 TrendMACD", True),
    ]

    rows = []
    for label, key, rank_mom in variants:
        m = sim_entry(prep, syms_order, test_dates, key, xcfg, rank_by_momentum=rank_mom)
        rows.append(dict(variant=label, **m))
        print(f"{label:38s} → ผลตอบแทน {m['ret_pct']:+7.1f}%  ·  ไม้ {m['trades']:4d}  ·  win rate {m['wr']:5.1f}%")

    df = pd.DataFrame(rows)
    df.to_csv("entry_variants_results.csv", index=False)
    print("\nบันทึกไว้ที่ entry_variants_results.csv")


if __name__ == "__main__":
    main()
