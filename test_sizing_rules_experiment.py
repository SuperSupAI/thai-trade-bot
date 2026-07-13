#!/usr/bin/env python
"""
การทดลอง: ผลของ "วิธีใส่เงิน (position sizing)" × "เงื่อนไขเข้า" × "เงื่อนไขออก"
ต่อผลตอบแทนจริงของพอร์ตหุ้น US (universe เดียวกับ webull_bot)

ปัจจัยที่ทดลอง (full factorial):
  เงินต่อไม้ (slots): แบ่งทุน 100,000 บาท เป็น 1 / 3 / 5 / 10 ไม้
      slots=1  → ไม้ละ 100,000 (ถือทีละตัวเต็มพอร์ต)
      slots=10 → ไม้ละ 10,000  (กระจาย 10 ตัว)
  เงื่อนไขเข้า 3 แบบ:
      E1 StackNewHigh : EMA เรียง 5>10>30>50>100>200 + ทำ New High รอบ 252 วัน (สูตรบอทปัจจุบัน)
      E2 StackOnly    : EMA เรียงครบอย่างเดียว ไม่ต้องรอ New High
      E3 TrendMACD    : Close>EMA200 & EMA10>EMA50 & EMA50>EMA200 & MACD>0 (สูตร default ใน app.py)
  เงื่อนไขออก 4 แบบ:
      X1 TP5/SL10  : ชนเป้า +5% ขาย / หลุด -10% ตัดขาดทุน (สูตรบอทปัจจุบัน)
      X2 TP15/SL8  : ปล่อยกำไรวิ่งไกลขึ้น เป้า +15% / ตัดที่ -8%
      X3 SL8+EMA50 : ตัดขาดทุน -8% + ขี่เทรนด์จนราคาหลุด EMA50 (ไม่มีเป้ากำไร)
      X4 TP10/SL5  : เป้า +10% / ตัดไว -5%

รวม 4×3×4 = 48 คอมโบ ทดสอบซ้ำ 2 หน้าต่างเวลา (ปีล่าสุด กับ ปีก่อนหน้า) = 96 รอบ
เทียบกับ Buy & Hold แบบถ่วงน้ำหนักเท่ากันของ universe เดียวกันในแต่ละหน้าต่าง

ความสมจริงที่คงไว้:
  - ซื้อได้เฉพาะจำนวนหุ้นเต็มหุ้น (int) → เงินต่อไม้เล็กจะ "ซื้อหุ้นแพงไม่ได้เลย" เหมือนของจริง
    (นับจำนวนสัญญาณที่พลาดเพราะเงินไม่พอไว้ในคอลัมน์ skip)
  - ค่าธรรมเนียม 0.2%/ข้าง · อัตราแลกเปลี่ยน 35.5 บาท/USD
  - ลำดับเลือกหุ้นเมื่อสัญญาณชนกัน = ลำดับใน US_STOCKS (deterministic ทุกคอมโบ เท่าเทียมกัน)

ดาวน์โหลดข้อมูลครั้งเดียว (4 ปี เพื่อให้ปีก่อนหน้ามี warm-up EMA200 พอ) แล้ว cache เป็น pickle
รันซ้ำครั้งต่อไปไม่ต้องโหลดใหม่
"""
import os
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from safe_fetch import safe_download_one
from universe import US_STOCKS

CACHE_FILE = "us_close_4y_cache.pkl"
CAPITAL_THB = 100_000
THB_PER_USD = 35.5
FEE = 0.002
YEARS_DOWNLOAD = 4
WINDOW_DAYS = 252

SLOT_LEVELS = [1, 3, 5, 10]

