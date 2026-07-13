#!/usr/bin/env python
"""
Backtest ย้อนหลัง 1 ปี: ถ้าลงทุนด้วยกลยุทธ์เดียวกับที่บอทใช้จริงตอนนี้
(Trend+MACD เข้า / TP12%+SL15% ออก จาก strategy.py) จะซื้ออะไรบ้าง กำไร/ขาดทุนเท่าไหร่

โมเดล: ถือได้พร้อมกันหลายตัว ไม้ละไม่เกิน POSITION_SIZE_THB บาท (ปรับได้ด้านล่าง)
  - POSITION_SIZE_THB = CAPITAL_THB → ถือได้ทีละ 1 ตัวเต็มพอร์ต (เดิม)
  - POSITION_SIZE_THB < CAPITAL_THB → กระจายได้หลายตัวพร้อมกัน (สูงสุด ~CAPITAL_THB/POSITION_SIZE_THB ตัว)
ถ้าวันไหนมีสัญญาณเข้าหลายตัวพร้อมกันเกินโควตา จะเลือกตัวที่มาก่อนใน US_STOCKS (ลำดับ deterministic)

ค่าธรรมเนียม: สมมติ 0.2%/ข้าง (ตามที่ใช้ทั่วทั้งโปรเจกต์ — ปรับ FEE ด้านล่างได้ถ้ารู้ค่าจริงของ Webull)
อัตราแลกเปลี่ยน: สมมติ 35.5 บาท/USD (ปรับ THB_PER_USD ได้ถ้าอยากใช้เรตอื่น)
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
sys.path.insert(0, "..")
from safe_fetch import safe_download_one
from universe import US_STOCKS

from strategy import entry_signal, should_exit

CAPITAL_THB = 100_000
POSITION_SIZE_THB = 10_000    # 10 ไม้พร้อมกัน — ตรงกับที่ validate ไว้ใน strategy.py ล่าสุด (Trend+MACD/TP12/SL15)
THB_PER_USD = 35.5
FEE = 0.002
YEARS_DOWNLOAD = 2      # โหลด 2 ปี ให้ EMA200/New-High มี warm-up พอ (เหมือน bot.py)
TEST_DAYS = 252         # ทดสอบจริงแค่ ~1 ปีล่าสุด (252 trading days)


def main():
    capital_usd = CAPITAL_THB / THB_PER_USD
    position_size_usd = POSITION_SIZE_THB / THB_PER_USD
    max_slots = max(1, int(CAPITAL_THB / POSITION_SIZE_THB))
    print(f"ทุนเริ่มต้น: {CAPITAL_THB:,.0f} บาท (~{capital_usd:,.2f} USD ที่ {THB_PER_USD} บาท/USD)")
    print(f"เงินต่อไม้: {POSITION_SIZE_THB:,.0f} บาท (~{position_size_usd:,.2f} USD) → ถือพร้อมกันได้สูงสุด ~{max_slots} ตัว")
    print(f"กลยุทธ์: Trend+MACD (เข้า) / TP+12% SL-15% (ออก) — จาก webull_bot/strategy.py")
    print(f"โหลดหุ้น US: {len(US_STOCKS)} ตัว ({YEARS_DOWNLOAD} ปี)...\n")

    data = {}
    for i, sym in enumerate(US_STOCKS):
        c = safe_download_one(sym, YEARS_DOWNLOAD)
        if c is not None and len(c) > 260:
            data[sym] = c
        if (i + 1) % 20 == 0:
            print(f"  โหลดแล้ว {i+1}/{len(US_STOCKS)} ตัว...")
    print(f"ใช้ได้ {len(data)} ตัว\n")

    # ทุกตัวต้องมี entry_signal ล่วงหน้าไว้ครบ (ต้องใช้ full history เพื่อ EMA/New-High ถูกต้อง)
    signals = {sym: entry_signal(c) for sym, c in data.items()}

    # calendar หลัก = union ของทุกวันเทรดที่มีของทุกตัว แล้วตัดมาแค่ TEST_DAYS วันล่าสุด
    all_dates = sorted(set().union(*[c.index for c in data.values()]))
    test_dates = all_dates[-TEST_DAYS:]
    print(f"ช่วงทดสอบจริง: {test_dates[0].date()} ถึง {test_dates[-1].date()} ({len(test_dates)} วันเทรด)\n")

    cash = capital_usd
    positions = {}  # symbol -> dict(qty, entry_price, entry_date)
    trades = []  # dict: symbol, entry_date, entry_price, exit_date, exit_price, reason, pnl_usd, pnl_pct

    for dt in test_dates:
        # 1) เช็คไม้ที่ถืออยู่ก่อน ว่าถึงจุดออกหรือยัง
        for sym in list(positions.keys()):
            close_series = data[sym]
            if dt not in close_series.index:
                continue
            pos = positions[sym]
            price_today = float(close_series.loc[dt])
            exit_now, reason = should_exit(pos["entry_price"], price_today)
            if exit_now:
                proceeds = pos["qty"] * price_today * (1 - FEE)
                pnl_usd = proceeds - (pos["qty"] * pos["entry_price"] * (1 + FEE))
                cash += proceeds
                trades.append(dict(
                    symbol=sym, entry_date=pos["entry_date"], entry_price=pos["entry_price"],
                    exit_date=dt, exit_price=price_today, reason=reason,
                    pnl_usd=pnl_usd, pnl_pct=(price_today / pos["entry_price"] - 1) * 100,
                ))
                del positions[sym]

        # 2) เปิดไม้ใหม่เท่าที่โควตา/เงินสดเหลือพอ (ตามลำดับ US_STOCKS, deterministic)
        if len(positions) < max_slots:
            for sym in US_STOCKS:
                if len(positions) >= max_slots or cash < 1:
                    break
                if sym in positions or sym not in data or dt not in signals[sym].index:
                    continue
                if bool(signals[sym].loc[dt]):
                    price_today = float(data[sym].loc[dt])
                    budget = min(position_size_usd, cash)
                    qty = int((budget * (1 - FEE)) / price_today)
                    if qty < 1:
                        continue  # เงินที่แบ่งไว้ไม่พอซื้อแม้ 1 หุ้น ข้ามสัญญาณนี้ไป
                    cost = qty * price_today * (1 + FEE)
                    cash -= cost
                    positions[sym] = dict(qty=qty, entry_price=price_today, entry_date=dt)

    # ปิดไม้ที่ยังถืออยู่ตอนจบ ด้วยราคาล่าสุด (mark-to-market ไม่ใช่ปิดจริง)
    open_position_value = 0.0
    if positions:
        print("⚠️ ยังถือค้างอยู่ตอนจบช่วงทดสอบ:")
        for sym, pos in positions.items():
            last_price = float(data[sym].iloc[-1])
            val = pos["qty"] * last_price
            open_position_value += val
            unrealized_pnl = val - pos["qty"] * pos["entry_price"]
            print(f"  {sym}: {pos['qty']} หุ้น @ {pos['entry_price']:.2f} → ราคาล่าสุด {last_price:.2f} "
                  f"(unrealized P&L {unrealized_pnl:+.2f} USD)")
        print()

    final_value_usd = cash + open_position_value
    final_value_thb = final_value_usd * THB_PER_USD
    total_pnl_thb = final_value_thb - CAPITAL_THB

    print("=" * 100)
    print(f"ไม้ที่ปิดจริงทั้งหมด: {len(trades)}")
    print("=" * 100)
    if trades:
        rows = []
        for k, t in enumerate(sorted(trades, key=lambda x: x["entry_date"]), 1):
            rows.append(dict(
                **{"#": k, "หุ้น": t["symbol"],
                   "ซื้อ": t["entry_date"].strftime("%Y-%m-%d"), "ราคาซื้อ": round(t["entry_price"], 2),
                   "ขาย": t["exit_date"].strftime("%Y-%m-%d"), "ราคาขาย": round(t["exit_price"], 2),
                   "เหตุออก": t["reason"], "กำไร%": round(t["pnl_pct"], 1),
                   "กำไร(USD)": round(t["pnl_usd"], 2), "กำไร(บาท)": round(t["pnl_usd"] * THB_PER_USD)}
            ))
        df = pd.DataFrame(rows)
        print(df.to_string(index=False))

        wins = [t for t in trades if t["pnl_usd"] > 0]
        print(f"\nชนะ {len(wins)}/{len(trades)} ไม้ (win rate {len(wins)/len(trades)*100:.1f}%)")
    else:
        print("ไม่มีไม้ไหนปิดเลยในช่วงทดสอบ (อาจยังถือค้างอยู่ หรือไม่มีสัญญาณเข้าเลย)")

    print("\n" + "=" * 100)
    print(f"มูลค่าสุดท้าย: {final_value_usd:,.2f} USD (~{final_value_thb:,.0f} บาท)")
    print(f"กำไร/ขาดทุนรวม: {total_pnl_thb:+,.0f} บาท ({(final_value_thb/CAPITAL_THB - 1)*100:+.1f}%)")
    print("=" * 100)


if __name__ == "__main__":
    main()
