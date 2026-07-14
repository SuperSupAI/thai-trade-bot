#!/usr/bin/env python
"""
รอบใหม่: หาวิธีเอาชนะ SPY จริงๆ (ไม่ใช่แค่ปิดช่องว่าง)

ไอเดีย: E4 (Close>EMA200 เข้า) ดีที่สุดที่เจอมา แต่ยังใช้ exit TP12%/SL15% ซึ่ง "จำกัดกำไรบนไว้ที่ +12%"
— SPY ไม่มีเพดานกำไรเลย (buy&hold ตลอด) ลองเปลี่ยน exit เป็น "ถือจนกว่าเทรนด์จะหักจริง" แทน:
  Exit F: ขายเมื่อ Close < EMA200 (เทรนด์หักจริง) + hard stop -20% กันหายนะเฉพาะกรณีร่วงแรงเร็ว
  ไม่มีเพดานกำไรเลย ปล่อยให้หุ้นที่วิ่งแรงต่อเนื่อง (แบบ NVDA) วิ่งได้เต็มที่เหมือน SPY ปล่อยให้ winner วิ่ง

ทดสอบที่ 3 ระดับความเข้มข้นของพอร์ต (5 / 10 / 20 ไม้เป้าหมาย) เพราะรอบก่อนพบว่ากระจายเยอะไปก็เจือจาง
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 100_000
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.20

KNOWN = {
    "SPY Buy & Hold": 315.3,
    "E4 (Close>EMA200) + TP12/SL15 (10 ไม้)": 287.2,
}


def sim_e4_trendexit(prep, syms_order, test_dates, target_slots, capital_thb=CAPITAL_THB):
    """entry = E4_Simple200 · exit = Close<EMA200 (ไม่มีเพดานกำไร) + hard stop -20%"""
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / target_slots
    cash = capital_usd
    positions = {}
    full_exits = 0
    wins = 0

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            ema200 = float(P["emas"][200].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1

            exit_now = False
            if chg <= -HARD_SL:
                exit_now = True
            elif price < ema200:
                exit_now = True

            if exit_now:
                cash += pos["qty"] * price * (1 - FEE)
                full_exits += 1
                if chg > 0:
                    wins += 1
                del positions[sym]

        for sym in syms_order:
            if cash < 1:
                break
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
            positions[sym] = dict(qty=qty, entry_price=price)

    val = cash
    for sym, pos in positions.items():
        val += pos["qty"] * float(prep[sym]["close"].iloc[-1])
    ret_pct = (val / capital_usd - 1) * 100
    wr = (wins / full_exits * 100) if full_exits else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=full_exits, wr=round(wr, 1))


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"ใช้ cache เดิม: {len(data)} หุ้น")
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบเต็ม: {all_dates[0].date()} → {all_dates[-1].date()}\n")

    for k, v in KNOWN.items():
        print(f"{k:45s} → {v:+7.1f}%  (ผลเดิม)")

    rows = list(KNOWN.items())
    for slots in [5, 10, 20]:
        m = sim_e4_trendexit(prep, syms_order, all_dates, slots)
        label = f"E4 + Exit F (Close<EMA200, ไม่มีเพดาน) {slots} ไม้"
        print(f"{label:45s} → {m['ret_pct']:+7.1f}%  ·  ไม้ {m['trades']:5d}  ·  win rate {m['wr']:5.1f}%")
        rows.append((label, m["ret_pct"]))

    df = pd.DataFrame(rows, columns=["variant", "ret_pct"])
    df["final_thb"] = (CAPITAL_THB * (1 + df["ret_pct"] / 100)).round().astype(int)
    df = df.sort_values("ret_pct", ascending=False)
    print("\n" + "=" * 70)
    print("สรุปเรียงจากดีสุด → แย่สุด")
    print("=" * 70)
    print(df.to_string(index=False))
    df.to_csv("beat_spy_v2_results.csv", index=False)


if __name__ == "__main__":
    main()
