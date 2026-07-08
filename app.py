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
CUT, TP1, TP_HALF = 0.05, 0.10, 0.15


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
    rsi_v = df["rsi"].values; e10 = df["ema10"].values; e50 = df["ema50"].values

    held, ep, half = 0.0, 0.0, False
    strat, events, trade_ret, cur = [], [], [], 0.0
    for i in range(len(df)):
        r = held * ret[i]; ft = 0.0; price = c[i]
        if held > 0:
            chg = price / ep - 1
            if chg <= -CUT:
                cur += held * chg; trade_ret.append(cur); events.append((i, "SELL·SL", price)); ft += held * fee; held = 0; half = False
            elif chg >= TP1 and rsi_v[i] >= 80:
                cur += held * chg; trade_ret.append(cur); events.append((i, "SELL·TP", price)); ft += held * fee; held = 0; half = False
            elif chg >= TP_HALF and not half and held >= 1.0:
                cur += 0.5 * chg; events.append((i, "SELL·½", price)); ft += 0.5 * fee; held = 0.5; half = True
            elif e10[i] < e50[i]:
                cur += held * chg; trade_ret.append(cur); events.append((i, "SELL·trend", price)); ft += held * fee; held = 0; half = False
        else:
            if cond[i]:
                events.append((i, "BUY", price)); ft += fee; held = 1.0; ep = price; half = False; cur = 0.0
        strat.append(r - ft)
    df["equity"] = (1 + pd.Series(strat, index=df.index)).cumprod()
    df["bh"] = (1 + df["close"].pct_change().fillna(0)).cumprod()

    eq = df["equity"]; yrs = len(df) / 252
    m = dict(
        total=eq.iloc[-1] - 1, bh=df["bh"].iloc[-1] - 1,
        cagr=eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0,
        maxdd=(eq / eq.cummax() - 1).min(),
        nbuy=sum(1 for e in events if e[1] == "BUY"),
        wr=(len([t for t in trade_ret if t > 0]) / len(trade_ret) * 100) if trade_ret else 0,
    )
    return df, events, m


# ── sidebar ──
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    mode = st.radio("โหมด", ["หุ้นเดียว", "สแกนทั้งกลุ่ม"])
    if mode == "หุ้นเดียว":
        symbol = st.text_input("หุ้น (เช่น PIMO.BK)", "PIMO.BK").strip().upper()
    else:
        group = st.selectbox("กลุ่ม", ["SET100 (ทั้งหมด)"] + list(SECTORS.keys()))
    years = st.slider("ปีย้อนหลัง", 1, 10, 5)
    cap = st.number_input("เงินต้น (บาท)", 1000, 10_000_000, 50_000, 1000)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, 0.2, 0.05) / 100
    run = st.button("🚀 รัน Backtest", type="primary", use_container_width=True)

st.markdown("""
**กลยุทธ์ ① — EMA Trend + SET Filter**
- **เข้า** (ครบทุกข้อ): หุ้น `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200` · `MACD>0` **และ** SET `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200`
- **ออก**: Cut Loss `-5%` · `+10%` (RSI≥80 ขาย / <80 ปล่อยวิ่ง) · `+15%` ขายครึ่ง · เทรนด์พัง (EMA10<EMA50) ขายที่เหลือ
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
    st.dataframe(res, use_container_width=True, hide_index=True)
    st.caption("เรียงจากผลตอบแทนสูง→ต่ำ · 'ชนะ B&H' = กลยุทธ์ดีกว่าถือเฉยๆ · ⚠️ กัน overfit: ลองหลายช่วงเวลา")
    st.stop()

# ══════════ โหมดหุ้นเดียว ══════════
close = load_one(symbol, int(years))
if close is None:
    st.error(f"ไม่มีข้อมูล {symbol}"); st.stop()
df, events, m = build_and_sim(close, setclose, fee)

eq = df["equity"]
final_value = cap * eq.iloc[-1]; profit = final_value - cap
c1, c2, c3, c4 = st.columns(4)
c1.metric("มูลค่าสุดท้าย", f"{final_value:,.0f} ฿", f"{profit:+,.0f} ฿")
c2.metric("ผลตอบแทน (บอต)", f"{m['total']*100:+.1f}%", f"vs B&H {m['bh']*100:+.1f}%")
c3.metric("CAGR / ปี", f"{m['cagr']*100:+.1f}%")
c4.metric("Max Drawdown", f"{m['maxdd']*100:.1f}%")
c5, c6 = st.columns(2)
c5.metric("Win rate", f"{m['wr']:.0f}%", f"{m['nbuy']} ไม้")
c6.metric("ถ้าถือเฉยๆ (B&H)", f"{cap*df['bh'].iloc[-1]:,.0f} ฿", f"{cap*m['bh']:+,.0f} ฿")

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

st.subheader(f"🧾 รายการซื้อ/ขาย ({len(events)})")
if events:
    st.dataframe(pd.DataFrame([{"วันที่": df.index[i].strftime("%Y-%m-%d"), "การกระทำ": a, "ราคา": round(p, 2)}
                              for (i, a, p) in events]), use_container_width=True, hide_index=True)
else:
    st.info("ไม่มีสัญญาณเข้าในช่วงนี้")

st.caption("⚠️ backtest ≠ ผลจริง · ลองหลายตัว/หลายช่วง กัน overfit · Sandbox ≤10%")
