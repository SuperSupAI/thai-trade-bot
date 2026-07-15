#!/usr/bin/env python
"""
เทียบผลตอบแทน "หลังภาษีจริง" ของแต่ละช่องทาง ทุนก้อนเดียว 1,000,000 บาท ถือ 10 ปี
ใช้ตารางภาษีก้าวหน้าจริงของไทย (2026) ไม่ใช่แค่สมมติ flat 25% เหมือนที่ทำมาทั้งวัน

ช่องทางที่เทียบ:
  A) RMF S&P500 -- ลดหย่อนได้จริงแค่ 500,000 บาท/ปี (ลิมิตรวมกับ SSF/PVD ตามกฎจริง) ส่วนเกิน
     500,000 บาทที่เหลือ ไปลงกองทุนทั่วไปแทน (ไม่มีประโยชน์ลง RMF เกินลิมิต) -- capital gain ยกเว้นภาษีทั้งคู่
  B) กองทุนทั่วไป (ไม่ใช่ RMF) ลงหุ้นสหรัฐฯ เช่น K-USA-A -- ไม่ลดหย่อน, capital gain ยกเว้นภาษี,
     fee จัดการจริง 1.60%/ปี (fee รวม 1.70%/ปี ตามข้อมูลกองจริง)
  C) DR (SP50001 ติดตาม Hang Seng S&P500 ETF) -- ไม่ลดหย่อน, capital gain ยกเว้นภาษีเหมือนหุ้นไทย,
     fee ETF ต้นทาง 0.90%/ปี (จาก fact sheet จริง)
  D) ซื้อ SPY ตรงๆ ผ่านโบรกต่างประเทศ -- ไม่ลดหย่อน, fee ต่ำมาก 0.03%/ปี, "กำไร" ทั้งก้อนโดนภาษี
     ก้าวหน้าตอนโอนเงินกลับไทยปีที่ 10 (กฎ ป.161/2566) คำนวณด้วยตารางภาษีจริง ซ้อนทับรายได้อื่นสมมติ 1.5 ล้าน/ปี
  E) หุ้นไทย (ใช้ THD เป็น proxy ตลาดหุ้นไทยรวม) -- ไม่ลดหย่อน, capital gain ยกเว้นภาษี (ไม่รวมผลปันผล
     10% WHT เพื่อให้ใช้ price-only series สอดคล้องกับทุกช่องทางอื่นในการทดลองนี้)
"""
import pickle
import numpy as np
import pandas as pd
import yfinance as yf

LUMP_SUM_THB = 1_000_000
N_YEARS = 10
THB_PER_USD = 35.5
RMF_FEE = 0.0054
KUSA_FEE = 0.017          # ค่าธรรมเนียมรวมจริงของ K-USA-A (active fund, ไม่ใช่ index)
DR_UNDERLYING_FEE = 0.0090  # expense ratio จริงของ Hang Seng S&P500 Index ETF (3195.HK)
SPY_DIRECT_FEE = 0.0003
ASSUMED_OTHER_INCOME_THB = 1_500_000  # รายได้อื่นสมมติ/ปี (อยู่ฐาน 25%) ไว้คำนวณภาษีก้าวหน้าซ้อนทับ
RMF_DEDUCTION_CAP_THB = 500_000       # ลิมิตลดหย่อนรวม RMF+SSF+PVD ตามกฎจริง

# ตารางภาษีก้าวหน้าไทย 2026 (บาท, อัตรา)
BRACKETS = [(0, 150_000, 0.00), (150_000, 300_000, 0.05), (300_000, 500_000, 0.10),
            (500_000, 750_000, 0.15), (750_000, 1_000_000, 0.20), (1_000_000, 2_000_000, 0.25),
            (2_000_000, 5_000_000, 0.30), (5_000_000, float("inf"), 0.35)]


def thai_pit(income):
    tax = 0.0
    for lo, hi, rate in BRACKETS:
        if income > lo:
            tax += (min(income, hi) - lo) * rate
        else:
            break
    return tax


def load(ticker, cache):
    with open(cache, "rb") as f:
        return pickle.load(f)


