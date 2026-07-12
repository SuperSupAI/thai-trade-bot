#!/usr/bin/env python
"""
ทดสอบ FVMR Framework (Fundamentals, Valuation, Momentum, Revisions) แบบ UOB Kay Hian
ให้คะแนนหุ้นแต่ละตัว 4 มิติ แล้วเช็คว่าหุ้นคะแนนสูง (Top tercile) ทำผลตอบแทนล่วงหน้า
(forward return 3 เดือนถัดไป) ดีกว่าหุ้นคะแนนต่ำ (Bottom tercile) จริงหรือไม่

*** ข้อจำกัดสำคัญที่ต้องเปิดเผยตรงๆ ***
yfinance ฟรีไม่มีข้อมูล fundamental แบบ point-in-time ย้อนหลัง (เช่น ROE เมื่อ 3 ปีก่อน)
มีแต่ค่าปัจจุบันล่าสุดเท่านั้น ดังนั้น:
  - F (Fundamentals), V (Valuation), R (Revisions proxy) จะใช้ค่า "ปัจจุบัน" คงที่ตลอดการทดสอบ
    (มี look-ahead bias เล็กน้อย เพราะเราใช้ข้อมูลปัจจุบันไปตัดสินอดีต)
  - M (Momentum) คำนวณแบบ point-in-time จริง (ใช้ผลตอบแทนย้อนหลัง 6 เดือน ณ เวลานั้นๆ เท่านั้น)
    ส่วนนี้ไม่มี look-ahead
ผลลัพธ์จึงเป็น "การทดสอบแนวคิด" ว่า F/V/R ปัจจุบันของหุ้นที่ดีมักจะโมเมนตัมดีย้อนหลังด้วยหรือไม่
ไม่ใช่ backtest แบบเป๊ะที่จะเอาไปเทรดจริงได้ 100% (ต้องมีข้อมูล fundamental ย้อนหลังแบบเสียเงินถึงจะทำได้เป๊ะ)
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf

FEE = 0.002


def fetch_fvmr_static(sym):
    """คะแนน F, V, R (คงที่ตลอดการทดสอบ เพราะเป็นค่าปัจจุบันล่าสุดเท่านั้นที่ดึงได้ฟรี)"""
    try:
        info = yf.Ticker(sym).info
    except Exception:
        return None
    if not info or info.get("trailingPE") is None and info.get("returnOnEquity") is None:
        return None

    roe = info.get("returnOnEquity") or 0
    ebit_margin = info.get("operatingMargins") or 0
    pe = info.get("trailingPE")
    pb = info.get("priceToBook")
    eps_growth = info.get("earningsGrowth") or 0

    f_score = (1 if roe > 0.15 else 0) + (1 if ebit_margin > 0.10 else 0)
    v_score = (1 if (pe is not None and 0 < pe < 25) else 0) + (1 if (pb is not None and 0 < pb < 3) else 0)
    r_score = (1 if eps_growth > 0.05 else 0) * 2  # ให้น้ำหนักเท่า F/V (คูณ 2 เพราะมีแค่ตัวเดียว)
    return dict(f=f_score, v=v_score, r=r_score, roe=roe, pe=pe, pb=pb, eps_growth=eps_growth)


def load_price(sym, years=10):
    try:
        df = yf.download(sym, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 400:
            return None
        c = df["Close"]
        if isinstance(c, pd.DataFrame):
            c = c.iloc[:, 0]
        return c.dropna()
    except Exception:
        return None


def quarterly_snapshots(close, fvr_static):
    """คืน list ของ (quarter_end_idx, momentum_score, forward_3m_return)"""
    n = len(close)
    step = 63  # ~3 เดือนเทรดวัน
    lookback = 126  # ~6 เดือน สำหรับวัด momentum
    out = []
    for i in range(lookback, n - step, step):
        mom_ret = close.iloc[i] / close.iloc[i - lookback] - 1
        fwd_ret = close.iloc[i + step] / close.iloc[i] - 1 - 2 * FEE
        out.append(dict(mom_ret=mom_ret, fwd_ret=fwd_ret, f=fvr_static["f"], v=fvr_static["v"], r=fvr_static["r"]))
    return out


def main():
    sys.path.insert(0, ".")
    from universe import US_STOCKS
    syms = list(US_STOCKS)
    print(f"ดึง fundamentals (F/V/R แบบ snapshot ปัจจุบัน) + ราคา 10 ปี: {len(syms)} หุ้น US...")

    rows = []
    ok = 0
    for s in syms:
        fvr = fetch_fvmr_static(s)
        if fvr is None:
            continue
        c = load_price(s, 10)
        if c is None:
            continue
        snaps = quarterly_snapshots(c, fvr)
        for sn in snaps:
            sn["symbol"] = s
            rows.append(sn)
        ok += 1
    print(f"ใช้ได้ {ok}/{len(syms)} หุ้น, รวม {len(rows)} หุ้น-ไตรมาส")

    df = pd.DataFrame(rows)
    if df.empty:
        print("ไม่มีข้อมูลพอ")
        return

    # terzile momentum แบบ global (ทั้งชุดข้อมูล) -- ค่า mom_ret เองคำนวณ point-in-time ถูกต้อง (ไม่ look-ahead)
    # แค่การแบ่ง tercile ใช้สถิติของทั้งชุดข้อมูล (คล้าย cross-sectional rank เทียบทั้งตลาด)
    df["mom_tercile"] = pd.qcut(df["mom_ret"], 3, labels=["low", "mid", "high"], duplicates="drop")
    df["fvr_total"] = df["f"] + df["v"] + df["r"]

    def bucket(row):
        m = {"low": 0, "mid": 1, "high": 2}[row["mom_tercile"]]
        return row["fvr_total"] + m  # รวม FVMR เต็ม (F+V+M+R) คะแนนเต็ม 8

    df["total_score"] = df.apply(bucket, axis=1)

    q_lo, q_hi = df["total_score"].quantile([0.33, 0.67])
    top = df[df["total_score"] >= q_hi]
    bot = df[df["total_score"] <= q_lo]

    def stats(d, label):
        wr = (d["fwd_ret"] > 0).mean() * 100
        avg = d["fwd_ret"].mean() * 100
        print(f"{label}: n={len(d)}, win rate (forward 3m บวก)={wr:.1f}%, avg forward return={avg:.2f}%")
        return wr, avg

    print(f"\nคะแนนรวม FVMR (F+V+M+R, เต็ม 8): เส้นแบ่ง top>={q_hi:.1f}, bottom<={q_lo:.1f}")
    stats(top, "Top tercile (FVMR สูง)")
    stats(bot, "Bottom tercile (FVMR ต่ำ)")
    print(f"\nค่าเฉลี่ยทั้งชุด: n={len(df)}, win rate={  (df['fwd_ret']>0).mean()*100:.1f}%, avg={df['fwd_ret'].mean()*100:.2f}%")

    df.to_csv("fvmr_us_snapshots.csv", index=False)
    print("\nบันทึกไว้ที่ fvmr_us_snapshots.csv")


if __name__ == "__main__":
    main()
