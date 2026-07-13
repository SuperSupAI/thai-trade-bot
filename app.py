"""
Thai Trade Bot — Backtest web app (Streamlit)
กลยุทธ์ ① EMA Trend + SET Filter · โหมด: หุ้นเดียว / สแกนทั้งกลุ่ม
"""
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from universe import SECTORS, group_symbols, get_market_type, is_us_group, US_MARKET_INDEX


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

RESEARCH_LOG_MD = """
## 📋 สรุปผลการทดลอง Win Rate 60%+ (อัปเดตล่าสุด)

กติกาทุกการทดลอง: แบ่งข้อมูลราคาแต่ละหุ้นเป็น **TRAIN (60%) / VALID (20%) / TEST (20%)** ตามเวลา
(ห้ามดู TEST ก่อนล็อกเงื่อนไข), รายงาน**ทุก combo** ที่ลอง ไม่ใช่แค่ตัวที่ผ่าน (กัน survivorship/p-hacking)
เกณฑ์ผ่าน: valid win rate ≥55%, test win rate ≥52%, กำไรเฉลี่ยต่อไม้เป็นบวกทั้งคู่, ไม้ ≥40 ต่อช่วง

### 📅 ไทม์ไลน์การทดลอง (วันไหนเทสอะไรบ้าง)

- **13 ก.ค. 2026 (รอบ 2)** — ไล่หา combo ที่เอาชนะ SPY 10 ปีให้ได้จริง: capital sizing sensitivity,
  scale-out/trailing exit 5 แบบ, entry 5 แบบ → เจอ **E4 (Close>EMA200 เข้าอย่างเดียว)** ปิดช่องว่างกับ
  SPY จาก 88pp เหลือ 28pp (ดูหัวข้อ 🆕🆕 ด้านล่าง) — ยังไม่ implement ในบอทจริง (เป็นแค่ผลทดลอง)
- **13 ก.ค. 2026 (รอบ 1)** — ชุดการทดลอง `webull_bot` ทั้งหมด: position sizing factorial, grid search 690 คอมโบ,
  bear-market stress test (2020 COVID / 2022 Fed hiking), sideways-stock test (KER) → เปลี่ยนสูตร
  `webull_bot/strategy.py` เป็น Trend+MACD + TP12%/SL15% และเพิ่มตัวเลือก "Quick TP/SL" ในแอปนี้
  (ดูหัวข้อ 🆕 ด้านล่าง) พร้อมต่อ `webull_bot` เข้ากับ SDK ทางการของ Webull
- **12 ก.ค. 2026** — ชุดการทดลองเดิมทั้งหมดด้านล่าง: Volume Profile POC Pullback Bounce, RVI+MACD,
  Trend Ribbon+Hull+SuperTrend, FVMR Framework, ความสัมพันธ์จำนวน/โทนข่าวกับผลเทรด

---

### 🆕🆕 ไล่ล่า SPY 10 ปี (13 ก.ค. 2026 รอบ 2) — ปรับ exit ก่อน แล้วค่อยปรับ entry

ต่อยอดจากรอบ 1 (Trend+MACD + TP12%/SL15%) ตั้งคำถามใหม่: **ทุนเริ่มต้นมีผลไหม? ปรับ exit ให้ดีกว่านี้ได้ไหม?
สู้ SPY 10 ปีได้จริงไหม?** (โค้ดอยู่ที่ `test_capital_sensitivity.py`, `test_capital_idle_time.py`,
`test_capital_reinvest_leftover.py`, `test_10y_vs_spy.py`, `test_dca_10y_vs_spy.py`,
`test_scaleout_variants.py`, `test_entry_variants.py`, `test_e4_combo_and_brkb.py`)

**A) ทุนเริ่มต้น (10 ไม้ตายตัว, เงินต่อไม้ = ทุน/10):**
- ทุน 10,000-20,000 บาท → เงินต่อไม้เล็กจนซื้อหุ้นแพงไม่ได้ พลาดสัญญาณ **~6,000-7,000 ครั้ง** ผลตอบแทนติดลบ
- ทุน 50,000 บาทขึ้นไป → เริ่มเป็นบวกชัดเจน (**ทุนขั้นต่ำที่ควรใช้กับ universe หุ้น US ~76 ตัวนี้**)
- แม้ไม้เต็ม 10/10 ตลอด ก็ยังมีเงินสดค้าง **22-30%** จากเศษเงินทอนปัดเศษซื้อหุ้นเต็มหุ้น (ไม่ใช่แค่ทุนน้อยที่มีปัญหา)

**B) ปลดล็อกจำนวนไม้ (ใช้เงินทอนซื้อตัวใหม่แทนที่จะปล่อยว่าง):** ช่วยจริงช่วงทุน 50,000-80,000 บาท
(+4.3 ถึง +4.4 percentage points) แต่ทุนใหญ่มาก (100,000+) กลับกระจายเจือจางเกิน ไม่ช่วยหรือแย่ลงนิดหน่อย

**C) เทียบ SPY 10 ปีเต็ม (2016-2026) ทุน 100,000 บาทก้อนเดียว:** สูตรเดิม (Trend+MACD+TP12/SL15)
ได้ **+227.4%** ขณะ SPY ได้ **+315.3%** — **แพ้ขาด 88 percentage points** แม้ DCA เติมทุนปีละ 200,000 บาท
(กันความเสี่ยง timing) ก็ยังแพ้ (+92.2% vs +144.9%)

**D) ลอง exit แบบ scale-out/trailing 5 แบบ** (ขาย 50%@+10%, ขยับ stop ไป breakeven+ratchet, แบ่ง 1/3,
pure trailing) — แบบที่ดีสุด (**50%@+10% + breakeven stop + ratchet ทุก+10%**) ปิดช่องว่างได้จริงบน 10 ปี
(+240.6%) แต่ **ยังห่าง SPY 74.7pp** — สรุปว่าปัญหาไม่ได้อยู่ที่จุดออกเป็นหลัก

**E) เปลี่ยนมาลอง entry 5 แบบแทน** (เข้มงวดน้อยลง/มากขึ้น, เรียงตามโมเมนตัม) — **E4 (Close>EMA200
อย่างเดียว ไม่ต้องมี MACD/EMA อื่น)** ชนะขาดทุกแบบ: **+287.2%** บน 10 ปีเต็ม (ปิดช่องว่างกับ SPY เหลือแค่
**28.1pp**, จาก 88pp เดิม) และ**ทนตลาดหมี 2022 ได้ดีมาก** (+76.3% ขณะ B&H เฉลี่ย -16.0% — ตรงข้ามกับ
สูตร trailing เดิมที่เคยพังในปีเดียวกัน) — **บทเรียน: เงื่อนไขเข้าที่หลวมกว่า จับจังหวะเริ่มเทรนด์ได้ไวกว่า
สำคัญกว่าการปรับจุดออกให้ซับซ้อนขึ้น**

**F) เอา E4 + exit ที่ดีสุด (D) มารวมกัน:** ผลกลับ**แย่กว่า E4 เดี่ยวๆ** (+252.6%) — ยืนยันว่า "เอาของดี
ที่สุด 2 อย่างมาต่อกัน" ไม่ได้แปลว่าจะดีที่สุดเสมอ (win rate ร่วงจาก 66.8% เหลือ 45.2%)

**G) ซื้อ BRK-B (Berkshire Hathaway) เฉยๆ:** **+243.0%** (CAGR 13.2%, MaxDD -29.6% ต่ำกว่า SPY) —
ทางเลือกขี้เกียจที่ดีกว่าสูตรเทรดพื้นฐาน แต่ยังแพ้ทั้ง E4 และ SPY

**สรุปอันดับ 10 ปี (ทุน 100,000 บาท):** SPY +315.3% → **E4 +287.2%** → E4+scale-out +252.6% →
BRK-B +243.0% → scale-out C +240.6% → สูตรเดิม +227.4%

**ข้อสรุปสุดท้าย:** ยังไม่มีสูตรไหนเอาชนะ SPY ได้จริงในรอบ 10 ปีนี้ (E4 เข้าใกล้ที่สุดแต่ยังแพ้ 28pp) —
สอดคล้องกับคำแนะนำที่ Warren Buffett พูดซ้ำมาตลอด: **"คนทั่วไปควรซื้อ Index Fund"** (ดูการวิเคราะห์บทความ
"ลอกการบ้านปู่บัฟเฟตต์ผ่าน 13F" ในแชทวันเดียวกัน — backtest อิสระคนละวิธี ได้ข้อสรุปเดียวกัน)
**E4 ยังเป็นแค่ผลทดลอง ไม่ได้ถูกนำไปใช้ใน `webull_bot/strategy.py` จริง**

---

### 🆕 การทดลอง webull_bot (13 ก.ค. 2026 รอบ 1) — หา combo ที่ "ไม่หายนะ" ไม่ใช่แค่กำไรสูงสุด

ทดลองต่อยอดจากบอทเทรดหุ้น US จริง (`webull_bot/`) เริ่มจากสูตรเดิม EMA Stack+NewHigh / TP5%+SL10%
แล้วหาสูตรที่ดีกว่าผ่าน 4 การทดลองต่อเนื่อง (โค้ดอยู่ที่ `test_sizing_rules_experiment.py`,
`test_exit_optimization.py`, `test_exit_optimization_bearcheck.py`, `test_exit_optimization_crashcheck.py`,
`test_sideways_stocks.py`):

1. **Position sizing สำคัญพอๆ กับเงื่อนไขเข้า/ออก** — ทดลอง 4×3×2 (จำนวนไม้ × entry × ทุน) พบว่า
   "แชมป์" ของแต่ละปีสลับขั้วกันเอง ถ้าเลือกจากปีเดียวจะโดน overfit
2. **Grid search 690 คอมโบ** (3 entry × 46 exit × 5 ระดับจำนวนไม้) แยก TRAIN/TEST ปีต่างกัน — ผู้ชนะ
   อันดับ 1 ตอนแรก (Trend+MACD + trailing EMA100 ไม่มี SL ตายตัว) ดูดีมากบนตลาดขาขึ้นทั้ง 2 ปีที่ทดสอบ
3. **เช็คกับตลาดหมีจริง (2020 COVID crash, 2022 Fed hiking bear -16.0%)** — ผู้ชนะเดิม "แตก" ทันที
   (-8.0% ปี 2022, MaxDD -18.4%) เพราะ trailing ไม่มีเพดานขาดทุน ส่วน**อันดับ 2 เดิม (Trend+MACD entry
   + TP12%/SL15% ตายตัว)** กลับเป็นสูตรเดียวในกลุ่มที่**ยังกำไรได้จริงตอนตลาดหมี** (+4.7% ขณะ B&H -16.0%)
   → **นี่คือสูตรที่ `webull_bot/strategy.py` ใช้อยู่ตอนนี้** และเป็นตัวเลือก **"Quick TP/SL"** ในแอปนี้
   (ปรับ default เป็น TP12%/SL15% แล้ว)
4. **หุ้น sideway ทำให้สูตรนี้ขาดทุน** — ทดสอบด้วย Kaufman Efficiency Ratio (วัดว่าราคาวิ่งตรงทางเดียว
   แค่ไหน) พบว่าหุ้น sideway 15 ตัว (KER ต่ำ) ขาดทุน -6.6% ขณะหุ้นเทรนด์แข็งแรง 15 ตัวกำไร +48.6%
   ในช่วงเวลาเดียวกัน — **ยังไม่ implement ตัวกรอง sideway ใน bot จริง** (โน้ตไว้เป็น TODO)

**บทเรียนสำคัญ:** สูตรที่ดูดีที่สุดบนข้อมูล backtest (แม้ทำ train/test แยกถูกต้องแล้ว) อาจยังไม่ทนตลาดหมี
ถ้าไม่มี hard stop-loss ตายตัว — ต้องทดสอบทั้งตลาดขาขึ้นและขาลงจริงก่อนเชื่อผลเสมอ

---

### 📚 ผลการทดลองชุดแรก (12 ก.ค. 2026)

### 🥇 อันดับ 1 — Volume Profile "POC Pullback Bounce" (หุ้น US เท่านั้น)
ราคาย่อกลับมาแตะ **POC** (จุดราคาที่มี volume ซื้อขายมากสุดใน 60 วันย้อนหลัง) จากด้านบนแล้วเด้งขึ้น
ในเทรนด์ขึ้น (close>EMA200) — เข้าซื้อ, TP 5% / SL 10%

| ชุดข้อมูล | Train | Valid | Test | n(test) |
|---|---|---|---|---|
| US 76 หุ้น เต็ม | 74.5% | 69.3% | **69.8%** | 318 |

✅ เสถียรที่สุดในบรรดาทุกระบบที่เทส (ช่องว่าง valid→test แค่ 0.5%)
❌ หุ้นไทย: 0/48 combo ผ่าน (win rate สูงแต่กำไรเฉลี่ยติดลบ — ไม่ใช่ edge จริง)

### 🥈 อันดับ 2 — RVI + MACD(100,200,50) (หุ้น US เท่านั้น)
ที่มา: คลิป YouTube "ถ้าให้เลือกแค่ 2 อินดิเคเตอร์..." — RVI (Relative Vigor Index) ตัด Signal Line ขึ้น
หลังเคยต่ำกว่า -0.22, ยืนยันด้วย MACD trend filter แบบช้ามาก (100,200,50) — TP 5% / SL 10%

| ชุดข้อมูล | Train | Valid | Test | n(test) |
|---|---|---|---|---|
| US 76 หุ้น เต็ม | 71.8% | 71.2% | **66.9%** | 344 |

❌ หุ้นไทย: 0/36 combo ผ่าน

### 🥉 อันดับ 3 — Trend Ribbon + Hull Suite + SuperTrend (หุ้น US เท่านั้น)
ที่มา: คลิป YouTube "อินดิเคเตอร์นี้ใช้เป็นตัวหลักได้เลย" — Donchian Ribbon(30) + Hull Suite(60, mult 3)
+ SuperTrend(ATR period 50, mult 7.0) ต้องเขียวพร้อมกันทั้ง 3 ตัว — TP 8% / SL 10%

| ชุดข้อมูล | Train | Valid | Test | n(test) |
|---|---|---|---|---|
| US 76 หุ้น เต็ม | 68.1% | 60.4% | **56.2%** | 386 |

---

### ❌ ทดลองแล้วไม่ผ่าน / ไม่มี edge จริง

- **RSI Bullish Divergence + EMA12x26 cross** (คลิป "5 อินดิเคเตอร์ยอดฮิต"): ไม่ผ่านเกณฑ์ทั้งไทยและ US
  (valid/test กระโดดไปมาไม่เสถียร)
- **FVMR Framework** (Fundamentals/Valuation/Momentum/Revisions แบบ UOB Kay Hian): Top tercile win rate
  60.3% vs Bottom tercile 56.6% — ใกล้เคียง baseline เฉลี่ยทั้งชุด (59.5%) เกินไป ไม่ถือว่ามี edge
  (มีข้อจำกัด: F/V/R ใช้ข้อมูลปัจจุบัน คงที่ตลอด 10 ปีเพราะ yfinance ฟรีไม่มี point-in-time history)
- **COMBO: Volume Profile + RVI/MACD ต้องตรงกันวันเดียว**: แย่กว่าแยกใช้เดี่ยวๆ ชัดเจน (test win rate
  ร่วงเหลือ 53.8%, n เหลือแค่ 12-13 ไม้ต่อช่วง — สัญญาณเกิดยากเกินไปจนวัดผลไม่ได้)
- **จำนวนข่าว (GDELT) ก่อนเข้าไม้ POC Pullback**: ไม้ชนะ (n=57) news count เฉลี่ย 5,197 vs ไม้แพ้ (n=14)
  เฉลี่ย 5,427 — ไม่ต่างกันอย่างมีนัยสำคัญ จำนวนข่าวไม่ช่วยกรองสัญญาณ
- **โทนข่าว (บวก/ลบ) ก่อนเข้าไม้**: กำลังทดสอบ (ผลจะอัปเดตในสรุปนี้เมื่อเสร็จ)

### 📂 ไฟล์ผลการทดลองดิบ (อยู่ใน repo)
`volprofile_us_all_combos.csv` · `yt_indicators_us_all_combos.csv` ·
`combo_volprofile_rvimacd_us_all_combos.csv` · `fvmr_us_snapshots.csv` ·
`news_volume_vs_winloss.csv` · `news_tone_vs_winloss.csv`

### 🎯 สรุปเชิงปฏิบัติ
ถ้าจะเลือกใช้ระบบเดียวสำหรับหุ้น US: **Volume Profile POC Pullback Bounce (TP5%/SL10%)** คือตัวที่ผ่าน
เกณฑ์เข้มงวดที่สุดและเสถียรที่สุด — ยังไม่พบระบบไหนที่ใช้ได้ผลจริงกับหุ้นไทยเลยในทุกการทดลองที่ผ่านมา
"""

