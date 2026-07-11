"""
Thai Trade Bot — Backtest web app (Streamlit)
กลยุทธ์ ① EMA Trend + SET Filter · โหมด: หุ้นเดียว / สแกนทั้งกลุ่ม
"""
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from universe import SECTORS, group_symbols, get_market_type


def get_stock_sector(symbol):
    """หาว่าหุ้นนี้อยู่กลุ่มไหน"""
    sym_clean = symbol.replace(".BK", "")
    for sector, stocks in SECTORS.items():
        if sym_clean in stocks:
            return sector
    return "อื่นๆ"
from fundamentals import get_fundamentals, passes_fundamental_filter, format_ratio

st.set_page_config(page_title="Thai Trade Bot — Backtest", page_icon="🤖", layout="wide")
st.title("🤖 Thai Trade Bot — Backtest")
st.caption("ทดสอบกลยุทธ์บนข้อมูลอดีต · เทียบ Buy & Hold · เพื่อการเรียนรู้ ไม่ใช่คำแนะนำลงทุน")

SET_SYMBOL = "^SET.BK"
CUT = 0.08   # initial stop loss (กว้างขึ้น กัน noise) · หลังมีกำไรใช้ trailing EMA50


# ── data / indicators ──
# ดาวน์โหลดผ่าน safe_fetch (แยกโปรเซส) กัน segfault จาก yfinance/curl_cffi ลามมาที่แอปหลัก
from safe_fetch import safe_download_one, safe_download_many


@st.cache_data(ttl=3600, show_spinner=False)
def load_one(symbol, years):
    return safe_download_one(symbol, years)


@st.cache_data(ttl=3600, show_spinner=False)
def load_volume(symbol, years):
    """โหลดแยกต่างหาก (close+volume) เฉพาะหน้ารายตัว — ไม่ปนกับ load_one ที่โหมดสแกนใช้"""
    df = safe_download_one(symbol, years, with_volume=True)
    return df["volume"] if df is not None else None


@st.cache_data(ttl=3600, show_spinner=False)
def load_many(symbols, years):
    return safe_download_many(symbols, years, min_rows=210)


def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def find_pivots(close, lookback=3):
    """หา pivot high/low แบบ fractal — pivot ที่ index i ยืนยันได้ก็ต่อเมื่อผ่านไปแล้ว lookback แท่ง (กัน lookahead)"""
    c = close.values
    n = len(c)
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for i in range(lookback, n - lookback):
        window = c[i - lookback:i + lookback + 1]
        if c[i] == window.max() and (window == c[i]).sum() == 1:
            is_high[i] = True
        if c[i] == window.min() and (window == c[i]).sum() == 1:
            is_low[i] = True
    return is_high, is_low


def find_hh_hl_breakout_signal(close, lookback=3, low_tolerance=0.05):
    """
    หาแพทเทิร์น Higher-High/Higher-Low 2 ชุดติดกัน แล้วออกสัญญาณตอนราคาทะลุ Swing High ล่าสุด (breakout)
    stage: 0=รอ Low1 · 1=มี Low1 รอ High1 · 2=มี High1 รอ Low2(HL) · 3=มี Low2 รอ High2(HH) · 4=armed รอ breakout
    low_tolerance: Low2 ยังถือว่าเป็น Higher Low ได้ ถ้าต่ำกว่า Low1 ไม่เกินสัดส่วนนี้ (กันหลุดโดย noise เล็กน้อย)
    """
    c = close.values
    n = len(c)
    is_high, is_low = find_pivots(close, lookback)
    signal = np.zeros(n, dtype=bool)
    stage = 0
    low1 = low2 = high1 = high2 = None

    for i in range(n):
        if stage == 4 and c[i] > high2:
            signal[i] = True
            stage, low1, low2, high1, high2 = 0, None, None, None, None
            continue

        confirm_idx = i - lookback
        if confirm_idx < 0:
            continue

        if is_low[confirm_idx]:
            price = c[confirm_idx]
            if stage == 0:
                low1, stage = price, 1
            elif stage == 1 and price < low1:
                low1 = price
            elif stage == 2:
                if price >= low1 * (1 - low_tolerance):
                    low2, stage = price, 3
                else:
                    low1, stage = price, 1

        if is_high[confirm_idx]:
            price = c[confirm_idx]
            if stage == 1:
                high1, stage = price, 2
            elif stage == 2 and price > high1:
                high1 = price
            elif stage == 3:
                if price > high1:
                    high2, stage = price, 4
                else:
                    stage, low1, low2, high1, high2 = 0, None, None, None, None

    return signal