def main():
    spy = load("SPY", "spy_10y_cache.pkl")
    import os
    if os.path.exists("thd_10y_cache.pkl"):
        with open("thd_10y_cache.pkl", "rb") as f:
            thd = pickle.load(f)
    else:
        thd = yf.download("THD", period="10y", progress=False)["Close"]
        if isinstance(thd, pd.DataFrame):
            thd = thd.iloc[:, 0]
        thd = thd.dropna()
        thd.index = pd.to_datetime(thd.index).tz_localize(None)
        with open("thd_10y_cache.pkl", "wb") as f:
            pickle.dump(thd, f)

    spy_ret = float(spy.iloc[-1] / spy.iloc[0] - 1)
    thd_ret = float(thd.iloc[-1] / thd.iloc[0] - 1)
    print(f"ช่วง SPY: {spy.index[0].date()} -> {spy.index[-1].date()}  ผลตอบแทนก่อนหักค่าธรรมเนียม {spy_ret*100:+.1f}%")
    print(f"ช่วง THD (proxy หุ้นไทย): {thd.index[0].date()} -> {thd.index[-1].date()}  ผลตอบแทนก่อนหักค่าธรรมเนียม {thd_ret*100:+.1f}%\n")

    def fee_decay(rate):
        return (1 - rate) ** N_YEARS

    rows = []

    # ===== A) RMF (500k ลดหย่อนได้) + ส่วนเกิน 500k ไปกองทุนทั่วไป =====
    rmf_portion = min(LUMP_SUM_THB, RMF_DEDUCTION_CAP_THB)
    excess_portion = LUMP_SUM_THB - rmf_portion
    tax_saved = thai_pit(ASSUMED_OTHER_INCOME_THB) - thai_pit(ASSUMED_OTHER_INCOME_THB - rmf_portion)
    rmf_invested = rmf_portion + tax_saved  # เงินคืนภาษีเอาไปลงเพิ่มในกองเดียวกัน
    rmf_final = rmf_invested * (1 + spy_ret) * fee_decay(RMF_FEE)
    excess_final = excess_portion * (1 + spy_ret) * fee_decay(KUSA_FEE)  # ส่วนเกินไปกองทุนทั่วไปแทน
    a_final = rmf_final + excess_final
    rows.append(dict(ช่องทาง=f"A) RMF S&P500 (ลดหย่อนได้จริงแค่ {rmf_portion:,.0f} บาท) + ส่วนเกินไปกองทั่วไป",
                      final_thb=a_final, note=f"คืนภาษี {tax_saved:,.0f} บาท (อัตราเฉลี่ย {tax_saved/rmf_portion*100:.1f}%)"))

    # ===== B) กองทุนทั่วไป (K-USA-A style) ล้วน 100% =====
    b_final = LUMP_SUM_THB * (1 + spy_ret) * fee_decay(KUSA_FEE)
    rows.append(dict(ช่องทาง="B) กองทุนทั่วไป (ไม่ใช่ RMF) เช่น K-USA-A ล้วน 100% -- ไม่ลดหย่อน, fee 1.70%/ปี",
                      final_thb=b_final, note="capital gain ยกเว้นภาษี เหมือน RMF แต่ไม่ล็อกเงิน"))

    # ===== C) DR (SP50001 proxy) =====
    c_final = LUMP_SUM_THB * (1 + spy_ret) * fee_decay(DR_UNDERLYING_FEE)
    rows.append(dict(ช่องทาง="C) DR (SP50001 ติดตาม Hang Seng S&P500 ETF) -- fee ETF ต้นทาง 0.90%/ปี",
                      final_thb=c_final, note="capital gain ยกเว้นภาษีเหมือนหุ้นไทย ซื้อขายเหมือนหุ้น"))

    # ===== D) ซื้อ SPY ตรงๆ ต่างประเทศ -- โดนภาษีก้าวหน้าตอนโอนกลับปีที่ 10 =====
    d_pretax_final = LUMP_SUM_THB * (1 + spy_ret) * fee_decay(SPY_DIRECT_FEE)
    d_gain = d_pretax_final - LUMP_SUM_THB
    tax_on_gain = thai_pit(ASSUMED_OTHER_INCOME_THB + d_gain) - thai_pit(ASSUMED_OTHER_INCOME_THB)
    d_final = d_pretax_final - tax_on_gain
    rows.append(dict(ช่องทาง="D) ซื้อ SPY ตรงๆ ผ่านโบรกต่างประเทศ -- โดนภาษีก้าวหน้าตอนโอนเงินกลับปีที่ 10",
                      final_thb=d_final, note=f"กำไรก่อนภาษี {d_gain:,.0f} บาท ถูกภาษี {tax_on_gain:,.0f} บาท (อัตราเฉลี่ย {tax_on_gain/d_gain*100:.1f}%)"))

    # ===== E) หุ้นไทย (THD proxy) =====
    e_final = LUMP_SUM_THB * (1 + thd_ret)
    rows.append(dict(ช่องทาง="E) หุ้นไทย (proxy: THD) -- capital gain ยกเว้นภาษี (ไม่รวมปันผล 10% WHT)",
                      final_thb=e_final, note="ไม่มี fee กองทุน แต่มีค่าคอมมิชชั่นซื้อขายที่ไม่ได้รวมในนี้"))

    df = pd.DataFrame(rows)
    df["profit_thb"] = df["final_thb"] - LUMP_SUM_THB
    df["ret_pct"] = (df["final_thb"] / LUMP_SUM_THB - 1) * 100
    df = df.sort_values("ret_pct", ascending=False)

    print("=" * 115)
    print(f"ทุนก้อนเดียว {LUMP_SUM_THB:,} บาท ถือ {N_YEARS} ปี -- ผลตอบแทน 'หลังภาษีจริง' แต่ละช่องทาง")
    print(f"(สมมติมีรายได้อื่นอยู่แล้ว {ASSUMED_OTHER_INCOME_THB:,} บาท/ปี เพื่อคำนวณภาษีก้าวหน้าซ้อนทับ)")
    print("=" * 115)
    for _, r in df.iterrows():
        print(f"{r['ช่องทาง']}")
        print(f"    มูลค่าสุดท้าย {r['final_thb']:>13,.0f} บาท  กำไรหลังภาษี {r['profit_thb']:>+13,.0f} บาท  "
              f"ผลตอบแทน {r['ret_pct']:>+7.1f}%  |  {r['note']}")

    df.to_csv("aftertax_lumpsum_compare_results.csv", index=False)
    print("\nบันทึกไว้ที่ aftertax_lumpsum_compare_results.csv")


if __name__ == "__main__":
    main()