SET_SYMBOL = "^SET.BK"
CUT = 0.08   # initial stop loss (กว้างขึ้น กัน noise) · หลังมีกำไรใช้ trailing EMA50


# ── data / indicators ──
# ดาวน์โหลดผ่าน safe_fetch (แยกโปรเซส) กัน segfault จาก yfinance/curl_cffi ลามมาที่แอปหลัก
# เช็ค data_cache (อัปเดตวันละครั้งผ่าน GitHub Action) ก่อนเสมอ — มีแล้วไม่ต้องยิง yfinance สด
from safe_fetch import safe_download_one, safe_download_many
from data_cache import get_cached_close, get_cached_volume


@st.cache_data(ttl=3600, show_spinner=False)
def load_one(symbol, years):
    cached = get_cached_close(symbol, years)
    if cached is not None and len(cached) > 0:
        return cached
    return safe_download_one(symbol, years)


@st.cache_data(ttl=3600, show_spinner=False)
def load_volume(symbol, years):
    """โหลดแยกต่างหาก (close+volume) เฉพาะหน้ารายตัว — ไม่ปนกับ load_one ที่โหมดสแกนใช้"""
    cached = get_cached_volume(symbol, years)
    if cached is not None and len(cached) > 0:
        return cached
    df = safe_download_one(symbol, years, with_volume=True)
    return df["volume"] if df is not None else None


