"""UC04 – Lập hóa đơn bán hàng (phiếu tính tiền): chọn khách, thêm hàng, trừ kho theo lô, lưu."""
import streamlit as st

from db import giao_dich, hom_nay, query
from kho import cap_phat, la_boi_so_buoc, ton_ban_duoc
from quy_dinh import GIAM_SI, MOI_SO_HD, MOI_TONG_TIEN, NGUONG_SI
from ui import KENH, LOAI_KHACH, THANH_TOAN, kg, sdt_hop_le, thong_bao, vnd

KENH_NGUOC = {v: k for k, v in KENH.items()}
TT_NGUOC = {v: k for k, v in THANH_TOAN.items()}


def thanh_tien(so_luong, don_gia, giam=0):
    """Thành tiền (VNĐ). Giá là bội số của 1.000 và số lượng là bội số của 0,5 nên luôn ra số nguyên."""
    tien = round(so_luong * 2) * don_gia // 2
    return tien - tien * giam // 100


def la_khach_moi(khach_id):
    """QĐ8: hơn 10 hóa đơn và hơn 30 triệu trong năm dương lịch. Khách lẻ dùng chung (id 1) không tính."""
    if khach_id == 1:
        return False
    r = query("SELECT COUNT(*) AS n, COALESCE(SUM(tong_tien), 0) AS t FROM HoaDon "
              "WHERE khach_hang_id = ? AND trang_thai = 'hoan_thanh' AND substr(ngay_lap, 1, 4) = ?",
              (khach_id, str(hom_nay().year))).iloc[0]
    return r["n"] > MOI_SO_HD and r["t"] > MOI_TONG_TIEN


