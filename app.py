"""
Thai Trade Bot — Backtest web app (Streamlit)
รัน: streamlit run app.py
ใช้ logic จาก backtest.py
"""
import pandas as pd
import streamlit as st
import backtest as bt

st.set_page_config(page_title="Thai Trade Bot — Backtest", page_icon="🤖", layout="wide")

st.title("🤖 Thai Trade Bot — Backtest")
st.caption("ทดสอบกลยุทธ์บนข้อมูลอดีต · เทียบ Buy & Hold เสมอ · เพื่อการเรียนรู้ ไม่ใช่คำแนะนำลงทุน")

with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    symbol = st.text_input("หุ้น (เช่น PIMO.BK, SELIC.BK)", "PIMO.BK").strip().upper()
    years = st.slider("จำนวนปีย้อนหลัง", 1, 10, 5)
    fast = st.number_input("SMA เร็ว (fast)", 2, 200, 20)
    slow = st.number_input("SMA ช้า (slow)", 5, 400, 50)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, 0.2, 0.05) / 100
    run = st.button("🚀 รัน Backtest", type="primary", use_container_width=True)

if not run:
    st.info("👈 ตั้งค่าทางซ้าย แล้วกด **รัน Backtest**")
    st.stop()

if fast >= slow:
    st.error("fast ต้องน้อยกว่า slow"); st.stop()

try:
    with st.spinner(f"กำลังโหลดข้อมูล {symbol} ..."):
        df = bt.load(symbol, years)
        df = bt.backtest(df, int(fast), int(slow), fee)
except SystemExit as e:
    st.error(str(e)); st.stop()
except Exception as e:
    st.error(f"ผิดพลาด: {e}"); st.stop()

# ── เมตริก ──
eq = df["equity"]; n = len(df); yrs = n / 252
total = eq.iloc[-1] - 1
bh = df["bh"].iloc[-1] - 1
cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else 0
maxdd = (eq / eq.cummax() - 1).min()
tr = bt.per_trade(df, fee)
wins = [t for t in tr if t > 0]
wr = (len(wins) / len(tr) * 100) if tr else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("ผลตอบแทน (บอต)", f"{total*100:+.1f}%", f"vs B&H {bh*100:+.1f}%")
c2.metric("CAGR / ปี", f"{cagr*100:+.1f}%")
c3.metric("Max Drawdown", f"{maxdd*100:.1f}%")
c4.metric("Win rate", f"{wr:.0f}%", f"{len(tr)} ไม้")

if total > bh:
    st.success("✅ ชนะ Buy & Hold")
else:
    st.warning("❌ แพ้ Buy & Hold — กลยุทธ์นี้ยังไม่คุ้ม (ลองตัวอื่น / พารามิเตอร์อื่น)")

# ── กราฟ ──
st.subheader("📈 Equity Curve (เริ่มที่ 1.0)")
st.line_chart(pd.DataFrame({"บอต": df["equity"], "Buy & Hold": df["bh"]}))

st.subheader("💹 ราคา + เส้น SMA")
st.line_chart(pd.DataFrame({
    "ราคา": df["close"],
    f"SMA{int(fast)}": df["sma_f"],
    f"SMA{int(slow)}": df["sma_s"],
}))

# ── ตารางไม้ ──
st.subheader(f"🧾 ไม้ที่เทรด ({len(tr)})")
if tr:
    td = pd.DataFrame({
        "ไม้ที่": range(1, len(tr) + 1),
        "ผลตอบแทน %": [round(t * 100, 2) for t in tr],
        "ผล": ["✅ กำไร" if t > 0 else "❌ ขาดทุน" for t in tr],
    })
    st.dataframe(td, use_container_width=True, hide_index=True)
else:
    st.info("ไม่มีไม้ในช่วงนี้")

st.caption("⚠️ ชนะครั้งเดียวไม่พอ — ลองหลายตัว/หลายช่วงเวลา กัน overfit · backtest ≠ ผลจริง · เล่นในกรอบ Sandbox ≤10%")