@st.cache_data(ttl=3600, show_spinner=False)
def load_many(symbols, years):
    out = {}
    missing = []
    for s in symbols:
        c = get_cached_close(s, years)
        if c is not None and len(c) > 210:
            out[s] = c
        else:
            missing.append(s)
    if missing:
        out.update(safe_download_many(missing, years, min_rows=210))
    return out


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


def find_hh_hl_breakout_signal(close, lookback=3, low_tolerance=0.05, monitor_days=42):
    """
    หาแพทเทิร์น Higher-High/Higher-Low 2 ชุดติดกัน แล้วออกสัญญาณตอนราคาทะลุ Swing High ล่าสุด (breakout)
    stage: 0=รอ Low1 · 1=มี Low1 รอ High1 · 2=มี High1 รอ Low2(HL) · 3=มี Low2 รอ High2(HH) · 4=armed รอ breakout
    low_tolerance: Low2 ยังถือว่าเป็น Higher Low ได้ ถ้าต่ำกว่า Low1 ไม่เกินสัดส่วนนี้ (กันหลุดโดย noise เล็กน้อย)

    monitor_days: หลัง breakout ครั้งแรก ถ้าราคาหลุด EMA5 → เฝ้ามอนิเตอร์อีก ~2 เดือน (42 วันเทรด)
    ถ้าในช่วงนี้ราคาทะลุจุดสูงสุดที่เคยขึ้นไปถึงระหว่างถือไม้แรก (ไม่ใช่ราคาที่ breakout เข้าซื้อ) ซ้ำอีกครั้ง
    → เข้าใหม่ทันที ไม่ต้องรอสร้างแพทเทิร์น HH-HL ใหม่ทั้งชุด
    """
    c = close.values
    n = len(c)
    ema5 = close.ewm(span=5, adjust=False).mean().values
    is_high, is_low = find_pivots(close, lookback)
    signal = np.zeros(n, dtype=bool)
    is_reentry = np.zeros(n, dtype=bool)   # True = เข้าใหม่จากการทะลุจุดสูงสุดของไม้แรกซ้ำ (ไม่ใช่ breakout ชุดแรก)
    stage = 0
    low1 = low2 = high1 = high2 = None

    # เฝ้าระวังการทะลุซ้ำของจุดสูงสุดที่เคยขึ้นไปถึงระหว่างถือไม้แรก (ตั้งแต่วัน breakout จนถึงวันที่หลุด EMA5)
    in_trade = False
    trade_peak = None
    watch_level = None
    watch_deadline = None

    for i in range(n):
        if in_trade:
            trade_peak = max(trade_peak, c[i])
            if c[i] < ema5[i]:
                in_trade = False
                watch_level = trade_peak
                watch_deadline = i + monitor_days
        elif watch_level is not None:
            if i <= watch_deadline:
                if c[i] > watch_level:
                    signal[i] = True
                    is_reentry[i] = True
                    watch_level = watch_deadline = None
                    stage, low1, low2, high1, high2 = 0, None, None, None, None
                    continue
            else:
                watch_level = watch_deadline = None

        if stage == 4 and c[i] > high2:
            signal[i] = True
            in_trade, trade_peak = True, c[i]
            watch_level = watch_deadline = None
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

    return signal, is_reentry


