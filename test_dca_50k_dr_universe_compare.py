#!/usr/bin/env python
"""
DCA เดือนละ 50,000 บาท (10 ปี = 6,000,000 บาท) เข้ากลยุทธ์ momentum baseline บน DR universe
เทียบ: (1) DR เดิม 21 ตัว vs DR ขยายใหม่ 47 ตัว, top_n=3/5, (2) เทียบกับ SPY DCA เป็น benchmark
       (3) เทียบกับ lump-sum (ลงทีเดียว 6,000,000 บาทวันแรก) ของกลยุทธ์เดียวกัน -- ดูว่า DCA เสียโอกาสไปแค่ไหน
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum_dr_universe import DR_COVERED as DR_COVERED_OLD
from test_dr_universe_expanded_comparison import DR_COVERED_EXPANDED
from safe_fetch import safe_download_many

CACHE_FILE = "us_close_10y_cache.pkl"
MONTHLY_THB = 50_000
N_YEARS = 10
N_MONTHS = N_YEARS * 12
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
FORMATION, SKIP, REBAL = 252, 21, 21


def monthly_inject_indices(dates, n_months):
    idx = [0]
    cur_ym = (dates[0].year, dates[0].month)
    for i, d in enumerate(dates):
        ym = (d.year, d.month)
        if ym != cur_ym:
            idx.append(i)
            cur_ym = ym
        if len(idx) >= n_months:
            break
    return idx


def _momentum_scores(price_lookup, syms_order, dt):
    scores = {}
    for s in syms_order:
        close = price_lookup[s]
        if dt not in close.index:
            continue  # หุ้นยังไม่ IPO / ยังไม่มีราคา ณ วันนี้ -- ข้าม ไม่บังคับทั้ง universe ต้องมีข้อมูลพร้อมกัน
        i = close.index.get_loc(dt)
        if i < FORMATION:
            continue
        p_now = close.iloc[i - SKIP]
        p_form = close.iloc[i - FORMATION]
        if p_form > 0:
            scores[s] = p_now / p_form - 1
    return scores


def sim_dr_momentum_dca(price_lookup, syms_order, monthly_thb, top_n, n_months):
    """DCA: ฉีดเงินทุกเดือนตาม common_idx (union วันเทรดทั้ง universe) ตั้งแต่วันแรก
    เงินที่ฉีดมาก่อนมี momentum history พอ (yet no eligible stock) จะพักเป็นเงินสดรอ ไม่ได้หายไปไหน"""
    monthly_usd = monthly_thb / THB_PER_USD
    common_idx = sorted(set().union(*[set(price_lookup[s].index) for s in syms_order]))
    n = len(common_idx)
    inject_idx = set(monthly_inject_indices(common_idx, n_months))

    cash = 0.0
    shares = {s: 0.0 for s in syms_order}
    total_invested = 0.0
    rebal_counter = 0
    for i, dt in enumerate(common_idx):
        if i in inject_idx:
            cash += monthly_usd
            total_invested += monthly_thb
        scores = _momentum_scores(price_lookup, syms_order, dt)
        if not scores:
            continue
        if rebal_counter % REBAL == 0:
            ranked = sorted(scores, key=lambda k: -scores[k])[:top_n]
            held_val = sum(shares[s] * float(price_lookup[s].loc[dt]) for s in syms_order
                            if dt in price_lookup[s].index)
            port_value = (cash + held_val) * (1 - FEE)
            target_each = port_value / len(ranked)
            new_shares = {s: 0.0 for s in syms_order}
            for s in ranked:
                new_shares[s] = target_each / float(price_lookup[s].loc[dt])
            shares = new_shares
            cash = 0.0
        rebal_counter += 1
    last_dt = common_idx[-1]
    final_value = cash
    for s in syms_order:
        c = price_lookup[s]
        px = float(c.loc[last_dt]) if last_dt in c.index else float(c.iloc[-1])
        final_value += shares[s] * px
    final_value *= THB_PER_USD
    return final_value, total_invested


def sim_dr_momentum_lumpsum(price_lookup, syms_order, capital_thb, top_n):
    common_idx = sorted(set().union(*[set(price_lookup[s].index) for s in syms_order]))
    capital_usd = capital_thb / THB_PER_USD
    cash = capital_usd
    shares = {s: 0.0 for s in syms_order}
    rebal_counter = 0
    for i, dt in enumerate(common_idx):
        scores = _momentum_scores(price_lookup, syms_order, dt)
        if not scores:
            continue
        if rebal_counter % REBAL == 0:
            ranked = sorted(scores, key=lambda k: -scores[k])[:top_n]
            held_val = sum(shares[s] * float(price_lookup[s].loc[dt]) for s in syms_order
                            if dt in price_lookup[s].index)
            port_value = (cash + held_val) * (1 - FEE)
            target_each = port_value / len(ranked)
            new_shares = {s: 0.0 for s in syms_order}
            for s in ranked:
                new_shares[s] = target_each / float(price_lookup[s].loc[dt])
            shares = new_shares
            cash = 0.0
        rebal_counter += 1
    last_dt = common_idx[-1]
    final_value = cash
    for s in syms_order:
        c = price_lookup[s]
        px = float(c.loc[last_dt]) if last_dt in c.index else float(c.iloc[-1])
        final_value += shares[s] * px
    final_value *= THB_PER_USD
    return final_value, capital_thb


def sim_spy_dca(close, monthly_thb, n_months, fee_rate=0.0003):
    monthly_usd = monthly_thb / THB_PER_USD
    dates = close.index
    inject_idx = set(monthly_inject_indices(dates, n_months))
    shares = 0.0
    total_invested = 0.0
    last_year = dates[0].year
    for i, dt in enumerate(dates):
        if i in inject_idx:
            shares += monthly_usd / float(close.iloc[i])
            total_invested += monthly_thb
        if dt.year != last_year:
            shares *= (1 - fee_rate)
            last_year = dt.year
    final_value = shares * float(close.iloc[-1]) * THB_PER_USD
    return final_value, total_invested


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    if "SPY" not in data:
        print("ดาวน์โหลด SPY เพิ่ม...")
        new = safe_download_many(["SPY"], years=10, min_rows=210)
        data.update(new)
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data, f)

    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    price_lookup_all = {s: prep[s]["close"] for s in prep}

    results = []

    spy_v, spy_inv = sim_spy_dca(price_lookup_all["SPY"], MONTHLY_THB, N_MONTHS)
    results.append(("SPY DCA (pretax, benchmark)", spy_v, spy_inv, None))

    for uni_label, uni_syms in [("DR เดิม 21 ตัว", DR_COVERED_OLD), ("DR ขยาย 47 ตัว", DR_COVERED_EXPANDED)]:
        syms_order = [s for s in uni_syms if s in price_lookup_all]
        for top_n in [3, 5]:
            dca_v, dca_inv = sim_dr_momentum_dca(price_lookup_all, syms_order, MONTHLY_THB, top_n, N_MONTHS)
            lump_v, lump_inv = sim_dr_momentum_lumpsum(price_lookup_all, syms_order, dca_inv, top_n)
            results.append((f"{uni_label} top{top_n} -- DCA เดือนละ 50k", dca_v, dca_inv, None))
            results.append((f"{uni_label} top{top_n} -- Lump-sum {lump_inv:,.0f} วันแรกเทียบเคียง", lump_v, lump_inv, None))

    print(f"{'ทาง':52s} {'เงินลงทุนรวม':>15s} {'มูลค่าสุดท้าย':>15s} {'กำไร':>14s} {'ผลตอบแทน':>10s}")
    print("=" * 112)
    rows = []
    for label, final_v, invested, _ in results:
        profit_pct = (final_v / invested - 1) * 100
        print(f"{label:52s} {invested:15,.0f} {final_v:15,.0f} {final_v-invested:14,.0f} {profit_pct:9.1f}%")
        rows.append(dict(label=label, invested=invested, final_value=final_v, profit_pct=profit_pct))

    pd.DataFrame(rows).to_csv("dca_50k_dr_universe_compare_results.csv", index=False)
    print("\nบันทึกไว้ที่ dca_50k_dr_universe_compare_results.csv")


if __name__ == "__main__":
    main()
