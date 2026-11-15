"""Ứng dụng quản lý cửa hàng đặc sản khô Hằng Trần (Cà Mau) – file chạy chính.

Chạy:  streamlit run app.py
Tài khoản mẫu (mật khẩu 123456): chu_hang (chủ cửa hàng), nv_lieu, nv_ha, nv_le (nhân viên bán hàng)
"""
import streamlit as st

from auth import kiem_tra_dang_nhap
from ui import VAI_TRO, hien_thong_bao
from views import canh_bao, khach_hang, lap_hoa_don, nhap_hang, san_pham, thong_ke, tra_cuu

st.set_page_config(page_title="Cửa hàng Hằng Trần", layout="wide")

CHU, NV = "chu_cua_hang", "nhan_vien"
# Ma trận phân quyền, đọc từ sơ đồ Use Case: tên chức năng -> (hàm, các vai trò được dùng)
MENU = {
    "Lập hóa đơn": (lap_hoa_don.show, [CHU, NV]),
    "Tra cứu hóa đơn": (tra_cuu.show, [CHU, NV]),
    "Sản phẩm": (san_pham.show, [CHU, NV]),
    "Nhập hàng và chốt lô": (nhap_hang.show, [CHU, NV]),
    "Cảnh báo kho": (canh_bao.show, [CHU, NV]),
    "Khách hàng": (khach_hang.show, [CHU]),
    "Thống kê": (thong_ke.show, [CHU]),
}

# UC01 – Đăng nhập
if "user" not in st.session_state:
    st.title("Cửa hàng đặc sản khô Hằng Trần")
    with st.form("dang_nhap"):
        ten = st.text_input("Tên đăng nhập")
        mk = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập", type="primary"):
            user = kiem_tra_dang_nhap(ten, mk)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu")
    st.stop()  # chưa đăng nhập thì không chạy phần bên dưới

user = st.session_state["user"]
with st.sidebar:
    st.markdown(f"**{user['ho_ten']}**  \n{VAI_TRO[user['vai_tro']]}")
    duoc_dung = [ten for ten, (_, vai_tro) in MENU.items() if user["vai_tro"] in vai_tro]  # lớp bảo vệ 1
    chon = st.radio("Chức năng", duoc_dung)
    if st.button("Đăng xuất"):
        for khoa in ["user", "gio", "hd_lan"]:
            st.session_state.pop(khoa, None)
        st.rerun()

hien_thong_bao()
MENU[chon][0]()
