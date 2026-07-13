#!/usr/bin/env python
"""
ทดสอบสูตร E3 TrendMACD + TP12/SL15 (สูตรที่ใช้ใน webull_bot ตอนนี้) เฉพาะกับ "หุ้น sideway"
(ราคาแกว่งแต่ไม่ไปทางไหนชัดเจน) — เพราะกลยุทธ์นี้เป็นสาย trend-following (ต้องการ EMA เรียงตัว
+ MACD บวก) ซึ่งปกติจะเจอปัญหา "false breakout" บ่อยตอนตลาด sideway (เข้าแล้วโดนสับกลับไปมา)

วิธีหา "หุ้น sideway": ใช้ Kaufman Efficiency Ratio (KER)
  KER = |ราคาสุดท้าย - ราคาเริ่มต้น| / ผลรวมของ |ราคาเปลี่ยนแปลงรายวัน| ตลอดช่วง
  - KER ใกล้ 1 = เทรนด์แข็งแรง (ราคาวิ่งทางเดียวแทบไม่มีการสวนกลับ)
  - KER ใกล้ 0 = sideway/choppy (ราคาแกว่งไปมาเยอะ แต่จบใกล้จุดเริ่มต้น)
คัดหุ้นที่มี KER ต่ำสุด (choppy สุด) ของหน้าต่างปีล่าสุด มาทดสอบสูตรเฉพาะกลุ่มนี้
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import US_STOCKS
from test_exit_optimization import load_data, precompute, simulate, buy_hold_return, build_exit_grid

N_SIDEWAYS = 15   # เอาหุ้น choppy สุด N ตัวมาทดสอบ
SLOTS = 5          # ถือพร้อมกันได้น้อยกว่าเดิม เพราะ universe ย่อยเหลือแค่ 15 ตัว


def kaufman_efficiency_ratio(close: pd.Series) -> float:
    net_move = abs(close.iloc[-1] - close.iloc[0])
    total_move = close.diff().abs().sum()
    return net_move / total_move if total_move > 0 else 0.0


def main():
    data = load_data()
    prep = precompute(data)
    exits = build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    test_dates = all_dates[-252:]  # ปีล่าสุด
    print(f"หน้าต่างที่ใช้หา sideway: {test_dates[0].date()} → {test_dates[-1].date()}\n")

    # คำนวณ KER ของทุกหุ้นในช่วงนี้
    ker_rows = []
    for sym, P in prep.items():
        c = P["close"]
        seg = c[(c.index >= test_dates[0]) & (c.index <= test_dates[-1])]
        if len(seg) < 200:
            continue
        ker = kaufman_efficiency_ratio(seg)
        bh = (seg.iloc[-1] / seg.iloc[0] - 1) * 100
        ker_rows.append(dict(symbol=sym, ker=round(ker, 3), bh_pct=round(bh, 1)))

    ker_df = pd.DataFrame(ker_rows).sort_values("ker")
    print("=" * 70)
    print(f"หุ้น {N_SIDEWAYS} ตัวที่ 'sideway' สุด (KER ต่ำสุด = แกว่งเยอะ ไปทางไหนไม่ชัด)")
    print("=" * 70)
    sideways = ker_df.head(N_SIDEWAYS)
    print(sideways.to_string(index=False))

    print("\n" + "=" * 70)
    print(f"เทียบ: หุ้น {N_SIDEWAYS} ตัวที่ 'เทรนด์แข็งแรง' สุด (KER สูงสุด) — ไว้เทียบ")
    print("=" * 70)
    trending = ker_df.tail(N_SIDEWAYS).sort_values("ker", ascending=False)
    print(trending.to_string(index=False))

    sideways_syms = sideways["symbol"].tolist()
    trending_syms = trending["symbol"].tolist()

    bh_sideways = np.mean(sideways["bh_pct"])
    bh_trending = np.mean(trending["bh_pct"])

    print("\n" + "=" * 70)
    print(f"ทดสอบสูตร E3 TrendMACD + TP12/SL15 บนหุ้น sideway {N_SIDEWAYS} ตัว (B&H เฉลี่ย {bh_sideways:+.1f}%)")
    print("=" * 70)
    m_side = simulate(prep, sideways_syms, test_dates, "E3 TrendMACD", exits["TP12/SL15"], SLOTS)
    print(f"ผลตอบแทน: {m_side['ret_pct']:+.1f}%  ·  Win rate: {m_side['wr']:.1f}%  ·  "
          f"MaxDD: {m_side['maxdd_pct']:.1f}%  ·  ไม้: {m_side['trades']}  ·  พลาดเพราะเงินไม่พอ: {m_side['skip']}")

    print("\n" + "=" * 70)
    print(f"เทียบ: สูตรเดียวกันบนหุ้นเทรนด์แข็งแรง {N_SIDEWAYS} ตัว (B&H เฉลี่ย {bh_trending:+.1f}%)")
    print("=" * 70)
    m_trend = simulate(prep, trending_syms, test_dates, "E3 TrendMACD", exits["TP12/SL15"], SLOTS)
    print(f"ผลตอบแทน: {m_trend['ret_pct']:+.1f}%  ·  Win rate: {m_trend['wr']:.1f}%  ·  "
          f"MaxDD: {m_trend['maxdd_pct']:.1f}%  ·  ไม้: {m_trend['trades']}  ·  พลาดเพราะเงินไม่พอ: {m_trend['skip']}")

    print("\n" + "=" * 70)
    print("สรุปเทียบข้าง")
    print("=" * 70)
    summary = pd.DataFrame([
        dict(กลุ่ม="Sideway (choppy)", bh_เฉลี่ย=round(bh_sideways, 1), **m_side),
        dict(กลุ่ม="เทรนด์แข็งแรง", bh_เฉลี่ย=round(bh_trending, 1), **m_trend),
    ])
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
