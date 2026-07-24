#!/usr/bin/env python
"""
DR Momentum Bot -- รีบาลานซ์รายเดือน ตามผลวิจัยทั้งเซสชัน (momentum baseline ล้วนๆ ไม่มี overlay,
DR universe 47 ตัวสหรัฐฯ, top_n=3, ไม่ rebalance เกิน 1 ครั้ง/เดือน)

Delta-only trading (เหมือน sim_cross_sectional_momentum ตัว canonical ที่ backtest ทั้งเซสชันอ้างอิง):
ขายเฉพาะตัวที่หลุด top-N, ซื้อเฉพาะตัวใหม่ที่เข้ามา, ตัวที่ยังติดอยู่ปล่อยผ่านไม่แตะ (ไม่ rebalance
กลับเท่ากันทุกเดือน)

โหมดปลอดภัยเป็นค่าเริ่มต้น: DRY_RUN=True แค่ "พิมพ์" ว่าจะส่งออเดอร์อะไร ไม่ยิงจริง
เปิดยิงจริงต้องตั้ง env var DR_BOT_DRY_RUN=false เอง (และควรทดสอบผ่าน SETTRADE_BROKER_ID=SANDBOX
จนมั่นใจก่อน ค่อยเปลี่ยนไปโบรกจริง)

รันได้จาก dr_momentum_bot/ โดยตรง:  python bot.py
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from dr_universe import DR_COVERED_EXPANDED, get_dr_symbol
from rank_momentum import fetch_prices, rank_top_n

TOP_N = 3
CAPITAL_THB = float(os.environ.get("DR_BOT_CAPITAL_THB", "10000"))  # ทุนเล่น satellite ตามแผนเดิม
DRY_RUN = os.environ.get("DR_BOT_DRY_RUN", "true").lower() != "false"
LOT_SIZE = int(os.environ.get("DR_BOT_LOT_SIZE", "100"))  # board lot มาตรฐาน -- ยังไม่ยืนยันว่า DR
# เทรดแบบ odd-lot ได้ไหม (ต่ำกว่า 100 หน่วย) เช็คกับ SET/โบรกก่อนแก้ค่านี้

TRADE_LOG_PATH = os.path.join(os.path.dirname(__file__), "trade_history.csv")
_TRADE_LOG_FIELDS = ["timestamp", "action", "ticker", "dr_symbol", "volume", "price",
                      "value_thb", "momentum_pct", "dry_run"]


def log_trade(action: str, ticker: str, dr_symbol: str, volume: int, price: float, momentum_pct: float):
    """บันทึกทุกคำสั่งซื้อ/ขาย (ทั้ง DRY_RUN และยิงจริง) ลงไฟล์ถาวร -- ไม่งั้นไม่มีประวัติเทรดจริงให้ดูย้อนหลัง
    เลย เพราะบอทตัวนี้ไม่มี state ข้ามรอบรัน (query พอร์ต Settrade สดทุกครั้ง)"""
    is_new = not os.path.exists(TRADE_LOG_PATH)
    with open(TRADE_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_TRADE_LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(dict(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            action=action, ticker=ticker, dr_symbol=dr_symbol, volume=volume,
            price=round(price, 4), value_thb=round(volume * price, 2),
            momentum_pct=round(momentum_pct * 100, 2), dry_run=DRY_RUN,
        ))

# universe ที่ใช้จัดอันดับ = เฉพาะตัวที่มี DR จริงเท่านั้น (ตัดตัวที่ไม่มี DR ออกตั้งแต่ต้น ไม่ใช่กรอง
# หลังจัดอันดับ -- กัน top-N ที่เทรดจริงได้เหลือน้อยกว่า TOP_N เพราะดันมีตัวที่ไม่มี DR ติดอันดับมาด้วย)
TRADABLE_TICKERS = [t for t in DR_COVERED_EXPANDED if get_dr_symbol(t)[0]]


def get_current_dr_price(equity_marketdata, dr_symbol: str) -> float:
    quote = equity_marketdata.get_quote_symbol(dr_symbol)
    # โครงสร้าง response จริงต้องเช็คตอนต่อ Sandbox จริง (คีย์อาจชื่อ 'last' หรือ 'lastPrice' -- ปรับตามที่เจอ)
    return float(quote.get("last") or quote.get("lastPrice") or quote["marketPrice"])


def get_held_symbols(equity) -> dict:
    """คืน dict {dr_symbol: volume} ที่ถืออยู่จริงในบัญชีตอนนี้
    โครงสร้าง response จริงต้องเช็คตอนต่อ Sandbox จริง (คีย์อาจชื่อ 'symbol'/'securitySymbol' และ
    'volume'/'actualVolume' -- ปรับตามที่เจอ)"""
    portfolios = equity.get_portfolios()
    portfolio_list = portfolios.get("portfolioList", []) if isinstance(portfolios, dict) else portfolios
    held = {}
    for p in portfolio_list or []:
        symbol = p.get("symbol") or p.get("securitySymbol") or p.get("securityName")
        volume = p.get("actualVolume") or p.get("volume") or p.get("startVolume") or 0
        if symbol and volume:
            held[str(symbol)] = int(volume)
    return held


def round_to_lot(volume: int) -> int:
    return (volume // LOT_SIZE) * LOT_SIZE


def main():
    print(f"{'='*70}")
    print(f"DR Momentum Bot -- {'DRY RUN (ไม่ส่งออเดอร์จริง)' if DRY_RUN else '⚠️ LIVE MODE'}")
    print(f"ทุน: {CAPITAL_THB:,.0f} บาท · top_n={TOP_N} · universe เทรดได้จริง {len(TRADABLE_TICKERS)}/{len(DR_COVERED_EXPANDED)} ตัว")
    print(f"{'='*70}\n")

    # 1) จัดอันดับ momentum จากราคาหุ้นแม่ (yfinance) -- ตรงกับวิธี backtest, เฉพาะตัวที่มี DR จริง
    price_data = fetch_prices(TRADABLE_TICKERS, years=2)
    ranked = rank_top_n(price_data, top_n=TOP_N)
    print("\nTop momentum เดือนนี้:")
    for ticker, score in ranked:
        print(f"  {ticker:8s}  {score*100:+.1f}%")

    # 2) แปลง ticker หุ้นแม่ -> รหัส DR จริงบน SET (ทุกตัวควรมี mapping แล้วเพราะกรอง TRADABLE_TICKERS ไว้แล้ว)
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

    target_symbols = {dr_symbol for _, dr_symbol, _ in orders}
    budget_each = CAPITAL_THB / len(orders)

    # 3) เชื่อม Settrade Open API (ต้องตั้ง env vars ก่อน — ดู settrade_client.py)
    try:
        from settrade_client import get_equity_account, get_investor, place_buy_order, place_sell_order
        investor = get_investor()
        equity = get_equity_account()
        market = investor.MarketData()
    except Exception as e:
        print(f"\n⚠️ ยังต่อ Settrade API ไม่ได้ ({type(e).__name__}: {e})")
        print("   (ปกติถ้ายังไม่ได้ตั้ง env vars SETTRADE_APP_ID ฯลฯ — ดูวิธีตั้งค่าใน settrade_client.py)")
        print("   แสดงแค่แผนการซื้อคร่าวๆ แทน (ไม่มีราคาตลาดจริง ไม่เช็คพอร์ตเดิม):")
        for ticker, dr_symbol, score in orders:
            print(f"  ซื้อ {dr_symbol} งบ ~{budget_each:,.0f} บาท (momentum {score*100:+.1f}%)")
        return

    # 4) ขายตัวที่หลุด top-N (delta-only: เช็คพอร์ตปัจจุบันจริงจาก Settrade เทียบกับ target รอบนี้)
    print(f"\n{'='*70}")
    print("ขายตัวที่หลุด top-N:")
    try:
        held = get_held_symbols(equity)
    except Exception as e:
        print(f"  ⚠️ ดึงพอร์ตปัจจุบันไม่ได้ ({e}) — ข้ามขั้นตอนขาย ต้องเช็คด้วยมือ!")
        held = {}
    to_sell = [sym for sym in held if sym not in target_symbols]
    if held and not to_sell:
        print("  (ไม่มี -- ตัวที่ถืออยู่ยังติด top-N ทั้งหมด)")
    elif not held:
        print("  (ไม่มีตัวถืออยู่เดิม หรือดึงพอร์ตไม่ได้)")
    for sym in to_sell:
        volume = held[sym]
        try:
            price = get_current_dr_price(market, sym)
        except Exception as e:
            print(f"  {sym}: ดึงราคาขายไม่ได้ ({e}) ข้าม -- ต้องขายด้วยมือ!")
            continue
        print(f"  SELL {sym:10s} จำนวน {volume:6d} หน่วย @ {price:,.2f} บาท (~{volume*price:,.0f} บาท)")
        sell_ticker = next((t for t, dr, _ in orders if dr == sym), None) or \
            next((t for t in DR_COVERED_EXPANDED if get_dr_symbol(t)[0] == sym), sym)
        log_trade("SELL", sell_ticker, sym, volume, price, 0.0)
        if not DRY_RUN:
            result = place_sell_order(equity, sym, volume, price)
            print(f"    -> ส่งออเดอร์ขายแล้ว: {result}")

    # 5) ซื้อตัวใหม่ที่เข้า top-N (ตัวที่ถืออยู่แล้วและยังติด top-N ปล่อยผ่าน ไม่ rebalance ซ้ำ)
    print(f"\n{'='*70}")
    print("แผนคำสั่งซื้อ (เฉพาะตัวที่ยังไม่ได้ถือ):")
    for ticker, dr_symbol, score in orders:
        if dr_symbol in held:
            print(f"  {dr_symbol}: ถืออยู่แล้ว ({held[dr_symbol]} หน่วย) ยังติด top-N — ไม่แตะ")
            continue
        try:
            price = get_current_dr_price(market, dr_symbol)
        except Exception as e:
            print(f"  {dr_symbol}: ดึงราคาไม่ได้ ({e}) ข้าม")
            continue
        volume = round_to_lot(int(budget_each / price))
        if volume <= 0:
            print(f"  {dr_symbol}: งบ {budget_each:,.0f} บาทไม่พอซื้อแม้แต่ 1 board lot "
                  f"({LOT_SIZE} หน่วย @ {price:,.2f} บาท = {LOT_SIZE*price:,.0f} บาท) ข้าม")
            continue
        print(f"  BUY {dr_symbol:10s} จำนวน {volume:6d} หน่วย @ {price:,.2f} บาท "
              f"(~{volume*price:,.0f} บาท, momentum {score*100:+.1f}%)")
        log_trade("BUY", ticker, dr_symbol, volume, price, score)

        if not DRY_RUN:
            result = place_buy_order(equity, dr_symbol, volume, price)
            print(f"    -> ส่งออเดอร์แล้ว: {result}")

    if DRY_RUN:
        print("\n(DRY RUN — ยังไม่ได้ส่งออเดอร์จริง ตั้ง env var DR_BOT_DRY_RUN=false เพื่อยิงจริง)")


if __name__ == "__main__":
    main()
