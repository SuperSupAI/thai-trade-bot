"""
Backtest starter — กลยุทธ์ SMA Crossover (long-only) สำหรับหุ้นไทย
พิสูจน์กลยุทธ์ก่อนเอาเงินจริงเข้า · เทียบกับ Buy & Hold เสมอ

ใช้:
  python backtest.py --symbol PIMO.BK --years 5 --fast 20 --slow 50

หมายเหตุ:
- long-only (หุ้นไทย short ยาก)
- รวมค่าธรรมเนียม ~0.2%/ข้าง (fee) ในการคำนวณ
- yfinance หุ้นไทยอาจดีเลย์/ข้อมูลไม่ครบ — ของจริงใช้ข้อมูล Settrade
"""
import argparse
import sys
import numpy as np
import pandas as pd

# กันภาษาไทยพังบน Windows console (cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load(symbol, years):
    import yfinance as yf
    df = yf.download(symbol, period=f"{years}y", interval="1d",
                     auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise SystemExit(f"ไม่มีข้อมูล {symbol} (ลองสัญลักษณ์อื่น หรือเช็กเน็ต)")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):   # กรณี yfinance คืน multiindex
        close = close.iloc[:, 0]
    return pd.DataFrame({"close": close}).dropna()


def backtest(df, fast, slow, fee=0.002):
    df = df.copy()
    df["sma_f"] = df["close"].rolling(fast).mean()
    df["sma_s"] = df["close"].rolling(slow).mean()
    # สัญญาณ: fast > slow = ถือหุ้น (1) · เข้าตำแหน่ง "วันถัดไป" กันมองอนาคต
    df["signal"] = (df["sma_f"] > df["sma_s"]).astype(float)
    df["pos"] = df["signal"].shift(1).fillna(0.0)

    df["ret"] = df["close"].pct_change().fillna(0.0)
    df["strat"] = df["pos"] * df["ret"]
    # ค่าธรรมเนียมเมื่อสถานะเปลี่ยน (ซื้อ/ขาย)
    df["trade"] = df["pos"].diff().abs().fillna(0.0)
    df["strat"] -= df["trade"] * fee

    df["equity"] = (1 + df["strat"]).cumprod()
    df["bh"] = (1 + df["ret"]).cumprod()
    return df


def per_trade(df, fee=0.002):
    """คืน list ผลตอบแทนต่อไม้ (เข้า→ออก)"""
    trades, in_pos, entry = [], False, 0.0
    for price, pos in zip(df["close"].values, df["pos"].values):
        if pos == 1 and not in_pos:
            in_pos, entry = True, price
        elif pos == 0 and in_pos:
            in_pos = False
            trades.append(price / entry - 1 - 2 * fee)
    if in_pos:  # ยังถืออยู่ ปิดที่ราคาล่าสุด
        trades.append(df["close"].values[-1] / entry - 1 - fee)
    return trades


def report(df, symbol, fast, slow, fee):
    eq = df["equity"]
    n = len(df)
    years = n / 252 if n else 0
    total = eq.iloc[-1] - 1
    bh_total = df["bh"].iloc[-1] - 1
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    maxdd = (eq / eq.cummax() - 1).min()
    bh_maxdd = (df["bh"] / df["bh"].cummax() - 1).min()
    tr = per_trade(df, fee)
    wins = [t for t in tr if t > 0]
    winrate = (len(wins) / len(tr) * 100) if tr else 0

    p = lambda x: f"{x*100:+.1f}%"
    print(f"\n{'='*46}")
    print(f" {symbol}  SMA({fast}/{slow})  · {years:.1f} ปี · fee {fee*100:.1f}%/ข้าง")
    print(f"{'='*46}")
    print(f" {'ผลตอบแทนรวม (บอต)':<24} {p(total)}")
    print(f" {'ผลตอบแทนรวม (Buy&Hold)':<24} {p(bh_total)}  <- ต้องชนะอันนี้")
    print(f" {'CAGR (บอต/ปี)':<24} {p(cagr)}")
    print(f" {'Max Drawdown (บอต)':<24} {p(maxdd)}")
    print(f" {'Max Drawdown (B&H)':<24} {p(bh_maxdd)}")
    print(f" {'จำนวนไม้':<24} {len(tr)}")
    print(f" {'Win rate':<24} {winrate:.0f}%")
    print(f"{'='*46}")
    verdict = "✅ ชนะ Buy&Hold" if total > bh_total else "❌ แพ้ Buy&Hold — ยังไม่คุ้ม"
    print(f" สรุป: {verdict}")
    print(" (ชนะครั้งเดียวไม่พอ — ลองหลายตัว/หลายช่วงเวลา กัน overfit)\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PIMO.BK")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--fast", type=int, default=20)
    ap.add_argument("--slow", type=int, default=50)
    ap.add_argument("--fee", type=float, default=0.002)
    args = ap.parse_args()

    if args.fast >= args.slow:
        raise SystemExit("fast ต้องน้อยกว่า slow")

    df = load(args.symbol, args.years)
    df = backtest(df, args.fast, args.slow, args.fee)
    report(df, args.symbol, args.fast, args.slow, args.fee)


if __name__ == "__main__":
    main()
