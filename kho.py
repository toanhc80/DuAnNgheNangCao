"""Tính tồn kho theo lô, dùng chung cho nhập hàng, lập hóa đơn, hủy hóa đơn, cảnh báo.

Quy ước: tồn bán được của một sản phẩm = tổng (số còn lại - 1 kg cuối) của các lô đang bán và chưa hết hạn.
"""
from db import hom_nay, query
from quy_dinh import BUOC_KG, KG_CUOI


def la_boi_so_buoc(so_luong):
    """QĐ2: số lượng phải là bội số của 0,5 kg."""
    return abs(so_luong / BUOC_KG - round(so_luong / BUOC_KG)) < 1e-9


def ton_ban_duoc():
    """DataFrame mọi sản phẩm kèm cột ton (kg có thể bán hôm nay)."""
    return query(
        "SELECT sp.id, sp.ma, sp.ten, sp.nhom, sp.gia_ban, "
        "COALESCE(SUM(CASE WHEN nh.trang_thai = 'dang_ban' AND nh.han_dung >= ? "
        "                  THEN MAX(nh.so_luong_con_lai - ?, 0) END), 0) AS ton "
        "FROM SanPham sp LEFT JOIN NhapHang nh ON nh.san_pham_id = sp.id "
        "GROUP BY sp.id ORDER BY sp.id", (hom_nay().isoformat(), KG_CUOI))


def cap_phat(conn, san_pham_id, so_luong):
    """Chia số lượng bán vào các lô, lô gần hết hạn trước (QĐ5). Trả về [(id lô, kg)].
    Không đủ hàng thì báo ValueError."""
    lo = conn.execute(
        "SELECT id, so_luong_con_lai FROM NhapHang "
        "WHERE san_pham_id = ? AND trang_thai = 'dang_ban' AND han_dung >= ? AND so_luong_con_lai > ? "
        "ORDER BY han_dung, ngay_nhap, id", (san_pham_id, hom_nay().isoformat(), KG_CUOI)).fetchall()
    can = round(so_luong, 2)
    ket_qua = []
    for lo_id, con_lai in lo:
        lay = min(can, round(con_lai - KG_CUOI, 2))
        if lay > 0:
            ket_qua.append((lo_id, lay))
            can = round(can - lay, 2)
        if can <= 0:
            break
    if can > 0:
        raise ValueError("Không đủ hàng để bán")
    return ket_qua
