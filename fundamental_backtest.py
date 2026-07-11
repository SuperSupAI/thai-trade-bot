#!/usr/bin/env python
"""
Fundamental Ranking Backtest — ไม่ดูกราฟ ใช้แต่งบการเงิน
ทุกสิ้นปี: คัดหุ้น "งบดีสุด Top 20%" ตาม score (ROE, Rev growth, D/E, Op Margin, Cash flow)
ถือปีถัดไป (unseen ตอน rank) เทียบกับ Bottom 20% / ทั้งกลุ่ม / SET

ข้อจำกัด: yfinance annual financials ย้อนหลังได้จำกัด (~4 ปี) → ตัวอย่างเล็กกว่าเทคนิค
"""
import numpy as np
import pandas as pd
import yfinance as yf
from universe import group_symbols


def get_fund_history(sym):
    """คืน DataFrame รายปี: index=ปีที่งบประกาศ (fiscal year end), columns=score components"""
    try:
        t = yf.Ticker(sym)
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow
        if fin is None or fin.empty or bs is None or bs.empty:
            return None

        rows = []
        for col in fin.columns:
            year = col.year
            try:
                revenue = fin.loc["Total Revenue", col] if "Total Revenue" in fin.index else np.nan
                net_income = fin.loc["Net Income", col] if "Net Income" in fin.index else np.nan
                op_income = fin.loc["Operating Income", col] if "Operating Income" in fin.index else np.nan
                equity = bs.loc["Stockholders Equity", col] if (col in bs.columns and "Stockholders Equity" in bs.index) else np.nan
                debt = bs.loc["Total Debt", col] if (col in bs.columns and "Total Debt" in bs.index) else np.nan
                ocf = np.nan
                if cf is not None and not cf.empty and col in cf.columns:
                    key = None
                    for k in ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities"):
                        if k in cf.index:
                            key = k; break
                    if key: ocf = cf.loc[key, col]

                roe = (net_income / equity) if (pd.notna(equity) and equity != 0 and pd.notna(net_income)) else np.nan
                opm = (op_income / revenue) if (pd.notna(revenue) and revenue != 0 and pd.notna(op_income)) else np.nan
                de = (debt / equity) if (pd.notna(equity) and equity != 0 and pd.notna(debt)) else np.nan
                rows.append(dict(year=year, revenue=revenue, roe=roe, opm=opm, de=de,
                                 ocf_pos=(1.0 if (pd.notna(ocf) and ocf > 0) else 0.0)))
            except Exception:
                continue
        if not rows:
            return None
        df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
        df["rev_growth"] = df["revenue"].pct_change()
        return df
    except Exception:
        return None


def score_row(r):
    """รวมคะแนน 0-5: ROE>15%, RevGrowth>5%, D/E<1, OpMargin>10%, OCF บวก"""
    s = 0
    if pd.notna(r.roe) and r.roe > 0.15: s += 1
    if pd.notna(r.rev_growth) and r.rev_growth > 0.05: s += 1
    if pd.notna(r.de) and r.de < 1.0: s += 1
    if pd.notna(r.opm) and r.opm > 0.10: s += 1
    if r.ocf_pos > 0: s += 1
    return s


def price_return(close, y0, y1):
    a = close.index.searchsorted(pd.Timestamp(f"{y0}-01-01"))
    b = close.index.searchsorted(pd.Timestamp(f"{y1}-01-01"))
    if b <= a or b - a < 100:
        return None
    return close.iloc[b - 1] / close.iloc[a] - 1


def main():
    syms = group_symbols("SET100 (ทั้งหมด)")
    print(f"ดึงงบการเงิน {len(syms)} ตัว (yfinance annual — จำกัด ~4 ปีย้อนหลัง)...")

    fund, prices = {}, {}
    for i, s in enumerate(syms):
        f = get_fund_history(s)
        if f is not None and len(f) >= 2:
            fund[s] = f
        try:
            d = yf.download(s, period="6y", interval="1d", auto_adjust=True, progress=False)
            if d is not None and len(d):
                c = d["Close"]; c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
                prices[s] = c.dropna()
        except Exception:
            pass
        if (i + 1) % 20 == 0:
            print(f"  ...{i+1}/{len(syms)}")

    print(f"มีงบใช้ได้ {len(fund)} ตัว · มีราคา {len(prices)} ตัว\n" + "=" * 78)

    sd = yf.download("^SET.BK", period="6y", interval="1d", auto_adjust=True, progress=False)
    sc = sd["Close"]; sc = sc.iloc[:, 0] if isinstance(sc, pd.DataFrame) else sc
    sc = sc.dropna()

    all_years = sorted({int(y) for f in fund.values() for y in f["year"]})
    results = []
    for fy in all_years:
        hold_year = fy + 1
        scored = []
        for s, f in fund.items():
            row = f[f.year == fy]
            if row.empty or s not in prices:
                continue
            sc_val = score_row(row.iloc[0])
            scored.append((s, sc_val))
        if len(scored) < 15:
            continue
        scored.sort(key=lambda x: x[1], reverse=True)
        n_top = max(3, len(scored) // 5)
        top = [s for s, _ in scored[:n_top]]
        bot = [s for s, _ in scored[-n_top:]]

        def grp_ret(lst):
            rr = [price_return(prices[s], hold_year, hold_year + 1) for s in lst if s in prices]
            rr = [x for x in rr if x is not None]
            return np.mean(rr) if rr else np.nan

        top_r, bot_r = grp_ret(top), grp_ret(bot)
        all_r = grp_ret([s for s, _ in scored])
        set_r = price_return(sc, hold_year, hold_year + 1)

        results.append(dict(FiscalYear=fy, HoldYear=hold_year, N=len(scored),
                            TopScore_n=n_top, Top20pct=round((top_r or 0) * 100, 1),
                            Bottom20pct=round((bot_r or 0) * 100, 1),
                            AllAvg=round((all_r or 0) * 100, 1),
                            SET=round((set_r or 0) * 100, 1) if set_r is not None else None))

    res = pd.DataFrame(results)
    if res.empty:
        print("ข้อมูลไม่พอสำหรับสร้าง backtest (yfinance ให้ fundamentals ย้อนหลังน้อยเกินไป)")
        return
    res.to_csv("fundamental_backtest.csv", index=False)
    print(res.to_string(index=False))

    print("\n" + "=" * 78)
    print(f"จำนวนปีที่ทดสอบ: {len(res)}  (ตัวอย่างเล็ก — ตีความอย่างระวัง)")
    print(f"ผลตอบแทนเฉลี่ย/ปี:  Top20%งบดี {res['Top20pct'].mean():+.1f}%  ·  "
          f"Bottom20%งบแย่ {res['Bottom20pct'].mean():+.1f}%  ·  ทั้งกลุ่ม {res['AllAvg'].mean():+.1f}%  ·  "
          f"SET {res['SET'].dropna().mean():+.1f}%")
    beat = (res["Top20pct"] > res["AllAvg"]).sum()
    print(f"Top20% ชนะค่าเฉลี่ยกลุ่ม: {beat}/{len(res)} ปี")
    print("→ บันทึก fundamental_backtest.csv")


if __name__ == "__main__":
    main()