def build_and_sim(close, setclose, fee, use_scaling=False, use_ema_cross=False, use_hh_hl=False, use_ema5_trail=False,
                   use_ema_stack=False, use_ema30_50_exit=False, use_ema30_50_tp15_exit=False, use_tp5_sl10_exit=False,
                   tp_pct=0.05, sl_pct=0.10):
    df = pd.DataFrame({"close": close})
    df["ema5"] = ema(close, 5); df["ema10"] = ema(close, 10); df["ema30"] = ema(close, 30); df["ema50"] = ema(close, 50)
    df["ema100"] = ema(close, 100); df["ema200"] = ema(close, 200)
    df["rsi"] = rsi(close); df["macd"] = ema(close, 12) - ema(close, 26)
    hh_hl_reentry = None
    if use_hh_hl:
        # เข้าตอนราคาทะลุ Swing High หลังเกิดแพทเทิร์น Higher-High/Higher-Low 2 ชุดติดกัน (price action breakout)
        # เพิ่มเงื่อนไข: ราคาต้องอยู่เหนือ EMA200 (กรองหุ้นขาลง/sideways ต่ำกว่าแนวโน้มใหญ่)
        hh_hl_signal, hh_hl_reentry = find_hh_hl_breakout_signal(close)
        stock_ok = pd.Series(hh_hl_signal, index=df.index) & (df["close"] > df["ema200"])
    elif use_ema_cross:
        # เข้าเฉพาะวันที่ EMA50 ตัดขึ้น EMA100 (ครั้งแรก) — ไม่บังคับ EMA50>EMA200 ฝั่งหุ้น
        # เพราะตอนตัดขึ้น EMA50 มักยังไม่ทัน EMA200 (เส้นช้ากว่า)
        cross_up = (df["ema50"] > df["ema100"]) & (df["ema50"].shift(1) <= df["ema100"].shift(1))
        stock_ok = (df["close"] > df["ema200"]) & (df["ema10"] > df["ema50"]) & (df["macd"] > 0) & cross_up
    elif use_ema_stack:
        # เรียงเต็มขั้นบันได: Close>EMA5>EMA10>EMA30>EMA50>EMA100>EMA200 (แนวโน้มขึ้นชัดเจนทุกกรอบเวลา)
        # + ต้องมีการ breakout จริงในรอบ 1 ปีที่ผ่านมา (ราคาทำ New High 252 วันเทรด) ไม่งั้นไม่เข้า
        yr_high = df["close"].rolling(252, min_periods=60).max()
        broke_1y_high = df["close"] >= yr_high
        stock_ok = (df["close"] > df["ema5"]) & (df["ema5"] > df["ema10"]) & (df["ema10"] > df["ema30"]) \
            & (df["ema30"] > df["ema50"]) & (df["ema50"] > df["ema100"]) & (df["ema100"] > df["ema200"]) \
            & broke_1y_high
    else:
        stock_ok = (df["close"] > df["ema200"]) & (df["ema10"] > df["ema50"]) \
            & (df["ema50"] > df["ema200"]) & (df["macd"] > 0)
    if setclose is not None and not use_hh_hl and not use_ema_stack:
        # HH-HL Breakout / EMA Stack ไม่ใช้ SET filter — ดูโครงสร้าง EMA ของหุ้นล้วนๆ
        s = setclose.reindex(df.index).ffill()
        set_ok = (s > ema(s, 200)) & (ema(s, 10) > ema(s, 50)) & (ema(s, 50) > ema(s, 200))
        cond = (stock_ok & set_ok).values
    else:
        cond = stock_ok.values

    c = df["close"].values
    ret = df["close"].pct_change().fillna(0).values
    e5 = df["ema5"].values
    e30 = df["ema30"].values
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

            # ไม้ที่เข้าจากการ "เข้าครั้งที่สอง" (HH-HL re-entry) รัดเข็มขัดด้วย EMA30 แทน EMA5 (หลวมกว่า กันหลุดง่ายเกิน)
            trail_ema = e30 if entry.get("is_reentry") else e5

            # Quick TP 5% + SL 10% — ไม่มีเงื่อนไข EMA เลย ขายทำกำไรเร็วที่ +5% หรือตัดขาดทุนที่ -10%
            # เท่านั้น (ไม่มี trailing) — ทดสอบด้วย train/valid/test split บนหุ้น US พบว่า win rate
            # 60-80% สม่ำเสมอทั้ง 3 ช่วง (ไม่ค่อยเวิร์คกับหุ้นไทยเท่าไหร่ — win rate สูงเพราะ TP แคบ
            # ไม่ใช่เพราะทำนายทิศทางแม่นขึ้น กำไรรวมจะน้อยกว่าถือยาวเฉยๆ)
            if use_tp5_sl10_exit:
                reason = f"SL -{sl_pct*100:.0f}%" if chg <= -sl_pct else (f"TP +{tp_pct*100:.0f}%" if chg >= tp_pct else None)
                if reason:
                    ft += fee; held = 0
                    trades.append({**entry, "exit_i": i, "exit_price": price, "reason": reason,
                                   "pnl": price / entry["price"] - 1 - 2 * fee})
                    events.append((i, "SELL", price)); entry = None

            # EMA30 ตัดลง EMA50 + Take Profit 15% — เหมือน EMA30<EMA50 เดิม แต่ขายทำกำไรทันที
            # ที่ +15% ด้วย (ไม่ต้องรอ EMA30 หลุดซึ่งมักคืนกำไรกลับไปเยอะ) — ทดสอบแล้วช่วยเพิ่ม win rate จริง
            elif use_ema30_50_tp15_exit:
                reason = "SL -8%" if chg <= -CUT else ("TP +15%" if chg >= 0.15 else ("EMA30<EMA50" if e30[i] < e50[i] else None))
                if reason:
                    ft += fee; held = 0
                    trades.append({**entry, "exit_i": i, "exit_price": price, "reason": reason,
                                   "pnl": price / entry["price"] - 1 - 2 * fee})
                    events.append((i, "SELL", price)); entry = None

            # EMA30 ตัดลง EMA50 — เงื่อนไขเดียวล้วนๆ: SL -8% หรือ EMA30 หลุดต่ำกว่า EMA50
            elif use_ema30_50_exit:
                reason = "SL -8%" if chg <= -CUT else ("EMA30<EMA50" if e30[i] < e50[i] else None)
                if reason:
                    ft += fee; held = 0
                    trades.append({**entry, "exit_i": i, "exit_price": price, "reason": reason,
                                   "pnl": price / entry["price"] - 1 - 2 * fee})
                    events.append((i, "SELL", price)); entry = None

            # EMA5 Trail strategy — เงื่อนไขเดียวล้วนๆ: SL -8% หรือราคาตัดเส้น trail (ไม่ผสม scaling/EMA50)
            elif use_ema5_trail:
                reason = "SL -8%" if chg <= -CUT else (("ตัด EMA30" if entry.get("is_reentry") else "ตัด EMA5") if price < trail_ema[i] else None)
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
                # (ไม้ที่เข้าจาก "เข้าครั้งที่สอง" ใช้ EMA30 แทน EMA5)
                reason = None
                if chg <= -CUT:
                    reason = "SL -8%"
                elif sold_at_10pct and price < trail_ema[i]:
                    reason = "ตัด EMA30 (หลังขาย 50%)" if entry.get("is_reentry") else "ตัด EMA5 (หลังขาย 50%)"
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
                is_reentry_buy = hh_hl_reentry is not None and hh_hl_reentry[i]
                entry = {"entry_i": i, "price": price, "eq": run_eq, "is_reentry": is_reentry_buy}
                sold_at_10pct = False
                sold_at_20pct = False
                peak_at_20pct = 0.0
                events.append((i, "BUY2" if is_reentry_buy else "BUY", price))

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


