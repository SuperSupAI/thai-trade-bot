"""
ดึงข้อมูลทางการเงิน (P/E, ROE, D/E, Margins ฯลฯ) จาก yfinance
"""
import concurrent.futures
import yfinance as yf
from typing import Dict, Optional
import streamlit as st

FETCH_TIMEOUT = 8  # วินาที — yfinance Ticker.info ขึ้นชื่อเรื่องค้างไม่มีกำหนดเมื่อ Yahoo ช้า/บล็อก IP
                    # (พบบ่อยบน cloud server) → บังคับ timeout กันหน้าเว็บค้าง


def _fetch_info(symbol: str) -> Optional[dict]:
    ticker = yf.Ticker(symbol)
    info = ticker.info
    return info if info else None


@st.cache_data(ttl=86400, show_spinner=False)  # cache 1 วัน
def get_fundamentals(symbol: str) -> Optional[Dict]:
    """
    ดึง financial ratios สำหรับหุ้นตัวนึง
    Return: dict หรือ None หากไม่มีข้อมูล/หมดเวลา (ไม่ทำให้แอปค้าง)
    """
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = ex.submit(_fetch_info, symbol)
        info = future.result(timeout=FETCH_TIMEOUT)
        ex.shutdown(wait=False)
        if not info:
            return None

        return {
            'symbol': symbol,
            'pe_ratio': info.get('trailingPE'),
            'roe': info.get('returnOnEquity'),
            'de_ratio': info.get('debtToEquity'),
            'gross_margin': info.get('grossMargins'),
            'ebit_margin': info.get('operatingMargins'),
            'eps_growth': info.get('earningsGrowth'),
            'profit_margin': info.get('profitMargins'),
            'price': info.get('currentPrice'),
            'market_cap': info.get('marketCap'),
        }
    except concurrent.futures.TimeoutError:
        ex.shutdown(wait=False)  # ปล่อย thread ที่ค้างทิ้งไว้เบื้องหลัง ไม่รอมัน (กัน UI ค้าง)
        print(f"Timeout ({FETCH_TIMEOUT}s) fetching {symbol} — ข้ามไป ไม่ให้แอปค้าง")
        return None
    except Exception as e:
        ex.shutdown(wait=False)
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
