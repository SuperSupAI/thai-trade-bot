# Webull Trading Bot (US100, EMA Stack + Quick TP5%/SL10%)

บอทสแกนหุ้น US100 ทุกวันหลังตลาดปิด ใช้สูตรที่ทดสอบแล้วใน `test_winrate_60_search.py`
(win rate 60-80% แบบ train/valid/test — แต่ผลตอบแทนรวมต่ำกว่า Buy & Hold ธรรมดา อ่าน
คำเตือนในแชทก่อนใช้เงินจริง)

## ตั้งค่าก่อนใช้ (ทำเองทุกขั้นตอน — บอทจะไม่ขอ/กรอกรหัสให้เอง)

1. สมัคร API ที่ https://www.webull.co.th/open-api-management/application (รอผลอนุมัติ 1-3 วันทำการ
   — ระหว่างรอ ข้ามไปข้อ 2-4 แล้วใช้ **shared test account** ที่ให้ไว้ใน `.env.example` ทดลองรันบอทได้เลย)
2. ได้ App Key + App Secret มาแล้ว copy `.env.example` เป็น `.env`:
   ```
   cp .env.example .env
   ```
3. เปิด `.env` แล้วกรอกค่าจริงเอง — **ห้ามส่งไฟล์นี้ให้ใครหรือ commit ขึ้น git เด็ดขาด**
4. ติดตั้ง dependencies (รวม SDK ทางการของ Webull):
   ```
   pip install -r requirements.txt
   ```
5. รอบแรกที่บอทเรียก API (ตอน live) ต้องยืนยัน **2FA ผ่านแอป Webull** ครั้งเดียว — SDK จัดการ flow
   นี้ให้อัตโนมัติ แล้วเก็บ token ไว้ที่ `webull_bot/conf/token.txt` (ใช้ซ้ำได้โดยไม่ต้องยืนยันใหม่ทุกรอบ)

## รันแบบทดสอบก่อนเสมอ (ค่าเริ่มต้นปลอดภัยอยู่แล้ว)

ค่าเริ่มต้นใน `.env.example`:
- `WEBULL_ENV=sandbox` — ต่อ Webull test/UAT environment จริง (`th-api.uat.webullbroker.com`)
  คนละ endpoint กับเงินจริงเด็ดขาด
- `LIVE_TRADING=false` — แค่ log ว่าจะเทรดอะไร ไม่ส่งคำสั่งจริง

```
python bot.py
```

จะเห็น log แบบ `[DRY RUN — ไม่ส่งจริง] BUY AAPL @ 123.45 (EMA Stack+NewHigh)` — ยังไม่มีอะไรเกิดขึ้นจริง

## เมื่อพร้อมจริงๆ แล้วเท่านั้น

1. ทดสอบด้วย `WEBULL_ENV=sandbox` + `LIVE_TRADING=true` ก่อน (ยิง order จริงผ่าน test/UAT environment
   — ใช้ shared test account ก็ได้ ไม่กระทบเงินจริงแน่นอนเพราะคนละ endpoint กับ production)
2. ตรวจสอบผลลัพธ์ให้แน่ใจว่าทำงานถูกต้องหลายรอบ (เช็ค log + `state.json`)
3. ค่อยเปลี่ยน `WEBULL_ENV=production` พร้อมใส่ App Key/Secret ของตัวเอง (ไม่ใช่ shared test account
   แล้ว) — **นี่คือเงินจริง** ทำความเข้าใจความเสี่ยงให้ครบก่อน

## รันอัตโนมัติทุกวัน

ไม่ต้องเปิดคอมค้างทั้งวัน — ตั้ง cron (Linux/Mac) หรือ Task Scheduler (Windows) หรือ GitHub
Action ให้รัน `python bot.py` วันละครั้งหลังตลาด US ปิด (~21:00 น. เวลาไทย ช่วงเวลาปกติ,
เปลี่ยนเป็น 20:00 ช่วง daylight saving)

## สถานะปัจจุบัน (อัปเดตหลังตรวจกับเอกสารทางการแล้ว)

- ✅ `webull_client.py` เปลี่ยนไปใช้ **SDK ทางการของ Webull** (`webull-openapi-python-sdk`)
  แทนการเขียน HTTP + HMAC signing เอง — endpoint (`api.webull.co.th` / `th-api.uat.webullbroker.com`),
  method (`account_v2.get_account_list/get_account_balance`, `order_v3.preview_order/place_order`
  ฯลฯ) และ field ของ order (`combo_type`, `entrust_type`, `time_in_force` ฯลฯ) ตรวจกับ
  https://developer.webull.co.th/apis/docs/ แล้ว **และทดสอบยิงจริงกับ shared test account สำเร็จ**:
  `get_account_list()` / `get_account_balance()` / `order_v3.preview_order()` ทำงานถูกต้องทั้งหมด
  (แก้บั๊กที่เจอระหว่างทดสอบไปแล้ว 1 จุด: `get_account_list()` คืน bare JSON array ไม่ได้ห่อด้วย
  `{"accounts": [...]}` แบบที่เดาไว้แต่แรก)
- ✅ 2FA login ครั้งแรก — SDK จัดการให้อัตโนมัติ ไม่ต้อง implement เอง (ดูขั้นตอนด้านบน) — ยืนยันแล้วว่า
  shared test account ไม่ต้องผ่าน 2FA ก็เรียก API ได้เลย (`_check_token_enable result is False`)
- ✅ Position sizing ปรับเป็นคำนวณจาก `POSITION_SIZE_USD` (เงินคงที่ต่อไม้) แทน fix 1 หุ้น —
  ปรับได้ใน `.env`
- ✅ Circuit breaker: `MAX_OPEN_POSITIONS` (ถือพร้อมกันสูงสุด) + `MAX_NEW_ENTRIES_PER_RUN`
  (เปิดไม้ใหม่ได้สูงสุดต่อรอบ) กันบอทเทรดผิดพลาดรัว

## ข้อจำกัดที่ยังไม่ได้ทำ (TODO ถ้าจะใช้จริง)

- `place_order()` **ยังไม่เคยทดสอบยิงจริง** (ตั้งใจไม่ยิง แม้กับ shared test account เพราะเป็น
  บัญชีสาธารณะที่คนอื่นใช้ทดสอบร่วมกัน ไม่อยากสร้าง order ค้างไว้ในนั้น) — `preview_order()`
  ที่ใช้ order schema เดียวกันทดสอบผ่านแล้ว จึงมั่นใจได้ระดับหนึ่งว่า field ถูกต้อง แต่ควรลอง
  `place_order()` จริงอย่างน้อย 1 ครั้งด้วย App Key ของตัวเอง (ไม่ใช่ shared account) ก่อนใช้จริง
- Position sizing แบบเงินคงที่ต่อไม้ (`POSITION_SIZE_USD`) ยังไม่ได้คำนวณตาม buying power จริง
  ของบัญชี (มี `WebullClient.get_buying_power()` ให้แล้ว แต่ `bot.py` ยังไม่ได้เอามาคำนวณ % ของ
  ทุนจริง — ตอนนี้เป็นแค่ fixed dollar amount)
- ยังไม่มี stop-trading / alert อัตโนมัติถ้า drawdown รวมเกินเกณฑ์ที่รับได้