def build_and_sim(close, setclose, fee, use_scaling=False, use_ema_cross=False, use_hh_hl=False, use_ema5_trail=False):
    df = pd.DataFrame({"close": close})
    df["ema5"] = ema(close, 5); df["ema10"] = ema(close, 10); df["ema50"] = ema(close, 50)
    df["ema100"] = ema(close, 100); df["ema200"] = ema(close, 200)
    df["rsi"] = rsi(close); df["macd"] = ema(close, 12) - ema(close, 26)
    if use_hh_hl:
        # เข้าตอนราคาทะลุ Swing High หลังเกิดแพทเทิร์น Higher-High/Higher-Low 2 ชุดติดกัน (price action breakout)
        stock_ok = pd.Series(find_hh_hl_breakout_signal(close), index=df.index)
    elif use_ema_cross:
        # เข้าเฉพาะวันที่ EMA50 ตัดขึ้น EMA100 (ครั้งแรก) — ไม่บังคับ EMA50>EMA200 ฝั่งหุ้น
        # เพราะตอนตัดขึ้น EMA50 มักยังไม่ทัน EMA200 (เส้นช้ากว่า)
        cross_up = (df["ema50"] > df["ema100"]) & (df["ema50"].shift(1) <= df["ema100"].shift(1))
        stock_ok = (df["close"] > df["ema200"]) & (df["ema10"] > df["ema50"]) & (df["macd"] > 0) & cross_up
    else:
        stock_ok = (df["close"] > df["ema200"]) & (df["ema10"] > df["ema50"]) \
            & (df["ema50"] > df["ema200"]) & (df["macd"] > 0)
    if setclose is not None and not use_hh_hl:
        # HH-HL Breakout ไม่ใช้ SET filter — เป็น price action ของหุ้นล้วนๆ
        s = setclose.reindex(df.index).ffill()
        set_ok = (s > ema(s, 200)) & (ema(s, 10) > ema(s, 50)) & (ema(s, 50) > ema(s, 200))
        cond = (stock_ok & set_ok).values
    else:
        cond = stock_ok.values

    c = df["close"].values
    ret = df["close"].pct_change().fillna(0).values
    e5 = df["ema5"].values
    e50 = df["ema50"].values

    held, ep, run_eq, days_in = 0.0, 0.0, 1.0, 0
    strat, events, trades, entry = [], [], [], None

    # สำหรับ scaling strategy
    sold_at_10pct = False
    sold_at_20pct = False
    peak_at_20pct = 0.0

    for i in range(len(df)):
        if held > 0:
            days_in += 1
        r = held * ret[i]; ft = 0.0; price = c[i]

        if held > 0:
            chg = price / ep - 1

            # EMA5 Trail strategy — เงื่อนไขเดียวล้วนๆ: SL -8% หรือราคาตัด EMA5 (ไม่ผสม scaling/EMA50)
            if use_ema5_trail:
                reason = "SL -8%" if chg <= -CUT else ("ตัด EMA5" if price < e5[i] else None)
                if reason:
                    ft += fee; held = 0
                    trades.append({**entry, "exit_i": i, "exit_price": price, "reason": reason,
                                   "pnl": price / entry["price"] - 1 - 2 * fee})
                    events.append((i, "SELL", price)); entry = None

            # Scaling strategy
            elif use_scaling:
                # ที่ 10% profit → ขาย 50%
                if not sold_at_10pct and chg >= 0.10:
                    ft += fee
                    held *= 0.5
                    sold_at_10pct = True
                    events.append((i, "SELL 50%", price))

                # ที่ 20% profit → ขาย 50% ของที่เหลือ
                elif not sold_at_20pct and chg >= 0.20:
                    ft += fee
                    held *= 0.5
                    sold_at_20pct = True
                    peak_at_20pct = price
                    events.append((i, "SELL 50%", price))

                # ขายหมด — หลังขายบางส่วนแล้ว (sold_at_10pct) รัดเข็มขัดด้วย EMA5 (ไวกว่า EMA50)
                # เพื่อป้องกันกำไรที่เหลือ ก่อนขายยังไม่ถึง 10% ปล่อยวิ่งด้วย EMA50 ตามเดิม
                reason = None
                if chg <= -CUT:
                    reason = "SL -8%"
                elif sold_at_10pct and price < e5[i]:
                    reason = "ตัด EMA5 (หลังขาย 50%)"
                elif not sold_at_10pct and price < e50[i]:
                    reason = "หลุด EMA50"
                elif sold_at_20pct and price <= peak_at_20pct * 0.95:
                    reason = "หลุด -5% from 20%"

                if reason and held > 0:
                    ft += fee
                    trades.append({**entry, "exit_i": i, "exit_price": price, "reason": reason,
                                   "pnl": price / entry["price"] - 1 - 2 * fee})
                    held = 0
                    events.append((i, "SELL ALL", price))
            else:
                # Default strategy
                reason = "SL -8%" if chg <= -CUT else ("หลุด EMA50" if price < e50[i] else None)
                if reason:
                    ft += fee; held = 0
                    trades.append({**entry, "exit_i": i, "exit_price": price, "reason": reason,
                                   "pnl": price / entry["price"] - 1 - 2 * fee})
                    events.append((i, "SELL", price)); entry = None
        else:
            if cond[i]:
                ft += fee; held = 1.0; ep = price
                entry = {"entry_i": i, "price": price, "eq": run_eq}
                sold_at_10pct = False
                sold_at_20pct = False
                peak_at_20pct = 0.0
                events.append((i, "BUY", price))

        day_ret = r - ft; strat.append(day_ret); run_eq *= (1 + day_ret)

    if held > 0 and entry:                         # ไม้ที่ยังถืออยู่ตอนจบ
        trades.append({**entry, "exit_i": None, "exit_price": c[-1], "reason": "ยังถืออยู่",
                       "pnl": c[-1] / entry["price"] - 1 - fee})

    df["equity"] = (1 + pd.Series(strat, index=df.index)).cumprod()
    df["bh"] = (1 + df["close"].pct_change().fillna(0)).cumprod()

    eq = df["equity"]; yrs = len(df) / 252
    m = dict(
        total=eq.iloc[-1] - 1, bh=df["bh"].iloc[-1] - 1,
        cagr=eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0,
        maxdd=(eq / eq.cummax() - 1).min(),
        nbuy=len(trades),
        wr=(len([t for t in trades if t["pnl"] > 0]) / len(trades) * 100) if trades else 0,
        time_in=days_in / len(df) * 100 if len(df) else 0,
        trades=trades,
    )
    return df, events, m


