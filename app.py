"""
Thai Trade Bot — Backtest web app (Streamlit)
รัน: streamlit run app.py

กลยุทธ์ตายตัว (fixed) · เลือกกลยุทธ์ + หุ้น · ไม่ต้องปรับพารามิเตอร์
"""
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Thai Trade Bot — Backtest", page_icon="🤖", layout="wide")
st.title("🤖 Thai Trade Bot — Backtest")
st.caption("ทดสอบกลยุทธ์บนข้อมูลอดีต · เทียบ Buy & Hold · เพื่อการเรียนรู้ ไม่ใช่คำแนะนำลงทุน")

SET_SYMBOL = "^SET.BK"  # ดัชนี SET บน Yahoo


@st.cache_data(ttl=3600, show_spinner=False)
def load(symbol, years):
    import yfinance as yf
    df = yf.download(symbol, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
    if df is None or df.empty:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(s, period=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = (-d.clip(upper=0)).rolling(period).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50)


# ── sidebar ──
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    strat = st.selectbox("กลยุทธ์", ["① EMA Trend + SET Filter"])
    symbol = st.text_input("หุ้น (เช่น PIMO.BK)", "PIMO.BK").strip().upper()
    years = st.slider("ปีย้อนหลัง", 1, 10, 5)
    cap = st.number_input("เงินต้น (บาท)", 1000, 10_000_000, 50_000, 1000)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, 0.2, 0.05) / 100
    run = st.button("🚀 รัน Backtest", type="primary", use_container_width=True)

st.markdown("""
**กลยุทธ์ ① — EMA Trend + SET Filter**
- **เข้า** (ครบทุกข้อ): หุ้น `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200` **และ** SET เข้าเงื่อนไขเดียวกัน
- **ออก**: Cut Loss `-5%` · `+10%` (RSI≥80 ขาย / <80 ปล่อยวิ่ง) · `+15%` ขายครึ่ง · เทรนด์พัง (EMA10<EMA50) ขายที่เหลือ
""")

if not run:
    st.info("👈 ใส่ชื่อหุ้น แล้วกด **รัน Backtest**")
    st.stop()

# ── โหลดข้อมูล ──
with st.spinner("กำลังโหลดข้อมูล..."):
    px = load(symbol, int(years))
    setpx = load(SET_SYMBOL, int(years))
if px is None:
    st.error(f"ไม่มีข้อมูล {symbol}"); st.stop()

df = pd.DataFrame({"close": px})
df["ema10"] = ema(df["close"], 10)
df["ema50"] = ema(df["close"], 50)
df["ema200"] = ema(df["close"], 200)
df["rsi"] = rsi(df["close"])

stock_ok = (df["close"] > df["ema200"]) & (df["ema10"] > df["ema50"]) & (df["ema50"] > df["ema200"])

if setpx is not None:
    s = setpx.reindex(df.index).ffill()
    set_ok = (s > ema(s, 200)) & (ema(s, 10) > ema(s, 50)) & (ema(s, 50) > ema(s, 200))
    cond = stock_ok & set_ok
    st.caption("✅ ใช้ SET filter ด้วย")
else:
    cond = stock_ok
    st.warning("⚠️ ไม่พบข้อมูล SET — ใช้เงื่อนไขหุ้นอย่างเดียว")

# ── simulate (event loop, มีขายครึ่ง) ──
CUT, TP1, TP_HALF = 0.05, 0.10, 0.15
close = df["close"].values
ret = df["close"].pct_change().fillna(0).values
rsi_v = df["rsi"].values
ema10_v, ema50_v = df["ema10"].values, df["ema50"].values
cond_v = cond.values

held, ep, half = 0.0, 0.0, False
strat_ret, held_ser, events = [], [], []
trade_ret, cur_real = [], 0.0

for i in range(len(df)):
    r = held * ret[i]
    fee_today = 0.0
    price = close[i]
    if held > 0:
        chg = price / ep - 1
        if chg <= -CUT:                                   # cut loss
            cur_real += held * chg; trade_ret.append(cur_real)
            events.append((i, "SELL·SL", price)); fee_today += held * fee; held = 0.0; half = False
        elif chg >= TP1 and rsi_v[i] >= 80:               # +10% & overbought → ขายทิ้ง
            cur_real += held * chg; trade_ret.append(cur_real)
            events.append((i, "SELL·TP", price)); fee_today += held * fee; held = 0.0; half = False
        elif chg >= TP_HALF and not half and held >= 1.0: # +15% → ขายครึ่ง
            cur_real += 0.5 * chg
            events.append((i, "SELL·½", price)); fee_today += 0.5 * fee; held = 0.5; half = True
        elif ema10_v[i] < ema50_v[i]:                     # เทรนด์พัง → ขายที่เหลือ
            cur_real += held * chg; trade_ret.append(cur_real)
            events.append((i, "SELL·trend", price)); fee_today += held * fee; held = 0.0; half = False
    else:
        if cond_v[i]:                                     # เข้า
            events.append((i, "BUY", price)); fee_today += fee; held = 1.0; ep = price; half = False; cur_real = 0.0
    strat_ret.append(r - fee_today)
    held_ser.append(held)

