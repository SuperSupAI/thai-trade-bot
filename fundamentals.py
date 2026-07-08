"""
ดึงข้อมูลทางการเงิน (P/E, ROE, D/E, Margins ฯลฯ) จาก yfinance
"""
import yfinance as yf
from typing import Dict, Optional
import streamlit as st


@st.cache_data(ttl=86400, show_spinner=False)  # cache 1 วัน
def get_fundamentals(symbol: str) -> Optional[Dict]:
    """
    ดึง financial ratios สำหรับหุ้นตัวนึง
    Return: dict หรือ None หากไม่มีข้อมูล
    """
    try:
        ticker = yf.Ticker(symbol)
        if not ticker.info:
            return None

        info = ticker.info

        # Extract ตัวชี้วัดที่ต้องการ
        return {
            'symbol': symbol,
            'pe_ratio': info.get('trailingPE'),  # P/E Ratio
            'roe': info.get('returnOnEquity'),  # ROE (0.15 = 15%)
            'de_ratio': info.get('debtToEquity'),  # D/E Ratio
            'gross_margin': info.get('grossMargins'),  # Gross Margin (0.4 = 40%)
            'ebit_margin': info.get('operatingMargins'),  # EBIT Margin
            'eps_growth': info.get('earningsGrowth'),  # EPS Growth (0.1 = 10%)
            'profit_margin': info.get('profitMargins'),
            'price': info.get('currentPrice'),
            'market_cap': info.get('marketCap'),
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


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