def show_stock_detail(symbol, close, setclose, fee, cap, use_scaling=False, use_ema_cross=False, use_hh_hl=False, use_ema5_trail=False, years=None):
    """แสดงรายละเอียดหุ้นตัวเดียว: เมตริก + กราฟจุดซื้อขาย + log"""
    df, events, m = build_and_sim(close, setclose, fee, use_scaling, use_ema_cross, use_hh_hl, use_ema5_trail)
    eq = df["equity"]
    final_value = cap * eq.iloc[-1]; profit = final_value - cap

    st.markdown(f"### 📊 {symbol.replace('.BK', '')}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("มูลค่าสุดท้าย", f"{final_value:,.0f} ฿", f"{profit:+,.0f} ฿")
    c2.metric("ผลตอบแทน (บอต)", f"{m['total']*100:+.1f}%", f"vs B&H {m['bh']*100:+.1f}%")
    c3.metric("CAGR / ปี", f"{m['cagr']*100:+.1f}%")
    c4.metric("Max Drawdown", f"{m['maxdd']*100:.1f}%")
    c5, c6, c7 = st.columns(3)
    c5.metric("Win rate", f"{m['wr']:.0f}%", f"{m['nbuy']} ไม้")
    c6.metric("⏱️ เวลาเงินทำงาน", f"{m['time_in']:.0f}%", f"นอนเฉย {100-m['time_in']:.0f}%")
    c7.metric("ถ้าถือเฉยๆ (B&H)", f"{cap*df['bh'].iloc[-1]:,.0f} ฿", f"{cap*m['bh']:+,.0f} ฿")
    if m["total"] > m["bh"]:
        st.success("✅ ชนะ Buy & Hold")
    else:
        st.warning("❌ แพ้ Buy & Hold")

    # แสดง Fundamental Data (Expander)
    with st.expander("📈 ตัวชี้วัดทางการเงิน", expanded=True):
        fund = get_fundamentals(symbol)
        if fund:
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            fc1.metric("P/E", format_ratio(fund.get('pe_ratio'), ".2f"))
            fc2.metric("ROE", format_ratio(fund.get('roe'), ".2%"))
            fc3.metric("D/E", format_ratio(fund.get('de_ratio'), ".2f"))
            fc4.metric("Gross Margin", format_ratio(fund.get('gross_margin'), ".2%"))
            fc5.metric("EPS Growth", format_ratio(fund.get('eps_growth'), ".2%"))
            fc6, fc7 = st.columns(2)
            fc6.metric("EBIT Margin", format_ratio(fund.get('ebit_margin'), ".2%"))
            fc7.metric("Profit Margin", format_ratio(fund.get('profit_margin'), ".2%"))
        else:
            st.info("ไม่มีข้อมูล fundamental")

    st.subheader("📈 มูลค่าเงินต้นตามเวลา (บาท)")
    comp = {"บอต": df["equity"] * cap, "ถือหุ้นนี้ (B&H)": df["bh"] * cap}
    if setclose is not None:
        s = setclose.reindex(df.index).ffill()
        base = s.dropna()
        if len(base):
            comp["SET Index"] = s / base.iloc[0] * cap
    st.line_chart(pd.DataFrame(comp))

    st.subheader("💹 ราคา + EMA + MACD + จุดซื้อ/ขาย")
    pdf = pd.DataFrame({"date": df.index, "close": df["close"].values,
                        "EMA5": df["ema5"].values, "EMA50": df["ema50"].values, "EMA100": df["ema100"].values,
                        "EMA200": df["ema200"].values, "macd": df["macd"].values})

    # ราคา + EMA
    line = alt.Chart(pdf).mark_line(color="#9aa4b2").encode(x="date:T", y=alt.Y("close:Q", title="ราคา"))
    e5 = alt.Chart(pdf).mark_line(color="#58a6ff", strokeDash=[4, 3]).encode(x="date:T", y="EMA5:Q")
    e50 = alt.Chart(pdf).mark_line(color="#3fb950", strokeDash=[4, 3]).encode(x="date:T", y="EMA50:Q")
    e100 = alt.Chart(pdf).mark_line(color="#a371f7", strokeDash=[4, 3]).encode(x="date:T", y="EMA100:Q")
    e200 = alt.Chart(pdf).mark_line(color="#f0883e", strokeDash=[4, 3]).encode(x="date:T", y="EMA200:Q")

    mk = pd.DataFrame([{"date": df.index[i], "price": p, "act": a} for (i, a, p) in events])
    layers = [line, e5, e50, e100, e200]
    if not mk.empty:
        buy = mk[mk.act == "BUY"]
        sell_partial = mk[mk.act == "SELL 50%"]
        sell_all = mk[mk.act.isin(["SELL", "SELL ALL"])]
        if not buy.empty:
            layers.append(alt.Chart(buy).mark_point(shape="triangle-up", size=90, color="#2ea043", filled=True).encode(x="date:T", y="price:Q"))
        if not sell_partial.empty:
            layers.append(alt.Chart(sell_partial).mark_point(shape="circle", size=80, color="#f0883e", filled=True).encode(x="date:T", y="price:Q"))
        if not sell_all.empty:
            layers.append(alt.Chart(sell_all).mark_point(shape="triangle-down", size=90, color="#f85149", filled=True).encode(x="date:T", y="price:Q"))
    price_chart = alt.layer(*layers).properties(height=300)

    # MACD ใต้ราคา
    macd_line = alt.Chart(pdf).mark_line(color="#1f77b4").encode(x="date:T", y=alt.Y("macd:Q", title="MACD"))
    zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#666", strokeDash=[2, 2]).encode(y="y:Q")
    macd_chart = (macd_line + zero_line).properties(height=150)

    chart_stack = [price_chart, macd_chart]

    # Volume — แท่งสีต่างสำหรับวัน BUY
    vol = load_volume(symbol, years) if years else None
    if vol is not None and not vol.empty:
        vdf = pd.DataFrame({"date": df.index, "volume": vol.reindex(df.index).values})
        buy_dates = set(mk[mk.act == "BUY"]["date"]) if not mk.empty else set()
        vdf["is_buy"] = vdf["date"].isin(buy_dates)
        vol_chart = alt.Chart(vdf).mark_bar().encode(
            x="date:T",
            y=alt.Y("volume:Q", title="Volume"),
            color=alt.condition(alt.datum.is_buy, alt.value("#2ea043"), alt.value("#4a5568")),
        ).properties(height=100)
        chart_stack.append(vol_chart)

    # รวมกราฟ
    combined = alt.vconcat(*chart_stack).resolve_scale(x='shared')
    st.altair_chart(combined.interactive(), use_container_width=True)
    st.caption("เส้น EMA: 🔵 ฟ้า = EMA5 · 🟢 เขียว = EMA50 · 🟣 ม่วง = EMA100 · 🟠 ส้ม (เส้นประ) = EMA200")
    st.caption("จุดซื้อขาย: 🔺 เขียว = BUY · 🔴 แดง = SELL (ขายหมด) · 🟠 ส้ม (วงกลม) = SELL 50% (ขายบางส่วน — เฉพาะกลยุทธ์ Scaling Out)")
    if vol is not None and not vol.empty:
        st.caption("Volume: 🟢 เขียว = วัน BUY · ⬛ เทา = วันอื่นๆ")

    trades = m["trades"]
    st.subheader(f"🧾 แต่ละไม้ที่เทรด ({len(trades)})")
    if trades:
        rows = []
        for k, t in enumerate(trades, 1):
            last = t["exit_i"] if t["exit_i"] is not None else len(df) - 1
            rows.append({
                "ไม้": k,
                "ซื้อ": df.index[t["entry_i"]].strftime("%d/%m/%y"),
                "ราคาซื้อ": round(t["price"], 2),
                "ขาย": (df.index[t["exit_i"]].strftime("%d/%m/%y") if t["exit_i"] is not None else "ยังถือ"),
                "ราคาขาย": round(t["exit_price"], 2),
                "ถือ(วัน)": last - t["entry_i"],
                "เหตุออก": t["reason"],
                "กำไร%": round(t["pnl"] * 100, 1),
                "กำไร(บาท)": round(cap * t["eq"] * t["pnl"]),
            })
        tdf = pd.DataFrame(rows)
        st.dataframe(tdf, use_container_width=True, hide_index=True)
        w = len([t for t in trades if t["pnl"] > 0]); l = len(trades) - w
        st.caption(f"กำไร {w} ไม้ · ขาดทุน {l} ไม้ · กำไรรวมจากตาราง ~{tdf['กำไร(บาท)'].sum():+,.0f} ฿ "
                   f"(บาทต่อไม้คิดจากเงินที่ทบต้น ณ ตอนนั้น)")
    else:
        st.info("ไม่มีสัญญาณเข้าในช่วงนี้")


def simulate_portfolio(closes, setclose, fee, n_slots):
    """พอร์ตหมุนเงิน: ถือได้ n_slots ตัวพร้อมกัน · ออกตัวนึง → เอาเงินไปเข้าตัวอื่นที่มีสัญญาณ (ไม่ถือเงินเฉย)"""
    prices = pd.DataFrame(closes).sort_index().ffill().dropna(how="all")
    e50 = prices.ewm(span=50, adjust=False).mean()
    e200 = prices.ewm(span=200, adjust=False).mean()
    e10 = prices.ewm(span=10, adjust=False).mean()
    macd = prices.ewm(span=12, adjust=False).mean() - prices.ewm(span=26, adjust=False).mean()
    C = ((prices > e200) & (e10 > e50) & (e50 > e200) & (macd > 0)).values
    if setclose is not None:
        s = setclose.reindex(prices.index).ffill()
        setmask = ((s > ema(s, 200)) & (ema(s, 10) > ema(s, 50)) & (ema(s, 50) > ema(s, 200))).values
        C = C & setmask[:, None]

    P = prices.values; E50 = e50.values; SC = (macd / prices).values
    T, M = P.shape; cols = list(prices.columns); idx = prices.index

    cash, pos = 1.0, {}
    eqc, fill, trades = [], [], []
    for i in range(T):
        for j in list(pos):                                    # อัปเดต + เช็คออก
            if i > 0 and not np.isnan(P[i-1, j]) and P[i-1, j] > 0 and not np.isnan(P[i, j]):
                pos[j]["val"] *= P[i, j] / P[i-1, j]
            p = P[i, j]
            if np.isnan(p):
                continue
            if p <= pos[j]["entry"] * (1 - CUT) or (not np.isnan(E50[i, j]) and p < E50[i, j]):
                cash += pos[j]["val"] * (1 - fee)
                trades.append(dict(sym=cols[j].replace(".BK", ""), ei=pos[j]["ei"], ep=pos[j]["entry"],
                                   xi=i, xp=p, reason=("SL -8%" if p <= pos[j]["entry"]*(1-CUT) else "หลุด EMA50"),
                                   pnl=p / pos[j]["entry"] - 1 - 2*fee))
                del pos[j]
        free = n_slots - len(pos)                              # เติมช่องว่างด้วยตัวที่มีสัญญาณ
        if free > 0:
            elig = [j for j in range(M) if C[i, j] and j not in pos and not np.isnan(P[i, j])]
            elig.sort(key=lambda j: (SC[i, j] if not np.isnan(SC[i, j]) else -9), reverse=True)
            total = cash + sum(v["val"] for v in pos.values())
            target = total / n_slots
            for j in elig[:free]:
                amt = min(cash, target)
                if amt < total * 0.01:
                    break
                cash -= amt; pos[j] = dict(val=amt * (1 - fee), entry=P[i, j], ei=i)
        eqc.append(cash + sum(v["val"] for v in pos.values())); fill.append(len(pos))

    for j, v in pos.items():                                   # ไม้ที่ยังถือตอนจบ
        trades.append(dict(sym=cols[j].replace(".BK", ""), ei=v["ei"], ep=v["entry"],
                           xi=None, xp=P[-1, j], reason="ยังถือ", pnl=P[-1, j] / v["entry"] - 1 - fee))

    eq = pd.Series(eqc, index=idx)
    bh = (1 + pd.Series(np.nanmean(prices.pct_change().values, axis=1), index=idx).fillna(0)).cumprod()
    return dict(eq=eq, bh=bh, trades=trades, fill=fill, idx=idx, n_slots=n_slots)


# ── query params (คลิกจากผลสแกน → เปิดแท็บใหม่ด้วยค่าที่ใช้ตอนสแกน) ──
# เช็คก่อนสร้าง sidebar เพื่อใช้เป็นค่าเริ่มต้นของ widget — จากนั้น sidebar จะ "ใช้งานได้จริง"
# บนแท็บนี้ด้วย (แก้ค่าแล้วกราฟอัปเดตตาม ไม่ใช่ค่าตายตัวจากตอนสแกน)
qp = st.query_params
is_deep_link = "sym" in qp
if is_deep_link:
    sym_q = qp.get("sym", "")
    if sym_q and not sym_q.upper().endswith(".BK"):
        sym_q += ".BK"
    years_q = int(qp.get("years", "5"))
    cap_q = float(qp.get("cap", "50000"))
    fee_q = float(qp.get("fee", "0.002"))
    scaling_q = qp.get("scaling", "0") == "1"
    cross_q = qp.get("cross", "0") == "1"
    hhhl_q = qp.get("hhhl", "0") == "1"
    ema5trail_q = qp.get("ema5trail", "0") == "1"
    entry_idx_q = 2 if hhhl_q else (1 if cross_q else 0)
    exit_idx_q = 2 if ema5trail_q else (1 if scaling_q else 0)

# ── sidebar ──
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    mode = st.radio("โหมด", ["หุ้นเดียว", "สแกนทั้งกลุ่ม"])
    if mode == "หุ้นเดียว":
        symbol = st.text_input("หุ้น (เช่น PIMO.BK)", sym_q if is_deep_link else "PIMO.BK").strip().upper()
    else:
        group = st.selectbox("กลุ่ม", ["SET100 (ทั้งหมด)", "SET Index"] + list(SECTORS.keys()))
        scan_style = st.radio("รูปแบบ", ["ดูรายตัว (ตาราง+คลิก)", "จัดพอร์ตหมุนเงิน (ไม่ให้ว่าง)"])
        n_slots = 1
        if scan_style.startswith("จัดพอร์ต"):
            n_slots = st.radio("ถือพร้อมกันกี่ตัว", [1, 5], horizontal=True,
                               format_func=lambda x: f"{x} ไม้")
    years = st.slider("ปีย้อนหลัง", 1, 10, years_q if is_deep_link else 5)
    cap = st.number_input("เงินต้น (บาท)", 1000, 10_000_000, int(cap_q) if is_deep_link else 50_000, 1000)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, round(fee_q * 100, 2) if is_deep_link else 0.2, 0.05) / 100

    st.divider()
    st.subheader("🎯 กลยุทธ์ ENTRY (เข้า)")
    entry_strategy = st.radio("เลือกเงื่อนไขเข้า",
                       ["Default (EMA10>50>200 + MACD>0)", "EMA50 ตัดขึ้น EMA100 + Trend Filter",
                        "HH-HL Breakout (2 ชุดติดกัน)"],
                       index=entry_idx_q if is_deep_link else 0,
                       help="แบบที่ 2: เข้าเฉพาะวันที่ EMA50 ตัดขึ้น EMA100 (ครั้งแรก) + Close>EMA200 · EMA10>EMA50 · MACD>0 "
                            "(ไม่บังคับ EMA50>EMA200 ฝั่งหุ้น เพราะตอนตัดขึ้นมักยังไม่ทัน)\n\n"
                            "แบบที่ 3: เข้าตอนราคาทะลุ Swing High (breakout) หลังเกิดแพทเทิร์น Higher-High/"
                            "Higher-Low ติดกัน 2 ชุด — เป็น price action ล้วน ไม่ใช้เงื่อนไข EMA ฝั่งหุ้น "
                            "และไม่ใช้เงื่อนไข SET เลย "
                            "(Low ชุดที่ 2 ยังนับเป็น Higher Low ได้ถ้าต่ำกว่า Low ชุดแรกไม่เกิน 5%)")
    use_ema_cross = entry_strategy == "EMA50 ตัดขึ้น EMA100 + Trend Filter"
    use_hh_hl = entry_strategy == "HH-HL Breakout (2 ชุดติดกัน)"

    st.divider()
    st.subheader("🎯 กลยุทธ์ EXIT")
    strategy = st.radio("เลือกกลยุทธ์",
                       ["Default (Trail EMA50)", "Scaling Out (10%→50%, 20%→50%)", "EMA5 Trail (ตัด EMA5 ขายหมด)"],
                       index=exit_idx_q if is_deep_link else 0,
                       help="Scaling Out: ขาย50% ที่ 10%, ขาย50% ที่ 20%, ปล่อยไป -5%\n\n"
                            "EMA5 Trail: เงื่อนไขเดียวล้วนๆ ไม่ผสม scaling — ถือเต็มไม้ ขายหมดทันทีที่ราคาปิดต่ำกว่า EMA5 "
                            "(หรือโดน SL -8% ก่อน) รัดเข็มขัดไวกว่า Default ที่ใช้ EMA50")
    use_scaling = strategy == "Scaling Out (10%→50%, 20%→50%)"
    use_ema5_trail = strategy == "EMA5 Trail (ตัด EMA5 ขายหมด)"

    st.divider()
    fundamental_criteria = {}
    with st.expander("📊 ตัวชี้วัดทางการเงิน (Fundamental)", expanded=False):
        st.caption("✅ เลือกเงื่อนไขที่ต้องการใช้")

        # เปิด/ปิดแต่ละเงื่อนไข
        col_chk1, col_val1 = st.columns([1, 2])
        with col_chk1:
            use_pe = st.checkbox("P/E Ratio", value=False, key="use_pe")
        with col_val1:
            if use_pe:
                max_pe = st.number_input("< ", value=20.0, step=1.0, key="max_pe")
                fundamental_criteria['max_pe'] = max_pe

        col_chk2, col_val2 = st.columns([1, 2])
        with col_chk2:
            use_roe = st.checkbox("ROE", value=False, key="use_roe")
        with col_val2:
            if use_roe:
                min_roe = st.number_input("% > ", value=15.0, step=1.0, key="min_roe")
                fundamental_criteria['min_roe'] = min_roe / 100

        col_chk3, col_val3 = st.columns([1, 2])
        with col_chk3:
            use_de = st.checkbox("D/E Ratio", value=False, key="use_de")
        with col_val3:
            if use_de:
                max_de = st.number_input("< ", value=1.0, step=0.1, key="max_de")
                fundamental_criteria['max_de'] = max_de

        col_chk4, col_val4 = st.columns([1, 2])
        with col_chk4:
            use_gross = st.checkbox("Gross Margin", value=False, key="use_gross")
        with col_val4:
            if use_gross:
                min_gross = st.number_input("% > ", value=40.0, step=5.0, key="min_gross")
                fundamental_criteria['min_gross_margin'] = min_gross / 100

        col_chk5, col_val5 = st.columns([1, 2])
        with col_chk5:
            use_ebit = st.checkbox("EBIT Margin", value=False, key="use_ebit")
        with col_val5:
            if use_ebit:
                min_ebit = st.number_input("% > ", value=10.0, step=1.0, key="min_ebit")
                fundamental_criteria['min_ebit_margin'] = min_ebit / 100

        col_chk6, col_val6 = st.columns([1, 2])
        with col_chk6:
            use_eps = st.checkbox("EPS Growth", value=False, key="use_eps")
        with col_val6:
            if use_eps:
                min_eps = st.number_input("% > ", value=10.0, step=1.0, key="min_eps")
                fundamental_criteria['min_eps_growth'] = min_eps / 100

    # ตรวจสอบว่ามีเงื่อนไข fundamental ถูกเปิดใช้หรือไม่
    use_fundamental = len(fundamental_criteria) > 0

    run = st.button("🚀 รัน Backtest", type="primary", use_container_width=True)

