"""UC02 – Quản lý sản phẩm: ai cũng tìm và xem, chỉ chủ cửa hàng được thêm, sửa giá, xóa."""
import pandas as pd
import streamlit as st

from db import execute, query
from kho import ton_ban_duoc
from ui import kg, la_chu, thong_bao, vnd


def gia_hop_le(gia):
    return gia > 0 and gia % 1000 == 0          # QĐ1: giá là bội số của 1.000 VNĐ


def show():
    st.header("Sản phẩm")
    ds = ton_ban_duoc()
    c1, c2 = st.columns([2, 1])
    tu_khoa = c1.text_input("Tìm theo mã hoặc tên", key="sp_tim").strip().lower()
    nhom = c2.selectbox("Nhóm hàng", ["Tất cả"] + sorted(ds["nhom"].unique()), key="sp_nhom")
    loc = ds
    if tu_khoa:
        loc = loc[loc["ma"].str.lower().str.contains(tu_khoa, regex=False)
                  | loc["ten"].str.lower().str.contains(tu_khoa, regex=False)]
    if nhom != "Tất cả":
        loc = loc[loc["nhom"] == nhom]
    if loc.empty:
        st.info("Không tìm thấy sản phẩm nào")                         # 3a
    else:
        st.dataframe(pd.DataFrame({
            "Mã": loc["ma"], "Tên": loc["ten"], "Nhóm": loc["nhom"],
            "Giá 1 kg": loc["gia_ban"].map(vnd), "Giá 0,5 kg": (loc["gia_ban"] // 2).map(vnd),
            "Tồn bán được": loc["ton"].map(kg)}), hide_index=True, width="stretch")
    if not la_chu():                                                    # nhân viên chỉ tìm và xem
        return

    st.divider()
    st.subheader("Thêm sản phẩm")
    with st.form("them_sp", clear_on_submit=True):
        ma = st.text_input("Mã sản phẩm (ví dụ SP21)")
        ten = st.text_input("Tên sản phẩm")
        nhom_moi = st.text_input("Nhóm hàng (Khô cá, Tôm khô, Mắm, Ba khía, Khô mực...)")
        gia = st.number_input("Giá bán 1 kg (VNĐ)", min_value=0, step=1000, value=0)
        if st.form_submit_button("Thêm sản phẩm", type="primary"):
            ma, ten, nhom_moi = ma.strip().upper(), ten.strip(), nhom_moi.strip()
            if not ma or not ten or not nhom_moi:
                st.error("Nhập đủ mã, tên và nhóm hàng")                 # 4a
            elif not gia_hop_le(gia):
                st.error("Giá bán phải lớn hơn 0 và là bội số của 1.000 VNĐ")   # 4b
            elif not query("SELECT id FROM SanPham WHERE ma = ?", (ma,)).empty:
                st.error(f"Mã {ma} đã tồn tại")                           # 4c
            else:
                execute("INSERT INTO SanPham (ma, ten, nhom, gia_ban) VALUES (?, ?, ?, ?)", (ma, ten, nhom_moi, int(gia)))
                thong_bao(f"Đã thêm sản phẩm {ma} – {ten}")
                st.rerun()

    st.subheader("Sửa giá bán")
    if ds.empty:
        st.info("Chưa có sản phẩm nào để sửa giá")
    else:
        nhan = {f"{r.ma} – {r.ten}": int(r.id) for r in ds.itertuples()}
        chon = st.selectbox("Sản phẩm cần sửa giá", list(nhan), key="sp_sua")
        gia_cu = int(ds[ds["id"] == nhan[chon]]["gia_ban"].iloc[0])
        gia_moi = st.number_input("Giá bán 1 kg mới (VNĐ)", min_value=0, step=1000, value=gia_cu, key=f"sp_gia_{nhan[chon]}")
        if st.button("Lưu giá mới", type="primary"):
            if not gia_hop_le(gia_moi):
                st.error("Giá bán phải lớn hơn 0 và là bội số của 1.000 VNĐ")
            else:
                execute("UPDATE SanPham SET gia_ban = ? WHERE id = ?", (int(gia_moi), nhan[chon]))   # hóa đơn cũ giữ giá cũ
                thong_bao(f"Đã đổi giá {chon} thành {vnd(gia_moi)}/kg")
                st.rerun()

    st.subheader("Xóa sản phẩm")
    if ds.empty:
        st.info("Chưa có sản phẩm nào để xóa")
    else:
        nhan = {f"{r.ma} – {r.ten}": int(r.id) for r in ds.itertuples()}
        xoa = st.selectbox("Sản phẩm cần xóa", list(nhan), key="sp_xoa")
        if st.button("Xóa sản phẩm"):
            sp_id = nhan[xoa]
            da_dung = query("SELECT (SELECT COUNT(*) FROM NhapHang WHERE san_pham_id = ?) + "
                            "(SELECT COUNT(*) FROM ChiTietHoaDon WHERE san_pham_id = ?) AS n", (sp_id, sp_id))["n"].iloc[0]
            if da_dung > 0:
                st.error("Sản phẩm đã có lô nhập hoặc hóa đơn nên không xóa được")        # 6a
            else:
                execute("DELETE FROM SanPham WHERE id = ?", (sp_id,))
                thong_bao(f"Đã xóa {xoa}")
                st.rerun()