def show_stock_detail(symbol, close, setclose, fee, cap, use_scaling=False, use_ema_cross=False, use_hh_hl=False, use_ema5_trail=False, years=None,
                       use_ema_stack=False, use_ema30_50_exit=False, use_ema30_50_tp15_exit=False, use_tp5_sl10_exit=False,
                       tp_pct=0.05, sl_pct=0.10):
    """แสดงรายละเอียดหุ้นตัวเดียว: เมตริก + กราฟจุดซื้อขาย + log"""
    df, events, m = build_and_sim(close, setclose, fee, use_scaling, use_ema_cross, use_hh_hl, use_ema5_trail, use_ema_stack, use_ema30_50_exit, use_ema30_50_tp15_exit, use_tp5_sl10_exit, tp_pct, sl_pct)
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
                        "EMA5": df["ema5"].values, "EMA10": df["ema10"].values, "EMA30": df["ema30"].values,
                        "EMA50": df["ema50"].values, "EMA100": df["ema100"].values, "EMA200": df["ema200"].values,
                        "macd": df["macd"].values})

    # ราคา + EMA
    line = alt.Chart(pdf).mark_line(color="#9aa4b2").encode(x="date:T", y=alt.Y("close:Q", title="ราคา"))
    e5 = alt.Chart(pdf).mark_line(color="#58a6ff", strokeDash=[4, 3]).encode(x="date:T", y="EMA5:Q")
    e10 = alt.Chart(pdf).mark_line(color="#e3b341", strokeDash=[4, 3]).encode(x="date:T", y="EMA10:Q")
    e30 = alt.Chart(pdf).mark_line(color="#f778ba", strokeDash=[4, 3]).encode(x="date:T", y="EMA30:Q")
    e50 = alt.Chart(pdf).mark_line(color="#3fb950", strokeDash=[4, 3]).encode(x="date:T", y="EMA50:Q")
    e100 = alt.Chart(pdf).mark_line(color="#a371f7", strokeDash=[4, 3]).encode(x="date:T", y="EMA100:Q")
    e200 = alt.Chart(pdf).mark_line(color="#f0883e", strokeDash=[4, 3]).encode(x="date:T", y="EMA200:Q")

    mk = pd.DataFrame([{"date": df.index[i], "price": p, "act": a} for (i, a, p) in events])
    layers = [line, e5, e10, e30, e50, e100, e200]
    if not mk.empty:
        buy = mk[mk.act == "BUY"]
        buy2 = mk[mk.act == "BUY2"]
        sell_partial = mk[mk.act == "SELL 50%"]
        sell_all = mk[mk.act.isin(["SELL", "SELL ALL"])]
        if not buy.empty:
            layers.append(alt.Chart(buy).mark_point(shape="triangle-up", size=90, color="#2ea043", filled=True).encode(x="date:T", y="price:Q"))
        if not buy2.empty:
            layers.append(alt.Chart(buy2).mark_point(shape="triangle-up", size=90, color="#d29922", filled=True).encode(x="date:T", y="price:Q"))
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
        buy_dates = set(mk[mk.act.isin(["BUY", "BUY2"])]["date"]) if not mk.empty else set()
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
    st.caption("เส้น EMA: 🔵 ฟ้า = EMA5 · 🟡 เหลือง = EMA10 · 🩷 ชมพู = EMA30 · 🟢 เขียว = EMA50 · 🟣 ม่วง = EMA100 · 🟠 ส้ม (เส้นประ) = EMA200")
    st.caption("จุดซื้อขาย: 🔺 เขียว = BUY (breakout ครั้งแรก) · 🔺 เหลือง/น้ำตาล = BUY ครั้งที่ 2 (ทะลุจุดเดิมซ้ำ — เฉพาะ HH-HL Breakout) · "
               "🔴 แดง = SELL (ขายหมด) · 🟠 ส้ม (วงกลม) = SELL 50% (ขายบางส่วน — เฉพาะกลยุทธ์ Scaling Out)")
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


def simulate_portfolio(closes, setclose, fee, n_slots, use_scaling=False, use_ema_cross=False, use_hh_hl=False,
                        use_ema5_trail=False, use_ema_stack=False, use_ema30_50_exit=False, use_ema30_50_tp15_exit=False,
                        use_tp5_sl10_exit=False, tp_pct=0.05, sl_pct=0.10):
    """พอร์ตหมุนเงิน: ถือได้ n_slots ตัวพร้อมกัน · ออกตัวนึง → เอาเงินไปเข้าตัวอื่นที่มีสัญญาณ (ไม่ถือเงินเฉย)
    ใช้เงื่อนไขเข้า/ออกเดียวกับที่เลือกในแถบข้าง (เหมือน build_and_sim) — ยกเว้น Scaling Out ที่ตกไปใช้
    Default (SL-8%/หลุด EMA50) แทน เพราะขายบางส่วนไม่เข้ากับโมเดล 'ช่อง' ที่ถือเต็ม-ว่างของโหมดนี้"""
    prices = pd.DataFrame(closes).sort_index().ffill().dropna(how="all")
    e5 = prices.ewm(span=5, adjust=False).mean()
    e10 = prices.ewm(span=10, adjust=False).mean()
    e30 = prices.ewm(span=30, adjust=False).mean()
    e50 = prices.ewm(span=50, adjust=False).mean()
    e100 = prices.ewm(span=100, adjust=False).mean()
    e200 = prices.ewm(span=200, adjust=False).mean()
    macd = prices.ewm(span=12, adjust=False).mean() - prices.ewm(span=26, adjust=False).mean()

    if use_hh_hl:
        # pattern-based ไม่ vectorize ได้ตรงๆ ต้องคำนวณทีละหุ้น
        sig = pd.DataFrame(False, index=prices.index, columns=prices.columns)
        for col in prices.columns:
            s = prices[col].dropna()
            if len(s) < 60:
                continue
            signal, _ = find_hh_hl_breakout_signal(s)
            sig.loc[s.index, col] = signal
        stock_ok = sig & (prices > e200)
    elif use_ema_cross:
        cross_up = (e50 > e100) & (e50.shift(1) <= e100.shift(1))
        stock_ok = (prices > e200) & (e10 > e50) & (macd > 0) & cross_up
    elif use_ema_stack:
        yr_high = prices.rolling(252, min_periods=60).max()
        stock_ok = (prices > e5) & (e5 > e10) & (e10 > e30) & (e30 > e50) & (e50 > e100) & (e100 > e200) & (prices >= yr_high)
    else:
        stock_ok = (prices > e200) & (e10 > e50) & (e50 > e200) & (macd > 0)

    if setclose is not None and not use_hh_hl and not use_ema_stack:
        s = setclose.reindex(prices.index).ffill()
        setmask = ((s > ema(s, 200)) & (ema(s, 10) > ema(s, 50)) & (ema(s, 50) > ema(s, 200))).values
        C = stock_ok.values & setmask[:, None]
    else:
        C = stock_ok.values

    P = prices.values; E5 = e5.values; E30 = e30.values; E50 = e50.values; SC = (macd / prices).values
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
            chg = p / pos[j]["entry"] - 1
            reason = None
            if use_tp5_sl10_exit:
                if chg <= -sl_pct:
                    reason = f"SL -{sl_pct*100:.0f}%"
                elif chg >= tp_pct:
                    reason = f"TP +{tp_pct*100:.0f}%"
            elif chg <= -CUT:
                reason = "SL -8%"
            elif use_ema30_50_tp15_exit:
                if chg >= 0.15:
                    reason = "TP +15%"
                elif not np.isnan(E30[i, j]) and not np.isnan(E50[i, j]) and E30[i, j] < E50[i, j]:
                    reason = "EMA30<EMA50"
            elif use_ema30_50_exit:
                if not np.isnan(E30[i, j]) and not np.isnan(E50[i, j]) and E30[i, j] < E50[i, j]:
                    reason = "EMA30<EMA50"
            elif use_ema5_trail:
                if not np.isnan(E5[i, j]) and p < E5[i, j]:
                    reason = "ตัด EMA5"
            else:
                if not np.isnan(E50[i, j]) and p < E50[i, j]:
                    reason = "หลุด EMA50"
            if reason:
                cash += pos[j]["val"] * (1 - fee)
                trades.append(dict(sym=cols[j].replace(".BK", ""), ei=pos[j]["ei"], ep=pos[j]["entry"],
                                   xi=i, xp=p, reason=reason, pnl=chg - 2*fee))
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

    for j, v in pos.items():                                   # ไม้ที่ยังถืออยู่ตอนจบ
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
    is_us_deep_link = qp.get("us", "0") == "1"
    if sym_q and not is_us_deep_link and not sym_q.upper().endswith(".BK"):
        sym_q += ".BK"  # หุ้น US (ticker เปล่า) ไม่ต้องเติม .BK
    years_q = int(qp.get("years", "5"))
    cap_q = float(qp.get("cap", "50000"))
    fee_q = float(qp.get("fee", "0.002"))
    scaling_q = qp.get("scaling", "0") == "1"
    cross_q = qp.get("cross", "0") == "1"
    hhhl_q = qp.get("hhhl", "0") == "1"
    ema5trail_q = qp.get("ema5trail", "0") == "1"
    emastack_q = qp.get("emastack", "0") == "1"
    ema3050_q = qp.get("ema3050", "0") == "1"
    ema3050tp15_q = qp.get("ema3050tp15", "0") == "1"
    tp5sl10_q = qp.get("tp5sl10", "0") == "1"
    entry_idx_q = 3 if emastack_q else (2 if hhhl_q else (1 if cross_q else 0))
    exit_idx_q = 5 if tp5sl10_q else (4 if ema3050tp15_q else (3 if ema3050_q else (2 if ema5trail_q else (1 if scaling_q else 0))))

