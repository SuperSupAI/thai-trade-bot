"""
Parameter Optimizer - หาเงื่อนไขที่กำไรสูงสุดสำหรับแต่ละหุ้น
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


def ema(s, n):
    """Calculate exponential moving average"""
    return s.ewm(span=n, adjust=False).mean()


def rsi(s, p=14):
    """Calculate RSI"""
    d = s.diff()
    up = d.clip(lower=0).rolling(p).mean()
    dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def optimize_parameters(close, setclose=None, fee=0.002):
    """
    Test multiple entry/exit conditions และหา best performer
    Return: {condition_name, entry_params, exit_params, total_return, win_rate, max_dd}
    """

    df = pd.DataFrame({"close": close})
    df["ema10"] = ema(close, 10)
    df["ema20"] = ema(close, 20)
    df["ema50"] = ema(close, 50)
    df["ema200"] = ema(close, 200)
    df["rsi"] = rsi(close, 14)
    df["macd"] = ema(close, 12) - ema(close, 26)

    # Entry conditions to test
    entry_conditions = {
        "EMA10>50>200+MACD": (df["ema10"] > df["ema50"]) & (df["ema50"] > df["ema200"]) & (df["macd"] > 0),
        "EMA20>50>200": (df["ema20"] > df["ema50"]) & (df["ema50"] > df["ema200"]),
        "Close>EMA50+MACD": (df["close"] > df["ema50"]) & (df["macd"] > 0),
        "Close>EMA200+RSI>50": (df["close"] > df["ema200"]) & (df["rsi"] > 50),
        "RSI30-70+EMA10>50": (df["rsi"] > 30) & (df["rsi"] < 70) & (df["ema10"] > df["ema50"]),
    }

    # Exit conditions to test
    exit_configs = [
        {"name": "SL-8%+EMA50", "sl": -0.08, "tp": None, "trail_ema": 50},
        {"name": "SL-5%+EMA200", "sl": -0.05, "tp": None, "trail_ema": 200},
        {"name": "SL-10%", "sl": -0.10, "tp": None, "trail_ema": None},
        {"name": "SL-3%+EMA50", "sl": -0.03, "tp": None, "trail_ema": 50},
        {"name": "TP15%+SL-8%", "sl": -0.08, "tp": 0.15, "trail_ema": None},
    ]

    results = []
    c = close.values
    ret = close.pct_change().fillna(0).values

    for entry_name, entry_cond in entry_conditions.items():
        cond = entry_cond.values

        for exit_cfg in exit_configs:
            held, ep, equity, trades = 0.0, 0.0, 1.0, []

            e50 = df["ema50"].values if exit_cfg["trail_ema"] == 50 else None
            e200 = df["ema200"].values if exit_cfg["trail_ema"] == 200 else None

            for i in range(len(df)):
                price = c[i]
                r = held * ret[i]
                should_exit = False           # ต้องตั้งทุกวัน (กัน UnboundLocalError ตอนไม่ถือหุ้น)

                if held > 0:
                    chg = price / ep - 1
                    reason = None

                    if chg <= exit_cfg["sl"]:
                        should_exit = True
                        reason = f"SL {exit_cfg['sl']:.0%}"
                    elif exit_cfg["tp"] and chg >= exit_cfg["tp"]:
                        should_exit = True
                        reason = f"TP {exit_cfg['tp']:.0%}"
                    elif e50 is not None and price < e50[i]:
                        should_exit = True
                        reason = "Below EMA50"
                    elif e200 is not None and price < e200[i]:
                        should_exit = True
                        reason = "Below EMA200"

                    if should_exit:
                        pnl = price / ep - 1 - 2 * fee
                        trades.append(pnl)
                        held = 0
                else:
                    if cond[i]:
                        held = 1.0
                        ep = price

                equity *= (1 + r - (fee if should_exit else 0))

            if trades:
                win_rate = (sum(1 for t in trades if t > 0) / len(trades)) * 100
                avg_pnl = np.mean(trades)
                total_ret = equity - 1
            else:
                win_rate, avg_pnl, total_ret = 0, 0, 0

            results.append({
                "Entry": entry_name,
                "Exit": exit_cfg["name"],
                "Return%": total_ret * 100,
                "Trades": len(trades),
                "WinRate%": win_rate,
                "AvgPnL%": avg_pnl * 100,
            })

    if not results:
        return None

    df_results = pd.DataFrame(results)
    best = df_results.loc[df_results["Return%"].idxmax()]
    return best


def scan_set100(symbols: List[str], limit=30) -> pd.DataFrame:
    """
    Scan SET100 หาเงื่อนไขที่ดีที่สุด
    limit: ตัดจำนวนหุ้นที่ scan (เพราะ slow)
    """
    import yfinance as yf

    print(f"Scanning {min(len(symbols), limit)} stocks...")
    all_results = []
    symbols = symbols[:limit]  # ลิมิตเพื่อให้รวดเร็ว

    for i, sym in enumerate(symbols):
        try:
            df = yf.download(sym, period="5y", interval="1d", auto_adjust=True, progress=False)
            if df is None or len(df) < 100:
                continue

            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.dropna()

            best = optimize_parameters(close, None, 0.002)
            if best is not None and best.get("Return%", 0) is not None:
                all_results.append({
                    "Stock": sym.replace(".BK", ""),
                    "Entry": best["Entry"],
                    "Exit": best["Exit"],
                    "Return%": round(best["Return%"], 1),
                    "Trades": int(best["Trades"]),
                    "WinRate%": round(best["WinRate%"], 1),
                })

            print(f"  [{i + 1}/{len(symbols)}] {sym.replace('.BK', '')} ✓")

        except Exception as e:
            print(f"  [{i + 1}/{len(symbols)}] {sym.replace('.BK', '')} ✗ ({str(e)[:30]})")

    if not all_results:
        print("No valid results found!")
        return pd.DataFrame()

    return pd.DataFrame(all_results).sort_values("Return%", ascending=False)
