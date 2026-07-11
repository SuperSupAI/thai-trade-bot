"""
Client เชื่อมต่อ Webull OpenAPI (Thailand) — https://developer.webull.co.th/apis/docs/

ทุก request ต้องเซ็นด้วย HMAC-SHA256 จาก App Secret ตามที่เอกสารกำหนด:
  - x-app-key, x-timestamp, x-signature, x-signature-algorithm,
    x-signature-version, x-signature-nonce, x-version, x-access-token

หมายเหตุความปลอดภัย: ไฟล์นี้ไม่มีค่า API key/secret จริงฝังอยู่เลย — อ่านจาก
environment variables (.env ที่ผู้ใช้สร้างเอง, ไม่ถูก commit ขึ้น git) เท่านั้น
"""
import base64
import hashlib
import hmac
import os
import time
import uuid

import requests
from dotenv import load_dotenv

load_dotenv()

SANDBOX_BASE_URL = "https://api.sandbox.webull.co.th"   # โหมดทดสอบ (เงินปลอม) — ใช้ก่อนเสมอ
PRODUCTION_BASE_URL = "https://api.webull.co.th"         # เงินจริง — ใช้เมื่อพร้อมจริงๆ เท่านั้น


class WebullConfigError(Exception):
    """ยังไม่ได้ตั้งค่า .env ให้ครบ (APP_KEY/APP_SECRET)"""


class WebullClient:
    def __init__(self):
        self.app_key = os.environ.get("WEBULL_APP_KEY")
        self.app_secret = os.environ.get("WEBULL_APP_SECRET")
        env = os.environ.get("WEBULL_ENV", "sandbox").strip().lower()
        if not self.app_key or not self.app_secret or "your_app" in self.app_key:
            raise WebullConfigError(
                "ยังไม่ได้ตั้งค่า WEBULL_APP_KEY / WEBULL_APP_SECRET ใน webull_bot/.env "
                "(คัดลอกจาก .env.example แล้วใส่ค่าจริงจาก Webull OpenAPI Management)"
            )
        self.base_url = SANDBOX_BASE_URL if env == "sandbox" else PRODUCTION_BASE_URL
        self.env = env
        self.access_token = None  # ได้จากขั้นตอน 2FA ครั้งแรก (ยังไม่ implement ในไฟล์นี้)

    def _sign(self, body: str, timestamp: str, nonce: str) -> str:
        """HMAC-SHA256 ตามสเปกของ Webull OpenAPI"""
        payload = f"{self.app_key}{timestamp}{nonce}{body}".encode("utf-8")
        digest = hmac.new(self.app_secret.encode("utf-8"), payload, hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _headers(self, body: str = "") -> dict:
        timestamp = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex
        headers = {
            "x-app-key": self.app_key,
            "x-timestamp": timestamp,
            "x-signature-nonce": nonce,
            "x-signature": self._sign(body, timestamp, nonce),
            "x-signature-algorithm": "HmacSHA256",
            "x-signature-version": "1.0",
            "x-version": "v2",
            "Content-Type": "application/json",
        }
        if self.access_token:
            headers["x-access-token"] = self.access_token
        return headers

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        import json
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        resp = requests.request(
            method, f"{self.base_url}{path}",
            headers=self._headers(body_str),
            data=body_str if body else None,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # ── ตัวอย่าง endpoint พื้นฐาน (ปรับ path ตามเอกสารจริงตอนสมัคร API key แล้ว) ──
    def get_account(self) -> dict:
        return self.request("GET", "/account/v1/summary")

    def place_order(self, symbol: str, side: str, qty: int, order_type: str = "MARKET") -> dict:
        """side: 'BUY' หรือ 'SELL' — เรียกเฉพาะตอน LIVE_TRADING=true เท่านั้น (เช็คใน bot.py ไม่ใช่ที่นี่)"""
        return self.request("POST", "/trade/v1/order/place", {
            "symbol": symbol, "side": side, "quantity": qty, "orderType": order_type,
        })