# ── sidebar ──
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    # ตั้งค่าเริ่มต้นไว้ก่อนเสมอ กัน NameError ตอน mode != "หุ้นเดียว" (เช่น session ของแท็บเดิม
    # ที่ค้างโหมด "สแกนทั้งกลุ่ม" จาก session cookie เดียวกัน แต่แท็บนี้เป็น deep link ที่ต้องใช้ symbol)
    symbol = sym_q if is_deep_link else "PIMO.BK"
    group = None  # ตั้งไว้ก่อนกัน NameError ตอน mode == "หุ้นเดียว" (group ไม่ถูกตั้งค่าในโหมดนั้น)
    mode = st.radio("โหมด", ["หุ้นเดียว", "สแกนทั้งกลุ่ม", "คัดหุ้นถือยาว (Fundamental)",
                             "📋 สรุปผลการทดลอง (Research Log)"])
    if mode == "หุ้นเดียว":
        symbol = st.text_input("หุ้น (เช่น PIMO.BK)", symbol).strip().upper()
    elif mode == "สแกนทั้งกลุ่ม":
        group = st.selectbox("กลุ่ม", ["SET100 (ทั้งหมด)", "SET Index", "US100 (หุ้นอเมริกาจริง)",
                                       "DR หุ้นอเมริกา (มีใน SET)",
                                       "DR หุ้นต่างชาติอื่นๆ (ไม่ใช่อเมริกา)"] + list(SECTORS.keys()))
        scan_style = st.radio("รูปแบบ", ["ดูรายตัว (ตาราง+คลิก)", "จัดพอร์ตหมุนเงิน (ไม่ให้ว่าง)"])
        n_slots = 1
        if scan_style.startswith("จัดพอร์ต"):
            n_slots = st.radio("ถือพร้อมกันกี่ตัว", [1, 5], horizontal=True,
                               format_func=lambda x: f"{x} ไม้")
    elif mode == "คัดหุ้นถือยาว (Fundamental)":
        group = st.selectbox("กลุ่ม", ["SET100 (ทั้งหมด)", "US100 (หุ้นอเมริกาจริง)", "DR หุ้นอเมริกา (มีใน SET)",
                                       "DR หุ้นต่างชาติอื่นๆ (ไม่ใช่อเมริกา)"] + list(SECTORS.keys()), key="screener_group")
    years = st.slider("ปีย้อนหลัง", 1, 10, years_q if is_deep_link else 5)
    cap = st.number_input("เงินต้น (บาท)", 1000, 10_000_000, int(cap_q) if is_deep_link else 50_000, 1000)
    fee = st.number_input("ค่าธรรมเนียม %/ข้าง", 0.0, 1.0, round(fee_q * 100, 2) if is_deep_link else 0.2, 0.05) / 100

    st.divider()
    st.subheader("🎯 กลยุทธ์ ENTRY (เข้า)")
    entry_strategy = st.radio("เลือกเงื่อนไขเข้า",
                       ["Default (EMA10>50>200 + MACD>0)", "EMA50 ตัดขึ้น EMA100 + Trend Filter",
                        "HH-HL Breakout (2 ชุดติดกัน)", "EMA Stack เรียงขั้นบันได (5>10>30>50>100>200)"],
                       index=entry_idx_q if is_deep_link else 0,
                       help="แบบที่ 2: เข้าเฉพาะวันที่ EMA50 ตัดขึ้น EMA100 (ครั้งแรก) + Close>EMA200 · EMA10>EMA50 · MACD>0 "
                            "(ไม่บังคับ EMA50>EMA200 ฝั่งหุ้น เพราะตอนตัดขึ้นมักยังไม่ทัน)\n\n"
                            "แบบที่ 3: เข้าตอนราคาทะลุ Swing High (breakout) หลังเกิดแพทเทิร์น Higher-High/"
                            "Higher-Low ติดกัน 2 ชุด — เป็น price action ล้วน ไม่ใช้เงื่อนไข EMA ฝั่งหุ้น "
                            "และไม่ใช้เงื่อนไข SET เลย "
                            "(Low ชุดที่ 2 ยังนับเป็น Higher Low ได้ถ้าต่ำกว่า Low ชุดแรกไม่เกิน 5%)\n\n"
                            "แบบที่ 4: หุ้น `Close>EMA5>EMA10>EMA30>EMA50>EMA100>EMA200` เรียงขั้นบันไดครบทุกเส้น "
                            "(แนวโน้มขึ้นชัดเจนทุกกรอบเวลา) **และ** ต้องทำ New High รอบ 1 ปี (252 วันเทรด) ด้วย "
                            "— ถ้าไม่เบรก 1 ปีย้อนหลังไม่เข้า — เช็คตอนปิดตลาด ซื้อได้ระหว่างวันถัดไป")
    use_ema_cross = entry_strategy == "EMA50 ตัดขึ้น EMA100 + Trend Filter"
    use_hh_hl = entry_strategy == "HH-HL Breakout (2 ชุดติดกัน)"
    use_ema_stack = entry_strategy == "EMA Stack เรียงขั้นบันได (5>10>30>50>100>200)"

    st.divider()
    st.subheader("🎯 กลยุทธ์ EXIT")
    strategy = st.radio("เลือกกลยุทธ์",
                       ["Default (Trail EMA50)", "Scaling Out (10%→50%, 20%→50%)", "EMA5 Trail (ตัด EMA5 ขายหมด)",
                        "EMA30 ตัดลง EMA50 (ขายหมด)", "EMA30 ตัดลง EMA50 + Take Profit 15%",
                        "Quick TP/SL (ไม่มี EMA)"],
                       index=exit_idx_q if is_deep_link else 0,
                       help="Scaling Out: ขาย50% ที่ 10%, ขาย50% ที่ 20%, ปล่อยไป -5%\n\n"
                            "EMA5 Trail: เงื่อนไขเดียวล้วนๆ ไม่ผสม scaling — ถือเต็มไม้ ขายหมดทันทีที่ราคาปิดต่ำกว่า EMA5 "
                            "(หรือโดน SL -8% ก่อน) รัดเข็มขัดไวกว่า Default ที่ใช้ EMA50\n\n"
                            "EMA30 ตัดลง EMA50: เงื่อนไขเดียวล้วนๆ — ขายหมดทันทีที่ EMA30 ต่ำกว่า EMA50 "
                            "(หรือโดน SL -8% ก่อน) — เช็คตอนปิดตลาด ขายได้ระหว่างวันถัดไป\n\n"
                            "EMA30 ตัดลง EMA50 + TP15%: เหมือนอันข้างบน แต่ขายทำกำไรทันทีที่กำไรถึง +15% ด้วย "
                            "(ไม่ต้องรอ EMA30 หลุด) — ทดสอบด้วย train/test split แล้วช่วยเพิ่ม win rate จริง "
                            "(win rate ~32-40% เทียบสูตรเดิม ~20-28%)\n\n"
                            "Quick TP/SL: ไม่มีเงื่อนไข EMA เลย ขายทำกำไรเร็วที่ TP% หรือตัดขาดทุนที่ SL% ตามที่ตั้งไว้ "
                            "— ค่า default 12%/15% มาจากการทดลอง grid search 690 คอมโบ (webull_bot) ที่พบว่า "
                            "เป็นสูตรเดียวที่ยังกำไรได้จริงตอนตลาดหมี 2022 (Fed hiking, +4.7% ขณะ B&H -16.0%) "
                            "ต่างจาก TP5%/SL10% เดิมที่ win rate สูงแต่กำไรรวมน้อยกว่าถือยาวเฉยๆ")
    use_scaling = strategy == "Scaling Out (10%→50%, 20%→50%)"
    use_ema5_trail = strategy == "EMA5 Trail (ตัด EMA5 ขายหมด)"
    use_ema30_50_exit = strategy == "EMA30 ตัดลง EMA50 (ขายหมด)"
    use_ema30_50_tp15_exit = strategy == "EMA30 ตัดลง EMA50 + Take Profit 15%"
    tp_pct, sl_pct = 0.05, 0.10
    if strategy == "Quick TP/SL (ไม่มี EMA)":
        c_tp, c_sl = st.columns(2)
        with c_tp:
            tp_pct = st.number_input("TP %", 1.0, 50.0, 12.0, 1.0) / 100
        with c_sl:
            sl_pct = st.number_input("SL %", 1.0, 50.0, 15.0, 1.0) / 100
    use_tp5_sl10_exit = strategy == "Quick TP/SL (ไม่มี EMA)"

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

