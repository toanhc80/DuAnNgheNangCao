"""UC03 – Nhập hàng theo lô và chốt lô (nhân viên trực quầy và chủ cửa hàng cùng dùng)."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from db import execute, hom_nay, query
from kho import la_boi_so_buoc
from quy_dinh import HAN_DUNG_MAC_DINH, KG_CUOI
from ui import kg, la_chu, thong_bao, vnd


def show():
    st.header("Nhập hàng và chốt lô")
    tab1, tab2 = st.tabs(["Nhập hàng", "Chốt lô"])
    with tab1:
        nhap_hang()
    with tab2:
        chot_lo()


def tinh_trang(han_dung, con_lai):
    if han_dung < hom_nay().isoformat():
        return "Đã hết hạn"
    return "Chờ chốt" if con_lai <= KG_CUOI else "Đang bán"


def nhap_hang():
    chu = la_chu()
    sp = query("SELECT id, ma, ten FROM SanPham ORDER BY id")
    if sp.empty:
        st.info("Chưa có sản phẩm nào trong hệ thống để nhập hàng")
        return
    ds = {f"{r.ma} – {r.ten}": int(r.id) for r in sp.itertuples()}
    with st.form("nhap_hang", clear_on_submit=True):
        chon = st.selectbox("Sản phẩm", list(ds))
        ngay = st.date_input("Ngày nhập", value=hom_nay())
        han = st.date_input("Hạn dùng (mặc định 1 năm, sửa theo nhãn nếu khác)",
                            value=hom_nay() + timedelta(days=HAN_DUNG_MAC_DINH))
        so_luong = st.number_input("Số lượng nhập (kg)", min_value=0.0, step=0.5, value=0.0)
        gia = st.number_input("Giá nhập 1 kg (VNĐ), để 0 nếu chưa biết", min_value=0, step=1000, value=0) if chu else 0
        ghi_chu = st.text_input("Ghi chú")
        if st.form_submit_button("Lưu lô nhập", type="primary"):
            if so_luong <= 0 or not la_boi_so_buoc(so_luong):
                st.error("Số lượng nhập phải lớn hơn 0 và là bội số của 0,5 kg")         # 4a
            elif han <= ngay:
                st.error("Hạn dùng phải sau ngày nhập")                                  # 4b
            elif han < hom_nay():
                st.error("Lô này đã quá hạn dùng nên không nhập được")                   # 4c
            else:
                execute("INSERT INTO NhapHang (san_pham_id, ngay_nhap, han_dung, so_luong_nhap, so_luong_con_lai, "
                        "gia_nhap, nguoi_nhap_id, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (ds[chon], ngay.isoformat(), han.isoformat(), float(so_luong), float(so_luong),
                         int(gia) if gia else None, int(st.session_state["user"]["id"]), ghi_chu.strip() or None))
                thong_bao(f"Đã nhập {kg(so_luong)} {chon}")
                st.rerun()

    st.subheader("Các lô đang bán")
    lo = query("SELECT nh.id, sp.ten, nh.ngay_nhap, nh.han_dung, nh.so_luong_nhap, nh.so_luong_con_lai, nh.gia_nhap "
               "FROM NhapHang nh JOIN SanPham sp ON sp.id = nh.san_pham_id "
               "WHERE nh.trang_thai = 'dang_ban' ORDER BY nh.han_dung, nh.id")
    if lo.empty:
        st.info("Chưa có lô nào đang bán")
        return
    bang = pd.DataFrame({"Lô": lo["id"], "Sản phẩm": lo["ten"], "Ngày nhập": lo["ngay_nhap"], "Hạn dùng": lo["han_dung"],
                         "Nhập": lo["so_luong_nhap"].map(kg), "Còn lại": lo["so_luong_con_lai"].map(kg),
                         "Tình trạng": [tinh_trang(h, c) for h, c in zip(lo["han_dung"], lo["so_luong_con_lai"])]})
    if chu:                                                      # QĐ10: giá nhập chỉ chủ cửa hàng xem
        bang["Giá nhập 1 kg"] = [vnd(g) if pd.notna(g) else "Chưa điền" for g in lo["gia_nhap"]]
    st.dataframe(bang, hide_index=True, width="stretch")

    if chu:
        st.subheader("Cập nhật giá nhập")
        nhan = {f"Lô {r.id} – {r.ten} – nhập {r.ngay_nhap}": int(r.id) for r in lo.itertuples()}
        chon_lo = st.selectbox("Lô cần cập nhật", list(nhan), key="gn_lo")
        gia_moi = st.number_input("Giá nhập 1 kg (VNĐ)", min_value=0, step=1000, value=0, key="gn_gia")
        if st.button("Lưu giá nhập"):
            if gia_moi <= 0:
                st.error("Giá nhập phải lớn hơn 0")
            else:
                execute("UPDATE NhapHang SET gia_nhap = ? WHERE id = ?", (int(gia_moi), nhan[chon_lo]))
                thong_bao(f"Đã lưu giá nhập {vnd(gia_moi)}/kg cho {chon_lo}")
                st.rerun()


def chot_lo():
    """QĐ7: lô còn <= 1 kg hoặc đã hết hạn thì chốt. Người trực quầy chỉ nhập số kg mẫu thử."""
    hn = hom_nay().isoformat()
    lo = query("SELECT nh.id, sp.ten, nh.han_dung, nh.so_luong_con_lai FROM NhapHang nh "
               "JOIN SanPham sp ON sp.id = nh.san_pham_id "
               "WHERE nh.trang_thai = 'dang_ban' AND (nh.so_luong_con_lai <= ? OR nh.han_dung < ?) "
               "ORDER BY nh.han_dung, nh.id", (KG_CUOI, hn))
    if lo.empty:
        st.info("Chưa có lô nào cần chốt")                                           # 2a
        return
    ds = {f"Lô {r.id} – {r.ten} – còn {kg(r.so_luong_con_lai)}" + (" – ĐÃ HẾT HẠN" if r.han_dung < hn else ""): r
          for r in lo.itertuples()}
    chon = st.selectbox("Lô cần chốt", list(ds), key="chot_lo")
    r = ds[chon]
    het_han = r.han_dung < hn
    if het_han:
        st.warning(f"Lô đã hết hạn ngày {r.han_dung}: toàn bộ {kg(r.so_luong_con_lai)} ghi là hàng bỏ")
        mau = 0.0
    else:
        mau = st.number_input("Số kg đã bịch làm mẫu thử", min_value=0.0, step=0.1, value=0.0, key="chot_mau")
        st.caption("Phần còn lại sau khi trừ mẫu thử được ghi là hao hụt")
    if st.button("Chốt lô", type="primary"):
        if mau > r.so_luong_con_lai + 1e-9:
            st.error("Số kg mẫu thử không được lớn hơn số còn lại của lô")                # 4a
        else:
            hao = round(r.so_luong_con_lai - mau, 2)
            execute("UPDATE NhapHang SET trang_thai = 'da_chot', mau_thu = ?, hao_hut = ?, ly_do_chot = ?, "
                    "ngay_chot = ?, nguoi_chot_id = ?, so_luong_con_lai = 0 WHERE id = ? AND trang_thai = 'dang_ban'",
                    (round(float(mau), 2), hao, "het_han" if het_han else "het_hang", hn,
                     int(st.session_state["user"]["id"]), int(r.id)))
            thong_bao(f"Đã chốt lô {r.id}: mẫu thử {kg(mau)}, hao hụt {kg(hao)}")
            st.rerun()
