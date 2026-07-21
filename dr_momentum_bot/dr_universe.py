#!/usr/bin/env python
"""
Universe 47 ตัวที่ backtest ไว้ (test_dr_universe_expanded_comparison.py) + ตาราง mapping
"underlying ticker (yfinance)" -> "รหัส DR จริงบน SET" ที่ใช้ตอนส่งออเดอร์จริง

**สำคัญ**: ranking momentum ใช้ราคาหุ้นแม่ (yfinance) เหมือนที่ backtest ทั้งเซสชันทำมาตลอด เพราะ DR
ราคาผูกกับหุ้นแม่ตามอัตราส่วนคงที่อยู่แล้ว (ผลตอบแทน % ควรใกล้เคียงกันมาก) แต่ตอน**ส่งออเดอร์จริงต้องใช้
รหัส DR** (เช่น NVDA80 ไม่ใช่ NVDA) — mapping ด้านล่างเช็คจากบทความ/ประกาศ ก.ค. 2026 (Finnomena, Yuanta)
**ไม่ใช่ข้อมูลทางการจาก SET โดยตรง** ตัวที่ confidence="unconfirmed" ต้องเช็คซ้ำที่
https://www.set.or.th/th/market/product/dr/marketdata ก่อนเปิดโหมดส่งออเดอร์จริงทุกตัว
"""

DR_COVERED_EXPANDED = [
    "AAPL", "MSFT", "JPM", "V", "UNH", "KO", "CSCO", "CRM", "GS", "JNJ",
    "DIS", "NKE", "GOOGL", "AMZN", "META", "NVDA", "PFE", "COST", "PEP", "ADBE", "LULU",
    "ABBV", "AMD", "AVGO", "BAC", "BDX", "BKNG", "BRK-B", "EL", "ISRG", "LLY",
    "MA", "MELI", "MU", "MNST", "MS", "NDAQ", "NFLX", "ORCL", "PANW", "PLTR",
    "RBLX", "SBUX", "SNOW", "SPOT", "TSLA", "UBER",
]

# ticker (yfinance) -> (รหัส DR ที่จะใช้ส่งออเดอร์จริง, confidence)
# confidence="confirmed": เจอชื่อชัดเจนจาก Finnomena/Yuanta ก.ค. 2026
# confidence="unconfirmed": เดาจาก pattern (ยังไม่เจอชื่อจริง) -- ห้ามใช้ส่งออเดอร์จริงจนกว่าจะเช็ค SET เอง
DR_SYMBOL_MAP = {
    "AAPL":  ("AAPL01", "confirmed"),
    "MSFT":  ("MSFT01", "confirmed"),
    "JPM":   ("JPMUS19", "confirmed"),
    "V":     ("VISA80", "confirmed"),
    "UNH":   ("UNH19", "confirmed"),
    "KO":    ("KO80", "confirmed"),
    "CSCO":  ("CSCO06", "confirmed"),
    "CRM":   ("CRM01", "confirmed"),
    "GS":    (None, "unconfirmed"),   # ไม่เจอในลิสต์ ก.ค. 2026 -- อาจไม่มี DR แล้ว ต้องเช็ค
    "JNJ":   ("JNJ03", "confirmed"),
    "DIS":   (None, "unconfirmed"),   # ไม่เจอในลิสต์ ก.ค. 2026 -- อาจไม่มี DR แล้ว ต้องเช็ค
    "NKE":   ("NIKE80", "confirmed"),
    "GOOGL": ("GOOGL01", "confirmed"),
    "AMZN":  ("AMZN01", "confirmed"),
    "META":  ("META01", "confirmed"),
    "NVDA":  ("NVDA80", "confirmed"),
    "PFE":   ("PFIZER19", "confirmed"),
    "COST":  ("COSTCO19", "confirmed"),
    "PEP":   ("PEP80", "confirmed"),
    "ADBE":  ("ADBE03", "confirmed"),
    "LULU":  (None, "unconfirmed"),   # ไม่เจอในลิสต์ ก.ค. 2026 -- อาจไม่มี DR แล้ว ต้องเช็ค
    "ABBV":  ("ABBV19", "confirmed"),
    "AMD":   ("AMD80", "confirmed"),
    "AVGO":  ("AVGO80", "confirmed"),
    "BAC":   ("BAC03", "confirmed"),
    "BDX":   ("BDX06", "confirmed"),
    "BKNG":  ("BKNG80", "confirmed"),
    "BRK-B": ("BRKB80", "confirmed"),
    "EL":    ("ESTEE80", "confirmed"),
    "ISRG":  ("ISRG01", "confirmed"),
    "LLY":   ("LLY80", "confirmed"),
    "MA":    ("MA80", "confirmed"),
    "MELI":  ("MELI06", "confirmed"),
    "MU":    ("MICRON01", "confirmed"),
    "MNST":  ("MNST06", "confirmed"),
    "MS":    ("MS06", "confirmed"),
    "NDAQ":  ("NDAQ06", "confirmed"),
    "NFLX":  ("NFLX80", "confirmed"),
    "ORCL":  ("ORCL01", "confirmed"),
    "PANW":  ("PANW80", "confirmed"),
    "PLTR":  ("PLTR01", "confirmed"),
    "RBLX":  ("RBLX06", "confirmed"),
    "SBUX":  ("SBUX80", "confirmed"),
    "SNOW":  ("SNOW06", "confirmed"),
    "SPOT":  ("SPOT06", "confirmed"),
    "TSLA":  ("TSLA80", "confirmed"),
    "UBER":  ("UBER06", "confirmed"),
}