df["equity"] = (1 + pd.Series(strat_ret, index=df.index)).cumprod()
df["bh"] = (1 + df["close"].pct_change().fillna(0)).cumprod()

# ── metrics ──
eq = df["equity"]; yrs = len(df) / 252
total = eq.iloc[-1] - 1
bh = df["bh"].iloc[-1] - 1
cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0
maxdd = (eq / eq.cummax() - 1).min()
nbuy = sum(1 for e in events if e[1] == "BUY")
wr = (len([t for t in trade_ret if t > 0]) / len(trade_ret) * 100) if trade_ret else 0

final_value = cap * eq.iloc[-1]
profit_baht = final_value - cap

c1, c2, c3, c4 = st.columns(4)
c1.metric("มูลค่าสุดท้าย", f"{final_value:,.0f} ฿", f"{profit_baht:+,.0f} ฿")
c2.metric("ผลตอบแทน (บอต)", f"{total*100:+.1f}%", f"vs B&H {bh*100:+.1f}%")
c3.metric("CAGR / ปี", f"{cagr*100:+.1f}%")
c4.metric("Max Drawdown", f"{maxdd*100:.1f}%")

c5, c6 = st.columns(2)
c5.metric("Win rate", f"{wr:.0f}%", f"{nbuy} ไม้")
c6.metric("ถ้าถือเฉยๆ (Buy & Hold)", f"{cap*df['bh'].iloc[-1]:,.0f} ฿", f"{cap*bh:+,.0f} ฿")

if total > bh:
    st.success("✅ ชนะ Buy & Hold")
else:
    st.warning("❌ แพ้ Buy & Hold")

# ── equity (บาท) ──
st.subheader("📈 มูลค่าเงินต้นเมื่อเวลาผ่านไป (บาท)")
st.line_chart(pd.DataFrame({"บอต": df["equity"] * cap, "Buy & Hold": df["bh"] * cap}))

# ── price + จุดซื้อขาย (Altair) ──
st.subheader("💹 ราคา + EMA + จุดซื้อ/ขาย")
pdf = pd.DataFrame({"date": df.index, "close": df["close"].values,
                    "EMA50": df["ema50"].values, "EMA200": df["ema200"].values})
line = alt.Chart(pdf).mark_line(color="#9aa4b2").encode(x="date:T", y=alt.Y("close:Q", title="ราคา"))
e50 = alt.Chart(pdf).mark_line(color="#3fb950", strokeDash=[4, 3]).encode(x="date:T", y="EMA50:Q")
e200 = alt.Chart(pdf).mark_line(color="#f0883e", strokeDash=[4, 3]).encode(x="date:T", y="EMA200:Q")

mk = pd.DataFrame([{"date": df.index[i], "price": p,
                    "act": "BUY" if a == "BUY" else "SELL"} for (i, a, p) in events])
layers = [line, e50, e200]
if not mk.empty:
    buys = alt.Chart(mk[mk.act == "BUY"]).mark_point(shape="triangle-up", size=90, color="#2ea043", filled=True).encode(x="date:T", y="price:Q")
    sells = alt.Chart(mk[mk.act == "SELL"]).mark_point(shape="triangle-down", size=90, color="#f85149", filled=True).encode(x="date:T", y="price:Q")
    layers += [buys, sells]
st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# ── event log ──
st.subheader(f"🧾 รายการซื้อ/ขาย ({len(events)})")
if events:
    st.dataframe(pd.DataFrame([{
        "วันที่": df.index[i].strftime("%Y-%m-%d"),
        "การกระทำ": a,
        "ราคา": round(p, 2),
    } for (i, a, p) in events]), use_container_width=True, hide_index=True)
else:
    st.info("ไม่มีสัญญาณเข้าในช่วงนี้ (เงื่อนไขเข้ม)")

st.caption("⚠️ backtest ≠ ผลจริง · ลองหลายตัว/หลายช่วง กัน overfit · Sandbox ≤10%")