def show():
    st.header("Lập hóa đơn")
    lan = st.session_state.get("hd_lan", 0)          # đổi số này để xóa sạch các ô nhập sau khi lưu
    gio = st.session_state.setdefault("gio", {})     # {id sản phẩm: số kg}
    sp = ton_ban_duoc()

    # ---- 1. Khách hàng ----
    st.subheader("1. Khách hàng")
    sdt = st.text_input("Số điện thoại khách (bỏ trống nếu khách không cho)", key=f"hd_sdt_{lan}").strip()
    khach_id, loai, ten_moi, loi_khach = None, "le", "", None
    if sdt == "":
        khach_id = 1
        st.info("Khách không cho số điện thoại: ghi là Khách lẻ")                      # 2a
    elif not sdt_hop_le(sdt):
        loi_khach = "Số điện thoại gồm 10 chữ số, bắt đầu bằng số 0"                   # 2b
        st.error(loi_khach)
    else:
        df = query("SELECT id, ho_ten, loai FROM KhachHang WHERE so_dien_thoai = ?", (sdt,))
        if df.empty:
            ten_moi = st.text_input("Khách mới, nhập họ tên", key=f"hd_ten_{lan}").strip()   # 2c
        else:
            khach_id, loai = int(df["id"].iloc[0]), df["loai"].iloc[0]
            nhan = LOAI_KHACH[loai] + (" – Khách mối" if la_khach_moi(khach_id) else "")
            st.success(f"{df['ho_ten'].iloc[0]} – {nhan}")

    # ---- 2. Hàng bán ----
    st.subheader("2. Hàng bán")
    if sp.empty:
        st.info("Chưa có sản phẩm nào trong hệ thống")
    else:
        nhan_sp = {f"{r.ma} – {r.ten} (còn {kg(r.ton)}, {vnd(r.gia_ban)}/kg)": int(r.id) for r in sp.itertuples()}
        c1, c2, c3 = st.columns([3, 1, 1])
        chon = c1.selectbox("Sản phẩm", list(nhan_sp), key=f"hd_sp_{lan}")
        so_kg = c2.number_input("Số kg", min_value=0.5, step=0.5, value=1.0, key=f"hd_kg_{lan}")
        if c3.button("Thêm vào hóa đơn", key=f"hd_them_{lan}"):
            r = sp[sp["id"] == nhan_sp[chon]].iloc[0]
            moi = round(gio.get(int(r["id"]), 0) + so_kg, 2)
            if not la_boi_so_buoc(so_kg):
                st.error("Chỉ bán theo bội số của 0,5 kg (ví dụ 0,5 – 1 – 1,5 kg)")       # 4a
            elif moi > r["ton"]:
                st.error(f"{r['ten']} chỉ còn {kg(r['ton'])} có thể bán")                  # 4b
            else:
                gio[int(r["id"])] = moi
                st.rerun()

    dong, tong = [], 0
    for sid, so in gio.items():
        r = sp[sp["id"] == sid].iloc[0]
        giam = GIAM_SI if loai == "si" and so >= NGUONG_SI else 0                      # QĐ3
        tt = thanh_tien(so, int(r["gia_ban"]), giam)
        tong += tt
        dong.append({"Sản phẩm": r["ten"], "Số kg": kg(so), "Đơn giá 1 kg": vnd(r["gia_ban"]),
                     "Giảm": f"{giam}%", "Thành tiền": vnd(tt)})
    if dong:
        st.dataframe(dong, hide_index=True, width="stretch")
        d1, d2, d3 = st.columns([3, 1, 1])
        xoa = d1.selectbox("Dòng cần xóa", [d["Sản phẩm"] for d in dong], key=f"hd_xoa_{lan}")
        if d2.button("Xóa dòng", key=f"hd_xoa_dong_{lan}"):
            for sid in list(gio):
                if sp[sp["id"] == sid]["ten"].iloc[0] == xoa:
                    del gio[sid]
            st.rerun()
        if d3.button("Xóa hết", key=f"hd_xoa_het_{lan}"):
            gio.clear()
            st.rerun()
    st.metric("Tổng tiền", vnd(tong))

    # ---- 3. Kênh bán, thanh toán ----
    st.subheader("3. Kênh bán và thanh toán")
    e1, e2 = st.columns(2)
    kenh = e1.selectbox("Kênh bán", list(KENH_NGUOC), key=f"hd_kenh_{lan}")
    la_online = KENH_NGUOC[kenh] == "online"
    ds_thanh_toan = [THANH_TOAN["chuyen_khoan"]] if la_online else list(TT_NGUOC)
    thanh_toan = e2.selectbox("Hình thức thanh toán", ds_thanh_toan, key=f"hd_tt_{lan}")
    if la_online:
        e2.caption("Đơn online bắt buộc thanh toán chuyển khoản trước (QĐ4)")
    dia_chi = ""
    if la_online:
        dia_chi = st.text_input("Địa chỉ giao (tỉnh/thành, khách trả tiền gửi xe)", key=f"hd_dc_{lan}").strip()

    if st.button("Lưu hóa đơn", type="primary", key=f"hd_luu_{lan}"):
        if not gio:
            st.error("Hóa đơn chưa có sản phẩm")                                       # 6a
        elif loi_khach:
            st.error(loi_khach)
        elif khach_id is None and not ten_moi:
            st.error("Nhập họ tên cho khách mới")                                      # 6b
        elif la_online and (sdt == "" or not dia_chi):
            st.error("Đơn online cần số điện thoại và địa chỉ giao của khách")         # 6c
        elif la_online and TT_NGUOC.get(thanh_toan) != "chuyen_khoan":
            st.error("Đơn online bắt buộc thanh toán chuyển khoản trước (QĐ4)")
        else:
            try:
                with giao_dich() as conn:
                    if khach_id is None:                                               # tạo hồ sơ khách mới (khách lẻ)
                        khach_id = conn.execute("INSERT INTO KhachHang (ho_ten, so_dien_thoai, dia_chi, loai) "
                                                "VALUES (?, ?, ?, 'le')", (ten_moi, sdt, dia_chi or None)).lastrowid
                    elif dia_chi and khach_id != 1:
                        conn.execute("UPDATE KhachHang SET dia_chi = ? WHERE id = ?", (dia_chi, khach_id))
                    hd_id = conn.execute(
                        "INSERT INTO HoaDon (ngay_lap, khach_hang_id, kenh, thanh_toan, nguoi_lap_id, tong_tien) "
                        "VALUES (?, ?, ?, ?, ?, 0)",
                        (hom_nay().isoformat(), khach_id, KENH_NGUOC[kenh], TT_NGUOC[thanh_toan],
                         int(st.session_state["user"]["id"]))).lastrowid
                    tong_hd = 0
                    for sid, so in gio.items():
                        gia = int(sp[sp["id"] == sid]["gia_ban"].iloc[0])
                        giam = GIAM_SI if loai == "si" and so >= NGUONG_SI else 0
                        for lo_id, lay in cap_phat(conn, sid, so):                    # QĐ5: lô gần hết hạn trước
                            tt = thanh_tien(lay, gia, giam)
                            conn.execute("INSERT INTO ChiTietHoaDon (hoa_don_id, san_pham_id, nhap_hang_id, so_luong, "
                                         "don_gia, giam_gia, thanh_tien) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                         (hd_id, sid, lo_id, lay, gia, giam, tt))
                            conn.execute("UPDATE NhapHang SET so_luong_con_lai = ROUND(so_luong_con_lai - ?, 2) WHERE id = ?",
                                         (lay, lo_id))
                            tong_hd += tt
                    conn.execute("UPDATE HoaDon SET tong_tien = ? WHERE id = ?", (tong_hd, hd_id))
            except ValueError as loi:                                                  # hết hàng giữa chừng: hủy toàn bộ
                st.error(str(loi))
                return
            st.session_state["gio"] = {}
            st.session_state["hd_lan"] = lan + 1
            thong_bao(f"Đã lưu hóa đơn số {hd_id}, tổng {vnd(tong_hd)}")
            st.rerun()