def get_dr_symbol(underlying_ticker: str):
    """คืน (รหัส DR, confidence) หรือ (None, 'missing') ถ้าไม่มีใน mapping เลย"""
    return DR_SYMBOL_MAP.get(underlying_ticker, (None, "missing"))


# Universe หุ้นไทย 75 ตัว (test_thai_cross_sectional_momentum.py, thai_stocks_10y_cache.pkl) --
# เทรดตรงบน SET ไม่ต้องแปลง DR ไม่ต้องแปลงสกุลเงิน (THB อยู่แล้ว) -- ticker มี .BK ต่อท้ายสำหรับ yfinance
# เท่านั้น ตอนส่งออเดอร์จริงบน Settrade ใช้แค่ชื่อย่อ (ตัด .BK ออก) เช่น "ADVANC" ไม่ใช่ "ADVANC.BK"
THAI_MOMENTUM_UNIVERSE = [
    "ADVANC.BK", "AEONTS.BK", "AH.BK", "AMATA.BK", "AOT.BK", "AP.BK", "BANPU.BK", "BBL.BK", "BCH.BK",
    "BCP.BK", "BDMS.BK", "BEM.BK", "BGRIM.BK", "BH.BK", "BJC.BK", "BLA.BK", "BTS.BK", "CBG.BK",
    "CENTEL.BK", "CHG.BK", "CK.BK", "COM7.BK", "CPALL.BK", "CPF.BK", "CRC.BK", "DELTA.BK", "DOHOME.BK",
    "EA.BK", "EGCO.BK", "ERW.BK", "GFPT.BK", "GLOBAL.BK", "GPSC.BK", "HANA.BK", "HMPRO.BK", "IRPC.BK",
    "ITC.BK", "IVL.BK", "KBANK.BK", "KCE.BK", "KKP.BK", "KTB.BK", "KTC.BK", "LH.BK", "MINT.BK",
    "MTC.BK", "NER.BK", "OR.BK", "ORI.BK", "OSP.BK", "PR9.BK", "PSH.BK", "PTT.BK", "PTTEP.BK",
    "PTTGC.BK", "QH.BK", "RATCH.BK", "SAT.BK", "SAWAD.BK", "SCB.BK", "SCC.BK", "SCCC.BK", "SCGP.BK",
    "SIRI.BK", "SPALI.BK", "SPRC.BK", "TASCO.BK", "TISCO.BK", "TOP.BK", "TPIPL.BK", "TRUE.BK", "TTB.BK",
    "TU.BK", "TVO.BK", "WHA.BK",
]


def get_thai_trade_symbol(yf_ticker: str) -> str:
    """ตัด .BK ออก -- ใช้เป็นรหัสหุ้นตอนส่งออเดอร์จริงบน Settrade"""
    return yf_ticker[:-3] if yf_ticker.endswith(".BK") else yf_ticker
