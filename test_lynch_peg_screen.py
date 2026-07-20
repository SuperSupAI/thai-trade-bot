#!/usr/bin/env python
"""
ทดสอบสไตล์ Peter Lynch "ten-bagger" screen: PEG ratio < 1 (P/E หารด้วยอัตราการเติบโต %) + EPS growth > 20%
ใช้ point-in-time จริงจาก SEC EDGAR (P/E คำนวณจากราคาจริง ณ วันนั้น หารด้วย EPS ที่ยื่นแล้ว ณ วันนั้น)

ข้อจำกัดที่ยังมีอยู่: ไม่ได้เช็ค "institutional ownership ต่ำ" และ "market cap เล็ก-กลาง" ตามที่ Lynch ใช้จริง
เพราะ SEC EDGAR ไม่มี field เหล่านี้ตรงๆ (institutional ownership ต้อง derive จาก 13F ซับซ้อนกว่ามาก)
เทสได้แค่มิติ valuation-vs-growth (PEG) ซึ่งเป็น point-in-time ถูกต้อง
"""
import json
import os
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from universe import US_STOCKS
from test_growth_quality_screen_pointintime import load_facts, value_asof, prior_year_value

PRICE_CACHE = "us_close_10y_cache.pkl"
FEE = 0.002


def compute_peg_asof(facts, price, asof_date_str):
    eps = value_asof(facts.get("EarningsPerShareDiluted", []), asof_date_str)
    if not eps or eps[0] is None or eps[0] <= 0:
        return None
    prior_eps = prior_year_value(facts.get("EarningsPerShareDiluted", []), eps[1])
    if prior_eps is None or prior_eps <= 0:
        return None
    eps_growth = (eps[0] - prior_eps) / prior_eps
    if eps_growth <= 0:
        return None
    pe = price / eps[0]
    peg = pe / (eps_growth * 100)
    passes = (peg < 1.0) and (eps_growth > 0.20)
    return dict(pe=pe, eps_growth=eps_growth, peg=peg, passes=passes)


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
            price = float(close.iloc[i])
            m = compute_peg_asof(facts, price, asof_str)
            if m is None:
                continue
            fwd_ret = float(close.iloc[i + step] / close.iloc[i] - 1) - 2 * FEE
            rows.append(dict(symbol=sym, date=dt, fwd_ret=fwd_ret, **m))
            got_any = True
        if got_any:
            n_ok += 1

    df = pd.DataFrame(rows)
    print(f"ใช้ได้ {n_ok}/{len(US_STOCKS)} หุ้น, รวม {len(df)} หุ้น-ไตรมาส (ต้องมี EPS โต + เป็นบวก ถึงคำนวณ PEG ได้)\n")
    if df.empty:
        print("ไม่มีข้อมูลพอ")
        return

    train_cut = df["date"].quantile(0.6)
    valid_cut = df["date"].quantile(0.8)
    train = df[df["date"] <= train_cut]
    valid = df[(df["date"] > train_cut) & (df["date"] <= valid_cut)]
    test = df[df["date"] > valid_cut]

    def report(d, label):
        passed = d[d["passes"]]
        failed = d[~d["passes"]]
        if len(passed) == 0:
            print(f"{label}: ไม่มีไม้ที่ผ่านเกณฑ์เลยในช่วงนี้ (n ทั้งหมด={len(d)})")
            return
        wr_p = (passed["fwd_ret"] > 0).mean() * 100
        avg_p = passed["fwd_ret"].mean() * 100
        wr_f = (failed["fwd_ret"] > 0).mean() * 100 if len(failed) else float("nan")
        avg_f = failed["fwd_ret"].mean() * 100 if len(failed) else float("nan")
        print(f"{label}: PEG<1+โต>20% n={len(passed)} WR={wr_p:.1f}% avg={avg_p:+.2f}%  |  "
              f"อื่นๆ n={len(failed)} WR={wr_f:.1f}% avg={avg_f:+.2f}%")

    print(f"ช่วงข้อมูล: {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"TRAIN ({train['date'].min().date()} -> {train['date'].max().date()}):")
    report(train, "  TRAIN")
    if len(valid):
        print(f"VALID ({valid['date'].min().date()} -> {valid['date'].max().date()}):")
        report(valid, "  VALID")
    if len(test):
        print(f"TEST  ({test['date'].min().date()} -> {test['date'].max().date()}):")
        report(test, "  TEST ")

    print("\nรวมทั้งชุด:")
    report(df, "  ALL  ")

    passed_all = df[df["passes"]].sort_values("peg")
    print(f"\nตัวอย่างหุ้น-ไตรมาสที่ผ่านเกณฑ์ PEG<1 ต่ำสุด 10 อันดับ:")
    for _, r in passed_all.head(10).iterrows():
        print(f"  {r['symbol']:6s} {r['date'].date()}  PEG={r['peg']:.2f}  P/E={r['pe']:.1f}  "
              f"EPS growth={r['eps_growth']*100:+.0f}%  fwd 3m={r['fwd_ret']*100:+.1f}%")

    df.to_csv("lynch_peg_screen_pointintime_results.csv", index=False)
    print("\nบันทึกไว้ที่ lynch_peg_screen_pointintime_results.csv")


if __name__ == "__main__":
    main()
