"""
โหลดข้อมูลราคา/volume/fundamentals จาก data/*.parquet ที่ GitHub Action อัปเดตให้วันละครั้ง
(scripts/update_data_cache.py) — ถ้ามีในนี้ ใช้อันนี้ก่อนเสมอ ไม่ต้องยิง yfinance สด
ถ้าไม่มี (หุ้นนอก SET100 ที่ cache ไว้ หรือไฟล์ยังไม่เคยสร้าง) ให้ผู้เรียกใช้ fallback ไปดึงสดเอง
"""
import json
import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PRICES_PATH = os.path.join(DATA_DIR, "prices.parquet")
VOLUMES_PATH = os.path.join(DATA_DIR, "volumes.parquet")
FUNDAMENTALS_PATH = os.path.join(DATA_DIR, "fundamentals.json")


@st.cache_data(ttl=3600, show_spinner=False)
def _load_prices():
    if not os.path.exists(PRICES_PATH):
        return None
    return pd.read_parquet(PRICES_PATH)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_volumes():
    if not os.path.exists(VOLUMES_PATH):
        return None
    return pd.read_parquet(VOLUMES_PATH)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_fundamentals():
    if not os.path.exists(FUNDAMENTALS_PATH):
        return {}
    with open(FUNDAMENTALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _slice_years(series, years):
    if series is None:
        return None
    s = series.dropna()
    if s.empty:
        return None
    cutoff = s.index[-1] - pd.DateOffset(years=years)
    return s[s.index > cutoff]


def get_cached_close(symbol, years):
    """คืน pandas Series ราคาปิด หรือ None ถ้าไม่มีใน cache"""
    df = _load_prices()
    if df is None or symbol not in df.columns:
        return None
    return _slice_years(df[symbol], years)


def get_cached_volume(symbol, years):
    df = _load_volumes()
    if df is None or symbol not in df.columns:
        return None
    return _slice_years(df[symbol], years)


def get_cached_fundamentals(symbol):
    funds = _load_fundamentals()
    return funds.get(symbol)


def cache_available_symbols():
    df = _load_prices()
    return set(df.columns) if df is not None else set()
