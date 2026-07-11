# Webull Trading Bot (US100, EMA Stack + Quick TP5%/SL10%)

บอทสแกนหุ้น US100 ทุกวันหลังตลาดปิด ใช้สูตรที่ทดสอบแล้วใน `test_winrate_60_search.py`
(win rate 60-80% แบบ train/valid/test — แต่ผลตอบแทนรวมต่ำกว่า Buy & Hold ธรรมดา อ่าน
คำเตือนในแชทก่อนใช้เงินจริง)

## ตั้งค่าก่อนใช้ (ทำเองทุกขั้นตอน — บอทจะไม่ขอ/กรอกรหัสให้เอง)

1. สมัคร API ที่ https://www.webull.co.th/open-api-management/application
2. ได้ App Key + App Secret มาแล้ว copy `.env.example` เป็น `.env`:
   ```
   cp .env.example .env
   ```
3. เปิด `.env` แล้วกรอกค่าจริงเอง — **ห้ามส่งไฟล์นี้ให้ใครหรือ commit ขึ้น git เด็ดขาด**
4. ติดตั้ง dependencies:
   ```
   pip install -r requirements.txt
   ```

## รันแบบทดสอบก่อนเสมอ (ค่าเริ่มต้นปลอดภัยอยู่แล้ว)

ค่าเริ่มต้นใน `.env.example`:
- `WEBULL_ENV=sandbox` — โหมดทดสอบ เงินปลอม
- `LIVE_TRADING=false` — แค่ log ว่าจะเทรดอะไร ไม่ส่งคำสั่งจริง

```
python bot.py
```

จะเห็น log แบบ `[DRY RUN — ไม่ส่งจริง] BUY AAPL @ 123.45 (EMA Stack+NewHigh)` — ยังไม่มีอะไรเกิดขึ้นจริง

## เมื่อพร้อมจริงๆ แล้วเท่านั้น

1. ทดสอบด้วย `WEBULL_ENV=sandbox` + `LIVE_TRADING=true` ก่อน (ยังเป็นเงินปลอมแต่ยิง order จริงผ่าน sandbox API)
2. ตรวจสอบผลลัพธ์ในบัญชี sandbox ให้แน่ใจว่าทำงานถูกต้องหลายรอบ
3. ค่อยเปลี่ยน `WEBULL_ENV=production` — **นี่คือเงินจริง** ทำความเข้าใจความเสี่ยงให้ครบก่อน

## รันอัตโนมัติทุกวัน

ไม่ต้องเปิดคอมค้างทั้งวัน — ตั้ง cron (Linux/Mac) หรือ Task Scheduler (Windows) หรือ GitHub
Action ให้รัน `python bot.py` วันละครั้งหลังตลาด US ปิด (~21:00 น. เวลาไทย ช่วงเวลาปกติ,
เปลี่ยนเป็น 20:00 ช่วง daylight saving)

## ข้อจำกัดที่ยังไม่ได้ทำ (TODO ถ้าจะใช้จริง)

- `webull_client.py` เป็นโครงร่างเบื้องต้น — endpoint path (`/account/v1/summary`,
  `/trade/v1/order/place`) เป็นตัวอย่างจากโครงสร้าง REST ทั่วไป **ยังไม่ได้ตรวจกับเอกสารจริง
  ทีละ endpoint** ต้องเทียบกับ https://developer.webull.co.th/apis/docs/ ให้ตรงก่อนใช้จริง
- ยังไม่มีขั้นตอน 2FA login ครั้งแรกที่ได้ access token มา (เอกสารบอกว่าจำเป็น) — ต้อง
  implement เพิ่มตาม flow ที่เอกสาร authentication ระบุ
- Position sizing ตอนนี้ fix ที่ 1 หุ้นต่อไม้ ควรปรับเป็นคำนวณจากเงินทุน/ความเสี่ยงจริง
- ยังไม่มีการจำกัดจำนวนไม้สูงสุดต่อวันหรือ circuit breaker กันบอทเทรดผิดพลาดรัว