if mode == "📋 สรุปผลการทดลอง (Research Log)":
    st.markdown(RESEARCH_LOG_MD)
    st.stop()

# ══════════ เปิดจากลิงก์แท็บใหม่ (ดูกราฟหุ้นเดียว จากผลสแกน) ══════════
# sidebar ด้านบนตั้งค่าเริ่มต้นตามลิงก์ให้แล้ว จากนี้ใช้ค่า "สด" จาก sidebar เสมอ
# (ปรับ sidebar บนแท็บนี้ได้จริง กราฟจะอัปเดตตาม ไม่ใช่ค่าตายตัวจากตอนสแกน)
effective_scaling = use_scaling
effective_ema_cross = use_ema_cross
effective_hh_hl = use_hh_hl
effective_ema5_trail = use_ema5_trail
effective_ema_stack = use_ema_stack
effective_ema30_50_exit = use_ema30_50_exit
effective_ema30_50_tp15_exit = use_ema30_50_tp15_exit
effective_tp5_sl10_exit = use_tp5_sl10_exit

if effective_ema_stack:
    entry_desc = ("หุ้น `Close>EMA5>EMA10>EMA30>EMA50>EMA100>EMA200` เรียงขั้นบันไดครบทุกเส้น (แนวโน้มขึ้นชัดเจนทุกกรอบเวลา) "
                  "**และ** ราคาต้องทำ **New High รอบ 1 ปี** (breakout จริงในช่วง 1 ปีที่ผ่านมา — ถ้าไม่เบรกไม่เข้า) "
                  "— **ไม่ใช้เงื่อนไข SET**")
elif effective_hh_hl:
    entry_desc = ("แพทเทิร์น **Higher-High / Higher-Low 2 ชุดติดกัน** (Low ชุด 2 ต่ำกว่าชุดแรกได้ไม่เกิน `5%`) "
                  "แล้วราคาทะลุ Swing High ล่าสุด (breakout) **และ** ราคาต้องอยู่เหนือ `EMA200` "
                  "— **ไม่ใช้เงื่อนไข SET** (price action ของหุ้นล้วนๆ)\n\n"
                  "หลัง breakout ถ้าราคาหลุด `EMA5` → **มอนิเตอร์ต่ออีก ~2 เดือน** ถ้าราคาทะลุ**จุดสูงสุดที่เคยขึ้นไปถึง"
                  "ระหว่างถือไม้แรก** (ไม่ใช่ราคาที่ breakout เข้าซื้อ) ซ้ำอีกครั้งในช่วงนี้ → **เข้าใหม่ทันที** "
                  "(ไม่ต้องรอสร้างแพทเทิร์น HH-HL ชุดใหม่)")
elif effective_ema_cross:
    entry_desc = ("วันที่ `EMA50` ตัดขึ้น `EMA100` **และ** หุ้น `Close>EMA200` · `EMA10>EMA50` · `MACD>0` "
                  "**และ** SET `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200`")
else:
    entry_desc = ("หุ้น `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200` · `MACD>0` "
                  "**และ** SET `Close>EMA200` · `EMA10>EMA50` · `EMA50>EMA200`")

if effective_tp5_sl10_exit:
    exit_desc = (f"**Quick TP/SL**: ขาย `หมด` ทันทีที่กำไรถึง `+{tp_pct*100:.0f}%` หรือขาดทุนถึง `-{sl_pct*100:.0f}%` "
                 "— ไม่มีเงื่อนไข EMA เลย")
elif effective_ema30_50_tp15_exit:
    exit_desc = ("**EMA30 ตัดลง EMA50 + TP15%**: ขาย `หมด` ทันทีที่ `EMA30 < EMA50` **หรือ** กำไรถึง `+15%` "
                 "(หรือ Cut Loss `-8%` ก่อน) — ไม่มี scaling")
elif effective_ema30_50_exit:
    exit_desc = "**EMA30 ตัดลง EMA50**: ขาย `หมด` ทันทีที่ `EMA30 < EMA50` (หรือ Cut Loss `-8%` ก่อน) — ไม่มี scaling"
