#!/usr/bin/env python
"""
ทดสอบว่ามีทางไหน "เอาชนะ SPY" ได้จริงบ้างไหม ด้วยการซื้อแล้วถือเฉยๆ (buy & hold) 10 ปี
ไม่ใช่การเทรดเข้าออก — เทียบทางเลือกที่งานวิจัยอ้างว่าเอาชนะตลาดได้ในระยะยาว:

  SPY   = S&P 500 (baseline)
  VTI   = ตลาดหุ้น US ทั้งหมด (คล้าย SPY แต่กว้างกว่านิดหน่อย)
  VTV   = หุ้น Value ขนาดใหญ่ (Fama-French value premium)
  VBR   = หุ้น Small-Cap Value (value premium + size premium รวมกัน)
  QQQ   = Nasdaq 100 (กระจุก Growth/Tech)
  SSO   = SPY x2 leverage (ทุกวัน)
  UPRO  = SPY x3 leverage (ทุกวัน)
  BRKB  = Berkshire Hathaway (เทียบเป็น proxy "หุ้นคุณค่าเดี่ยว")

วัด: Total Return, CAGR, Max Drawdown ตลอด 10 ปี ก้อนเดียว (lump sum) ไม่มี DCA
เพื่อดูว่า "ผลตอบแทนสูงกว่า" ต้องแลกกับ "ความเสี่ยง/แกว่งแรงกว่า" แค่ไหน
"""
import yfinance as yf
import pandas as pd
import numpy as np

TICKERS = {
    "SPY (baseline)": "SPY",
    "VTI (US ทั้งตลาด)": "VTI",
    "VTV (Large Value)": "VTV",
    "VBR (Small-Cap Value)": "VBR",
    "QQQ (Nasdaq100 Growth)": "QQQ",
    "SSO (SPY x2)": "SSO",
    "UPRO (SPY x3)": "UPRO",
    "BRK-B (Berkshire)": "BRK-B",
}


def max_drawdown(close):
    peak = close.cummax()
    dd = (close / peak - 1)
    return dd.min() * 100


def main():
    rows = []
    for label, sym in TICKERS.items():
        df = yf.download(sym, period="10y", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty:
            print(f"ไม่มีข้อมูล {sym}")
            continue
        c = df["Close"]
        if isinstance(c, pd.DataFrame):
            c = c.iloc[:, 0]
        c = c.dropna()
        years = (c.index[-1] - c.index[0]).days / 365.25
        total_ret = (c.iloc[-1] / c.iloc[0] - 1) * 100
        cagr = ((c.iloc[-1] / c.iloc[0]) ** (1 / years) - 1) * 100
        mdd = max_drawdown(c)
        # worst 1-year rolling return (252 วัน) — วัดว่าแย่สุดช่วงไหนเจ็บแค่ไหน
        roll_1y = (c / c.shift(252) - 1) * 100
        worst_1y = roll_1y.min()
        rows.append(dict(label=label, symbol=sym, years=round(years, 1),
                         total_return_pct=round(total_ret, 1), cagr_pct=round(cagr, 2),
                         max_drawdown_pct=round(mdd, 1), worst_1y_pct=round(worst_1y, 1)))
        print(f"{label:28s} total={total_ret:8.1f}%  CAGR={cagr:6.2f}%  MaxDD={mdd:7.1f}%  worst1y={worst_1y:7.1f}%")

    df_res = pd.DataFrame(rows).sort_values("total_return_pct", ascending=False)
    print("\n=== เรียงตาม Total Return ===")
    print(df_res.to_string(index=False))
    df_res.to_csv("beat_spy_alternatives.csv", index=False)
    print("\nบันทึกไว้ที่ beat_spy_alternatives.csv")


if __name__ == "__main__":
    main()
