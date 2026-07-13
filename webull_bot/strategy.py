"""
ตรรกะสัญญาณเข้า/ออก — คัดลอกมาจากผลทดสอบใน test_exit_optimization.py / test_exit_optimization_crashcheck.py
ของโปรเจกต์หลัก (Trend+MACD เข้า / TP12%+SL15% ออก, ถือพร้อมกัน 10 ไม้)

ทำไมเปลี่ยนจากสูตรเดิม (EMA Stack+NewHigh / TP5%+SL10%): grid search 690 คอมโบ (3 entry × 46 exit ×
5 ระดับจำนวนไม้) บน train/test แยกปี พบว่าสูตรเดิมอยู่อันดับ 279/690 เท่านั้น (train ret +3.9%)
ส่วนสูตรนี้ (Trend+MACD + TP12/SL15 + 10 ไม้) แม้ไม่ใช่อันดับ 1 บนตลาดขาขึ้น แต่เป็น**สูตรเดียว
ในกลุ่มที่ทดสอบที่ยังกำไรได้จริงในตลาดหมี 2022** (Fed hiking, B&H -16.0%) — ได้ +4.7% ขณะสูตร
"ผู้ชนะ" อันดับ 1 เดิม (trailing EMA100 ไม่มี SL ตายตัว) กลับขาดทุน -8.0% เพราะไม่มีเพดานจำกัด
ความเสียหายตอนตลาดไหลลงต่อเนื่องไม่มีจังหวะเด้งกลับ

ผลทดสอบสรุป (5 หน้าต่างเวลา ปี 2020-2026, 76 หุ้น US, ทุน 100,000 บาท แบ่ง 10 ไม้):
  2020 COVID (B&H +34.3%):        +1.8%   2022 Fed hiking (B&H -16.0%): +4.7%
  2023-24 (B&H +15.3%):          +12.3%   2024-25 (B&H +5.1%):          +11.9%
  2025-26 (B&H +21.4%):          +13.6%
  → win rate 57-85% ทุกช่วง (สูงกว่าสูตร trailing มาก) · ยังไม่เคยชนะ B&H ตอนตลาดขาขึ้นแรง
    แต่เป็นสูตรเดียวที่ไม่เจ๊งตอนตลาดขาลง — เลือกเพราะ "ไม่หายนะ" ไม่ใช่เพราะ "กำไรสูงสุด"

แยกเป็นไฟล์ standalone ไม่พึ่ง Streamlit (ต่างจาก app.py) เพราะบอทนี้รันเป็น background job
ไม่ใช่ web app — import app.py ตรงๆ ไม่ได้เพราะจะรัน st.set_page_config() ทันทีตอน import
"""
import pandas as pd


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def entry_signal(close: pd.Series) -> pd.Series:
    """True วันที่ Close>EMA200 · EMA10>EMA50 · EMA50>EMA200 · MACD>0 (Trend+MACD)"""
    e10, e50, e200 = (ema(close, n) for n in (10, 50, 200))
    macd = ema(close, 12) - ema(close, 26)
    cond = (close > e200) & (e10 > e50) & (e50 > e200) & (macd > 0)
    return cond.fillna(False)


def should_exit(entry_price: float, current_price: float, tp: float = 0.12, sl: float = 0.15) -> tuple[bool, str | None]:
    """TP12%+SL15% — SL ตายตัว จำกัดความเสียหายได้จริงตอนตลาดขาลง (ต่างจาก trailing ที่ไม่มีเพดาน)"""
    chg = current_price / entry_price - 1
    if chg <= -sl:
        return True, f"SL {-sl*100:.0f}%"
    if chg >= tp:
        return True, f"TP +{tp*100:.0f}%"
    return False, None