elif effective_ema5_trail:
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
    setclose_q = load_one(US_MARKET_INDEX if is_us_deep_link else SET_SYMBOL, int(years))
    close_q = load_one(symbol, int(years))
    if close_q is None:
        st.error(f"ไม่มีข้อมูล {symbol}")
    else:
        show_stock_detail(symbol, close_q, setclose_q, fee, cap, effective_scaling, effective_ema_cross, effective_hh_hl, effective_ema5_trail, int(years), effective_ema_stack, effective_ema30_50_exit, effective_ema30_50_tp15_exit, effective_tp5_sl10_exit, tp_pct, sl_pct)
    st.stop()

if not run:
    st.info("👈 เลือกโหมด + ตั้งค่า แล้วกด **รัน Backtest**")
    st.stop()

looks_like_us_ticker = mode == "หุ้นเดียว" and symbol and ".BK" not in symbol.upper()
market_index_symbol = US_MARKET_INDEX if (is_us_group(group) or looks_like_us_ticker) else SET_SYMBOL
setclose = load_one(market_index_symbol, int(years))
if setclose is None:
    st.warning(f"⚠️ ไม่พบข้อมูล {market_index_symbol} — ใช้เงื่อนไขหุ้นอย่างเดียว")

# ══════════ โหมดคัดหุ้นถือยาว (Fundamental Screener) ══════════
if mode == "คัดหุ้นถือยาว (Fundamental)":
    syms = group_symbols(group)
    st.subheader(f"🧭 คัดหุ้นถือยาว: {group} ({len(syms)} ตัว)")
    st.caption("ให้คะแนนจากงบการเงินปัจจุบัน (ไม่ดูกราฟ/เทคนิคเลย) — จุดเริ่มต้นหาหุ้นถือยาว ไม่ใช่คำแนะนำลงทุน")

    rows = []
    prog = st.progress(0.0)
    for i, sym in enumerate(syms):
        fund = get_fundamentals(sym)
        if fund:
            roe = fund.get('roe')
            eps_g = fund.get('eps_growth')
            de = fund.get('de_ratio')
            ebit_m = fund.get('ebit_margin')
            pe = fund.get('pe_ratio')

            score = 0
            score += 1 if (roe is not None and roe > 0.15) else 0
            score += 1 if (eps_g is not None and eps_g > 0.10) else 0
            score += 1 if (de is not None and de < 1.0) else 0
            score += 1 if (ebit_m is not None and ebit_m > 0.10) else 0
            score += 1 if (pe is not None and 0 < pe < 25) else 0

            rows.append({
                "หุ้น": sym.replace(".BK", ""),
                "คะแนน": score,
                "P/E": format_ratio(pe, ".2f"),
                "ROE": format_ratio(roe, ".2%"),
                "D/E": format_ratio(de, ".2f"),
                "EBIT Margin": format_ratio(ebit_m, ".2%"),
                "EPS Growth": format_ratio(eps_g, ".2%"),
            })
        prog.progress((i + 1) / len(syms))
    prog.empty()

    if not rows:
        st.error("ไม่มีข้อมูล fundamental พอสำหรับกลุ่มนี้"); st.stop()

    res = pd.DataFrame(rows).sort_values("คะแนน", ascending=False).reset_index(drop=True)

    st.caption("👉 คลิกที่ชื่อหุ้น → กราฟเด้งขึ้นแท็บใหม่ทันที (ใช้เงื่อนไข/กลยุทธ์เทคนิคที่ตั้งไว้ในแถบข้าง)")
    import html as html_lib
    cols = ["หุ้น", "คะแนน", "P/E", "ROE", "D/E", "EBIT Margin", "EPS Growth"]
    header = "".join(
        f'<th style="text-align:{"left" if c == "หุ้น" else "right"};padding:6px 10px;'
        f'border-bottom:2px solid rgba(128,128,128,.4);white-space:nowrap;">{c}</th>'
        for c in cols
    )
    rows_html = []
    for _, r in res.iterrows():
        sym = str(r["หุ้น"])
        url = (f"?sym={sym}&years={int(years)}&cap={cap:.0f}&fee={fee}"
               f"&scaling={1 if use_scaling else 0}&cross={1 if use_ema_cross else 0}"
               f"&hhhl={1 if use_hh_hl else 0}&ema5trail={1 if use_ema5_trail else 0}"
               f"&emastack={1 if use_ema_stack else 0}&ema3050={1 if use_ema30_50_exit else 0}"
               f"&ema3050tp15={1 if use_ema30_50_tp15_exit else 0}&tp5sl10={1 if use_tp5_sl10_exit else 0}"
               f"&us={1 if is_us_group(group) else 0}")
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

    st.caption("คะแนนเต็ม 5 ข้อ: ROE>15% · EPS Growth>10% (YoY) · D/E<1.0 · EBIT Margin>10% · P/E<25 "
               "(ข้อไหนไม่มีข้อมูลนับว่าไม่ผ่านข้อนั้น) — เกณฑ์เดียวกับกรอบคิด: คุณภาพธุรกิจ (ROE/กำไรโต) "
               "+ ฐานะการเงิน (D/E/Margin) + ราคาที่จ่าย (P/E) แต่ยังไม่รวมเรื่อง moat/ผู้บริหาร/เทรนด์อุตสาหกรรม "
               "ที่ต้องดูเองเพิ่ม")
    top = res[res["คะแนน"] >= 4]
    if not top.empty:
        st.success(f"หุ้นคะแนน 4-5/5 เต็ม: {', '.join(top['หุ้น'].tolist())}")
    st.stop()

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

        if use_scaling:
            st.info("ℹ️ กลยุทธ์ออก \"Scaling Out\" ขายบางส่วนไม่รองรับในโหมดพอร์ตหมุนเงิน "
                    "(ไม่เข้ากับโมเดลช่องถือเต็ม-ว่าง) — ใช้ Default (Trail EMA50) แทนในโหมดนี้")
        with st.spinner("กำลังจำลองพอร์ต..."):
            R = simulate_portfolio(closes_to_use, setclose, fee, n_slots, use_scaling, use_ema_cross, use_hh_hl,
                                   use_ema5_trail, use_ema_stack, use_ema30_50_exit, use_ema30_50_tp15_exit,
                                   use_tp5_sl10_exit, tp_pct, sl_pct)
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

            _, _, m = build_and_sim(c, setclose, fee, use_scaling, use_ema_cross, use_hh_hl, use_ema5_trail, use_ema_stack, use_ema30_50_exit, use_ema30_50_tp15_exit, use_tp5_sl10_exit, tp_pct, sl_pct)
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
                   f"&hhhl={1 if use_hh_hl else 0}&ema5trail={1 if use_ema5_trail else 0}"
                   f"&emastack={1 if use_ema_stack else 0}&ema3050={1 if use_ema30_50_exit else 0}"
                   f"&ema3050tp15={1 if use_ema30_50_tp15_exit else 0}&tp5sl10={1 if use_tp5_sl10_exit else 0}"
               f"&us={1 if is_us_group(group) else 0}")
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
show_stock_detail(symbol, close, setclose, fee, cap, use_scaling, use_ema_cross, use_hh_hl, use_ema5_trail, int(years), use_ema_stack, use_ema30_50_exit, use_ema30_50_tp15_exit, use_tp5_sl10_exit, tp_pct, sl_pct)
st.caption("⚠️ backtest ≠ ผลจริง · ลองหลายตัว/หลายช่วง กัน overfit · Sandbox ≤10%")
