#!/usr/bin/env python
"""
วิเคราะห์การกระจายความเสี่ยงระหว่างกอง RMF proxy ETF ทั้ง 10 ตัว:
  1. Correlation matrix ผลตอบแทนรายวัน เทียบกับ SPY (สหรัฐฯ)
  2. ช่วงที่ SPY ร่วงหนักที่สุด (worst drawdown windows ในกรอบ 10 ปี) แต่ละกองไปทางไหน
     -> ตอบคำถาม "ถ้าอเมริกาลง มีตัวไหนขึ้นหรือทรงตัวได้บ้าง" ด้วยข้อมูลย้อนหลังจริง (ไม่ใช่การพยากรณ์)
"""
import pickle
import numpy as np
import pandas as pd

FUNDS = [
    ("SPY", "K-US500XRMF (S&P500 สหรัฐฯ)"),
    ("QQQ", "K-USXNDQRMF (Nasdaq100 เทค สหรัฐฯ)"),
    ("MCHI", "K-CHINARMF (หุ้นจีน)"),
    ("INDA", "K-INDIARMF (หุ้นอินเดีย)"),
    ("EWJ", "K-JPRMF (หุ้นญี่ปุ่น)"),
    ("VGK", "K-EURMF (หุ้นยุโรป)"),
    ("VNM", "K-VIETNAMRMF (หุ้นเวียดนาม)"),
    ("GLD", "K-GDRMF (ทองคำ)"),
    ("ACWI", "K-WORLDXRMF (หุ้นทั่วโลก)"),
    ("IXN", "K-GTECHRMF (เทคโนโลยีทั่วโลก)"),
]


def main():
    data = {}
    for ticker, label in FUNDS:
        with open(f"{ticker.lower()}_10y_cache.pkl", "rb") as f:
            data[ticker] = pickle.load(f)

    all_dates = sorted(set().union(*[c.index for c in data.values()]))
    px = pd.DataFrame({t: data[t].reindex(all_dates).ffill() for t, _ in FUNDS})
    rets = px.pct_change().dropna()

    # ===== 1) Correlation matrix เทียบกับ SPY =====
    print("=" * 80)
    print("1) Correlation ผลตอบแทนรายวัน เทียบกับ SPY (สหรัฐฯ) — ยิ่งใกล้ 1 ยิ่งวิ่งตามกัน")
    print("=" * 80)
    corr = rets.corr()["SPY"].sort_values()
    label_map = dict(FUNDS)
    for t, c in corr.items():
        if t == "SPY":
            continue
        print(f"  {t:5s} {label_map[t]:35s} corr กับ SPY = {c:+.2f}")

    # ===== 2) SPY worst drawdown windows =====
    print("\n" + "=" * 80)
    print("2) ช่วงที่ SPY ร่วงหนักสุด 5 ครั้งในรอบ 10 ปี -> แต่ละกองไปทางไหน")
    print("=" * 80)
    spy = px["SPY"]
    roll_max = spy.cummax()
    dd = spy / roll_max - 1

    # หา local drawdown episodes: จุดต่ำสุดของแต่ละรอบที่ dd < -8%
    troughs = []
    in_dd = False
    start_idx = None
    worst_idx = None
    worst_val = 0
    for i in range(len(dd)):
        if dd.iloc[i] < -0.08:
            if not in_dd:
                in_dd = True
                start_idx = i
                worst_idx = i
                worst_val = dd.iloc[i]
            elif dd.iloc[i] < worst_val:
                worst_idx = i
                worst_val = dd.iloc[i]
        else:
            if in_dd:
                troughs.append((start_idx, worst_idx, i))
                in_dd = False
    if in_dd:
        troughs.append((start_idx, worst_idx, len(dd) - 1))

    troughs.sort(key=lambda x: dd.iloc[x[1]])
    troughs = troughs[:5]

    rows = []
    for start_idx, worst_idx, end_idx in troughs:
        d0 = all_dates[start_idx]
        d1 = all_dates[worst_idx]
        print(f"\n  ช่วง SPY ร่วง: {d0.date()} -> {d1.date()}  (SPY {dd.iloc[worst_idx]*100:+.1f}%)")
        row = dict(start=d0.date(), trough=d1.date(), spy_dd_pct=round(dd.iloc[worst_idx] * 100, 1))
        for t, label in FUNDS:
            p0 = px[t].iloc[start_idx]
            p1 = px[t].iloc[worst_idx]
            chg = (p1 / p0 - 1) * 100
            row[t] = round(chg, 1)
            flag = " <- ทรงตัว/ขึ้นสวนทาง" if chg > 0 else ""
            print(f"    {t:5s} {label:35s} {chg:+7.1f}%{flag}")
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv("rmf_diversification_drawdown_results.csv", index=False)

    # ===== สรุป: ใครสวนทาง SPY บ่อยสุด (ขึ้นตอนที่ SPY ร่วง) =====
    print("\n" + "=" * 80)
    print("3) สรุป: จำนวนครั้งที่แต่ละกอง 'ขึ้นหรือร่วงน้อยกว่า SPY มาก' ระหว่าง 5 ช่วงที่ SPY ร่วงหนัก")
    print("=" * 80)
    for t, label in FUNDS:
        if t == "SPY":
            continue
        vals = df[t].values
        better_count = sum(1 for v, s in zip(vals, df["spy_dd_pct"].values) if v > s + 3)
        avg = np.mean(vals)
        print(f"  {t:5s} {label:35s} เฉลี่ยช่วง SPY ร่วง = {avg:+6.1f}%  ·  ดีกว่า SPY ชัดเจน {better_count}/5 ครั้ง")

    print("\nบันทึกไว้ที่ rmf_diversification_drawdown_results.csv")


if __name__ == "__main__":
    main()
