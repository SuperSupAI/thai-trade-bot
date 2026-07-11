"""
ตรรกะสัญญาณเข้า/ออก — คัดลอกมาจากผลทดสอบใน test_winrate_60_search.py ของโปรเจกต์หลัก
(EMA Stack + New High เข้า / Quick TP5%+SL10% ออก — combo ที่ดีที่สุดจาก train/valid/test
บนหุ้น US: train WR 79.0%, valid WR 80.6%, test WR 71.2%)

แยกเป็นไฟล์ standalone ไม่พึ่ง Streamlit (ต่างจาก app.py) เพราะบอทนี้รันเป็น background job
ไม่ใช่ web app — import app.py ตรงๆ ไม่ได้เพราะจะรัน st.set_page_config() ทันทีตอน import
"""
import pandas as pd


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def entry_signal(close: pd.Series, breakout_days: int = 252) -> pd.Series:
    """True วันที่หุ้นเรียง EMA ขั้นบันไดครบ (5>10>30>50>100>200) และทำ New High รอบ 1 ปี"""
    e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
    yr_high = close.rolling(breakout_days, min_periods=60).max()
    stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
    broke = close >= yr_high
    return (stack & broke).fillna(False)


def should_exit(entry_price: float, current_price: float, tp: float = 0.05, sl: float = 0.10) -> tuple[bool, str | None]:
    """Quick TP5%+SL10% — ไม่มีเงื่อนไข EMA เลย"""
    chg = current_price / entry_price - 1
    if chg <= -sl:
        return True, f"SL {-sl*100:.0f}%"
    if chg >= tp:
        return True, f"TP +{tp*100:.0f}%"
    return False, None
