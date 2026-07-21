#!/usr/bin/env python
"""ทดสอบต่อ Settrade Open API เบื้องต้น -- แค่ login ดูว่า credential ครบ/ถูกไหม ไม่แตะออเดอร์"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from settrade_client import get_investor

try:
    investor = get_investor()
    print("เชื่อมต่อสำเร็จ! login เข้า Settrade Open API (Sandbox) ได้แล้ว")
except KeyError as e:
    print(f"ยังขาด env var: {e} -- เติมใน dr_momentum_bot/.env ให้ครบก่อน")
except Exception as e:
    print(f"เชื่อมต่อไม่สำเร็จ: {type(e).__name__}: {e}")
