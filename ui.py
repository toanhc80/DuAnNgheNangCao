"""Hàm giao diện dùng chung."""
import re

import streamlit as st

VAI_TRO = {"chu_cua_hang": "Chủ cửa hàng", "nhan_vien": "Nhân viên bán hàng"}
KENH = {"tai_quay": "Tại quầy", "online": "Online"}
THANH_TOAN = {"tien_mat": "Tiền mặt", "chuyen_khoan": "Chuyển khoản"}
LOAI_KHACH = {"le": "Khách lẻ", "si": "Khách sỉ"}


def thong_bao(noi_dung):
    """Lưu thông báo để hiện sau khi trang tải lại (st.rerun xóa mọi thứ đang hiển thị)."""
    st.session_state["_thong_bao"] = noi_dung


def hien_thong_bao():
    noi_dung = st.session_state.pop("_thong_bao", None)
    if noi_dung:
        st.success(noi_dung)


def vnd(so):
    """1400000 -> '1.400.000 VNĐ'"""
    return f"{int(so):,}".replace(",", ".") + " VNĐ"


def kg(so):
    """0.5 -> '0,5 kg'; 21.0 -> '21 kg'"""
    s = f"{float(so):.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") + " kg"


def la_chu():
    return st.session_state["user"]["vai_tro"] == "chu_cua_hang"


def chi_chu_cua_hang():
    """Lớp bảo vệ 2: dù menu đã ẩn, trang chỉ dành cho chủ vẫn tự kiểm tra lại vai trò."""
    if not la_chu():
        st.error("Chức năng này chỉ dành cho chủ cửa hàng")
        return False
    return True


def sdt_hop_le(sdt):
    """Số điện thoại Việt Nam: 10 chữ số, bắt đầu bằng 0."""
    return re.fullmatch(r"0\d{9}", sdt) is not None
