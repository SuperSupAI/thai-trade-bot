"""
Client เชื่อมต่อ Webull OpenAPI (Thailand) ผ่าน SDK ทางการ (webull-openapi-python-sdk)
https://github.com/webull-inc/webull-openapi-python-sdk

ใช้ SDK ทางการแทนการเขียน HTTP request + HMAC signing เอง เพราะ:
  - SDK จัดการ signing (HMAC-SHA1 ตามสเปกจริงจาก docs — ไม่ใช่ SHA256 ที่เคยเดาไว้ผิด) ให้อัตโนมัติ
  - SDK จัดการขั้นตอน 2FA ครั้งแรก (ต้องยืนยันผ่านแอป Webull) + เก็บ token ให้เอง
    (ค่า default เก็บที่ webull_bot/conf/token.txt — ปรับ path ได้ด้วย WEBULL_TOKEN_DIR)

Environment (สำคัญ — "sandbox" ในที่นี่คือ Webull UAT/test environment จริงๆ ไม่ใช่คำที่ Webull
ใช้เอง แต่ทำหน้าที่เดียวกัน — endpoint คนละตัวกับ production เห็นชัดว่าไม่ใช่เงินจริงแน่นอน):
  - sandbox/test  → th-api.uat.webullbroker.com  (มี "shared test accounts" สาธารณะให้ใช้ทดสอบ
                     ได้ทันทีโดยไม่ต้องรออนุมัติ App Key ของตัวเอง — ดู .env.example)
  - production    → api.webull.co.th             (เงินจริง — ใช้เมื่อพร้อมจริงๆ เท่านั้น)

หมายเหตุความปลอดภัย: ไฟล์นี้ไม่มีค่า API key/secret จริงฝังอยู่เลย — อ่านจาก
environment variables (.env ที่ผู้ใช้สร้างเอง, ไม่ถูก commit ขึ้น git) เท่านั้น
"""
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

REGION_ID = "th"
TEST_ENDPOINT = "th-api.uat.webullbroker.com"
PRODUCTION_ENDPOINT = "api.webull.co.th"


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
                "(คัดลอกจาก .env.example แล้วใส่ค่าจริงจาก Webull OpenAPI Management "
                "หรือใช้ shared test account ที่ให้ไว้ใน .env.example เพื่อทดสอบก่อนได้)"
            )
        self.env = env
        self.endpoint = TEST_ENDPOINT if env == "sandbox" else PRODUCTION_ENDPOINT

        # import ตอน init เท่านั้น (ไม่ import ตอน module load) กันพังทั้งไฟล์ถ้ายังไม่ได้ pip install SDK
        from webull.core.client import ApiClient
        from webull.trade.trade_client import TradeClient

        token_dir = os.environ.get("WEBULL_TOKEN_DIR")
        api_client = ApiClient(self.app_key, self.app_secret, REGION_ID)
        api_client.add_endpoint(REGION_ID, self.endpoint)
        if token_dir:
            api_client.set_token_dir(token_dir)

        self._trade = TradeClient(api_client)
        self._account_id = os.environ.get("WEBULL_ACCOUNT_ID") or None

    def get_account_id(self) -> str:
        """ดึง account_id อัตโนมัติจาก account list ถ้ายังไม่ได้ระบุ WEBULL_ACCOUNT_ID ไว้เอง
        (รอบแรกที่เรียกจะเป็นจังหวะที่ต้องยืนยัน 2FA ผ่านแอป Webull ถ้ายังไม่เคยทำ)"""
        if self._account_id:
            return self._account_id
        res = self._trade.account_v2.get_account_list()
        res.raise_for_status()
        body = res.json()
        # get_account_list() คืน bare JSON array ของ account objects ตรงๆ (ยืนยันด้วยการยิงจริง
        # กับ shared test account) — ไม่ได้ห่อด้วย {"accounts": [...]} หรือ {"data": [...]} แบบที่เดาไว้แต่แรก
        accounts = body if isinstance(body, list) else (body.get("accounts") or body.get("data") or [])
        if not accounts:
            raise WebullConfigError("get_account_list() ไม่คืน account ใดเลย — เช็ค App Key/Secret ให้ตรงกับ env นี้")
        self._account_id = accounts[0]["account_id"]
        return self._account_id

    def get_balance(self) -> dict:
        res = self._trade.account_v2.get_account_balance(self.get_account_id())
        res.raise_for_status()
        return res.json()

    def get_buying_power(self, currency: str = "USD") -> float | None:
        """ดึง buying power (USD) จากบัญชี — คืน None ถ้าดึงไม่ได้ (ให้ผู้เรียก fallback เอง)"""
        try:
            data = self.get_balance()
            for asset in data.get("account_currency_assets", []):
                if asset.get("currency") == currency:
                    return float(asset["buying_power"])
        except Exception:
            return None
        return None

    def preview_order(self, symbol: str, side: str, qty: int) -> dict:
        """เช็คก่อนว่า order นี้ยิงได้จริงไหม (buying power พอ, symbol ถูกต้อง ฯลฯ) โดยไม่ส่งจริง
        ทดสอบยิงจริงกับ shared test account แล้ว: order_v3.preview_order(...) ทำงานถูกต้อง
        (คืน estimated_cost/estimated_transaction_fee) — เก็บ fallback ไป order_v2 ไว้เผื่อ SDK
        เวอร์ชันอื่นไม่มี preview_order ใน v3"""
        order = self._build_market_order(symbol, side, qty)
        order_client = self._trade.order_v3 if hasattr(self._trade.order_v3, "preview_order") else self._trade.order_v2
        res = order_client.preview_order(self.get_account_id(), [order])
        res.raise_for_status()
        return res.json()

    def place_order(self, symbol: str, side: str, qty: int) -> dict:
        """side: 'BUY' หรือ 'SELL' — เรียกเฉพาะตอน LIVE_TRADING=true เท่านั้น (เช็คใน bot.py ไม่ใช่ที่นี่)"""
        order = self._build_market_order(symbol, side, qty)
        res = self._trade.order_v3.place_order(self.get_account_id(), [order])
        res.raise_for_status()
        return res.json()

    @staticmethod
    def _build_market_order(symbol: str, side: str, qty: int) -> dict:
        return {
            "combo_type": "NORMAL",
            "client_order_id": uuid.uuid4().hex,
            "symbol": symbol,
            "instrument_type": "EQUITY",
            "market": "US",
            "order_type": "MARKET",
            "entrust_type": "QTY",
            "quantity": str(qty),
            "support_trading_session": "CORE",
            "side": side,
            "time_in_force": "DAY",
        }
