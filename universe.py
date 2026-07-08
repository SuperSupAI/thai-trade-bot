"""รายชื่อหุ้น SET100 แบ่งกลุ่มอุตสาหกรรม (curated · แก้ไขได้)
หมายเหตุ: SET100 เปลี่ยนได้เรื่อยๆ — ลิสต์นี้เป็นตัวยอดนิยม/สภาพคล่องสูง
"""
import streamlit as st
SECTORS = {
    "พลังงาน/สาธารณูปโภค": ["PTT", "PTTEP", "GULF", "GPSC", "BGRIM", "EGCO", "RATCH",
                            "BANPU", "TOP", "IRPC", "BCP", "OR", "SPRC", "EA"],
    "ธนาคาร/การเงิน": ["KBANK", "SCB", "BBL", "KTB", "TISCO", "KKP", "TTB",
                       "MTC", "SAWAD", "TIDLOR", "KTC", "AEONTS", "BLA"],
    "เทคโนโลยี/สื่อสาร": ["ADVANC", "INTUCH", "TRUE", "DELTA", "HANA", "KCE"],
    "พาณิชย์/บริการ": ["CPALL", "CPAXT", "HMPRO", "CRC", "COM7", "BJC", "GLOBAL", "DOHOME"],
    "ท่องเที่ยว/ขนส่ง": ["AOT", "BEM", "BTS", "MINT", "CENTEL", "ERW"],
    "โรงพยาบาล": ["BDMS", "BH", "BCH", "CHG", "PR9"],
    "เกษตร/อาหาร": ["CPF", "TU", "GFPT", "CBG", "OSP", "TVO", "NER", "ITC"],
    "อุตสาหกรรม/ปิโตรเคมี": ["SCC", "SCGP", "PTTGC", "IVL", "SCCC", "TASCO", "AH", "SAT"],
    "อสังหา/รับเหมา": ["LH", "AP", "SPALI", "QH", "ORI", "SIRI", "PSH",
                       "WHA", "AMATA", "STEC", "CK", "TPIPL"],
}


@st.cache_data(ttl=86400, show_spinner=False)  # Cache 1 วัน
def get_all_set_stocks():
    """ดึงรายชื่อหุ้น SET ทั้งหมดจาก investpy (ประมาณ 900+ หุ้น)"""
    try:
        import investpy
        stocks_df = investpy.stocks.get_stocks(country='Thailand')
        symbols = stocks_df['symbol'].tolist()
        # เติม .BK และ filter ให้เหลือแค่สัญลักษณ์ที่มีค่า
        return sorted([s + ".BK" for s in symbols if s and len(s) > 0])
    except Exception as e:
        print(f"Error fetching SET stocks from investpy: {e}")
        # Fallback ใช้ SET100 ถ้า investpy ไม่ได้
        syms = sorted({s for lst in SECTORS.values() for s in lst})
        return [s + ".BK" for s in syms]


def group_symbols(group):
    """คืน list สัญลักษณ์ (เติม .BK) ของกลุ่มที่เลือก · 'SET100' = รวม 80+ · 'SET Index' = ทุกหุ้น SET ~900+"""
    if group == "SET100 (ทั้งหมด)":
        syms = sorted({s for lst in SECTORS.values() for s in lst})
        return [s + ".BK" for s in syms]
    elif group == "SET Index":
        return get_all_set_stocks()  # ดึงทุกหุ้นใน SET
    else:
        syms = SECTORS.get(group, [])
        return [s + ".BK" for s in syms]
