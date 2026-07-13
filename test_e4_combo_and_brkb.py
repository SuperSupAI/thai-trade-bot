#!/usr/bin/env python
"""
1) รวม E4 entry (Close>EMA200 อย่างเดียว) + exit C (50%@+10% + breakeven + ratchet) เข้าด้วยกัน
   ทดสอบ 10 ปีเต็ม ดูว่าปิดช่องว่างกับ SPY ได้มากกว่าแยกทดสอบแต่ละอย่างไหม
2) เช็ค E4 (baseline exit TP12/SL15) เฉพาะปี 2022 (ตลาดหมี Fed hiking, SPY -16% ในปีนั้น) ว่า robust ไหม
3) ดาวน์โหลด BRK-B (Berkshire Hathaway) เทียบ Buy & Hold 10 ปีเดียวกัน — คำตอบคำถาม "ซื้อ BRK-B ดีมั้ย"
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 100_000
TARGET_SLOTS = 10
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.15

KNOWN = {
    "SPY Buy & Hold": 315.3,
    "E3 TrendMACD (baseline)": 227.4,
    "C) E3 + 50%@+10%+breakeven+ratchet": 240.6,
    "E4 Simple (Close>EMA200) + TP12/SL15": 287.2,
}


def sim_e4_plus_scaleoutC(prep, syms_order, test_dates, capital_thb=CAPITAL_THB, target_slots=TARGET_SLOTS):
    """entry = E4_Simple200 · exit = scale-out C (50%@+10% -> breakeven stop + ratchet ทุก+10%)"""
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / target_slots
    cash = capital_usd
    positions = {}
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

            sell_frac, exit_all = 0.0, False
            if pos["stage"] == 0:
                if chg <= -HARD_SL:
                    sell_frac, exit_all = 1.0, True
                elif chg >= 0.10:
                    sell_frac = 0.5
                    pos["stage"] = 1
                    pos["stop"] = pos["entry_price"]
            else:
                locked_pct = ((pos["peak"] / pos["entry_price"] - 1) // 0.10) * 0.10 - 0.10
                new_stop = pos["entry_price"] * (1 + max(0, locked_pct))
                pos["stop"] = max(pos["stop"], new_stop)
                if price <= pos["stop"]:
                    sell_frac, exit_all = 1.0, True

            if sell_frac > 0:
                qty_sold = pos["qty"] * sell_frac if not exit_all else pos["qty"]
                cash += qty_sold * price * (1 - FEE)
                pnl_pct = price / pos["entry_price"] - 1
                pos["qty"] -= qty_sold
                if exit_all or pos["qty"] < 1e-9:
                    full_exits += 1
                    if pnl_pct > 0:
                        wins_full += 1
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
            positions[sym] = dict(qty=float(qty), entry_price=price, peak=price, stage=0, stop=0.0)

    val = cash
    for sym, pos in positions.items():
        val += pos["qty"] * float(prep[sym]["close"].iloc[-1])
    ret_pct = (val / capital_usd - 1) * 100
    wr = (wins_full / full_exits * 100) if full_exits else float("nan")
    return dict(ret_pct=round(ret_pct, 1), full_exits=full_exits, wr=round(wr, 1))


def sim_e4_bear_2022(prep, syms_order):
    """เช็ค E4 + TP12/SL15 (baseline exit) เฉพาะปี 2022"""
    from test_entry_variants import sim_entry
    exits = teo.build_exit_grid()
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    dates_2022 = [d for d in all_dates if d.year == 2022]
    m = sim_entry(prep, syms_order, dates_2022, "E4_Simple200", exits["TP12/SL15"], rank_by_momentum=False)
    bh_2022 = teo.buy_hold_return(prep, dates_2022)
    return m, bh_2022, dates_2022[0], dates_2022[-1]


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"ใช้ cache เดิม: {len(data)} หุ้น")
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))

    print("\n" + "=" * 70)
    print("1) E4 entry + Scale-out C exit รวมกัน (10 ปีเต็ม)")
    print("=" * 70)
    for k, v in KNOWN.items():
        print(f"{k:42s} → {v:+7.1f}%  (ผลเดิม)")
    m = sim_e4_plus_scaleoutC(prep, syms_order, all_dates)
    print(f"{'E4 + Scale-out C (รวมกัน)':42s} → {m['ret_pct']:+7.1f}%  ·  ไม้ปิดหมด {m['full_exits']:5d}  ·  win rate {m['wr']:5.1f}%")

    print("\n" + "=" * 70)
    print("2) E4 (baseline TP12/SL15) เฉพาะปี 2022 (ตลาดหมี Fed hiking)")
    print("=" * 70)
    m2022, bh2022, d0, d1 = sim_e4_bear_2022(prep, syms_order)
    print(f"ช่วง: {d0.date()} → {d1.date()} · B&H เฉลี่ยหุ้น US {bh2022:+.1f}%")
    print(f"E4 ผลตอบแทน: {m2022['ret_pct']:+.1f}%  ·  ไม้ {m2022['trades']}  ·  win rate {m2022['wr']:.1f}%")

    print("\n" + "=" * 70)
    print("3) ซื้อ BRK-B (Berkshire Hathaway) ถือเฉยๆ 10 ปีเทียบกัน")
    print("=" * 70)
    brkb = safe_download_one("BRK-B", 10)
    brkb_seg = brkb[(brkb.index >= all_dates[0]) & (brkb.index <= all_dates[-1])]
    brkb_ret = (brkb_seg.iloc[-1] / brkb_seg.iloc[0] - 1) * 100
    brkb_final_thb = CAPITAL_THB * (1 + brkb_ret / 100)
    yrs = len(brkb_seg) / 252
    brkb_cagr = ((brkb_seg.iloc[-1] / brkb_seg.iloc[0]) ** (1 / yrs) - 1) * 100
    brkb_maxdd = ((brkb_seg / brkb_seg.cummax() - 1).min()) * 100
    print(f"BRK-B ช่วงเดียวกัน: {brkb_seg.index[0].date()} → {brkb_seg.index[-1].date()}")
    print(f"ผลตอบแทนรวม: {brkb_ret:+.1f}%  ·  CAGR: {brkb_cagr:+.1f}%  ·  MaxDD: {brkb_maxdd:.1f}%")
    print(f"มูลค่าสุดท้าย (ทุน {CAPITAL_THB:,} บาท): {brkb_final_thb:,.0f} บาท")

    print("\n" + "=" * 70)
    print("สรุปเทียบทั้งหมด (10 ปี, ทุน 100,000 บาท)")
    print("=" * 70)
    rows = list(KNOWN.items()) + [("E4 + Scale-out C (รวมกัน)", m["ret_pct"]),
                                   ("BRK-B Buy & Hold", round(brkb_ret, 1))]
    df = pd.DataFrame(rows, columns=["variant", "ret_pct"])
    df["final_thb"] = (CAPITAL_THB * (1 + df["ret_pct"] / 100)).round().astype(int)
    df = df.sort_values("ret_pct", ascending=False)
    print(df.to_string(index=False))
    df.to_csv("e4_combo_and_brkb_results.csv", index=False)


if __name__ == "__main__":
    main()
