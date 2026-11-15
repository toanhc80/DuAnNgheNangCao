"""UC07 – Xem cảnh báo kho: sắp hết hàng, sắp hết hạn, đã hết hạn, lô chờ chốt."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from db import hom_nay, query
from kho import ton_ban_duoc
from quy_dinh import HAN_CANH_BAO_NGAY, KG_CUOI, NGUONG_TON
from ui import kg


def show():
    st.header("Cảnh báo kho")
    hn = hom_nay()
    moc = hn + timedelta(days=HAN_CANH_BAO_NGAY)
    ton = ton_ban_duoc()
    sap_het = ton[ton["ton"] <= NGUONG_TON]
    sql = ("SELECT nh.id, sp.ten, nh.han_dung, nh.so_luong_con_lai FROM NhapHang nh "
           "JOIN SanPham sp ON sp.id = nh.san_pham_id WHERE nh.trang_thai = 'dang_ban' AND nh.so_luong_con_lai > 0 ")
    sap_han = query(sql + "AND nh.han_dung BETWEEN ? AND ? ORDER BY nh.han_dung, nh.id", (hn.isoformat(), moc.isoformat()))
    het_han = query(sql + "AND nh.han_dung < ? ORDER BY nh.han_dung, nh.id", (hn.isoformat(),))
    cho_chot = query(sql + "AND nh.so_luong_con_lai <= ? AND nh.han_dung >= ? ORDER BY nh.id", (KG_CUOI, hn.isoformat()))

    c = st.columns(4)
    c[0].metric(f"Sắp hết hàng (≤ {NGUONG_TON} kg)", len(sap_het))
    c[1].metric(f"Lô sắp hết hạn (≤ {HAN_CANH_BAO_NGAY} ngày)", len(sap_han))
    c[2].metric("Lô đã hết hạn", len(het_han))
    c[3].metric("Lô chờ chốt", len(cho_chot))

    st.subheader(f"Sản phẩm sắp hết hàng (tồn bán được ≤ {NGUONG_TON} kg)")
    if sap_het.empty:
        st.success("Không có sản phẩm nào sắp hết")                                   # 2a
    else:
        st.dataframe(pd.DataFrame({"Mã": sap_het["ma"], "Sản phẩm": sap_het["ten"],
                                   "Tồn bán được": sap_het["ton"].map(kg)}), hide_index=True, width="stretch")

    def bang_lo(df, co_so_ngay):
        out = pd.DataFrame({"Lô": df["id"], "Sản phẩm": df["ten"], "Hạn dùng": df["han_dung"],
                            "Còn lại": df["so_luong_con_lai"].map(kg)})
        if co_so_ngay:
            out["Số ngày còn lại"] = [(date.fromisoformat(h) - hn).days for h in df["han_dung"]]
        return out

    st.subheader(f"Lô sắp hết hạn (còn ≤ {HAN_CANH_BAO_NGAY} ngày)")
    if sap_han.empty:
        st.success("Không có lô nào sắp hết hạn")
    else:
        st.dataframe(bang_lo(sap_han, True), hide_index=True, width="stretch")

    st.subheader("Lô đã hết hạn, cần chốt bỏ hàng")
    if het_han.empty:
        st.success("Không có lô nào đã hết hạn")
    else:
        st.dataframe(bang_lo(het_han, False), hide_index=True, width="stretch")

    st.subheader(f"Lô chờ chốt (còn ≤ {KG_CUOI} kg, làm mẫu thử)")
    if cho_chot.empty:
        st.success("Không có lô nào chờ chốt")
    else:
        st.dataframe(bang_lo(cho_chot, False), hide_index=True, width="stretch")