EXITS = {
    "X1 TP5/SL10":  dict(tp=0.05, sl=0.10, trail_ema=None),
    "X2 TP15/SL8":  dict(tp=0.15, sl=0.08, trail_ema=None),
    "X3 SL8+EMA50": dict(tp=None, sl=0.08, trail_ema=50),
    "X4 TP10/SL5":  dict(tp=0.10, sl=0.05, trail_ema=None),
}


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def load_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
        print(f"ใช้ cache เดิม: {len(data)} ตัว ({CACHE_FILE})")
        return data
    print(f"โหลดหุ้น US {len(US_STOCKS)} ตัว ({YEARS_DOWNLOAD} ปี)...")
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


def precompute(data):
    """คำนวณ indicator + สัญญาณเข้าทุกแบบ ล่วงหน้าตัวละครั้งเดียว"""
    prep = {}
    for sym, close in data.items():
        e5, e10, e30, e50, e100, e200 = (ema(close, n) for n in (5, 10, 30, 50, 100, 200))
        macd = ema(close, 12) - ema(close, 26)
        yr_high = close.rolling(252, min_periods=60).max()
        stack = (close > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200)
        entries = {
            "E1 StackNewHigh": (stack & (close >= yr_high)).fillna(False),
            "E2 StackOnly":    stack.fillna(False),
            "E3 TrendMACD":    ((close > e200) & (e10 > e50) & (e50 > e200) & (macd > 0)).fillna(False),
        }
        prep[sym] = dict(close=close, ema50=e50, entries=entries)
    return prep


def simulate(prep, syms_order, test_dates, entry_key, exit_cfg, slots):
    """จำลองพอร์ต: ถือได้พร้อมกัน `slots` ไม้ ไม้ละ CAPITAL/slots (USD)
    คืน metrics + equity curve"""
    capital_usd = CAPITAL_THB / THB_PER_USD
    pos_size = capital_usd / slots
    cash = capital_usd
    positions = {}   # sym -> dict(qty, entry_price)
    trades = []      # pnl_pct ต่อไม้ (หลังหักค่าธรรมเนียม)
    skipped_price = 0  # สัญญาณที่พลาดเพราะเงินต่อไม้ซื้อไม่ได้แม้ 1 หุ้น
    equity = []

    for dt in test_dates:
        # 1) เช็คออก
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            pos = positions[sym]
            chg = price / pos["entry_price"] - 1
            exit_now = False
            if chg <= -exit_cfg["sl"]:
                exit_now = True
            elif exit_cfg["tp"] is not None and chg >= exit_cfg["tp"]:
                exit_now = True
            elif exit_cfg["trail_ema"] and price < float(P["ema50"].loc[dt]):
                exit_now = True
            if exit_now:
                cash += pos["qty"] * price * (1 - FEE)
                trades.append(chg - 2 * FEE)
                del positions[sym]

        # 2) เข้าใหม่เท่าที่มีช่องว่าง
        if len(positions) < slots:
            for sym in syms_order:
                if len(positions) >= slots:
                    break
                if sym in positions or sym not in prep:
                    continue
                P = prep[sym]
                if dt not in P["close"].index or not bool(P["entries"][entry_key].loc[dt]):
                    continue
                price = float(P["close"].loc[dt])
                budget = min(pos_size, cash)
                qty = int((budget * (1 - FEE)) / price)
                if qty < 1:
                    skipped_price += 1
                    continue
                cash -= qty * price * (1 + FEE)
                positions[sym] = dict(qty=qty, entry_price=price)

        # 3) mark-to-market
        val = cash
        for sym, pos in positions.items():
            series = prep[sym]["close"]
            px = float(series.loc[dt]) if dt in series.index else float(series[series.index <= dt].iloc[-1])
            val += pos["qty"] * px
        equity.append(val)

    eq = pd.Series(equity)
    maxdd = (eq / eq.cummax() - 1).min() * 100 if len(eq) else 0.0
    final = eq.iloc[-1] if len(eq) else capital_usd
    wins = sum(1 for t in trades if t > 0)
    return dict(
        trades=len(trades),
        wr=round(wins / len(trades) * 100, 1) if trades else np.nan,
        ret_pct=round((final / capital_usd - 1) * 100, 1),
        final_thb=round(final * THB_PER_USD),
        maxdd_pct=round(maxdd, 1),
        skip=skipped_price,
    )


