#!/usr/bin/env python
"""
Optimize เงื่อนไข "ออก" หา expectancy สูงสุด — คราวนี้ทำ TP/SL grid ละเอียดขึ้นมาก
+ เพิ่มระดับจำนวนไม้ (slots) ให้กว้างขึ้น เพราะการทดลองก่อนหน้าชี้ชัดว่ายิ่งกระจายไม้มาก
ผลยิ่งดีขึ้นและสม่ำเสมอขึ้น (10 ไม้ชนะทุกคอมโบทั้ง 2 ปี ในการทดลองก่อนหน้า)

วิธีคัดเลือกกันโกงตัวเอง (data snooping) — เรียนบทเรียนจากรอบก่อนที่แชมป์แต่ละปีสลับขั้ว:
  1. หา combo ที่ดีที่สุดจาก TRAIN window (ปีก่อนหน้า) เท่านั้น ห้ามดู TEST ตอนเลือก
  2. เอา top-N จาก train ไปวัดผลจริงบน TEST window (ปีล่าสุด) ที่ไม่เคยดูเลยตอนเลือก
  3. รายงานทั้งคู่คู่กัน — ถ้า train ดีแต่ test แย่ = overfit ให้ทิ้งไป
  4. คัดผู้ชนะจริงจาก "ผลรวม/ผลแย่สุดของทั้ง 2 ช่วง" ไม่ใช่จาก train อย่างเดียว

Exit grid: TP ∈ {5,7,8,10,12,15,20}% × SL ∈ {5,7,8,10,12,15}% (fixed TP/SL)
         + trailing EMA {20,30,50,100} (ไม่มี TP ตายตัว ขี่เทรนด์จนหลุดเส้น)
Slots: 5 / 10 / 15 / 20 / 30
Entry: คงไว้ 3 แบบเดิม (E1 StackNewHigh, E2 StackOnly, E3 TrendMACD)
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

SLOT_LEVELS = [5, 10, 15, 20, 30]
TP_GRID = [0.05, 0.07, 0.08, 0.10, 0.12, 0.15, 0.20]
SL_GRID = [0.05, 0.07, 0.08, 0.10, 0.12, 0.15]
TRAIL_EMA_GRID = [20, 30, 50, 100]


def build_exit_grid():
    exits = {}
    for tp in TP_GRID:
        for sl in SL_GRID:
            exits[f"TP{tp*100:.0f}/SL{sl*100:.0f}"] = dict(tp=tp, sl=sl, trail_ema=None)
    for n in TRAIL_EMA_GRID:
        exits[f"Trail EMA{n}"] = dict(tp=None, sl=0.15, trail_ema=n)  # hard SL -15% กันหายนะ แม้ใช้ trailing
    return exits


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
    prep = {}
    needed_emas = set(TRAIL_EMA_GRID) | {5, 10, 30, 50, 100, 200}
    for sym, close in data.items():
        emas = {n: ema(close, n) for n in needed_emas}
        macd = ema(close, 12) - ema(close, 26)
        yr_high = close.rolling(252, min_periods=60).max()
        stack = (close > emas[5]) & (emas[5] > emas[10]) & (emas[10] > emas[30]) \
            & (emas[30] > emas[50]) & (emas[50] > emas[100]) & (emas[100] > emas[200])
        entries = {
            "E1 StackNewHigh": (stack & (close >= yr_high)).fillna(False),
            "E2 StackOnly":    stack.fillna(False),
            "E3 TrendMACD":    ((close > emas[200]) & (emas[10] > emas[50]) & (emas[50] > emas[200]) & (macd > 0)).fillna(False),
        }
        prep[sym] = dict(close=close, emas=emas, entries=entries)
    return prep


def simulate(prep, syms_order, test_dates, entry_key, exit_cfg, slots):
    capital_usd = CAPITAL_THB / THB_PER_USD
    pos_size = capital_usd / slots
    cash = capital_usd
    positions = {}
    trades = []
    skipped_price = 0
    equity = []
    trail_n = exit_cfg["trail_ema"]

    for dt in test_dates:
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
            elif trail_n and price < float(P["emas"][trail_n].loc[dt]):
                exit_now = True
            if exit_now:
                cash += pos["qty"] * price * (1 - FEE)
                trades.append(chg - 2 * FEE)
                del positions[sym]

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
        maxdd_pct=round(maxdd, 1),
        skip=skipped_price,
    )


def buy_hold_return(prep, test_dates):
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
    exits = build_exit_grid()

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    train_dates = all_dates[-2 * WINDOW_DAYS:-WINDOW_DAYS]   # ปีก่อนหน้า — ใช้เลือก combo เท่านั้น
    test_dates = all_dates[-WINDOW_DAYS:]                    # ปีล่าสุด — held-out ไม่ดูตอนเลือก

    bh_train = buy_hold_return(prep, train_dates)
    bh_test = buy_hold_return(prep, test_dates)
    print(f"TRAIN (ปีก่อนหน้า) {train_dates[0].date()}→{train_dates[-1].date()} · B&H {bh_train:+.1f}%")
    print(f"TEST  (ปีล่าสุด)   {test_dates[0].date()}→{test_dates[-1].date()} · B&H {bh_test:+.1f}%")

    entries = ["E1 StackNewHigh", "E2 StackOnly", "E3 TrendMACD"]
    total = len(entries) * len(exits) * len(SLOT_LEVELS)
    print(f"\nรวม {total} คอมโบ (train เท่านั้นก่อน)...")

    train_rows = []
    done = 0
    for entry_key in entries:
        for xname, xcfg in exits.items():
            for slots in SLOT_LEVELS:
                m = simulate(prep, syms_order, train_dates, entry_key, xcfg, slots)
                train_rows.append(dict(entry=entry_key, exit=xname, slots=slots, **m))
                done += 1
                if done % 100 == 0:
                    print(f"  ...{done}/{total}")

    train_df = pd.DataFrame(train_rows).sort_values("ret_pct", ascending=False)
    train_df.to_csv("exit_optimization_train_results.csv", index=False)

    print("\n" + "=" * 100)
    print(f"TOP 15 จาก TRAIN (ปีก่อนหน้า, B&H {bh_train:+.1f}%) — เลือกจากตรงนี้เท่านั้น")
    print("=" * 100)
    print(train_df.head(15).to_string(index=False))

    # เอา top 15 จาก train ไปวัดผลจริงบน TEST (held-out)
    top15 = train_df.head(15)
    print("\n" + "=" * 100)
    print(f"วัดผล top-15 (จาก train) บน TEST จริง (ปีล่าสุด, B&H {bh_test:+.1f}%) — held-out ไม่เคยดูตอนเลือก")
    print("=" * 100)
    validation_rows = []
    for _, r in top15.iterrows():
        xcfg = exits[r["exit"]]
        m_test = simulate(prep, syms_order, test_dates, r["entry"], xcfg, int(r["slots"]))
        validation_rows.append(dict(
            entry=r["entry"], exit=r["exit"], slots=int(r["slots"]),
            train_ret=r["ret_pct"], train_wr=r["wr"], train_maxdd=r["maxdd_pct"],
            test_ret=m_test["ret_pct"], test_wr=m_test["wr"], test_maxdd=m_test["maxdd_pct"],
            avg_ret=round((r["ret_pct"] + m_test["ret_pct"]) / 2, 1),
            worst_ret=round(min(r["ret_pct"], m_test["ret_pct"]), 1),
        ))
    val_df = pd.DataFrame(validation_rows)
    val_df.to_csv("exit_optimization_validated_results.csv", index=False)
    print(val_df.sort_values("worst_ret", ascending=False).to_string(index=False))

    print("\n" + "=" * 100)
    print("สรุป: robust ที่สุด = worst_ret สูงสุด (กำไรทั้ง 2 ช่วง ไม่ใช่แค่ช่วงที่เลือกมา)")
    best_robust = val_df.sort_values("worst_ret", ascending=False).iloc[0]
    best_avg = val_df.sort_values("avg_ret", ascending=False).iloc[0]
    print(f"Robust สุด: {best_robust['entry']} + {best_robust['exit']} + {best_robust['slots']} ไม้ "
          f"→ train {best_robust['train_ret']:+.1f}% / test {best_robust['test_ret']:+.1f}% "
          f"(แย่สุด {best_robust['worst_ret']:+.1f}%)")
    print(f"เฉลี่ยสูงสุด: {best_avg['entry']} + {best_avg['exit']} + {best_avg['slots']} ไม้ "
          f"→ train {best_avg['train_ret']:+.1f}% / test {best_avg['test_ret']:+.1f}% "
          f"(เฉลี่ย {best_avg['avg_ret']:+.1f}%)")
    print("=" * 100)


if __name__ == "__main__":
    main()
