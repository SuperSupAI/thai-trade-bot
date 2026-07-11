"""
ดาวน์โหลดข้อมูลหุ้นแบบแยกโปรเซส (process isolation)

เหตุผล: yfinance ใช้ curl_cffi (C extension ผ่าน cffi) เพื่อคุย Yahoo Finance
บางครั้งเจอ response ผิดปกติ (เช่นหุ้น delisted) แล้ว "segfault" — โปรแกรมล่ม
ทั้งโปรเซสทันที ซึ่ง try/except ในภาษา Python จับไม่ได้เลย (มันตายก่อนที่
exception จะถูก raise ด้วยซ้ำ)

ทางแก้ทางเดียวที่ได้ผลจริง: รันการดาวน์โหลดแต่ละตัวใน "โปรเซสลูก" แยกต่างหาก
ถ้าโปรเซสลูก segfault มันตายแค่ตัวมันเอง โปรเซสหลัก (แอป Streamlit) ไม่กระทบเลย

หมายเหตุสำคัญ: ต้องใช้ context "fork" เท่านั้น (ใช้ได้บน Linux/Streamlit Cloud)
เพราะ "spawn" จะพยายาม re-import ไฟล์สคริปต์หลัก (app.py) ใหม่ทั้งหมดในโปรเซสลูก
ซึ่งพังกับสคริปต์ Streamlit (ไม่มี if __name__=="__main__" guard)
บน Windows (เครื่อง dev) ไม่มี fork → fallback ไปดาวน์โหลดตรงๆ ในโปรเซสเดียว
(ไม่มีปัญหานี้บน Windows local เพราะ segfault เกิดเฉพาะบน Streamlit Cloud/Linux)
"""
import multiprocessing as mp
import pandas as pd

TIMEOUT_PER_SYMBOL = 15  # วินาที ต่อหุ้น 1 ตัว
CHUNK = 6                # ดาวน์โหลดพร้อมกันกี่ตัว (จำกัดไม่ให้ spawn โปรเซสเยอะเกิน)

_HAS_FORK = "fork" in mp.get_all_start_methods()


def _download_direct(symbol, years, with_volume=False):
    """ดาวน์โหลดตรงๆ ในโปรเซสปัจจุบัน (ทางสำรองบน Windows / ที่ไม่มี fork)"""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=f"{years}y", interval="1d",
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        c = df["Close"]
        if isinstance(c, pd.DataFrame):
            c = c.iloc[:, 0]
        c = c.dropna()
        if not with_volume:
            return c
        v = df["Volume"]
        if isinstance(v, pd.DataFrame):
            v = v.iloc[:, 0]
        return pd.DataFrame({"close": c, "volume": v.reindex(c.index)})
    except Exception:
        return None


def _dl_worker(symbol, years, q, with_volume=False):
    """รันในโปรเซสลูก (fork) — ถ้า segfault ตรงนี้ กระทบแค่โปรเซสนี้"""
    c = _download_direct(symbol, years, with_volume)
    q.put(("ok", c))


def safe_download_one(symbol, years, timeout=TIMEOUT_PER_SYMBOL, with_volume=False):
    """ดาวน์โหลดหุ้น 1 ตัวแบบปลอดภัย คืน pandas Series (close) หรือ DataFrame (close+volume) หรือ None"""
    if not _HAS_FORK:
        return _download_direct(symbol, years, with_volume)

    ctx = mp.get_context("fork")
    q = ctx.Queue()
    p = ctx.Process(target=_dl_worker, args=(symbol, years, q, with_volume))
    p.start()
    p.join(timeout)

    if p.is_alive():                  # ค้าง → ฆ่าทิ้ง
        p.terminate(); p.join()
        return None
    if p.exitcode != 0:                # segfault หรือ crash อื่นๆ (exitcode ติดลบ = โดน signal)
        return None
    try:
        status, payload = q.get_nowait()
        return payload if status == "ok" else None
    except Exception:
        return None


def _direct_fetch_info(symbol):
    """ดึง yf.Ticker(symbol).info ตรงๆ ในโปรเซสปัจจุบัน"""
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info
        return info if info else None
    except Exception:
        return None


def _info_worker(symbol, q):
    info = _direct_fetch_info(symbol)
    q.put(("ok", info))


def safe_fetch_info(symbol, timeout=15):
    """ดึง yf.Ticker(symbol).info แบบแยกโปรเซส กัน segfault ลามมาที่แอปหลัก (เช่นเดียวกับ safe_download_one)"""
    if not _HAS_FORK:
        return _direct_fetch_info(symbol)

    ctx = mp.get_context("fork")
    q = ctx.Queue()
    p = ctx.Process(target=_info_worker, args=(symbol, q))
    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate(); p.join()
        return None
    if p.exitcode != 0:
        return None
    try:
        status, payload = q.get_nowait()
        return payload if status == "ok" else None
    except Exception:
        return None


def safe_download_many(symbols, years, min_rows=210, progress_cb=None):
    """ดาวน์โหลดหลายตัว แบบแบ่งชุด (chunk) กันโปรเซสเยอะเกินไปพร้อมกัน
    1 ตัว segfault/ค้าง = ข้ามไปเฉย ๆ ตัวอื่นในชุดไม่กระทบ"""
    out = {}
    n = len(symbols)

    if not _HAS_FORK:                 # Windows fallback — ดาวน์โหลดตรงๆ ทีละตัว
        for i, s in enumerate(symbols):
            c = _download_direct(s, years)
            if c is not None and len(c) > min_rows:
                out[s] = c
            if progress_cb:
                progress_cb(i + 1, n)
        return out

    ctx = mp.get_context("fork")
    for i in range(0, n, CHUNK):
        batch = symbols[i:i + CHUNK]
        procs = []
        for s in batch:
            q = ctx.Queue()
            p = ctx.Process(target=_dl_worker, args=(s, years, q))
            p.start()
            procs.append((s, p, q))
        for s, p, q in procs:
            p.join(TIMEOUT_PER_SYMBOL)
            if p.is_alive():
                p.terminate(); p.join()
                continue
            if p.exitcode != 0:
                continue
            try:
                status, payload = q.get_nowait()
                if status == "ok" and payload is not None and len(payload) > min_rows:
                    out[s] = payload
            except Exception:
                pass
        if progress_cb:
            progress_cb(min(i + CHUNK, n), n)
    return out
