#!/usr/bin/env python
"""
บอทสแกน US100 ทุกวันหลังตลาดปิด ใช้สัญญาณ EMA Stack+NewHigh (เข้า) / Quick TP5%+SL10% (ออก)

ความปลอดภัย (สำคัญมาก อ่านก่อนรัน):
  - ค่าเริ่มต้น LIVE_TRADING=false → แค่ "log" ว่าจะซื้อ/ขายอะไร ไม่ส่งคำสั่งจริงเด็ดขาด
  - ต้องตั้ง LIVE_TRADING=true ใน webull_bot/.env ด้วยตัวเองเท่านั้นถึงจะเริ่มส่งคำสั่งจริง
  - WEBULL_ENV=sandbox (ค่าเริ่มต้น) = เงินปลอม ไม่กระทบเงินจริง — ทดสอบตรงนี้ให้มั่นใจก่อนเสมอ
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

    actions = []
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
            sig = entry_signal(close)
            if bool(sig.iloc[-1]):
                qty = 1  # ปรับ position sizing เองตามเงินทุน/ความเสี่ยงที่รับได้
                actions.append(dict(action="BUY", symbol=sym, price=price_today, reason="EMA Stack+NewHigh"))
                if live and client:
                    client.place_order(sym, "BUY", qty)
                positions[sym] = dict(entry_price=price_today, qty=qty,
                                      entry_date=datetime.now(timezone.utc).date().isoformat())

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
