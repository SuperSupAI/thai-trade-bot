#!/usr/bin/env python
"""
ลองเอากลยุทธ์ E4 (Close>EMA200 เข้า) + Exit F (Close<EMA200 ออก, ไม่มีเพดานกำไร, hard stop -20%)
ที่เพิ่งเอาชนะ SPY ได้ ไปทดสอบกับหุ้นรายตัวใน 2 ตลาด:
  - ไต้หวัน: B&H ดัชนี (EWT) ชนะ SPY อยู่แล้ว (+481.8%) — กลยุทธ์จะช่วยเพิ่มได้อีกไหม หรือแค่กวนน้ำ
  - จีน: B&H ดัชนี (MCHI) แย่มาก (+43.5%, MaxDD -62.8%) — กลยุทธ์ trend-following น่าจะช่วยหลบช่วงร่วงหนักได้
    (สมมติฐาน: ตลาดผันผวน/ขาลงยาว เป็นจุดที่กลยุทธ์แบบนี้น่าจะช่วยได้มากกว่าตลาดขาขึ้นเรียบๆ แบบไต้หวัน)
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
import test_exit_optimization as teo
from test_beat_spy_v2 import sim_e4_trendexit
from test_entry_variants import add_extra_signals

YEARS = 10
CAPITAL_THB = 100_000

TAIWAN_STOCKS = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2412.TW", "1301.TW",
    "2881.TW", "2882.TW", "1216.TW", "2891.TW", "2303.TW", "3711.TW", "2002.TW", "2886.TW",
]
CHINA_STOCKS = [
    "BABA", "PDD", "JD", "BIDU", "NTES", "TCEHY", "LI", "NIO", "XPEV", "BILI",
    "TME", "YUMC", "ZTO", "TAL", "EDU",
]
BENCH = {"ไต้หวัน": "EWT", "จีน": "MCHI"}


def load_universe(symbols, label):
    print(f"โหลดหุ้น {label}: {len(symbols)} ตัว ({YEARS} ปี)...")
    data = {}
    for sym in symbols:
        c = safe_download_one(sym, YEARS)
        if c is not None and len(c) > 500:
            data[sym] = c
        else:
            print(f"  {sym}: โหลดไม่ได้/ข้อมูลสั้นไป ข้าม")
    print(f"  ใช้ได้ {len(data)}/{len(symbols)} ตัว")
    return data


def basket_bh(data, all_dates):
    rets = []
    for sym, c in data.items():
        seg = c[(c.index >= all_dates[0]) & (c.index <= all_dates[-1])]
        if len(seg) > 200:
            rets.append(seg.iloc[-1] / seg.iloc[0] - 1)
    return round(float(np.mean(rets)) * 100, 1) if rets else float("nan")


def run_market(label, symbols, bench_sym):
    data = load_universe(symbols, label)
    if len(data) < 5:
        print(f"หุ้น {label} โหลดได้น้อยเกินไป ข้ามตลาดนี้\n")
        return None
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = list(prep.keys())
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))

    bh_basket = basket_bh(data, all_dates)
    bench = safe_download_one(bench_sym, YEARS)
    bench_seg = bench[(bench.index >= all_dates[0]) & (bench.index <= all_dates[-1])]
    bench_ret = round((bench_seg.iloc[-1] / bench_seg.iloc[0] - 1) * 100, 1)

    print(f"\n{'='*70}\n{label}: {all_dates[0].date()} → {all_dates[-1].date()}\n{'='*70}")
    print(f"B&H เฉลี่ยหุ้นในตะกร้า ({len(data)} ตัว): {bh_basket:+.1f}%")
    print(f"B&H ดัชนี ETF ({bench_sym}): {bench_ret:+.1f}%")

    rows = [(f"B&H ตะกร้าหุ้น {label}", bh_basket), (f"B&H ETF ดัชนี {bench_sym}", bench_ret)]
    for slots in [5, 10]:
        m = sim_e4_trendexit(prep, syms_order, all_dates, slots, capital_thb=CAPITAL_THB)
        label2 = f"E4+ExitF {label} {slots} ไม้"
        print(f"{label2:30s} → {m['ret_pct']:+7.1f}%  ·  ไม้ {m['trades']:4d}  ·  win rate {m['wr']:5.1f}%")
        rows.append((label2, m["ret_pct"]))
    return rows


def main():
    all_rows = []
    for label, symbols in [("ไต้หวัน", TAIWAN_STOCKS), ("จีน", CHINA_STOCKS)]:
        rows = run_market(label, symbols, BENCH[label])
        if rows:
            all_rows += rows

    print("\n" + "=" * 70)
    print("สรุปเทียบทั้งหมด (10 ปี, ทุน 100,000 บาท) — อ้างอิง SPY +315.3%, E4+ExitF US 5ไม้ +430.5%")
    print("=" * 70)
    df = pd.DataFrame(all_rows, columns=["variant", "ret_pct"]).sort_values("ret_pct", ascending=False)
    print(df.to_string(index=False))
    df.to_csv("asia_taiwan_china_results.csv", index=False)


if __name__ == "__main__":
    main()
