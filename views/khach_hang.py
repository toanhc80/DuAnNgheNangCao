"""UC08 – Quản lý khách hàng (chỉ chủ cửa hàng): xem, thêm, sửa, xóa, đánh dấu khách sỉ, xem lịch sử mua."""
import pandas as pd
import streamlit as st

from db import execute, hom_nay, query
from quy_dinh import MOI_SO_HD, MOI_TONG_TIEN
from ui import KENH, LOAI_KHACH, THANH_TOAN, chi_chu_cua_hang, sdt_hop_le, thong_bao, vnd

LOAI_NGUOC = {v: k for k, v in LOAI_KHACH.items()}
TRANG_THAI = {"hoan_thanh": "Hoàn thành", "da_huy": "Đã hủy"}


def danh_sach():
    """Mọi khách kèm số hóa đơn và tổng mua trong năm, và nhãn khách mối (QĐ8)."""
    df = query("SELECT k.id, k.ho_ten, k.so_dien_thoai, k.dia_chi, k.loai, COUNT(h.id) AS so_hd, "
               "COALESCE(SUM(h.tong_tien), 0) AS tong FROM KhachHang k LEFT JOIN HoaDon h ON h.khach_hang_id = k.id "
               "AND h.trang_thai = 'hoan_thanh' AND substr(h.ngay_lap, 1, 4) = ? GROUP BY k.id ORDER BY k.id",
               (str(hom_nay().year),))
    df["moi"] = (df["id"] != 1) & (df["so_hd"] > MOI_SO_HD) & (df["tong"] > MOI_TONG_TIEN)
    return df


def kiem_tra(ten, sdt, loai_id=None):
    """Trả về chuỗi lỗi hoặc None. loai_id là id khách đang sửa (để không tính trùng với chính nó)."""
    if not ten:
        return "Nhập họ tên khách"
    if not sdt_hop_le(sdt):
        return "Số điện thoại gồm 10 chữ số, bắt đầu bằng số 0"
    trung = query("SELECT id FROM KhachHang WHERE so_dien_thoai = ? AND id <> ?", (sdt, loai_id or 0))
    if not trung.empty:
        return "Số điện thoại này đã có trong danh sách khách"
    return None


