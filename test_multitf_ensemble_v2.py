#!/usr/bin/env python
"""
รอบ 2 ของ multi-timeframe ensemble: รอบแรก (EMA 20/50/100/200 โหวต 3/4) แพ้ E4 เดิม เพราะ EMA20
(เส้นเร็วสุด) ทำให้คะแนนโหวตแกว่งบ่อยเกินไป จนไม้เพิ่มขึ้นเกือบเท่าตัว -- รอบนี้ทดสอบ 2 ดีไซน์ใหม่:

  V1 "ตัด EMA20 ออก": โหวตจาก EMA 30/50/100/200 (ทั้ง 4 เส้นช้ากว่าเดิม) อย่างน้อย 3/4 เห็นตรงกัน
  V2 "EMA200 บังคับผ่าน + 2/3 ยืนยัน": ต้อง Close>EMA200 เสมอ บวกอย่างน้อย 2 ใน 3 ของ (30/50/100) เห็นด้วย
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

VARIANTS = {
    "V1 ตัด EMA20 (โหวต 3/4 จาก 30/50/100/200)": dict(vote_emas=[30, 50, 100, 200], min_votes=3, gate_200=False),
    "V2 EMA200 บังคับ + 2/3 ยืนยัน (30/50/100)": dict(vote_emas=[30, 50, 100], min_votes=2, gate_200=True),
}


def add_variant_signal(prep, key, cfg):
    for sym, P in prep.items():
        close = P["close"]
        votes_up = sum((close > P["emas"][n]).astype(int) for n in cfg["vote_emas"])
        sig = votes_up >= cfg["min_votes"]
        if cfg["gate_200"]:
            sig = sig & (close > P["emas"][200])
        P["entries"][key] = sig.fillna(False)
        P[f"votes_{key}"] = votes_up
        P[f"gate_{key}"] = (close > P["emas"][200]) if cfg["gate_200"] else None
    return prep


def sim_variant(prep, syms_order, test_dates, key, cfg, target_slots, capital_thb=CAPITAL_THB):
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
            votes_up = int(P[f"votes_{key}"].loc[dt])
            still_ok = votes_up >= cfg["min_votes"]
            if cfg["gate_200"]:
                still_ok = still_ok and bool(P[f"gate_{key}"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1

            exit_now = (chg <= -HARD_SL) or (not still_ok)
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
            if dt not in P["close"].index or not bool(P["entries"][key].loc[dt]):
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
    for key, cfg in VARIANTS.items():
        prep = add_variant_signal(prep, key, cfg)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบ: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"ทุนก้อนเดียว {CAPITAL_THB:,} บาท\n")

    rows = []
    for slots in [5, 10, 20]:
        m_old = sim_e4_trendexit(prep, syms_order, all_dates, target_slots=slots, capital_thb=CAPITAL_THB)
        print(f"{slots:2d} ไม้:")
        print(f"  E4 เดิม (EMA200 เดี่ยว):                       {m_old['ret_pct']:+7.1f}%  ไม้ {m_old['trades']:4d}  WR {m_old['wr']:5.1f}%")
        rows.append(dict(slots=slots, variant="E4 เดิม", **m_old))
        for key, cfg in VARIANTS.items():
            m = sim_variant(prep, syms_order, all_dates, key, cfg, target_slots=slots, capital_thb=CAPITAL_THB)
            print(f"  {key:48s} {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:4d}  WR {m['wr']:5.1f}%")
            rows.append(dict(slots=slots, variant=key, **m))
        print()

    pd.DataFrame(rows).to_csv("multitf_ensemble_v2_results.csv", index=False)
    print("บันทึกไว้ที่ multitf_ensemble_v2_results.csv")


if __name__ == "__main__":
    main()