def buy_hold_return(prep, test_dates):
    """Buy & Hold ถ่วงน้ำหนักเท่ากันทุกตัวใน universe ช่วงเดียวกัน (%)"""
    rets = []
    d0, d1 = test_dates[0], test_dates[-1]
    for sym, P in prep.items():
        c = P["close"]
        seg = c[(c.index >= d0) & (c.index <= d1)]
        if len(seg) > WINDOW_DAYS // 2:
            rets.append(seg.iloc[-1] / seg.iloc[0] - 1)
    return round(float(np.mean(rets)) * 100, 1) if rets else np.nan


def main():
    data = load_data()
    prep = precompute(data)
    syms_order = [s for s in US_STOCKS if s in prep]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    windows = {
        "ปีล่าสุด":  all_dates[-WINDOW_DAYS:],
        "ปีก่อนหน้า": all_dates[-2 * WINDOW_DAYS:-WINDOW_DAYS],
    }

    rows = []
    total = len(windows) * len(EXITS) * 3 * len(SLOT_LEVELS)
    done = 0
    for wname, dates in windows.items():
        bh = buy_hold_return(prep, dates)
        print(f"\nหน้าต่าง {wname}: {dates[0].date()} → {dates[-1].date()} · B&H เฉลี่ย {bh:+.1f}%")
        for entry_key in ["E1 StackNewHigh", "E2 StackOnly", "E3 TrendMACD"]:
            for xname, xcfg in EXITS.items():
                for slots in SLOT_LEVELS:
                    m = simulate(prep, syms_order, dates, entry_key, xcfg, slots)
                    rows.append(dict(window=wname, bh_pct=bh, entry=entry_key, exit=xname,
                                     slots=slots, **m))
                    done += 1
                    if done % 12 == 0:
                        print(f"  ...{done}/{total} คอมโบ")

    df = pd.DataFrame(rows)
    df.to_csv("sizing_rules_experiment_results.csv", index=False)

    pd.set_option("display.width", 200)
    for wname in windows:
        sub = df[df.window == wname]
        print("\n" + "=" * 110)
        print(f"ผลทั้งหมด — หน้าต่าง {wname} (B&H เฉลี่ย {sub.bh_pct.iloc[0]:+.1f}%) · เรียงตามผลตอบแทน")
        print("=" * 110)
        cols = ["entry", "exit", "slots", "trades", "wr", "ret_pct", "maxdd_pct", "skip"]
        print(sub.sort_values("ret_pct", ascending=False)[cols].to_string(index=False))

    # pivot สรุปมุมมองหลัก
    print("\n" + "=" * 110)
    print("ค่าเฉลี่ยผลตอบแทน (%) ข้ามทั้ง 2 หน้าต่าง — แยกตาม เงื่อนไขออก × จำนวนไม้")
    print("=" * 110)
    print(df.pivot_table(values="ret_pct", index="exit", columns="slots", aggfunc="mean").round(1).to_string())

    print("\nค่าเฉลี่ยผลตอบแทน (%) — แยกตาม เงื่อนไขเข้า × จำนวนไม้")
    print(df.pivot_table(values="ret_pct", index="entry", columns="slots", aggfunc="mean").round(1).to_string())

    print("\nค่าเฉลี่ยผลตอบแทน (%) — แยกตาม เงื่อนไขเข้า × เงื่อนไขออก")
    print(df.pivot_table(values="ret_pct", index="entry", columns="exit", aggfunc="mean").round(1).to_string())

    print("\nบันทึกผลดิบทุกคอมโบไว้ที่ sizing_rules_experiment_results.csv")


if __name__ == "__main__":
    main()
