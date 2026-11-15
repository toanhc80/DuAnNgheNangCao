"""UC06 – Thống kê (chỉ chủ cửa hàng): doanh thu theo tháng, top 5 bán chạy, khách mối, mẫu thử và hao hụt."""
import pandas as pd
import streamlit as st

from db import hom_nay, query
from quy_dinh import MOI_SO_HD, MOI_TONG_TIEN
from ui import chi_chu_cua_hang, kg, vnd

HOAN_THANH = "h.trang_thai = 'hoan_thanh'"      # hóa đơn đã hủy không tính vào mọi thống kê


def show():
    st.header("Thống kê")
    if not chi_chu_cua_hang():
        return
    nam_co = query("SELECT DISTINCT substr(ngay_lap, 1, 4) AS nam FROM HoaDon ORDER BY nam DESC")["nam"].tolist()
    nam = st.selectbox("Năm", nam_co or [str(hom_nay().year)], key="tk_nam")

    # 1. Doanh thu theo tháng
    st.subheader("Doanh thu theo tháng")
    dt = query(f"SELECT substr(h.ngay_lap, 6, 2) AS thang, COUNT(*) AS so_hd, SUM(h.tong_tien) AS doanh_thu "
               f"FROM HoaDon h WHERE {HOAN_THANH} AND substr(h.ngay_lap, 1, 4) = ? GROUP BY thang", (nam,))
    if dt.empty:
        st.info("Năm này chưa có hóa đơn")                                              # 2a
    else:
        du_12 = pd.DataFrame({"thang": [f"{m:02d}" for m in range(1, 13)]}).merge(dt, how="left", on="thang").fillna(0)
        du_12["Tháng"] = "T" + du_12["thang"]
        st.bar_chart(du_12.set_index("Tháng")["doanh_thu"], y_label="Doanh thu (VNĐ)")
        st.dataframe(pd.DataFrame({"Tháng": du_12["Tháng"], "Số hóa đơn": du_12["so_hd"].astype(int),
                                   "Doanh thu": du_12["doanh_thu"].astype(int).map(vnd)}), hide_index=True, width="stretch")
        st.metric(f"Doanh thu cả năm {nam}", vnd(dt["doanh_thu"].sum()))

    # 2. Top 5 sản phẩm bán chạy
    st.subheader("Top 5 sản phẩm bán chạy (theo số kg)")
    top = query(f"SELECT sp.ten, SUM(ct.so_luong) AS kg, SUM(ct.thanh_tien) AS tien FROM ChiTietHoaDon ct "
                f"JOIN HoaDon h ON h.id = ct.hoa_don_id JOIN SanPham sp ON sp.id = ct.san_pham_id "
                f"WHERE {HOAN_THANH} AND substr(h.ngay_lap, 1, 4) = ? GROUP BY sp.id ORDER BY kg DESC, sp.ten LIMIT 5", (nam,))
    if top.empty:
        st.info("Năm này chưa bán sản phẩm nào")
    else:
        st.bar_chart(top.set_index("ten")["kg"], y_label="Số kg đã bán")
        st.dataframe(pd.DataFrame({"Sản phẩm": top["ten"], "Số kg đã bán": top["kg"].map(kg),
                                   "Doanh thu": top["tien"].map(vnd)}), hide_index=True, width="stretch")

    # 3. Khách mối của năm (QĐ8: cả hai điều kiện)
    st.subheader(f"Khách mối năm {nam} (hơn {MOI_SO_HD} hóa đơn và hơn {vnd(MOI_TONG_TIEN)})")
    moi = query(f"SELECT k.ho_ten, k.so_dien_thoai, k.loai, COUNT(*) AS so_hd, SUM(h.tong_tien) AS tong FROM HoaDon h "
                f"JOIN KhachHang k ON k.id = h.khach_hang_id WHERE {HOAN_THANH} AND k.id <> 1 "
                f"AND substr(h.ngay_lap, 1, 4) = ? GROUP BY k.id HAVING COUNT(*) > ? AND SUM(h.tong_tien) > ? "
                f"ORDER BY tong DESC", (nam, MOI_SO_HD, MOI_TONG_TIEN))
    if moi.empty:
        st.info("Chưa có khách nào đủ điều kiện khách mối")
    else:
        st.dataframe(pd.DataFrame({"Khách": moi["ho_ten"], "Số điện thoại": moi["so_dien_thoai"],
                                   "Số hóa đơn": moi["so_hd"], "Tổng mua": moi["tong"].map(vnd)}),
                     hide_index=True, width="stretch")

    # 4. Mẫu thử tích lũy và hao hụt theo sản phẩm (từ các lô đã chốt)
    st.subheader(f"Mẫu thử và hao hụt năm {nam} (các lô đã chốt)")
    hh = query("SELECT sp.ten, SUM(CASE WHEN nh.ly_do_chot = 'het_hang' THEN nh.so_luong_nhap END) AS nhap, "
               "SUM(CASE WHEN nh.ly_do_chot = 'het_hang' THEN nh.mau_thu END) AS mau, "
               "SUM(CASE WHEN nh.ly_do_chot = 'het_hang' THEN nh.hao_hut END) AS hao, "
               "SUM(CASE WHEN nh.ly_do_chot = 'het_han' THEN nh.hao_hut END) AS bo FROM NhapHang nh "
               "JOIN SanPham sp ON sp.id = nh.san_pham_id WHERE nh.trang_thai = 'da_chot' AND substr(nh.ngay_chot, 1, 4) = ? "
               "GROUP BY sp.id ORDER BY sp.id", (nam,)).fillna(0)
    if hh.empty:
        st.info("Năm này chưa chốt lô nào")
    else:
        ty_le = [f"{h / n * 100:.2f}%".replace(".", ",") if n else "-" for h, n in zip(hh["hao"], hh["nhap"])]
        st.dataframe(pd.DataFrame({"Sản phẩm": hh["ten"], "Mẫu thử tích lũy": hh["mau"].map(kg),
                                   "Hao hụt": hh["hao"].map(kg), "Tỷ lệ hao hụt trên số nhập": ty_le,
                                   "Hàng bỏ do hết hạn": hh["bo"].map(kg)}), hide_index=True, width="stretch")
        st.metric("Tổng mẫu thử có thể làm combo", kg(hh["mau"].sum()))
