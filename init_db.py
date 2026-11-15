"""Tạo lại CSDL từ database/schema.sql và database/seed.sql (XÓA dữ liệu cũ).

Chạy:  python init_db.py
"""
from db import query, tao_csdl

tao_csdl()
for bang in ["TaiKhoan", "KhachHang", "SanPham", "NhapHang", "HoaDon", "ChiTietHoaDon"]:
    print(f"{bang:15}: {query(f'SELECT COUNT(*) AS n FROM {bang}')['n'].iloc[0]} dòng")
print("Đã tạo xong CSDL")
