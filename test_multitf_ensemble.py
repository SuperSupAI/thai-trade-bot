#!/usr/bin/env python
"""
ทดสอบ multi-timeframe ensemble: แทนที่จะใช้ EMA200 เส้นเดียวตัดสิน (E4 เดิม) ให้โหวตจาก 4 EMA
(20/50/100/200) พร้อมกัน เข้า/ออกเมื่อ "เสียงส่วนใหญ่" (อย่างน้อย 3/4) เห็นตรงกัน แทนที่จะรอแค่เส้นเดียว
หวังผล: ลด whipsaw (ไม้แพ้เล็กๆ ซ้ำๆ จากราคาแกว่งตัดเส้นเดียวไปมา) เทียบ E4+ExitF เดิม

Exit เดิม (E4): Close<EMA200 อย่างเดียว + hard stop -20%
Exit ใหม่ (MultiTF): อย่างน้อย 3/4 ของ Close<EMA_n (20/50/100/200) + hard stop -20% (เหมือนเดิม)
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
VOTE_EMAS = [20, 50, 100, 200]
MIN_VOTES = 3


def add_multitf_signals(prep):
    for sym, P in prep.items():
        close = P["close"]
        votes_up = sum((close > P["emas"][n]).astype(int) for n in VOTE_EMAS)
        P["entries"]["E5_MultiTF"] = (votes_up >= MIN_VOTES).fillna(False)
        P["votes_up"] = votes_up
    return prep


def sim_multitf_exitf(prep, syms_order, test_dates, target_slots, capital_thb=CAPITAL_THB):
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / target_slots
    cash = capital_usd
    positions = {}
    trades_count, wins = 0, 0

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            votes_up = int(P["votes_up"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1

            exit_now = (chg <= -HARD_SL) or (votes_up < MIN_VOTES)
            if exit_now:
                cash += pos["qty"] * price * (1 - FEE)
                trades_count += 1
                if chg > 0:
                    wins += 1
                del positions[sym]

        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"]["E5_MultiTF"].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)
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
    prep = add_multitf_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท\n")

    rows = []
    for slots in [5, 10, 20]:
        m_old = sim_e4_trendexit(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        m_new = sim_multitf_exitf(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        print(f"{slots:2d} ไม้:")
        print(f"  E4 เดิม (EMA200 เดี่ยว):     {m_old['ret_pct']:+7.1f}%  ไม้ {m_old['trades']:4d}  WR {m_old['wr']:5.1f}%")
        print(f"  E5 MultiTF (โหวต 3/4):      {m_new['ret_pct']:+7.1f}%  ไม้ {m_new['trades']:4d}  WR {m_new['wr']:5.1f}%")
        rows.append(dict(slots=slots, variant="E4 เดิม", **m_old))
        rows.append(dict(slots=slots, variant="E5 MultiTF", **m_new))

    pd.DataFrame(rows).to_csv("multitf_ensemble_results.csv", index=False)
    print("\nบันทึกไว้ที่ multitf_ensemble_results.csv")


if __name__ == "__main__":
    main()
