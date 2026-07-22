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
    # ── ขยายรอบ 2 (22 ก.ค. 2026) -- เจอจากลิสต์ 132 หุ้นแม่ DR ของเพจ "เม่าปอย"/"fun manager"
    # (อ้างว่าทุกตัวมี DR จริงบน SET แต่ยัง verify รายตัวไม่ครบ ดู DR_SYMBOL_MAP ด้านล่าง) backtest
    # ยืนยันด้วย rolling-window robustness test แล้วว่าเพิ่ม universe ช่วยจริง (2022 พลิกเป็นบวก)
    "CRWD", "DDOG", "AMAT", "ASML", "DELL", "ETN", "KLAC", "LRCX", "MRVL", "MKSI",
    "SNDK", "TEL", "WDC", "AAOI", "COHR", "LITE", "QCOM", "SMCI",
    "BLK", "CME", "HOOD", "PYPL", "TME", "BILI",
    "FTNT", "DUOL", "NOW",
    "JCI", "KEYS", "NEE", "BE", "CEG", "AMPX", "EOSE", "CCJ",
    "RACE", "ONON", "HIMS",
    "FCX", "GOLD", "MP", "NEM",
    "INFY",
    "ASTS", "JOBY", "QBTS", "RGTI", "RKLB",
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
    "GS":    ("GSUS06", "confirmed"),   # เจอแล้ว 22 ก.ค. 2026 (Finnomena) -- แก้จาก unconfirmed
    "JNJ":   ("JNJ03", "confirmed"),
    "DIS":   ("DISNEY19", "confirmed"),   # เจอแล้ว 22 ก.ค. 2026 (Finnomena) -- แก้จาก unconfirmed
    "NKE":   ("NIKE80", "confirmed"),
    "GOOGL": ("GOOGL01", "confirmed"),
    "AMZN":  ("AMZN01", "confirmed"),
    "META":  ("META01", "confirmed"),
    "NVDA":  ("NVDA80", "confirmed"),
    "PFE":   ("PFIZER19", "confirmed"),
    "COST":  ("COSTCO19", "confirmed"),
    "PEP":   ("PEP80", "confirmed"),
    "ADBE":  ("ADBE03", "confirmed"),
    "LULU":  ("LULU06", "confirmed"),   # เจอแล้ว 22 ก.ค. 2026 (Finnomena) -- แก้จาก unconfirmed
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
    # ── ขยายรอบ 2 -- เช็คจาก Finnomena ก.ค. 2026 ได้แค่ 8/48 ตัว ที่เหลือ "unconfirmed" ทั้งหมด
    # (แหล่งต้นทาง "เม่าปอย"/"fun manager" อ้างว่ามี DR จริงครบทุกตัว แต่ยังหารหัสจริงไม่เจอเป็นรายตัว
    # ห้ามส่งออเดอร์จริงกับตัว unconfirmed จนกว่าจะเช็ค set.or.th เอง)
    "CRWD":  ("CRWD80", "confirmed"),
    "ASML":  ("ASML01", "confirmed"),
    "DELL":  ("DELL19", "confirmed"),
    "HOOD":  ("HOOD06", "confirmed"),
    "TME":   ("TME23", "confirmed"),
    "BILI":  ("BILIBILI01", "confirmed"),
    "ONON":  ("ONON03", "confirmed"),
    "RACE":  ("FERRARI80", "confirmed"),
    # ── ขยายรอบ 3 -- ไล่เช็ค set.or.th/settrade/pi/bualuang ทีละตัว 22 ก.ค. 2026 ต่อ 3 เจอเพิ่ม 13/43 ตัว
    "DDOG":  ("DDOG19", "confirmed"),     # เจอแล้ว (ผู้ใช้ส่งลิสต์ DR เต็มจาก settrade มาให้ 22 ก.ค. ต่อ 4)
    "AMAT":  ("AMAT01", "confirmed"),     # เจอแล้ว (มีทั้ง AMAT01/19/23 หลาย issuer, ใช้ AMAT01)
    "ETN":   ("ETN03", "confirmed"),      # เจอแล้ว (Pi Financial)
    "KLAC":  ("KLAC01", "confirmed"),     # เจอแล้ว (มีทั้ง KLAC01/19/23 หลาย issuer, ใช้ KLAC01)
    "LRCX":  ("LRCX01", "confirmed"),     # เจอแล้ว (รอบ 4, มีทั้ง LRCX01/19/23/80 หลาย issuer, ใช้ LRCX01)
    "MRVL":  ("MRVL80", "confirmed"),     # เจอแล้ว (KTB, ยืนยันที่ set.or.th)
    "MKSI":  ("MKSI03", "confirmed"),     # เจอแล้ว (รอบ 4)
    "SNDK":  ("SNDK03", "confirmed"),     # เจอแล้ว (Pi Financial)
    "TEL":   (None, "unconfirmed"),       # ระวัง: มี "TEL23"/"TEL80" จริง (ยืนยันซ้ำรอบ 4 ว่าตลาดอ้างอิงคือ TSE
                                           # = Tokyo Stock Exchange) เป็น Tokyo Electron ไม่ใช่ TE Connectivity
                                           # (yfinance ticker "TEL" ของเราคือ TE Connectivity เทรดที่ NYSE) -- ห้ามจับคู่ผิดบริษัท
    "WDC":   ("WDC03", "confirmed"),      # เจอแล้ว (รอบ 4)
    "AAOI":  ("AAOI03", "confirmed"),     # เจอแล้ว
    "COHR":  ("COHR23", "confirmed"),     # เจอแล้ว (มีทั้ง COHR23/COHR80 หลาย issuer, ใช้ COHR23)
    "LITE":  ("LITE01", "confirmed"),     # เจอแล้ว (Bualuang, มีทั้ง LITE01/23/80 หลาย issuer)
    "QCOM":  ("QCOM06", "confirmed"),     # เจอแล้ว (KKPS, ยืนยันที่ settrade)
    "SMCI":  ("SMCI03", "confirmed"),     # เจอแล้ว (Pi Securities)
    "BLK":   ("BLK06", "confirmed"),      # เจอแล้ว
    "CME":   ("CME03", "confirmed"),      # เจอแล้ว (รอบ 5, ผู้ใช้ส่งลิงก์ set.or.th โดยตรง, ยืนยัน CME Group ที่ PI)
    "PYPL":  ("PYPL06", "confirmed"),     # เจอแล้ว (รอบ 4)
    "FTNT":  ("FTNT03", "confirmed"),     # เจอแล้ว
    "DUOL":  ("DUOL06", "confirmed"),     # เจอแล้ว (KKPS, ยืนยันที่ set.or.th)
    "NOW":   ("NOW19", "confirmed"),      # เจอแล้ว (รอบ 4)
    "JCI":   ("JCI03", "confirmed"),      # เจอแล้ว
    "KEYS":  (None, "unconfirmed"),       # ยังไม่เจอในลิสต์ settrade ที่ผู้ใช้ส่งมา -- ระวังอย่าสับสนกับ KEYENCE23
                                           # (Keyence Corp ญี่ปุ่น คนละบริษัทกับ Keysight Technologies)
    "NEE":   ("NEE80", "confirmed"),      # เจอแล้ว (รอบ 4)
    "BE":    ("BE03", "confirmed"),       # เจอแล้ว
    "CEG":   ("CEG23", "confirmed"),      # เจอแล้ว
    "AMPX":  ("AMPX03", "confirmed"),     # เจอแล้ว
    "EOSE":  ("EOSE03", "confirmed"),     # เจอแล้ว
    "CCJ":   ("CCJ23", "confirmed"),      # เจอแล้ว (INVX, ยืนยันที่ set.or.th)
    "HIMS":  ("HIMS03", "confirmed"),     # เจอแล้ว
    "FCX":   ("FCX23", "confirmed"),      # เจอแล้ว
    "GOLD":  (None, "unconfirmed"),       # ระวัง: ในลิสต์มี GOLD03/GOLD19/GOLDUS* แต่เป็น SPDR Gold ETF (ทองคำแท่ง)
                                           # ไม่ใช่หุ้น Barrick Gold Corp (ticker เราคือ GOLD=Barrick) -- ห้ามจับคู่ผิด
    "MP":    ("MP23", "confirmed"),       # เจอแล้ว (รอบ 4)
    "NEM":   ("NEM06", "confirmed"),      # เจอแล้ว (รอบ 4)
    "INFY":  (None, "unconfirmed"),       # ยังไม่เจอในลิสต์ settrade ที่ผู้ใช้ส่งมา -- น่าจะยังไม่มี DR จริง
    "ASTS":  ("ASTS01", "confirmed"),     # เจอแล้ว (Bualuang, ยืนยันที่หน้า iNAV)
    "JOBY":  ("JOBY03", "confirmed"),     # เจอแล้ว
    "QBTS":  ("QBTS03", "confirmed"),     # เจอแล้ว (รอบ 4)
    "RGTI":  ("RGTI03", "confirmed"),     # เจอแล้ว (รอบ 4)
    "RKLB":  ("RKLB01", "confirmed"),     # เจอแล้ว (รอบ 4, มีทั้ง RKLB01/03/23/80 หลาย issuer, ใช้ RKLB01)
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
