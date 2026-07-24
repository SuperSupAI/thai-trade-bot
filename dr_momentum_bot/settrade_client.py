#!/usr/bin/env python
"""
Wrapper บาง ๆ รอบ settrade_v2 SDK (pip install settrade-v2) -- อ่าน credential จาก environment
variable เท่านั้น ห้าม hardcode ในโค้ด (เหมือนหลักการที่ webull_bot/conf/ ใช้อยู่แล้วในโปรเจกต์นี้)

ต้องตั้ง env vars ก่อนรัน (ตัวอย่าง PowerShell):
    $env:SETTRADE_APP_ID = "..."
    $env:SETTRADE_APP_SECRET = "..."
    $env:SETTRADE_APP_CODE = "..."
    $env:SETTRADE_BROKER_ID = "SANDBOX"      # ตอนเทส ใช้ "SANDBOX" เสมอ (ไม่ต้องมีบัญชีโบรกจริง)
    $env:SETTRADE_ACCOUNT_NO = "..."         # เลขบัญชี (Sandbox มีเลขบัญชีจำลองให้ในเอกสาร)
    $env:SETTRADE_PIN = "..."                # PIN เทรด (จำเป็นตอน place_order จริง)

สมัครขอ app_id/app_secret ได้ฟรีที่ https://developer.settrade.com/open-api/ (ไม่ต้องมีบัญชีโบรกจริง
สำหรับโหมด SANDBOX)
"""
import os

from dotenv import load_dotenv
from settrade_v2 import Investor

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_investor(is_auto_queue: bool = False) -> Investor:
    app_id = os.environ["SETTRADE_APP_ID"]
    app_secret = os.environ["SETTRADE_APP_SECRET"]
    app_code = os.environ["SETTRADE_APP_CODE"]
    broker_id = os.environ.get("SETTRADE_BROKER_ID", "SANDBOX")
    return Investor(
        app_id=app_id,
        app_secret=app_secret,
        app_code=app_code,
        broker_id=broker_id,
        is_auto_queue=is_auto_queue,
    )


def get_equity_account(investor: Investor = None):
    """รับ investor ที่ล็อกอินไว้แล้วมาใช้ต่อได้ (investor=None คือสร้างใหม่ -- ใช้ตอนเรียกแบบ standalone)
    สำคัญ: ถ้าต้องใช้ทั้ง Equity() และ MarketData() ในสคริปต์เดียวกัน ต้องสร้าง investor ตัวเดียวแล้วส่งเข้ามา
    ทั้งคู่ ห้ามสร้าง Investor(...) แยกกันคนละตัว เพราะแต่ละตัวล็อกอินเซสชันของตัวเองอิสระต่อกัน เจอบั๊กจริง
    ที่ Settrade Sandbox: สร้าง 2 เซสชันติดกันแล้วอีกฝั่งเจอ "Login required"/"Service is not ready yet"
    เพราะเซสชันชนกัน"""
    investor = investor or get_investor()
    account_no = os.environ["SETTRADE_ACCOUNT_NO"]
    return investor.Equity(account_no=account_no)


def place_buy_order(equity, symbol: str, volume: int, price: float, price_type: str = "Limit"):
    """ส่งคำสั่งซื้อ -- price_type='MP' คือ market price ถ้าไม่อยากล็อกราคา"""
    pin = os.environ["SETTRADE_PIN"]
    return equity.place_order(
        pin=pin,
        side="Buy",
        symbol=symbol,
        volume=volume,
        price=price,
        price_type=price_type,
        validity_type="Day",
    )


def place_sell_order(equity, symbol: str, volume: int, price: float, price_type: str = "Limit"):
    pin = os.environ["SETTRADE_PIN"]
    return equity.place_order(
        pin=pin,
        side="Sell",
        symbol=symbol,
        volume=volume,
        price=price,
        price_type=price_type,
        validity_type="Day",
    )
