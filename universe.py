"""รายชื่อหุ้น SET100 แบ่งกลุ่มอุตสาหกรรม (curated · แก้ไขได้)
หมายเหตุ: SET100 เปลี่ยนได้เรื่อยๆ — ลิสต์นี้เป็นตัวยอดนิยม/สภาพคล่องสูง
"""
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


def group_symbols(group):
    """คืน list สัญลักษณ์ (เติม .BK) ของกลุ่มที่เลือก · 'SET100' = รวมทุกกลุ่ม"""
    if group == "SET100 (ทั้งหมด)":
        syms = sorted({s for lst in SECTORS.values() for s in lst})
    elif group == "SET Index":
        return ["^SET.BK"]  # SET Index มี . อยู่แล้ว
    else:
        syms = SECTORS.get(group, [])
    return [s + ".BK" for s in syms]
