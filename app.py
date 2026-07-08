"""
Thai Trade Bot — Backtest web app (Streamlit)
รัน: streamlit run app.py

แนวคิดเงื่อนไข: base = SMA cross · เพิ่ม "ตัวกรอง" เปิด/ปิดได้ทีละอัน (AND กัน)
→ ล็อกทีละคอนดิชัน เทสต์ว่าอันไหนช่วยให้ดีขึ้น
"""
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Thai Trade Bot — Backtest", page_icon="🤖", layout="wide")
st.title("🤖 Thai Trade Bot — Backtest")
st.caption("ทดสอบกลยุทธ์บนข้อมูลอดีต · เทียบ Buy & Hold เสมอ · เพื่อการเรียนรู้ ไม่ใช่คำแนะนำลงทุน")


# ── data / indicators ──────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load(symbol, years):
    import yfinance as yf
    df = yf.download(symbol, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise ValueError(f"ไม่มีข้อมูล {symbol} (ลองสัญลักษณ์อื่น หรือเช็กเน็ต)")
    close = df["Close"];  vol = df["Volume"]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    if isinstance(vol, pd.DataFrame):   vol = vol.iloc[:, 0]
    return pd.DataFrame({"close": close, "volume": vol}).dropna()


def rsi(series, period=14):
    d = series.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = (-d.clip(upper=0)).rolling(period).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def per_trade(close, pos, fee):
    trades, inpos, ep = [], False, 0.0
    for price, p in zip(close, pos):
        if p == 1 and not inpos: inpos, ep = True, price
        elif p == 0 and inpos:   inpos = False; trades.append(price / ep - 1 - 2 * fee)
    if inpos: trades.append(close[-1] / ep - 1 - fee)
    return trades


# ── sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    symbol = st.text_input("หุ้น (เช่น PIMO.BK)", "PIMO.BK").strip().upper()
    years = st.slider("ปีย้อนหลัง", 1, 10, 5)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, 0.2, 0.05) / 100

    st.subheader("📐 กลยุทธ์หลัก (Base)")
    fast = st.number_input("SMA เร็ว", 2, 200, 20)
    slow = st.number_input("SMA ช้า", 5, 400, 50)

    st.subheader("🔓 เงื่อนไขเสริม (เปิด/ปิดทีละอัน)")
    use_trend = st.checkbox("① เทรนด์ใหญ่: ราคา > SMA200", value=False)
    use_rsi   = st.checkbox("② RSI ไม่ overbought", value=False)
    rsi_max   = st.slider("   RSI ต้อง <", 50, 90, 70, disabled=not use_rsi)
    use_vol   = st.checkbox("③ Volume > เฉลี่ย 20 วัน", value=False)

    run = st.button("🚀 รัน Backtest", type="primary", use_container_width=True)

if not run:
    st.info("👈 ตั้งค่าทางซ้าย · ติ๊กเงื่อนไขเสริมทีละอันเพื่อดูว่าช่วยไหม · แล้วกด **รัน Backtest**")
    st.stop()
if fast >= slow:
    st.error("SMA เร็ว ต้องน้อยกว่า SMA ช้า"); st.stop()

try:
    with st.spinner(f"กำลังโหลด {symbol} ..."):
        df = load(symbol, int(years))
except Exception as e:
    st.error(f"ผิดพลาด: {e}"); st.stop()

# ── indicators ──
df["sma_f"] = df["close"].rolling(int(fast)).mean()
df["sma_s"] = df["close"].rolling(int(slow)).mean()
df["sma200"] = df["close"].rolling(200).mean()
df["rsi"] = rsi(df["close"])
df["vol_ma"] = df["volume"].rolling(20).mean()

# ── สร้างสัญญาณ: base AND เงื่อนไขที่เปิด ──
cond = df["sma_f"] > df["sma_s"]           # base
active = ["SMA cross"]
if use_trend: cond &= df["close"] > df["sma200"];   active.append("Trend>SMA200")
if use_rsi:   cond &= df["rsi"] < rsi_max;           active.append(f"RSI<{rsi_max}")
if use_vol:   cond &= df["volume"] > df["vol_ma"];   active.append("Vol>MA20")

df["signal"] = cond.astype(float)
df["pos"] = df["signal"].shift(1).fillna(0.0)         # เข้าตำแหน่งวันถัดไป (กันมองอนาคต)
df["ret"] = df["close"].pct_change().fillna(0.0)
df["strat"] = df["pos"] * df["ret"] - df["pos"].diff().abs().fillna(0) * fee
df["equity"] = (1 + df["strat"]).cumprod()
df["bh"] = (1 + df["ret"]).cumprod()

st.caption("เงื่อนไขที่ใช้: " + " + ".join(active))

# ── metrics ──
eq = df["equity"]; yrs = len(df) / 252
total = eq.iloc[-1] - 1
bh = df["bh"].iloc[-1] - 1
cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0
maxdd = (eq / eq.cummax() - 1).min()
tr = per_trade(df["close"].values, df["pos"].values, fee)
wr = (len([t for t in tr if t > 0]) / len(tr) * 100) if tr else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("ผลตอบแทน (บอต)", f"{total*100:+.1f}%", f"vs B&H {bh*100:+.1f}%")
c2.metric("CAGR / ปี", f"{cagr*100:+.1f}%")
c3.metric("Max Drawdown", f"{maxdd*100:.1f}%")
c4.metric("Win rate", f"{wr:.0f}%", f"{len(tr)} ไม้")

st.success("✅ ชนะ Buy & Hold") if total > bh else st.warning("❌ แพ้ Buy & Hold — ลองเปิด/ปิดเงื่อนไข หรือปรับพารามิเตอร์")

st.subheader("📈 Equity Curve")
st.line_chart(pd.DataFrame({"บอต": df["equity"], "Buy & Hold": df["bh"]}))
st.subheader("💹 ราคา + SMA")
st.line_chart(pd.DataFrame({"ราคา": df["close"], f"SMA{int(fast)}": df["sma_f"], f"SMA{int(slow)}": df["sma_s"]}))

st.subheader(f"🧾 ไม้ที่เทรด ({len(tr)})")
if tr:
    st.dataframe(pd.DataFrame({
        "ไม้ที่": range(1, len(tr) + 1),
        "ผลตอบแทน %": [round(t * 100, 2) for t in tr],
        "ผล": ["✅ กำไร" if t > 0 else "❌ ขาดทุน" for t in tr],
    }), use_container_width=True, hide_index=True)
else:
    st.info("ไม่มีไม้ในช่วงนี้ (เงื่อนไขเข้มไป?)")

st.caption("⚠️ ชนะครั้งเดียวไม่พอ — ลองหลายตัว/หลายช่วงเวลา กัน overfit · backtest ≠ ผลจริง · Sandbox ≤10%")
