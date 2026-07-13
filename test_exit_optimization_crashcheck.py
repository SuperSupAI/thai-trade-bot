#!/usr/bin/env python
"""
เช็ค robustness ของผู้ชนะ (E3 TrendMACD + Trail EMA100 + 10 ไม้) กับสูตรเทียบ
บนตลาดขาลงจริง 2 รอบที่รุนแรงที่สุดในรอบ 10 ปี:
  - 2020 COVID crash: ม.ค.-ธ.ค. 2020 (ร่วง ~35% ใน 5 สัปดาห์ ก.พ.-มี.ค. แล้วฟื้นตัวรูปตัว V)
  - 2022 Fed hiking bear market: ม.ค.-ธ.ค. 2022 (S&P500 -19%, Nasdaq -33% ตลอดทั้งปี ไม่มี V-shape)
โหลดข้อมูลยาวขึ้น (8 ปี) เพื่อให้มี warm-up ของ EMA200 ก่อนเข้าปี 2020 พอสมควร
"""
import os
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
from universe import US_STOCKS
from test_exit_optimization import precompute, simulate, buy_hold_return, build_exit_grid

CACHE_FILE = "us_close_8y_cache.pkl"
YEARS_DOWNLOAD = 8

CHECK_COMBOS = [
    ("E3 TrendMACD", "Trail EMA100", 10, "ผู้ชนะจาก grid search"),
    ("E3 TrendMACD", "TP12/SL15", 10, "อันดับ 2 (สม่ำเสมอกว่า)"),
    ("E1 StackNewHigh", "TP5/SL10", 10, "สูตรบอทปัจจุบัน"),
    ("E1 StackNewHigh", "Trail EMA50", 10, "trailing แบบเดิม"),
]


def load_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
        print(f"ใช้ cache เดิม: {len(data)} ตัว ({CACHE_FILE})")
        return data
    print(f"โหลดหุ้น US {len(US_STOCKS)} ตัว ({YEARS_DOWNLOAD} ปี) — ใช้เวลานานกว่าปกติเพราะข้อมูลยาวขึ้น...")
    data = {}
    for i, sym in enumerate(US_STOCKS):
        c = safe_download_one(sym, YEARS_DOWNLOAD)
        if c is not None and len(c) > 600:
            data[sym] = c
        if (i + 1) % 20 == 0:
            print(f"  โหลดแล้ว {i+1}/{len(US_STOCKS)}...")
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"ใช้ได้ {len(data)} ตัว (cache ไว้ที่ {CACHE_FILE})")
    return data


def main():
    data = load_data()
    prep = precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    earliest = all_dates[0]
    print(f"ข้อมูลมีตั้งแต่ {earliest.date()} ถึง {all_dates[-1].date()} ({len(all_dates)} วันเทรด)")

    def window(d0, d1):
        return [d for d in all_dates if pd.Timestamp(d0) <= d <= pd.Timestamp(d1)]

    windows = {
        "2020 COVID crash (ม.ค.-ธ.ค. 2020)": window("2020-01-01", "2020-12-31"),
        "2022 Fed hiking bear (ม.ค.-ธ.ค. 2022)": window("2022-01-01", "2022-12-31"),
    }

    rows = []
    for wname, dates in windows.items():
        if len(dates) < 100:
            print(f"\n⚠️ {wname}: มีข้อมูลไม่พอ ({len(dates)} วัน) ข้ามหน้าต่างนี้ (อาจ warm-up EMA200 ไม่ทัน)")
            continue
        bh = buy_hold_return(prep, dates)
        print(f"\n{wname}: {dates[0].date()} → {dates[-1].date()} ({len(dates)} วัน) · B&H {bh:+.1f}%")
        for entry_key, exit_name, slots, label in CHECK_COMBOS:
            m = simulate(prep, syms_order, dates, entry_key, exits[exit_name], slots)
            rows.append(dict(window=wname, bh=bh, combo=label, entry=entry_key, exit=exit_name,
                             slots=slots, **m))
            print(f"  {label:30s} → ret {m['ret_pct']:+6.1f}%  wr {m['wr']:5.1f}%  "
                  f"maxdd {m['maxdd_pct']:6.1f}%  trades {m['trades']:3d}  skip {m['skip']:3d}")

    if not rows:
        print("\nไม่มีหน้าต่างไหนมีข้อมูลพอเลย — ข้อมูลที่โหลดมาอาจสั้นไป")
        return

    df = pd.DataFrame(rows)
    df.to_csv("exit_optimization_crashcheck_results.csv", index=False)

    print("\n" + "=" * 100)
    print("สรุป: ผลตอบแทนแต่ละคอมโบ บนตลาดขาลงจริง (แถว = คอมโบ, คอลัมน์ = หน้าต่างเวลา)")
    print("=" * 100)
    pivot = df.pivot_table(values="ret_pct", index="combo", columns="window", aggfunc="first")
    print(pivot.round(1).to_string())
    print("\n(เทียบ B&H ของแต่ละช่วง ดูจาก log ด้านบน — ถ้าคอมโบไหนบวกได้ในช่วง B&H ติดลบหนัก = ทนตลาดหมีได้จริง)")


if __name__ == "__main__":
    main()
