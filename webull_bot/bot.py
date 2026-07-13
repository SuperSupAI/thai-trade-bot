#!/usr/bin/env python
"""
บอทสแกน US100 ทุกวันหลังตลาดปิด ใช้สัญญาณ Trend+MACD (เข้า) / TP12%+SL15% (ออก)

ความปลอดภัย (สำคัญมาก อ่านก่อนรัน):
  - ค่าเริ่มต้น LIVE_TRADING=false → แค่ "log" ว่าจะซื้อ/ขายอะไร ไม่ส่งคำสั่งจริงเด็ดขาด
  - ต้องตั้ง LIVE_TRADING=true ใน webull_bot/.env ด้วยตัวเองเท่านั้นถึงจะเริ่มส่งคำสั่งจริง
  - WEBULL_ENV=sandbox (ค่าเริ่มต้น) = ต่อ Webull test/UAT environment (th-api.uat.webullbroker.com)
    คนละ endpoint กับเงินจริงเด็ดขาด — ทดสอบตรงนี้ให้มั่นใจก่อนเสมอ (มี shared test account
    ให้ใช้ทันทีใน .env.example ไม่ต้องรอ App Key ตัวเองอนุมัติก็ทดสอบได้)
  - Position sizing + circuit breaker ปรับได้ผ่าน .env: POSITION_SIZE_USD (เงินต่อไม้),
    MAX_OPEN_POSITIONS (ถือพร้อมกันสูงสุด), MAX_NEW_ENTRIES_PER_RUN (กันเปิดไม้รัวถ้ามีบั๊ก)
  - รันวันละครั้งพอ (สัญญาณคำนวณจากราคาปิดรายวัน EOD) ไม่ต้องเปิดเครื่องค้างทั้งวัน
    ใช้ cron / GitHub Action ตั้งเวลาหลังตลาด US ปิด (21:00 น. เวลาไทย ช่วงเวลาปกติ)

State (ตำแหน่งที่ถืออยู่) เก็บไว้ใน webull_bot/state.json — ไฟล์นี้สะท้อนสถานะจริง
ของบัญชีคุณ ไม่ควร commit ขึ้น git (อยู่ใน .gitignore แล้ว)
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ../  (root โปรเจกต์)

from dotenv import load_dotenv
from safe_fetch import safe_download_one
from universe import US_STOCKS

from strategy import entry_signal, should_exit
from webull_client import WebullClient, WebullConfigError

load_dotenv()

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
YEARS_LOOKBACK = 2  # โหลด 2 ปี ให้ EMA200/New-High มีข้อมูล warm-up พอ

# ── Position sizing + circuit breaker (ปรับได้ผ่าน .env) ──
POSITION_SIZE_USD = float(os.environ.get("POSITION_SIZE_USD", "500"))       # เงินต่อไม้ใหม่ (ดอลลาร์)
MAX_OPEN_POSITIONS = int(os.environ.get("MAX_OPEN_POSITIONS", "10"))        # ถือพร้อมกันได้สูงสุดกี่ตัว
MAX_NEW_ENTRIES_PER_RUN = int(os.environ.get("MAX_NEW_ENTRIES_PER_RUN", "3"))  # กันบอทซื้อรัวถ้ามีบั๊ก


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"positions": {}}


def save_state(state: dict):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def run():
    live = os.environ.get("LIVE_TRADING", "false").strip().lower() == "true"
    state = load_state()
    positions = state["positions"]

    client = None
    if live:
        try:
            client = WebullClient()
            print(f"[LIVE MODE] เชื่อมต่อ Webull ({client.env}) สำเร็จ — จะส่งคำสั่งจริง!")
        except WebullConfigError as e:
            print(f"ตั้ง LIVE_TRADING=true ไว้แต่ยังต่อ Webull ไม่ได้: {e}")
            print("ยกเลิกการรันรอบนี้ กัน error ตอนพยายามส่งคำสั่งจริง")
            return
    else:
        print("[DRY RUN] LIVE_TRADING=false — จะ log อย่างเดียว ไม่ส่งคำสั่งซื้อขายจริง")

    print(f"เวลารัน (UTC): {datetime.now(timezone.utc).isoformat()}")
    print(f"สแกน {len(US_STOCKS)} หุ้น...")
    print(f"Position sizing: ${POSITION_SIZE_USD:.0f}/ไม้ · ถือพร้อมกันสูงสุด {MAX_OPEN_POSITIONS} ตัว "
          f"· เปิดไม้ใหม่ได้สูงสุด {MAX_NEW_ENTRIES_PER_RUN} ไม้/รอบ")

    actions = []
    new_entries_this_run = 0
    for sym in US_STOCKS:
        close = safe_download_one(sym, YEARS_LOOKBACK)
        if close is None or len(close) < 260:
            continue
        price_today = float(close.iloc[-1])

        if sym in positions:
            entry_price = positions[sym]["entry_price"]
            exit_now, reason = should_exit(entry_price, price_today)
            if exit_now:
                actions.append(dict(action="SELL", symbol=sym, price=price_today, reason=reason,
                                    pnl_pct=round((price_today / entry_price - 1) * 100, 2)))
                if live and client:
                    client.place_order(sym, "SELL", positions[sym]["qty"])
                del positions[sym]
        else:
            # circuit breaker: หยุดเปิดไม้ใหม่ถ้าถือเต็มโควตา หรือเปิดไปแล้วครบโควตาของรอบนี้
            if len(positions) >= MAX_OPEN_POSITIONS or new_entries_this_run >= MAX_NEW_ENTRIES_PER_RUN:
                continue
            # TODO: ยังไม่กรองหุ้น sideway/choppy ออกก่อนสแกน (ดู README — "ยังไม่กรองหุ้น sideway
            # ออกจาก universe ก่อนสแกน") — สูตรนี้ขาดทุนบนหุ้น sideway ทดสอบแล้ว
            sig = entry_signal(close)
            if bool(sig.iloc[-1]):
                qty = max(1, int(POSITION_SIZE_USD / price_today))  # position sizing แบบเงินคงที่ต่อไม้
                actions.append(dict(action="BUY", symbol=sym, price=price_today, reason="Trend+MACD"))
                if live and client:
                    client.place_order(sym, "BUY", qty)
                positions[sym] = dict(entry_price=price_today, qty=qty,
                                      entry_date=datetime.now(timezone.utc).date().isoformat())
                new_entries_this_run += 1

    if not actions:
        print("วันนี้ไม่มีสัญญาณเข้า/ออก")
    for a in actions:
        tag = "[จะส่งจริง]" if live else "[DRY RUN — ไม่ส่งจริง]"
        print(f"{tag} {a['action']} {a['symbol']} @ {a['price']:.2f} ({a['reason']})"
              + (f" กำไร {a['pnl_pct']:+.1f}%" if "pnl_pct" in a else ""))

    save_state(state)
    print(f"\nถือครองอยู่ตอนนี้: {list(positions.keys()) or 'ไม่มี'}")


if __name__ == "__main__":
    run()