# ══════════ เปิดจากลิงก์แท็บใหม่ (ดูกราฟหุ้นเดียว จากผลสแกน) ══════════
# sidebar ด้านบนตั้งค่าเริ่มต้นตามลิงก์ให้แล้ว จากนี้ใช้ค่า "สด" จาก sidebar เสมอ
# (ปรับ sidebar บนแท็บนี้ได้จริง กราฟจะอัปเดตตาม ไม่ใช่ค่าตายตัวจากตอนสแกน)
effective_scaling = use_scaling
effective_ema_cross = use_ema_cross
effective_hh_hl = use_hh_hl
effective_ema5_trail = use_ema5_trail

if effective_hh_hl:
    entry_desc = ("แพทเทิร์น **Higher-High / Higher-Low 2 ชุดติดกัน** (Low ชุด 2 ต่ำกว่าชุดแรกได้ไม่เกิน `5%`) "
                  "แล้วราคาทะลุ Swing High ล่าสุด (breakout) — **ไม่ใช้เงื่อนไข SET** (price action ของหุ้นล้วนๆ)")
elif effective_ema_cross:
    entry_desc = ("วันที่ `EMA50` ตัดขึ้น `EMA100` **และ** หุ้น `Close>EMA200` · `EMA10>EMA50` · `MACD>0` "
                  "**และ** SET `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200`")
