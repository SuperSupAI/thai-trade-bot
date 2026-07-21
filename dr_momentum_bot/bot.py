#!/usr/bin/env python
"""
DR Momentum Bot -- รีบาลานซ์รายเดือน ตามผลวิจัยทั้งเซสชัน (momentum baseline ล้วนๆ ไม่มี overlay,
DR universe 47 ตัวสหรัฐฯ, top_n=3, ไม่ rebalance เกิน 1 ครั้ง/เดือน)

โหมดปลอดภัยเป็นค่าเริ่มต้น: DRY_RUN=True แค่ "พิมพ์" ว่าจะส่งออเดอร์อะไร ไม่ยิงจริง
เปิดยิงจริงต้องตั้ง env var DR_BOT_DRY_RUN=false เอง (และควรทดสอบผ่าน SETTRADE_BROKER_ID=SANDBOX
จนมั่นใจก่อน ค่อยเปลี่ยนไปโบรกจริง)

รันได้จาก dr_momentum_bot/ โดยตรง:  python bot.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dr_universe import DR_COVERED_EXPANDED, get_dr_symbol
from rank_momentum import fetch_prices, rank_top_n

TOP_N = 3
CAPITAL_THB = float(os.environ.get("DR_BOT_CAPITAL_THB", "10000"))  # ทุนเล่น satellite ตามแผนเดิม
DRY_RUN = os.environ.get("DR_BOT_DRY_RUN", "true").lower() != "false"


def get_current_dr_price(equity_marketdata, dr_symbol: str) -> float:
    quote = equity_marketdata.get_quote_symbol(dr_symbol)
    # โครงสร้าง response จริงต้องเช็คตอนต่อ Sandbox จริง (คีย์อาจชื่อ 'last' หรือ 'lastPrice' -- ปรับตามที่เจอ)
    return float(quote.get("last") or quote.get("lastPrice") or quote["marketPrice"])


def main():
    print(f"{'='*70}")
    print(f"DR Momentum Bot -- {'DRY RUN (ไม่ส่งออเดอร์จริง)' if DRY_RUN else '⚠️ LIVE MODE'}")
    print(f"ทุน: {CAPITAL_THB:,.0f} บาท · top_n={TOP_N}")
    print(f"{'='*70}\n")

    # 1) จัดอันดับ momentum จากราคาหุ้นแม่ (yfinance) -- ตรงกับวิธี backtest
    price_data = fetch_prices(DR_COVERED_EXPANDED, years=2)
    ranked = rank_top_n(price_data, top_n=TOP_N)
    print("\nTop momentum เดือนนี้:")
    for ticker, score in ranked:
        print(f"  {ticker:8s}  {score*100:+.1f}%")

    # 2) แปลง ticker หุ้นแม่ -> รหัส DR จริงบน SET
    print("\nแปลงเป็นรหัส DR:")
    orders = []
    for ticker, score in ranked:
        dr_symbol, confidence = get_dr_symbol(ticker)
        flag = "" if confidence == "confirmed" else f"  ⚠️ {confidence.upper()} -- เช็ค set.or.th ก่อนส่งจริง!"
        print(f"  {ticker:8s} -> {dr_symbol or '(ไม่มี mapping)':10s}{flag}")
        if dr_symbol:
            orders.append((ticker, dr_symbol, score))

    if not orders:
        print("\nไม่มี DR symbol ที่ map ได้เลย หยุดทำงาน")
        return

    budget_each = CAPITAL_THB / len(orders)

    # 3) เชื่อม Settrade Open API (ต้องตั้ง env vars ก่อน — ดู settrade_client.py)
    try:
        from settrade_client import get_equity_account, get_investor, place_buy_order
        investor = get_investor()
        equity = get_equity_account()
        market = investor.MarketData()
    except Exception as e:
        print(f"\n⚠️ ยังต่อ Settrade API ไม่ได้ ({type(e).__name__}: {e})")
        print("   (ปกติถ้ายังไม่ได้ตั้ง env vars SETTRADE_APP_ID ฯลฯ — ดูวิธีตั้งค่าใน settrade_client.py)")
        print("   แสดงแค่แผนการซื้อคร่าวๆ แทน (ไม่มีราคาตลาดจริง):")
        for ticker, dr_symbol, score in orders:
            print(f"  ซื้อ {dr_symbol} งบ ~{budget_each:,.0f} บาท (momentum {score*100:+.1f}%)")
        return

    print(f"\n{'='*70}")
    print("แผนคำสั่งซื้อ:")
    for ticker, dr_symbol, score in orders:
        try:
            price = get_current_dr_price(market, dr_symbol)
        except Exception as e:
            print(f"  {dr_symbol}: ดึงราคาไม่ได้ ({e}) ข้าม")
            continue
        volume = int(budget_each / price)
        # หมายเหตุ: board lot มาตรฐานหุ้นไทยคือ 100 หุ้น/ล็อต -- ปัดให้ลงตัวถ้าจำเป็นก่อนส่งจริง
        print(f"  BUY {dr_symbol:10s} จำนวน {volume:6d} หน่วย @ {price:,.2f} บาท "
              f"(~{volume*price:,.0f} บาท, momentum {score*100:+.1f}%)")

        if not DRY_RUN and volume > 0:
            result = place_buy_order(equity, dr_symbol, volume, price)
            print(f"    -> ส่งออเดอร์แล้ว: {result}")

    if DRY_RUN:
        print("\n(DRY RUN — ยังไม่ได้ส่งออเดอร์จริง ตั้ง env var DR_BOT_DRY_RUN=false เพื่อยิงจริง)")


if __name__ == "__main__":
    main()