def show():
    st.header("Khách hàng")
    if not chi_chu_cua_hang():
        return
    ds = danh_sach()
    tab1, tab2, tab3, tab4 = st.tabs(["Danh sách", "Thêm khách", "Sửa hoặc xóa", "Lịch sử mua"])

    with tab1:
        c1, c2 = st.columns([2, 1])
        tim = c1.text_input("Tìm theo tên hoặc số điện thoại", key="kh_tim").strip().lower()
        loai = c2.selectbox("Loại khách", ["Tất cả"] + list(LOAI_NGUOC), key="kh_loai")
        loc = ds
        if tim:
            loc = loc[loc["ho_ten"].str.lower().str.contains(tim, regex=False)
                      | loc["so_dien_thoai"].fillna("").str.contains(tim, regex=False)]
        if loai != "Tất cả":
            loc = loc[loc["loai"] == LOAI_NGUOC[loai]]
        if loc.empty:
            st.info("Không tìm thấy khách nào")
        else:
            st.dataframe(pd.DataFrame({
                "Họ tên": loc["ho_ten"], "Số điện thoại": loc["so_dien_thoai"].fillna("-"),
                "Địa chỉ": loc["dia_chi"].fillna("-"), "Loại": loc["loai"].map(LOAI_KHACH),
                "Khách mối": loc["moi"].map(lambda m: "Có" if m else ""),
                f"Số hóa đơn {hom_nay().year}": loc["so_hd"], f"Tổng mua {hom_nay().year}": loc["tong"].map(vnd)}),
                hide_index=True, width="stretch")

    with tab2:
        with st.form("them_khach", clear_on_submit=True):
            ten = st.text_input("Họ tên")
            sdt = st.text_input("Số điện thoại")
            dia_chi = st.text_input("Địa chỉ (tỉnh/thành)")
            loai_moi = st.selectbox("Loại khách", list(LOAI_NGUOC), key="kh_loai_moi")
            if st.form_submit_button("Thêm khách", type="primary"):
                ten, sdt = ten.strip(), sdt.strip()
                loi = kiem_tra(ten, sdt)
                if loi:
                    st.error(loi)                                                       # 4a
                else:
                    execute("INSERT INTO KhachHang (ho_ten, so_dien_thoai, dia_chi, loai) VALUES (?, ?, ?, ?)",
                            (ten, sdt, dia_chi.strip() or None, LOAI_NGUOC[loai_moi]))
                    thong_bao(f"Đã thêm khách {ten}")
                    st.rerun()

    with tab3:
        co_the_sua = ds[ds["id"] != 1]                  # "Khách lẻ" dùng chung không được sửa, không được xóa
        if co_the_sua.empty:
            st.info("Chưa có khách hàng nào khác để sửa hoặc xóa")
        else:
            nhan = {f"{r.ho_ten} – {r.so_dien_thoai}": int(r.id) for r in co_the_sua.itertuples()}
            chon = st.selectbox("Khách cần sửa hoặc xóa", list(nhan), key="kh_chon")
            k = ds[ds["id"] == nhan[chon]].iloc[0]
            kid = int(k["id"])
            ten = st.text_input("Họ tên", value=k["ho_ten"], key=f"kh_ten_{kid}").strip()
            sdt = st.text_input("Số điện thoại", value=k["so_dien_thoai"], key=f"kh_sdt_{kid}").strip()
            dia_chi = st.text_input("Địa chỉ", value=k["dia_chi"] or "", key=f"kh_dc_{kid}").strip()
            loai_sua = st.selectbox("Loại khách (theo danh sách khách sỉ của chị Hằng)", list(LOAI_NGUOC),
                                    index=0 if k["loai"] == "le" else 1, key=f"kh_lo_{kid}")
            b1, b2 = st.columns(2)
            if b1.button("Lưu thay đổi", type="primary"):
                loi = kiem_tra(ten, sdt, kid)
                if loi:
                    st.error(loi)
                else:
                    execute("UPDATE KhachHang SET ho_ten = ?, so_dien_thoai = ?, dia_chi = ?, loai = ? WHERE id = ?",
                            (ten, sdt, dia_chi or None, LOAI_NGUOC[loai_sua], kid))
                    thong_bao(f"Đã cập nhật khách {ten}")
                    st.rerun()
            if b2.button("Xóa khách này"):
                if query("SELECT COUNT(*) AS n FROM HoaDon WHERE khach_hang_id = ?", (kid,))["n"].iloc[0] > 0:
                    st.error("Khách đã có hóa đơn nên không xóa được")                       # 6a
                else:
                    execute("DELETE FROM KhachHang WHERE id = ?", (kid,))
                    thong_bao(f"Đã xóa khách {k['ho_ten']}")
                    st.rerun()

    with tab4:
        if ds.empty:
            st.info("Chưa có khách hàng nào")
        else:
            nhan_ls = {f"{r.ho_ten} – {r.so_dien_thoai if pd.notna(r.so_dien_thoai) else 'không có số'}": int(r.id)
                       for r in ds.itertuples()}
            chon_ls = st.selectbox("Khách cần xem lịch sử", list(nhan_ls), key="kh_ls")
            ls = query("SELECT id, ngay_lap, kenh, thanh_toan, tong_tien, trang_thai FROM HoaDon "
                       "WHERE khach_hang_id = ? ORDER BY ngay_lap DESC, id DESC", (nhan_ls[chon_ls],))
            if ls.empty:
                st.info("Khách này chưa mua hàng")
            else:
                st.dataframe(pd.DataFrame({"Số HĐ": ls["id"], "Ngày": ls["ngay_lap"], "Kênh": ls["kenh"].map(KENH),
                                           "Thanh toán": ls["thanh_toan"].map(THANH_TOAN), "Tổng tiền": ls["tong_tien"].map(vnd),
                                           "Trạng thái": ls["trang_thai"].map(TRANG_THAI)}), hide_index=True, width="stretch")
