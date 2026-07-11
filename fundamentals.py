"""
ดึงข้อมูลทางการเงิน (P/E, ROE, D/E, Margins ฯลฯ) จาก yfinance
"""
from typing import Dict, Optional
import streamlit as st
from safe_fetch import safe_fetch_info
from data_cache import get_cached_fundamentals

FETCH_TIMEOUT = 30  # วินาที — yfinance Ticker.info ค้างไม่มีกำหนด/segfault ได้เมื่อ Yahoo ช้า/บล็อก IP/ตอบผิดปกติ
                     # (พบบ่อยบน cloud server) → ดึงแบบแยกโปรเซส (เหมือน safe_download_one) กันทั้งค้างและ segfault ลามแอปหลัก


@st.cache_data(ttl=86400, show_spinner=False)  # cache 1 วัน
def get_fundamentals(symbol: str) -> Optional[Dict]:
    """
    ดึง financial ratios สำหรับหุ้นตัวนึง
    เช็ค data_cache (อัปเดตวันละครั้งผ่าน GitHub Action) ก่อนเสมอ — มีแล้วไม่ต้องยิง yfinance สด
    Return: dict หรือ None หากไม่มีข้อมูล/หมดเวลา/segfault (ไม่ทำให้แอปหลักพังหรือค้าง)
    """
    cached = get_cached_fundamentals(symbol)
    if cached:
        return {'symbol': symbol, **cached}

    info = safe_fetch_info(symbol, timeout=FETCH_TIMEOUT)
    if not info:
        return None

    de_raw = info.get('debtToEquity')  # yfinance คืนเป็น % (เช่น 60.6 แปลว่า D/E=0.606) ไม่ใช่ ratio ตรงๆ
    return {
        'symbol': symbol,
        'pe_ratio': info.get('trailingPE'),
        'roe': info.get('returnOnEquity'),
        'de_ratio': (de_raw / 100) if de_raw is not None else None,
        'gross_margin': info.get('grossMargins'),
        'ebit_margin': info.get('operatingMargins'),
        'eps_growth': info.get('earningsGrowth'),
        'profit_margin': info.get('profitMargins'),
        'price': info.get('currentPrice'),
        'market_cap': info.get('marketCap'),
    }


def passes_fundamental_filter(fundamentals: Dict, criteria: Dict[str, float]) -> bool:
    """
    เช็คว่าหุ้นนี้ผ่านเงื่อนไข fundamental หรือไม่

    criteria example:
    {
        'max_pe': 20,           # P/E < 20
        'min_roe': 0.15,        # ROE > 15%
        'max_de': 1.0,          # D/E < 1
        'min_gross_margin': 0.4,  # Gross Margin > 40%
        'min_ebit_margin': 0.10,   # EBIT Margin > 10%
        'min_eps_growth': 0.10,    # EPS Growth > 10%
    }
    """
    if not fundamentals:
        return True  # ไม่มีข้อมูล ยัง allow

    checks = []

    # P/E Ratio < 20
    if 'max_pe' in criteria and criteria['max_pe']:
        pe = fundamentals.get('pe_ratio')
        if pe is not None and pe > criteria['max_pe']:
            return False
        checks.append(('P/E', pe, '<', criteria['max_pe']))

    # ROE > 15%
    if 'min_roe' in criteria and criteria['min_roe']:
        roe = fundamentals.get('roe')
        if roe is not None and roe < criteria['min_roe']:
            return False
        checks.append(('ROE', roe, '>', criteria['min_roe']))

    # D/E < 1
    if 'max_de' in criteria and criteria['max_de']:
        de = fundamentals.get('de_ratio')
        if de is not None and de > criteria['max_de']:
            return False
        checks.append(('D/E', de, '<', criteria['max_de']))

    # Gross Margin > 40%
    if 'min_gross_margin' in criteria and criteria['min_gross_margin']:
        gm = fundamentals.get('gross_margin')
        if gm is not None and gm < criteria['min_gross_margin']:
            return False
        checks.append(('Gross Margin', gm, '>', criteria['min_gross_margin']))

    # EBIT Margin > 10%
    if 'min_ebit_margin' in criteria and criteria['min_ebit_margin']:
        em = fundamentals.get('ebit_margin')
        if em is not None and em < criteria['min_ebit_margin']:
            return False
        checks.append(('EBIT Margin', em, '>', criteria['min_ebit_margin']))

    # EPS Growth > 10%
    if 'min_eps_growth' in criteria and criteria['min_eps_growth']:
        eg = fundamentals.get('eps_growth')
        if eg is not None and eg < criteria['min_eps_growth']:
            return False
        checks.append(('EPS Growth', eg, '>', criteria['min_eps_growth']))

    return True


def format_ratio(value: Optional[float], fmt: str = ".2%") -> str:
    """Format ratio สำหรับแสดง (เช่น 0.15 -> 15%)"""
    if value is None:
        return "—"
    if fmt == ".2%":
        return f"{value*100:.1f}%"
    elif fmt == ".2f":
        return f"{value:.2f}"
    return str(value)
