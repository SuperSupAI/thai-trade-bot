#!/usr/bin/env python
"""
แก้ตรรกะ: เดิมเปิดไม้ใหม่ได้แค่ตอนช่องว่าง (< 10 ไม้) เท่านั้น เงินทอนจากการปัดเศษหุ้นเต็ม
ในแต่ละไม้ไม่เคยถูกเอาไปใช้ต่อ — ตอนนี้เปลี่ยนเป็น: ถ้ามีเงินสดพอซื้อหุ้นใหม่ (แม้แค่ 1 หุ้น)
ที่มีสัญญาณเข้า ก็ซื้อเลย ไม่จำกัดจำนวนไม้ตายตัวที่ 10 อีกต่อไป (จำนวนหุ้นต่อไม้จะเล็กลงเรื่อยๆ
ถ้าเงินเหลือน้อย) — เงินต่อไม้ "เป้าหมาย" (pos_size) ยังคงคำนวณจาก ทุน/10 เหมือนเดิม
เพื่อกำหนดขนาดไม้ปกติ แต่ไม่ใช่เพดานตายตัวของจำนวนไม้

ทดสอบ 6 ระดับทุน: 10,000 / 20,000 / 50,000 / 80,000 / 100,000 / 1,000,000 บาท
เทียบกับผลเดิม (แบบจำกัดไม้ตายตัว) ให้เห็นว่าการปลดล็อกนี้ช่วยได้แค่ไหน
"""
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from universe import US_STOCKS

CAPITAL_LEVELS = [10_000, 20_000, 50_000, 80_000, 100_000, 1_000_000]
TARGET_SLOTS = 10   # ใช้กำหนดขนาด "ไม้ปกติ" (ทุน/10) ไม่ใช่เพดานจำนวนไม้อีกต่อไป
FEE = teo.FEE
THB_PER_USD = teo.THB_PER_USD


def simulate_reinvest(prep, syms_order, test_dates, entry_key, exit_cfg, target_slots, capital_thb):
    capital_usd = capital_thb / THB_PER_USD
    pos_size = capital_usd / target_slots  # ขนาดไม้ "เป้าหมาย" อ้างอิงไว้เฉยๆ ไม่ใช่เพดาน
    cash = capital_usd
    positions = {}
    trades = []
    skipped_price = 0
    equity = []
    cash_pct_series = []
    n_positions_series = []
    trail_n = exit_cfg["trail_ema"]

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            exit_now = False
            if chg <= -exit_cfg["sl"]:
                exit_now = True
            elif exit_cfg["tp"] is not None and chg >= exit_cfg["tp"]:
                exit_now = True
            elif trail_n and price < float(P["emas"][trail_n].loc[dt]):
                exit_now = True
            if exit_now:
                cash += pos["qty"] * price * (1 - FEE)
                trades.append(chg - 2 * FEE)
                del positions[sym]

        # ไม่จำกัดจำนวนไม้อีกต่อไป — แค่เช็คว่าเงินสดพอซื้อหุ้นใหม่ (>=1 หุ้น) ไหม
        for sym in syms_order:
            if cash < 1:
                break
            if sym in positions or sym not in prep:
                continue
            P = prep[sym]
            if dt not in P["close"].index or not bool(P["entries"][entry_key].loc[dt]):
                continue
            price = float(P["close"].loc[dt])
            budget = min(pos_size, cash)   # ยังใช้ขนาดไม้เป้าหมายเป็นเพดานต่อไม้ แต่ถ้าเงินเหลือน้อยกว่าก็ใช้เท่าที่มี
            qty = int((budget * (1 - FEE)) / price)
            if qty < 1:
                skipped_price += 1
                continue
            cash -= qty * price * (1 + FEE)
            positions[sym] = dict(qty=qty, entry_price=price)

        val = cash
        for sym, pos in positions.items():
            series = prep[sym]["close"]
            px = float(series.loc[dt]) if dt in series.index else float(series[series.index <= dt].iloc[-1])
            val += pos["qty"] * px
        equity.append(val)
        cash_pct_series.append(cash / val * 100 if val > 0 else 100.0)
        n_positions_series.append(len(positions))

    eq = pd.Series(equity)
    final = eq.iloc[-1] if len(eq) else capital_usd
    wins = sum(1 for t in trades if t > 0)
    cash_pct = pd.Series(cash_pct_series)
    n_pos = pd.Series(n_positions_series)
    return dict(
        trades=len(trades),
        wr=round(wins / len(trades) * 100, 1) if trades else float("nan"),
        ret_pct=round((final / capital_usd - 1) * 100, 1),
        skip=skipped_price,
        avg_cash_pct=round(cash_pct.mean(), 1),
        avg_positions_held=round(n_pos.mean(), 1),
        max_positions_held=int(n_pos.max()),
    )


def main():
    data = teo.load_data()
    prep = teo.precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    test_dates = all_dates[-252:]
    print(f"หน้าต่างทดสอบ: {test_dates[0].date()} → {test_dates[-1].date()}")
    print(f"สูตร: E3 TrendMACD + TP12/SL15 + ไม่จำกัดจำนวนไม้ (เดิมอ้างอิงไม้ละ ทุน/{TARGET_SLOTS})\n")

    rows = []
    for capital in CAPITAL_LEVELS:
        m = simulate_reinvest(prep, syms_order, test_dates, "E3 TrendMACD", exits["TP12/SL15"], TARGET_SLOTS, capital)
        rows.append(dict(ทุน_บาท=capital, **m))
        print(f"ทุน {capital:>9,} บาท → ผลตอบแทน {m['ret_pct']:+6.1f}%  ·  win rate {m['wr']:5.1f}%  ·  "
              f"ไม้รวม {m['trades']:4d}  ·  เงินสดเฉลี่ย {m['avg_cash_pct']:5.1f}%  ·  "
              f"ถือเฉลี่ย {m['avg_positions_held']:5.1f} ตัว (สูงสุด {m['max_positions_held']})  ·  "
              f"พลาดเพราะเงินไม่พอ {m['skip']:4d}")

    df = pd.DataFrame(rows)
    df.to_csv("capital_reinvest_leftover_results.csv", index=False)

    print("\n" + "=" * 110)
    print("เทียบกับผลเดิม (จำกัดไม้ตายตัว 10 ไม้ จาก test_capital_idle_time.py)")
    print("=" * 110)
    old = pd.read_csv("capital_idle_time_results.csv")
    for _, r in df.iterrows():
        cap = r["ทุน_บาท"]
        old_row = old[old["ทุน_บาท"] == cap]
        old_ret = old_row["ret_pct"].iloc[0] if len(old_row) else None
        old_cash = old_row["avg_cash_pct"].iloc[0] if len(old_row) else None
        if old_ret is not None:
            print(f"ทุน {cap:>9,} บาท: เดิม {old_ret:+6.1f}% (เงินสด {old_cash:5.1f}%) → ใหม่ {r['ret_pct']:+6.1f}% "
                  f"(เงินสด {r['avg_cash_pct']:5.1f}%)  ส่วนต่าง {r['ret_pct']-old_ret:+.1f}pp")
        else:
            print(f"ทุน {cap:>9,} บาท: (ไม่มีผลเดิมเทียบ — เคสใหม่) → {r['ret_pct']:+6.1f}% (เงินสด {r['avg_cash_pct']:5.1f}%)")


if __name__ == "__main__":
    main()
