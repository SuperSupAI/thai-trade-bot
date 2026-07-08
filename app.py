"""
Thai Trade Bot — Backtest web app (Streamlit)
กลยุทธ์ ① EMA Trend + SET Filter · โหมด: หุ้นเดียว / สแกนทั้งกลุ่ม
"""
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from universe import SECTORS, group_symbols

st.set_page_config(page_title="Thai Trade Bot — Backtest", page_icon="🤖", layout="wide")
st.title("🤖 Thai Trade Bot — Backtest")
st.caption("ทดสอบกลยุทธ์บนข้อมูลอดีต · เทียบ Buy & Hold · เพื่อการเรียนรู้ ไม่ใช่คำแนะนำลงทุน")

SET_SYMBOL = "^SET.BK"
CUT = 0.08   # initial stop loss (กว้างขึ้น กัน noise) · หลังมีกำไรใช้ trailing EMA50


# ── data / indicators ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_one(symbol, years):
    import yfinance as yf
    df = yf.download(symbol, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
    if df is None or df.empty:
        return None
    c = df["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.dropna()


@st.cache_data(ttl=3600, show_spinner=False)
def load_many(symbols, years):
    import yfinance as yf
    data = yf.download(" ".join(symbols), period=f"{years}y", interval="1d",
                       auto_adjust=True, progress=False, group_by="ticker", threads=True)
    out = {}
    for s in symbols:
        try:
            c = data[s]["Close"] if isinstance(data.columns, pd.MultiIndex) else data["Close"]
            c = c.dropna()
            if len(c) > 210:
                out[s] = c
        except Exception:
            pass
    return out


def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(s, p=14):
    d = s.diff(); up = d.clip(lower=0).rolling(p).mean(); dn = (-d.clip(upper=0)).rolling(p).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


def build_and_sim(close, setclose, fee):
    df = pd.DataFrame({"close": close})
    df["ema10"] = ema(close, 10); df["ema50"] = ema(close, 50); df["ema200"] = ema(close, 200)
    df["rsi"] = rsi(close); df["macd"] = ema(close, 12) - ema(close, 26)
    stock_ok = (df["close"] > df["ema200"]) & (df["ema10"] > df["ema50"]) \
        & (df["ema50"] > df["ema200"]) & (df["macd"] > 0)
    if setclose is not None:
        s = setclose.reindex(df.index).ffill()
        set_ok = (s > ema(s, 200)) & (ema(s, 10) > ema(s, 50)) & (ema(s, 50) > ema(s, 200))
        cond = (stock_ok & set_ok).values
    else:
        cond = stock_ok.values

    c = df["close"].values
    ret = df["close"].pct_change().fillna(0).values
    e50 = df["ema50"].values

    held, ep, run_eq, days_in = 0.0, 0.0, 1.0, 0
    strat, events, trades, entry = [], [], [], None
    for i in range(len(df)):
        if held > 0:
            days_in += 1                           # วันที่เงินทำงาน (ถือหุ้นอยู่)
        r = held * ret[i]; ft = 0.0; price = c[i]
        if held > 0:
            chg = price / ep - 1
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


def show_stock_detail(symbol, close, setclose, fee, cap):
    """แสดงรายละเอียดหุ้นตัวเดียว: เมตริก + กราฟจุดซื้อขาย + log"""
    df, events, m = build_and_sim(close, setclose, fee)
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

    st.subheader("📈 มูลค่าเงินต้นตามเวลา (บาท)")
    st.line_chart(pd.DataFrame({"บอต": df["equity"] * cap, "Buy & Hold": df["bh"] * cap}))

    st.subheader("💹 ราคา + EMA + จุดซื้อ/ขาย")
    pdf = pd.DataFrame({"date": df.index, "close": df["close"].values,
                        "EMA50": df["ema50"].values, "EMA200": df["ema200"].values})
    line = alt.Chart(pdf).mark_line(color="#9aa4b2").encode(x="date:T", y=alt.Y("close:Q", title="ราคา"))
    e50 = alt.Chart(pdf).mark_line(color="#3fb950", strokeDash=[4, 3]).encode(x="date:T", y="EMA50:Q")
    e200 = alt.Chart(pdf).mark_line(color="#f0883e", strokeDash=[4, 3]).encode(x="date:T", y="EMA200:Q")
    mk = pd.DataFrame([{"date": df.index[i], "price": p, "act": "BUY" if a == "BUY" else "SELL"}
                       for (i, a, p) in events])
    layers = [line, e50, e200]
    if not mk.empty:
        layers.append(alt.Chart(mk[mk.act == "BUY"]).mark_point(shape="triangle-up", size=90, color="#2ea043", filled=True).encode(x="date:T", y="price:Q"))
        layers.append(alt.Chart(mk[mk.act == "SELL"]).mark_point(shape="triangle-down", size=90, color="#f85149", filled=True).encode(x="date:T", y="price:Q"))
    st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

    trades = m["trades"]
    st.subheader(f"🧾 แต่ละไม้ที่เทรด ({len(trades)})")
    if trades:
        rows = []
        for k, t in enumerate(trades, 1):
            last = t["exit_i"] if t["exit_i"] is not None else len(df) - 1
            rows.append({
                "ไม้": k,
                "ซื้อ": df.index[t["entry_i"]].strftime("%d/%m/%y"),
                "ราคาซื้อ": round(t["entry_price"], 2),
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


# ── sidebar ──
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    mode = st.radio("โหมด", ["หุ้นเดียว", "สแกนทั้งกลุ่ม"])
    if mode == "หุ้นเดียว":
        symbol = st.text_input("หุ้น (เช่น PIMO.BK)", "PIMO.BK").strip().upper()
    else:
        group = st.selectbox("กลุ่ม", ["SET100 (ทั้งหมด)"] + list(SECTORS.keys()))
        scan_style = st.radio("รูปแบบ", ["ดูรายตัว (ตาราง+คลิก)", "จัดพอร์ตหมุนเงิน (ไม่ให้ว่าง)"])
        n_slots = 1
        if scan_style.startswith("จัดพอร์ต"):
            n_slots = st.radio("ถือพร้อมกันกี่ตัว", [1, 5], horizontal=True,
                               format_func=lambda x: f"{x} ไม้")
    years = st.slider("ปีย้อนหลัง", 1, 10, 5)
    cap = st.number_input("เงินต้น (บาท)", 1000, 10_000_000, 50_000, 1000)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, 0.2, 0.05) / 100
    run = st.button("🚀 รัน Backtest", type="primary", use_container_width=True)

st.markdown("""
**กลยุทธ์ ① — EMA Trend + SET Filter**
- **เข้า** (ครบทุกข้อ): หุ้น `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200` · `MACD>0` **และ** SET `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200`
- **ออก (ขี่เทรนด์ ปล่อยกำไรวิ่ง)**: Cut Loss `-8%` (เริ่มต้น) · หลังมีกำไร → **ถือจนราคาหลุด `EMA50`** (trailing) จึงขาย
""")

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
        with st.spinner("กำลังจำลองพอร์ต..."):
            R = simulate_portfolio(closes, setclose, fee, n_slots)
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
        st.line_chart(pd.DataFrame({"พอร์ตหมุนเงิน": eq * cap, "ถือทั้งกลุ่ม (เฉลี่ย)": R["bh"] * cap}))

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
            _, _, m = build_and_sim(c, setclose, fee)
            rows.append({
                "หุ้น": sym.replace(".BK", ""),
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

    res = pd.DataFrame(rows).sort_values("ผลตอบแทน%", ascending=False).reset_index(drop=True)
    beat = (res["ชนะ B&H"] == "✅").sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("หุ้นที่ทดสอบ", len(res))
    c2.metric("ชนะ Buy & Hold", f"{beat} / {len(res)}")
    c3.metric("ผลตอบแทนเฉลี่ย", f"{res['ผลตอบแทน%'].mean():+.1f}%")
    st.caption("👉 คลิกที่แถวหุ้น เพื่อดูกราฟ+จุดซื้อขายของตัวนั้น · เรียงผลตอบแทนสูง→ต่ำ")
    event = st.dataframe(res, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row", key="scan_tbl")
    sel = event.selection.rows if event and event.selection else []
    if sel:
        sym = res.iloc[sel[0]]["หุ้น"] + ".BK"
        st.divider()
        show_stock_detail(sym, closes[sym], setclose, fee, cap)
    else:
        st.info("👆 คลิกแถวหุ้นในตารางเพื่อดูรายละเอียด")
    st.caption("⚠️ backtest ≠ ผลจริง · กัน overfit: ลองหลายช่วงเวลา · Sandbox ≤10%")
    st.stop()

# ══════════ โหมดหุ้นเดียว ══════════
close = load_one(symbol, int(years))
if close is None:
    st.error(f"ไม่มีข้อมูล {symbol}"); st.stop()
show_stock_detail(symbol, close, setclose, fee, cap)
st.caption("⚠️ backtest ≠ ผลจริง · ลองหลายตัว/หลายช่วง กัน overfit · Sandbox ≤10%")
