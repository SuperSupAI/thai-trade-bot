#!/usr/bin/env python
"""
Backtest ย้อนหลังจริงของสูตร growth+quality screen (EPS growth>15%, ROE>12%, EBIT margin>10%, D/E<1.5)
ใช้ข้อมูลงบ SEC EDGAR แบบ point-in-time จริง (ไม่ใช่ค่าปัจจุบันย้อนตัดสินอดีตแบบที่เคยทำก่อนหน้า)

เช็คว่า ณ แต่ละไตรมาสในอดีต หุ้นที่ "ผ่านเกณฑ์ทั้ง 4 ข้อ ณ ตอนนั้น" ทำผลตอบแทน 3 เดือนถัดไปดีกว่า
หุ้นที่ไม่ผ่านเกณฑ์ หรือดีกว่าค่าเฉลี่ยตลาดหรือไม่ -- ตาม TRAIN/VALID/TEST split เดียวกับที่ใช้ทั้งโปรเจกต์
"""
import json
import os
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import US_STOCKS

FACTS_DIR = "sec_facts_cache"
PRICE_CACHE = "us_close_10y_cache.pkl"
FEE = 0.002


def load_facts(sym):
    path = os.path.join(FACTS_DIR, f"{sym}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def value_asof(series, asof_date):
    candidates = [e for e in series if e["filed"] <= asof_date]
    if not candidates:
        return None
    best = max(candidates, key=lambda e: e["end"])
    return best["val"], best["end"]


def prior_year_value(series, current_end):
    cur = pd.Timestamp(current_end)
    best, best_gap = None, None
    for e in series:
        end = pd.Timestamp(e["end"])
        gap_days = (cur - end).days
        if 300 <= gap_days <= 430:
            if best_gap is None or abs(gap_days - 365) < abs(best_gap - 365):
                best, best_gap = e["val"], gap_days
    return best


def compute_metrics_asof(facts, asof_date_str):
    rev = value_asof(facts.get("Revenues", []), asof_date_str)
    ni = value_asof(facts.get("NetIncomeLoss", []), asof_date_str)
    eq = value_asof(facts.get("StockholdersEquity", []), asof_date_str)
    opinc = value_asof(facts.get("OperatingIncomeLoss", []), asof_date_str)
    eps = value_asof(facts.get("EarningsPerShareDiluted", []), asof_date_str)
    liab = value_asof(facts.get("Liabilities", []), asof_date_str)
    if not (rev and ni and eq and opinc and eps and liab):
        return None
    if eq[0] == 0 or rev[0] == 0:
        return None

    roe = ni[0] / eq[0]
    ebit_margin = opinc[0] / rev[0]
    de = liab[0] / eq[0] if eq[0] else None

    eps_series = facts.get("EarningsPerShareDiluted", [])
    prior_eps = prior_year_value(eps_series, eps[1])
    eps_growth = None
    if prior_eps is not None and prior_eps != 0:
        eps_growth = (eps[0] - prior_eps) / abs(prior_eps)

    if de is None or eps_growth is None:
        return None

    passes = (eps_growth > 0.15) and (roe > 0.12) and (ebit_margin > 0.10) and (de < 1.5)
    return dict(roe=roe, ebit_margin=ebit_margin, de=de, eps_growth=eps_growth, passes=passes)


def main():
    with open(PRICE_CACHE, "rb") as f:
        price_data = pickle.load(f)

    rows = []
    n_ok = 0
    for sym in US_STOCKS:
        facts = load_facts(sym)
        if not facts or sym not in price_data:
            continue
        close = price_data[sym]
        n = len(close)
        step = 63
        got_any = False
        for i in range(0, n - step, step):
            dt = close.index[i]
            asof_str = dt.strftime("%Y-%m-%d")
            m = compute_metrics_asof(facts, asof_str)
            if m is None:
                continue
            fwd_ret = float(close.iloc[i + step] / close.iloc[i] - 1) - 2 * FEE
            rows.append(dict(symbol=sym, date=dt, fwd_ret=fwd_ret, **m))
            got_any = True
        if got_any:
            n_ok += 1

    df = pd.DataFrame(rows)
    print(f"ใช้ได้ {n_ok}/{len(US_STOCKS)} หุ้น (มีทั้งราคา + งบ SEC ครบ 6 concept), รวม {len(df)} หุ้น-ไตรมาส\n")
    if df.empty:
        print("ไม่มีข้อมูลพอ")
        return

    df["year"] = df["date"].dt.year
    n = len(df)
    train_cut = df["date"].quantile(0.6)
    valid_cut = df["date"].quantile(0.8)
    train = df[df["date"] <= train_cut]
    valid = df[(df["date"] > train_cut) & (df["date"] <= valid_cut)]
    test = df[df["date"] > valid_cut]

    def report(d, label):
        passed = d[d["passes"]]
        failed = d[~d["passes"]]
        if len(passed) == 0:
            print(f"{label}: ไม่มีไม้ที่ผ่านเกณฑ์เลยในช่วงนี้")
            return
        wr_p = (passed["fwd_ret"] > 0).mean() * 100
        avg_p = passed["fwd_ret"].mean() * 100
        wr_f = (failed["fwd_ret"] > 0).mean() * 100 if len(failed) else float("nan")
        avg_f = failed["fwd_ret"].mean() * 100 if len(failed) else float("nan")
        print(f"{label}: ผ่านเกณฑ์ n={len(passed)} WR={wr_p:.1f}% avg={avg_p:+.2f}%  |  "
              f"ไม่ผ่าน n={len(failed)} WR={wr_f:.1f}% avg={avg_f:+.2f}%")

    print(f"ช่วงข้อมูล: {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"TRAIN ({train['date'].min().date()} -> {train['date'].max().date()}):")
    report(train, "  TRAIN")
    print(f"VALID ({valid['date'].min().date() if len(valid) else 'N/A'} -> {valid['date'].max().date() if len(valid) else 'N/A'}):")
    report(valid, "  VALID")
    print(f"TEST  ({test['date'].min().date() if len(test) else 'N/A'} -> {test['date'].max().date() if len(test) else 'N/A'}):")
    report(test, "  TEST ")

    print("\nรวมทั้งชุด (ไม่แบ่ง TRAIN/VALID/TEST):")
    report(df, "  ALL  ")

    df.to_csv("growth_quality_screen_pointintime_results.csv", index=False)
    print("\nบันทึกไว้ที่ growth_quality_screen_pointintime_results.csv")


if __name__ == "__main__":
    main()
