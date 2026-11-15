"""UC05 – Tra cứu hóa đơn, tổng kết cuối ngày, hủy hóa đơn (chỉ chủ cửa hàng được hủy)."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from db import giao_dich, hom_nay, query
from ui import KENH, THANH_TOAN, kg, la_chu, thong_bao, vnd

TRANG_THAI = {"hoan_thanh": "Hoàn thành", "da_huy": "Đã hủy"}


def show():
    st.header("Tra cứu hóa đơn")
    tab1, tab2 = st.tabs(["Tra cứu hóa đơn", "Tổng kết ngày"])
    with tab1:
        tra_cuu()
    with tab2:
        tong_ket()


def tra_cuu():
    user, chu = st.session_state["user"], la_chu()
    c1, c2, c3 = st.columns(3)
    tu = c1.date_input("Từ ngày", value=hom_nay() - timedelta(days=30), key="tc_tu")
    den = c2.date_input("Đến ngày", value=hom_nay(), key="tc_den")
    tim = c3.text_input("Tên hoặc số điện thoại khách", key="tc_tim").strip()
    sql = ("SELECT h.id, h.ngay_lap, k.ho_ten AS khach, h.kenh, h.thanh_toan, t.ho_ten AS nguoi_lap, "
           "h.tong_tien, h.trang_thai FROM HoaDon h JOIN KhachHang k ON k.id = h.khach_hang_id "
           "JOIN TaiKhoan t ON t.id = h.nguoi_lap_id WHERE h.ngay_lap BETWEEN ? AND ?")
    tham_so = [tu.isoformat(), den.isoformat()]
    if tim:
        sql += " AND (k.ho_ten LIKE ? OR k.so_dien_thoai LIKE ?)"
        tham_so += [f"%{tim}%", f"%{tim}%"]
    if chu:
        nguoi = st.selectbox("Người lập", ["Tất cả"] + query("SELECT ho_ten FROM TaiKhoan ORDER BY id")["ho_ten"].tolist(), key="tc_nguoi")
        if nguoi != "Tất cả":
            sql += " AND t.ho_ten = ?"
            tham_so.append(nguoi)
    else:                                                       # nhân viên chỉ thấy hóa đơn do mình lập
        sql += " AND h.nguoi_lap_id = ?"
        tham_so.append(int(user["id"]))
    tt = st.selectbox("Trạng thái", ["Tất cả"] + list(TRANG_THAI.values()), key="tc_tt")
    if tt != "Tất cả":
        sql += " AND h.trang_thai = ?"
        tham_so.append({v: k for k, v in TRANG_THAI.items()}[tt])
    ds = query(sql + " ORDER BY h.ngay_lap DESC, h.id DESC", tuple(tham_so))
    if ds.empty:
        st.info("Không có hóa đơn nào khớp")                                            # 3a
        return
    st.dataframe(pd.DataFrame({
        "Số HĐ": ds["id"], "Ngày": ds["ngay_lap"], "Khách": ds["khach"], "Kênh": ds["kenh"].map(KENH),
        "Thanh toán": ds["thanh_toan"].map(THANH_TOAN), "Người lập": ds["nguoi_lap"],
        "Tổng tiền": ds["tong_tien"].map(vnd), "Trạng thái": ds["trang_thai"].map(TRANG_THAI)}),
        hide_index=True, width="stretch")
    st.caption(f"{len(ds)} hóa đơn")

    nhan = {f"HĐ {r.id} – {r.ngay_lap} – {r.khach} – {vnd(r.tong_tien)}": int(r.id) for r in ds.head(200).itertuples()}
    chon = st.selectbox("Xem chi tiết hóa đơn", list(nhan), key="tc_chon")
    hd_id = nhan[chon]
    hd = ds[ds["id"] == hd_id].iloc[0]
    ct = query("SELECT sp.ten, ct.nhap_hang_id, ct.so_luong, ct.don_gia, ct.giam_gia, ct.thanh_tien "
               "FROM ChiTietHoaDon ct JOIN SanPham sp ON sp.id = ct.san_pham_id WHERE ct.hoa_don_id = ? ORDER BY ct.id", (hd_id,))
    st.dataframe(pd.DataFrame({"Sản phẩm": ct["ten"], "Lô": ct["nhap_hang_id"], "Số kg": ct["so_luong"].map(kg),
                               "Đơn giá 1 kg": ct["don_gia"].map(vnd), "Giảm": ct["giam_gia"].map(lambda g: f"{g}%"),
                               "Thành tiền": ct["thanh_tien"].map(vnd)}), hide_index=True, width="stretch")
    st.write(f"Tổng tiền: {vnd(hd['tong_tien'])} – {TRANG_THAI[hd['trang_thai']]}")
    if hd["trang_thai"] == "da_huy":
        goc = query("SELECT ly_do_huy, ngay_huy FROM HoaDon WHERE id = ?", (hd_id,)).iloc[0]
        st.info(f"Đã hủy ngày {goc['ngay_huy']}. Lý do: {goc['ly_do_huy']}")
    elif chu:
        st.subheader("Hủy hóa đơn")
        ly_do = st.text_area("Lý do hủy (bắt buộc)", key=f"tc_lydo_{hd_id}").strip()
        if st.button("Hủy hóa đơn", key=f"tc_huy_{hd_id}"):
            if not ly_do:
                st.error("Phải ghi lý do hủy")                                          # 6a
            else:
                loi = huy_hoa_don(hd_id, ly_do, int(st.session_state["user"]["id"]))
                if loi:
                    st.error(loi)                                                       # 6b
                else:
                    thong_bao(f"Đã hủy hóa đơn số {hd_id}, hàng đã hoàn về lô")
                    st.rerun()


def huy_hoa_don(hd_id, ly_do, nguoi_huy_id):
    """Phiếu chuyển sang 'da_huy' (không xóa) và hàng hoàn về đúng lô. Trả về chuỗi lỗi hoặc None."""
    with giao_dich() as conn:
        if conn.execute("SELECT trang_thai FROM HoaDon WHERE id = ?", (hd_id,)).fetchone()[0] != "hoan_thanh":
            return "Hóa đơn này đã hủy rồi"
        dong = conn.execute("SELECT ct.nhap_hang_id, ct.so_luong, nh.trang_thai FROM ChiTietHoaDon ct "
                            "JOIN NhapHang nh ON nh.id = ct.nhap_hang_id WHERE ct.hoa_don_id = ?", (hd_id,)).fetchall()
        if any(d[2] == "da_chot" for d in dong):
            return "Hóa đơn có hàng từ lô đã chốt nên không hoàn lại được"
        for lo_id, so, _ in dong:
            conn.execute("UPDATE NhapHang SET so_luong_con_lai = ROUND(so_luong_con_lai + ?, 2) WHERE id = ?", (so, lo_id))
        conn.execute("UPDATE HoaDon SET trang_thai = 'da_huy', ly_do_huy = ?, nguoi_huy_id = ?, ngay_huy = ? WHERE id = ?",
                     (ly_do, nguoi_huy_id, hom_nay().isoformat(), hd_id))
    return None


def tong_ket():
    """Tổng thu trong ngày theo người lập và hình thức thanh toán, để nhân viên đối chiếu khi nộp tiền."""
    user, chu = st.session_state["user"], la_chu()
    ngay = st.date_input("Ngày tổng kết", value=hom_nay(), key="tk_ngay")
    sql = ("SELECT t.ho_ten AS nguoi_lap, h.thanh_toan, COUNT(*) AS so_hd, SUM(h.tong_tien) AS tong FROM HoaDon h "
           "JOIN TaiKhoan t ON t.id = h.nguoi_lap_id WHERE h.ngay_lap = ? AND h.trang_thai = 'hoan_thanh'")
    tham_so = [ngay.isoformat()]
    if not chu:
        sql += " AND h.nguoi_lap_id = ?"
        tham_so.append(int(user["id"]))
    df = query(sql + " GROUP BY t.id, h.thanh_toan ORDER BY t.id", tuple(tham_so))
    if df.empty:
        st.info("Ngày này chưa có hóa đơn nào")
        return
    bang = {}
    for r in df.itertuples():
        b = bang.setdefault(r.nguoi_lap, {"Số hóa đơn": 0, "Tiền mặt": 0, "Chuyển khoản": 0})
        b["Số hóa đơn"] += r.so_hd
        b[THANH_TOAN[r.thanh_toan]] += r.tong
    kq = pd.DataFrame(bang).T
    kq["Tổng thu"] = kq["Tiền mặt"] + kq["Chuyển khoản"]
    if chu:
        kq.loc["Cả cửa hàng"] = kq.sum()
    hien = kq.copy()
    for cot in ["Tiền mặt", "Chuyển khoản", "Tổng thu"]:
        hien[cot] = hien[cot].map(vnd)
    hien.index.name = "Người lập"
    st.dataframe(hien.reset_index(), hide_index=True, width="stretch")
