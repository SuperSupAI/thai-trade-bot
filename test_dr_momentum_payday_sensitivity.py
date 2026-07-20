#!/usr/bin/env python
"""
เช็คว่า "วันไหนของเดือน" เหมาะที่สุดสำหรับรีบาลานซ์ DR Momentum Top-3
(บังคับด้วยเงื่อนไขจริง: เงินเดือนออกปลายเดือน ต้องรอเงินก่อนถึงจะซื้อได้ ไม่ใช่เลือกวันไหนก็ได้)

ทดสอบ "วันเป้าหมายของเดือน" หลายแบบ (20, 22, 25, 27, 28, 30 — ใกล้เคียงวันเงินเดือนออกจริงของคนทั่วไป)
วิธี: แต่ละเดือนหาวันเทรดจริงที่ >= วันเป้าหมาย (ถ้าวันนั้นตลาดปิด ให้เลื่อนไปวันทำการถัดไป)
เทียบผลตอบแทน 10 ปีเต็ม + win rate + ความเสถียรผ่าน TRAIN/VALID/TEST
"""
import sys
import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, ".")

FEE_DR = 0.002
FORMATION = 252
SKIP = 21

DR_COVERED = ["AAPL", "MSFT", "JPM", "V", "UNH", "KO", "CSCO", "CRM", "GS", "JNJ",
              "DIS", "NKE", "GOOGL", "AMZN", "META", "NVDA", "PFE", "COST", "PEP", "ADBE", "LULU"]


def load_close(sym, years=10):
    df = yf.download(sym, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
    if df is None or df.empty:
        return None
    c = df["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.dropna()


def payday_rebalance_indices(dates, target_day):
    """หา index ของวันเทรดจริงแรกที่ >= target_day ของแต่ละเดือน (ถ้าเดือนนั้นไม่มีวันเทรด >= target_day
    เพราะตลาดปิดยาว ให้ข้ามเดือนนั้นไปเลย ไม่บังคับซื้อ)"""
    idx = []
    seen_months = set()
    for i, d in enumerate(dates):
        key = (d.year, d.month)
        if key in seen_months:
            continue
        if d.day >= target_day:
            idx.append(i)
            seen_months.add(key)
    return idx


def sim_momentum_lumpsum(closes, rebalance_idx, top_n, capital_thb=1_000_000, thb_per_usd=35.5):
    """ทุนก้อนเดียว รีบาลานซ์ตาม index ที่กำหนด (ไม่ใช่ทุก 21 วันคงที่แบบเดิม)"""
    syms = list(closes.keys())
    common_idx = None
    for c in closes.values():
        common_idx = c.index if common_idx is None else common_idx.intersection(c.index)
    common_idx = sorted(common_idx)
    price = {s: closes[s].reindex(common_idx).ffill() for s in syms}
    n = len(common_idx)

    capital_usd = capital_thb / thb_per_usd
    cash = capital_usd
    shares = {s: 0.0 for s in syms}
    n_rebalances = 0
    equity_curve = []

    min_needed = FORMATION + SKIP
    for i in range(n):
        port_value = cash + sum(shares[s] * float(price[s].iloc[i]) for s in syms)
        equity_curve.append(port_value)
        if i in rebalance_idx and i >= min_needed:
            scores = {}
            for s in syms:
                p_now = price[s].iloc[i - SKIP]
                p_form = price[s].iloc[i - FORMATION]
                if p_form > 0:
                    scores[s] = p_now / p_form - 1
            ranked = sorted(scores, key=lambda k: -scores[k])[:top_n]
            port_value *= (1 - FEE_DR)
            target_each = port_value / top_n
            new_shares = {s: 0.0 for s in syms}
            for s in ranked:
                new_shares[s] = target_each / float(price[s].iloc[i])
            shares = new_shares
            cash = 0.0
            n_rebalances += 1

    final_value = (cash + sum(shares[s] * float(price[s].iloc[-1]) for s in syms)) * thb_per_usd
    ret_pct = (final_value / capital_thb - 1) * 100
    return dict(final_value=final_value, ret_pct=ret_pct, n_rebalances=n_rebalances)


def main():
    print(f"ดาวน์โหลดราคา 10 ปี ({len(DR_COVERED)} หุ้น DR mega-cap)...")
    closes = {}
    for s in DR_COVERED:
        c = load_close(s)
        if c is not None and len(c) > 400:
            closes[s] = c
    print(f"ใช้ได้ {len(closes)}/{len(DR_COVERED)} หุ้น\n")

    common_idx = None
    for c in closes.values():
        common_idx = c.index if common_idx is None else common_idx.intersection(c.index)
    common_idx = sorted(common_idx)
    n = len(common_idx)
    train_end = int(n * 0.6)
    valid_end = int(n * 0.8)

    target_days = [1, 2, 3, 4, 5, 20, 22, 25, 26, 27, 28, 29, 30]
    print(f"{'วันเป้าหมาย':>10s}  {'#รีบาลานซ์':>10s}  {'ALL 10ปี':>14s}  {'TRAIN':>14s}  {'VALID':>14s}  {'TEST':>14s}")
    print("=" * 90)

    rows = []
    for td in target_days:
        idx_all = payday_rebalance_indices(common_idx, td)
        idx_set = set(idx_all)

        def slice_result(lo, hi):
            sub_idx = {i for i in idx_set if lo <= i < hi}
            sub_closes = {s: c.iloc[lo:hi] for s, c in closes.items()}
            # ปรับ index ให้ตรงกับตำแหน่งใน sub slice
            sub_idx_local = {i - lo for i in sub_idx}
            return sim_momentum_lumpsum(sub_closes, sub_idx_local, top_n=3)

        r_all = sim_momentum_lumpsum(closes, idx_set, top_n=3)
        r_train = slice_result(0, train_end)
        r_valid = slice_result(train_end, valid_end)
        r_test = slice_result(valid_end, n)

        print(f"{td:>10d}  {r_all['n_rebalances']:>10d}  {r_all['ret_pct']:>13.1f}%  "
              f"{r_train['ret_pct']:>13.1f}%  {r_valid['ret_pct']:>13.1f}%  {r_test['ret_pct']:>13.1f}%")
        rows.append(dict(target_day=td, n_rebalances=r_all['n_rebalances'],
                         all_pct=r_all['ret_pct'], train_pct=r_train['ret_pct'],
                         valid_pct=r_valid['ret_pct'], test_pct=r_test['ret_pct']))

    df = pd.DataFrame(rows)
    df.to_csv("dr_momentum_payday_sensitivity.csv", index=False)
    print("\nบันทึกไว้ที่ dr_momentum_payday_sensitivity.csv")

    best = df.loc[df['test_pct'].idxmax()]
    print(f"\nวันที่ดีที่สุดตาม TEST (ช่วงล่าสุด, สำคัญสุดเพราะใกล้ปัจจุบัน): วันที่ {int(best['target_day'])} "
          f"-> TEST {best['test_pct']:.1f}%")


if __name__ == "__main__":
    main()