else:
    entry_desc = ("หุ้น `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200` · `MACD>0` "
                  "**และ** SET `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200`")

if effective_ema5_trail:
    exit_desc = "**EMA5 Trail**: ถือเต็มไม้ ขาย `หมด` ทันทีที่ราคาปิด `หลุด EMA5` (หรือ Cut Loss `-8%` ก่อน) — ไม่มี scaling"
elif effective_scaling:
    exit_desc = ("**Scaling Out**: ขาย `50%` ที่กำไร `+10%` → ขาย `50%` ที่เหลือที่กำไร `+20%` "
                 "→ ไม้สุดท้ายถือต่อจนหลุด `-5%` จากจุดสูงสุดหลัง `+20%` (หรือหลุด Cut Loss `-8%` / `EMA50` ก่อนถึง +10%)")
else:
    exit_desc = "Cut Loss `-8%` (เริ่มต้น) · หลังมีกำไร → **ถือจนราคาหลุด `EMA50`** (trailing) จึงขาย"

st.markdown(f"""
**กลยุทธ์ ① — EMA Trend + SET Filter**
- **เข้า** (ครบทุกข้อ): {entry_desc}
- **ออก**: {exit_desc}
""")

if is_deep_link:
    st.caption("🔗 เปิดจากผลสแกน · ปรับตั้งค่าด้านซ้ายได้เลย กราฟจะอัปเดตตาม")
    setclose_q = load_one(SET_SYMBOL, int(years))
    close_q = load_one(symbol, int(years))
    if close_q is None:
        st.error(f"ไม่มีข้อมูล {symbol}")
    else:
        show_stock_detail(symbol, close_q, setclose_q, fee, cap, effective_scaling, effective_ema_cross, effective_hh_hl, effective_ema5_trail, int(years))
    st.stop()

