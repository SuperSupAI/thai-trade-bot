#!/usr/bin/env python
"""
ทดสอบความน่าเชื่อถือของกลยุทธ์ "EMA Stack (5>10>30>50>100>200) + New High 1 ปี"
เข้า / "EMA30 ตัดลง EMA50" ออก ที่หน้าเว็บโชว์ผล +71.3% แต่มีแค่ 8 ไม้

ดึง build_and_sim ตรงจาก app.py (ผ่าน ast) เพื่อให้ตรงกับ logic ที่ deploy จริง 100%
ไม่ได้ copy สูตรมาเขียนใหม่ (กันพลาดเรื่อง logic ไม่ตรงกัน)

แผนทดสอบ:
  1) รายไม้ทั้งหมดใน SET100 5 ปี — เช็คว่ากระจุกอยู่ไม่กี่ตัวหรือกระจายจริง
  2) แบ่งครึ่งเวลา (2.5 ปีแรก / 2.5 ปีหลัง) รันแยกกัน — เช็คว่าได้ผลดีทั้งสองช่วง
     หรือดีแค่ช่วงใดช่วงหนึ่ง (สัญญาณของ "ได้ผลเพราะช่วงตลาดขาขึ้นพอดี" ไม่ใช่ edge จริง)
  3) เทียบ SET100 ทั้งหมด vs SET Index ทั้งหมด (~900 ตัว) — เช็คว่า sample ใหญ่ขึ้นแล้วผลยังทรงตัวไหม
"""
import ast
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import group_symbols
from safe_fetch import safe_download_one

# ── ดึง build_and_sim (+ dependency functions) ตรงจาก app.py ──
src = open("app.py", encoding="utf-8").read()
tree = ast.parse(src)
needed = {"ema", "rsi", "find_pivots", "find_hh_hl_breakout_signal", "build_and_sim"}
mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed],
                  type_ignores=[])
ns = {"np": np, "pd": pd, "CUT": 0.08}  # CUT = SL -8%, referenced as a module-level global in build_and_sim
exec(compile(mod, "app.py", "exec"), ns)
build_and_sim = ns["build_and_sim"]

FEE = 0.002
YEARS = 5


def run_one(close, setclose):
    """คืน (total_return, trades_list) จาก build_and_sim ด้วยสูตร EMA Stack + EMA30<50 exit"""
    df, events, m = build_and_sim(close, setclose, FEE, use_scaling=False, use_ema_cross=False,
                                   use_hh_hl=False, use_ema5_trail=False,
                                   use_ema_stack=True, use_ema30_50_exit=True)
    return m["total"], m["bh"], m["trades"]


def load_universe(years, group_name="SET100 (ทั้งหมด)"):
    syms = group_symbols(group_name)
    data = {}
    for s in syms:
        c = safe_download_one(s, years)
        if c is not None and len(c) > 210:
            data[s] = c
    return data


def part1_trade_detail(data, setclose):
    print("=" * 78)
    print("1) รายละเอียดไม้ทั้งหมด (SET100, 5 ปี) — เช็คการกระจุกตัว")
    print("=" * 78)
    rows = []
    for sym, close in data.items():
        total, bh, trades = run_one(close, setclose)
        for t in trades:
            entry_date = close.index[t["entry_i"]]
            exit_date = close.index[t["exit_i"]] if t["exit_i"] is not None else None
            rows.append(dict(หุ้น=sym.replace(".BK", ""), เข้า=entry_date.date(),
                             ออก=exit_date.date() if exit_date else "ถือ", เหตุออก=t["reason"],
                             กำไร_pct=round(t["pnl"] * 100, 1)))
    tdf = pd.DataFrame(rows).sort_values("เข้า")
    print(tdf.to_string(index=False) if not tdf.empty else "ไม่มีไม้เลย")
    print(f"\nรวม {len(tdf)} ไม้ จาก {tdf['หุ้น'].nunique() if not tdf.empty else 0} หุ้นต่างกัน")
    if not tdf.empty:
        print("จำนวนไม้ต่อหุ้น:")
        print(tdf["หุ้น"].value_counts().to_string())
    return tdf


def part2_time_split(data, setclose):
    print("\n" + "=" * 78)
    print("2) แบ่งครึ่งเวลา 2.5 ปีแรก vs 2.5 ปีหลัง — เช็คว่าดีสม่ำเสมอหรือฟลุคช่วงเดียว")
    print("=" * 78)
    for label, take in [("2.5 ปีแรก", lambda c: c.iloc[:len(c)//2]),
                        ("2.5 ปีหลัง", lambda c: c.iloc[len(c)//2:])]:
        rets, bhs, nbeat, ntrade = [], [], 0, 0
        for sym, close in data.items():
            sub = take(close)
            if len(sub) < 210:
                continue
            sc_sub = setclose.reindex(sub.index).ffill() if setclose is not None else None
            total, bh, trades = run_one(sub, sc_sub)
            rets.append(total); bhs.append(bh); ntrade += len(trades)
            if total > bh:
                nbeat += 1
        n = len(rets)
        print(f"\n[{label}] หุ้นที่ทดสอบ {n} ตัว · ไม้รวม {ntrade}")
        if n:
            print(f"  ผลตอบแทนเฉลี่ย: กลยุทธ์ {np.mean(rets)*100:+.1f}% · B&H {np.mean(bhs)*100:+.1f}% · "
                  f"ชนะ B&H {nbeat}/{n} ตัว")
        else:
            print("  ไม่มีข้อมูลพอทดสอบ")


def part3_bigger_universe(setclose):
    print("\n" + "=" * 78)
    print("3) ขยาย universe เป็น SET Index ทั้งหมด (~900 ตัว) — เช็คว่า sample ใหญ่ขึ้นผลยังทรงตัวไหม")
    print("   (จำกัดตัวอย่างสุ่ม 150 ตัวแรกที่ดาวน์โหลดได้ กันใช้เวลานานเกิน)")
    print("=" * 78)
    syms = group_symbols("SET Index")[:150]
    rets, bhs, nbeat, ntrade, nstock = [], [], 0, 0, 0
    for s in syms:
        c = safe_download_one(s, YEARS)
        if c is None or len(c) < 210:
            continue
        total, bh, trades = run_one(c, setclose)
        nstock += 1
        rets.append(total); bhs.append(bh); ntrade += len(trades)
        if total > bh:
            nbeat += 1
    print(f"หุ้นที่ทดสอบได้ {nstock} ตัว (จาก {len(syms)} ที่สุ่มมา) · ไม้รวม {ntrade}")
    if nstock:
        print(f"ผลตอบแทนเฉลี่ย: กลยุทธ์ {np.mean(rets)*100:+.1f}% · B&H {np.mean(bhs)*100:+.1f}% · "
              f"ชนะ B&H {nbeat}/{nstock} ตัว")


def main():
    print("โหลดข้อมูล SET100 (5 ปี)...")
    data = load_universe(YEARS, "SET100 (ทั้งหมด)")
    print(f"ใช้ได้ {len(data)} ตัว")
    setclose = safe_download_one("^SET.BK", YEARS)

    part1_trade_detail(data, setclose)
    part2_time_split(data, setclose)
    part3_bigger_universe(setclose)


if __name__ == "__main__":
    main()