if not run:
    st.info("👈 เลือกโหมด + ตั้งค่า แล้วกด **รัน Backtest**")
    st.stop()

setclose = load_one(SET_SYMBOL, int(years))
if setclose is None:
    st.warning("⚠️ ไม่พบข้อมูล SET — ใช้เงื่อนไขหุ้นอย่างเดียว")

# ══════════ โหมดสแกนทั้งกลุ่ม ══════════
if mode == "สแกนทั้งกลุ่ม":
    syms = group_symbols(group)
    st.subheader(f"🔍 สแกน: {group} ({len(syms)} ตัว)")
    with st.spinner("กำลังโหลดข้อมูลทั้งกลุ่ม..."):
        closes = load_many(syms, int(years))
    if not closes:
        st.error("โหลดข้อมูลไม่สำเร็จ (ลองใหม่ / ลดจำนวนปี)"); st.stop()

    # ══ โหมดจัดพอร์ตหมุนเงิน ══
    if scan_style.startswith("จัดพอร์ต"):
        # Filter by fundamentals ถ้าเปิดใช้
        if use_fundamental:
            filtered_closes = {}
            for sym, c in closes.items():
                fund = get_fundamentals(sym)
                if passes_fundamental_filter(fund, fundamental_criteria):
                    filtered_closes[sym] = c
            if not filtered_closes:
                st.error("ไม่มีหุ้นที่ผ่านเงื่อนไข fundamental"); st.stop()
            st.info(f"ผ่าน Fundamental Filter: {len(filtered_closes)} / {len(closes)} หุ้น")
            closes_to_use = filtered_closes
        else:
            closes_to_use = closes

        with st.spinner("กำลังจำลองพอร์ต..."):
            R = simulate_portfolio(closes_to_use, setclose, fee, n_slots)
        eq = R["eq"]; yrs = len(eq) / 252
        total = eq.iloc[-1] - 1; bh = R["bh"].iloc[-1] - 1
        cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0
        maxdd = (eq / eq.cummax() - 1).min()
        avg_work = (np.mean(R["fill"]) / n_slots * 100) if R["fill"] else 0
        trs = R["trades"]; wr = (len([t for t in trs if t["pnl"] > 0]) / len(trs) * 100) if trs else 0

        st.subheader(f"💼 พอร์ตหมุนเงิน · {group} · ถือ {n_slots} ไม้")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("มูลค่าสุดท้าย", f"{cap*eq.iloc[-1]:,.0f} ฿", f"{cap*total:+,.0f} ฿")
        c2.metric("ผลตอบแทน", f"{total*100:+.1f}%", f"vs ถือทั้งกลุ่ม {bh*100:+.1f}%")
        c3.metric("CAGR / ปี", f"{cagr*100:+.1f}%")
        c4.metric("Max Drawdown", f"{maxdd*100:.1f}%")
        c5, c6, c7 = st.columns(3)
        c5.metric("⏱️ เงินทำงานเฉลี่ย", f"{avg_work:.0f}%", f"ว่าง {100-avg_work:.0f}%")
        c6.metric("จำนวนไม้ทั้งหมด", len(trs))
        c7.metric("Win rate", f"{wr:.0f}%")
        if total > bh:
            st.success("✅ ชนะการถือทั้งกลุ่ม (equal-weight)")
        else:
            st.warning("❌ แพ้การถือทั้งกลุ่ม")

        st.subheader("📈 มูลค่าพอร์ตตามเวลา (บาท)")
        comp = {"พอร์ตหมุนเงิน": eq * cap, "ถือทั้งกลุ่ม (เฉลี่ย)": R["bh"] * cap}
        if setclose is not None:
            s = setclose.reindex(R["idx"]).ffill()
            base = s.dropna()
            if len(base):
                comp["SET Index"] = s / base.iloc[0] * cap
        st.line_chart(pd.DataFrame(comp))

        # สรุปรายตัว
        st.subheader("🏆 สรุปรายหุ้น (กำไรรวมต่อตัว)")
        agg = {}
        for t in trs:
            a = agg.setdefault(t["sym"], {"n": 0, "pnl": 0.0, "win": 0})
            a["n"] += 1; a["pnl"] += t["pnl"] * 100; a["win"] += 1 if t["pnl"] > 0 else 0
        sm = pd.DataFrame([{"หุ้น": k, "ไม้": v["n"], "ชนะ": v["win"],
                            "กำไรรวม%": round(v["pnl"], 1)} for k, v in agg.items()]) \
            .sort_values("กำไรรวม%", ascending=False)
        st.dataframe(sm, use_container_width=True, hide_index=True)

        # log ทุกไม้
        st.subheader(f"🧾 ทุกไม้ ({len(trs)})")
        idx = R["idx"]
        log = pd.DataFrame([{
            "หุ้น": t["sym"],
            "ซื้อ": idx[t["ei"]].strftime("%d/%m/%y"),
            "ขาย": (idx[t["xi"]].strftime("%d/%m/%y") if t["xi"] is not None else "ยังถือ"),
            "เหตุออก": t["reason"], "กำไร%": round(t["pnl"] * 100, 1),
        } for t in sorted(trs, key=lambda x: x["ei"])])
        st.dataframe(log, use_container_width=True, hide_index=True)
        st.caption("เงินทำงานเฉลี่ย = สัดส่วนเงินที่อยู่ในตลาด (ไม่นอนเฉย) · เทียบ 'ถือทั้งกลุ่ม' = ซื้อทุกตัวถือยาวเท่าๆกัน")
        st.stop()

    # ══ โหมดดูรายตัว ══
    rows, prog = [], st.progress(0.0)
    items = list(closes.items())
    for k, (sym, c) in enumerate(items):
        try:
            # เช็ค fundamental filter ถ้าเปิดใช้
            if use_fundamental:
                fund = get_fundamentals(sym)
                if not passes_fundamental_filter(fund, fundamental_criteria):
                    prog.progress((k + 1) / len(items))
                    continue

            _, _, m = build_and_sim(c, setclose, fee, use_scaling, use_ema_cross, use_hh_hl, use_ema5_trail)
            sym_clean = sym.replace(".BK", "")
            rows.append({
                "หุ้น": sym_clean,
                "ประเภท": get_market_type(sym),
                "กลุ่ม": get_stock_sector(sym),
                "ผลตอบแทน%": round(m["total"] * 100, 1),
                "B&H%": round(m["bh"] * 100, 1),
                "ชนะ B&H": "✅" if m["total"] > m["bh"] else "",
                "ไม้": m["nbuy"], "Win%": round(m["wr"]),
                "MaxDD%": round(m["maxdd"] * 100, 1),
                "กำไร(บาท)": round(cap * m["total"]),
            })
        except Exception:
            pass
        prog.progress((k + 1) / len(items))
    prog.empty()

    if not rows:
        st.error("ไม่มีหุ้นที่ผ่านเงื่อนไข (ลองปรับ Fundamental Filter หรือเพิ่มช่วงปี)")
        st.stop()

    res = pd.DataFrame(rows).sort_values("ผลตอบแทน%", ascending=False).reset_index(drop=True)
    beat = (res["ชนะ B&H"] == "✅").sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("หุ้นที่ทดสอบ", len(res))
    c2.metric("ชนะ Buy & Hold", f"{beat} / {len(res)}")
    c3.metric("ผลตอบแทนเฉลี่ย", f"{res['ผลตอบแทน%'].mean():+.1f}%")

    # ตัวเลือก filter ประเภทหุ้น
    all_types = sorted(res["ประเภท"].unique())
    selected_types = st.multiselect("ประเภท", all_types, default=all_types, key="market_filter")
    res_filtered = res[res["ประเภท"].isin(selected_types)]

    if len(res_filtered) == 0:
        st.error("ไม่มีหุ้นหลังจากกรองประเภท")
        st.stop()

    # ตัวเลือกแสดงผล
    view_mode = st.radio("แสดงผล", ["ทั้งหมด (เรียงผลตอบแทน)", "แยกตามกลุ่มอุตสาหกรรม"], horizontal=True, key="view_mode_scan")

    def render_scan_table(data):
        """ตารางผลสแกน: คอลัมน์ 'หุ้น' เป็นลิงก์ <a target=_blank> จริง คลิกแล้วเปิดแท็บใหม่ทันที"""
        import html as html_lib
        cols = ["หุ้น", "ผลตอบแทน%", "B&H%", "ชนะ B&H", "ไม้", "Win%", "MaxDD%", "กำไร(บาท)"]
        header = "".join(
            f'<th style="text-align:{"left" if c == "หุ้น" else "right"};padding:6px 10px;'
            f'border-bottom:2px solid rgba(128,128,128,.4);white-space:nowrap;">{c}</th>'
            for c in cols
        )
        rows_html = []
        for _, r in data.iterrows():
            sym = str(r["หุ้น"])
            url = (f"?sym={sym}&years={int(years)}&cap={cap:.0f}&fee={fee}"
                   f"&scaling={1 if use_scaling else 0}&cross={1 if use_ema_cross else 0}"
                   f"&hhhl={1 if use_hh_hl else 0}&ema5trail={1 if use_ema5_trail else 0}")
            tds = [f'<td style="padding:6px 10px;"><a href="{html_lib.escape(url)}" target="_blank" '
                   f'style="color:#3fa7ff;text-decoration:none;font-weight:600;">{html_lib.escape(sym)}</a></td>']
            for c in cols[1:]:
                tds.append(f'<td style="text-align:right;padding:6px 10px;white-space:nowrap;">{html_lib.escape(str(r[c]))}</td>')
            rows_html.append(f'<tr style="border-bottom:1px solid rgba(128,128,128,.15);">{"".join(tds)}</tr>')
        st.markdown(
            f'<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:14px;">'
            f'<thead><tr>{header}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>',
            unsafe_allow_html=True,
        )

    if view_mode == "แยกตามกลุ่มอุตสาหกรรม":
        # แสดงแยกกลุ่ม
        st.caption("👉 คลิกที่ชื่อหุ้น → กราฟเด้งขึ้นแท็บใหม่ทันที (ใช้เงื่อนไข/กลยุทธ์เดียวกับที่ตั้งไว้)")
        sectors_in_result = sorted(res_filtered["กลุ่ม"].unique())
        for sector in sectors_in_result:
            sector_data = res_filtered[res_filtered["กลุ่ม"] == sector].sort_values("ผลตอบแทน%", ascending=False)
            sector_beat = (sector_data["ชนะ B&H"] == "✅").sum()
            with st.expander(f"📊 {sector} ({len(sector_data)} หุ้น) - เฉลี่ย {sector_data['ผลตอบแทน%'].mean():+.1f}% | ชนะ {sector_beat}/{len(sector_data)}", expanded=True):
                render_scan_table(sector_data)
    else:
        # แสดงทั้งหมด
        st.caption("👉 คลิกที่ชื่อหุ้น → กราฟเด้งขึ้นแท็บใหม่ทันที (ใช้เงื่อนไข/กลยุทธ์เดียวกับที่ตั้งไว้) · เรียงผลตอบแทนสูง→ต่ำ")
        render_scan_table(res_filtered)
    st.caption("⚠️ backtest ≠ ผลจริง · กัน overfit: ลองหลายช่วงเวลา · Sandbox ≤10%")
    st.stop()

# ══════════ โหมดหุ้นเดียว ══════════
close = load_one(symbol, int(years))
if close is None:
    st.error(f"ไม่มีข้อมูล {symbol}"); st.stop()
show_stock_detail(symbol, close, setclose, fee, cap, use_scaling, use_ema_cross, use_hh_hl, use_ema5_trail, int(years))
st.caption("⚠️ backtest ≠ ผลจริง · ลองหลายตัว/หลายช่วง กัน overfit · Sandbox ≤10%")
