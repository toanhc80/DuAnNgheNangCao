"""Kiểm thử tự động: mỗi hàm test ứng với một dòng trong docs/TestCase_CuaHangHangTran.xlsx (mã TCxx ở dòng đầu mô tả).

Chạy:  pip install pytest
       pytest -v
Mỗi test chạy trên một bản CSDL mới tạo từ seed.sql và ngày cố định 11/11/2026, nên không ảnh hưởng dữ liệu đang dùng.
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
import db  # noqa: E402
from ui import kg, vnd  # noqa: E402
from views.lap_hoa_don import la_khach_moi, thanh_tien  # noqa: E402

MENU_CHU = ["Lập hóa đơn", "Tra cứu hóa đơn", "Sản phẩm", "Nhập hàng và chốt lô", "Cảnh báo kho", "Khách hàng", "Thống kê"]
MENU_NV = ["Lập hóa đơn", "Tra cứu hóa đơn", "Sản phẩm", "Nhập hàng và chốt lô", "Cảnh báo kho"]


# ---------------------------------------------------------------- công cụ dùng chung
@pytest.fixture(autouse=True)
def csdl(tmp_path, monkeypatch):
    path = tmp_path / "cuahang.db"
    db.tao_csdl(path)
    monkeypatch.setenv("DB_FILE", str(path))
    monkeypatch.setenv("HOM_NAY", "2026-11-11")
    return path


def sql(path, cau, params=()):
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute(cau, params)
        conn.commit()
        return cur.fetchall()
    finally:
        conn.close()


def ctl(at, loai, nhan=None, key=None):
    for w in getattr(at, loai):
        if (key is not None and w.key == key) or (key is None and w.label == nhan):
            return w
    raise AssertionError(f"Không thấy {loai} nhãn={nhan!r} key={key!r}")


def nut(at, nhan=None, key=None):
    return ctl(at, "button", nhan, key)


def dang_nhap(at, ten, mk):
    ctl(at, "text_input", "Tên đăng nhập").input(ten)
    ctl(at, "text_input", "Mật khẩu").input(mk)
    nut(at, "Đăng nhập").click().run()


def mo(ten="chu_hang", mk="123456", menu=None):
    at = AppTest.from_file(str(GOC / "app.py"), default_timeout=30).run()
    if ten is not None:
        dang_nhap(at, ten, mk)
    if menu:
        at.sidebar.radio[0].set_value(menu).run()
    assert not at.exception
    return at


def loi(at):
    return [e.value for e in at.error]


def chon_option(w, tu_khoa):
    return [o for o in w.options if tu_khoa in o][0]


def bang(at, i):
    return at.dataframe[i].value


def sp_id(path, ma):
    return sql(path, "SELECT id FROM SanPham WHERE ma = ?", (ma,))[0][0]


def con_lai_tong(path, ma):
    return sql(path, "SELECT SUM(so_luong_con_lai) FROM NhapHang WHERE san_pham_id = ?", (sp_id(path, ma),))[0][0]


def them_hang(at, ma, so_kg, lan=0):
    """Chọn sản phẩm theo mã, nhập số kg, bấm Thêm vào hóa đơn."""
    sb = ctl(at, "selectbox", key=f"hd_sp_{lan}")
    sb.set_value(chon_option(sb, f"{ma} –"))
    ctl(at, "number_input", key=f"hd_kg_{lan}").set_value(so_kg)
    nut(at, key=f"hd_them_{lan}").click().run()


def chon_khach(at, sdt, ten=None, lan=0):
    ctl(at, "text_input", key=f"hd_sdt_{lan}").set_value(sdt).run()
    if ten:
        ctl(at, "text_input", key=f"hd_ten_{lan}").set_value(ten).run()


def luu_hoa_don(at, lan=0):
    nut(at, key=f"hd_luu_{lan}").click().run()


def hoa_don_cuoi(path):
    return sql(path, "SELECT id, khach_hang_id, kenh, thanh_toan, nguoi_lap_id, tong_tien, trang_thai "
                     "FROM HoaDon ORDER BY id DESC LIMIT 1")[0]


# ================================================================ UC01 – Đăng nhập (TC01–TC04)
def test_tc01_dang_nhap_chu_cua_hang():
    """TC01 | UC01 | Chủ cửa hàng đăng nhập đúng, thấy đủ 7 chức năng"""
    at = mo("chu_hang", "123456")
    assert at.sidebar.radio[0].options == MENU_CHU
    assert "Chị Hằng" in at.sidebar.markdown[0].value


def test_tc02_dang_nhap_nhan_vien_chi_thay_5_chuc_nang():
    """TC02 | UC01 | Nhân viên đăng nhập đúng, chỉ thấy 5 chức năng (không có Khách hàng, Thống kê)"""
    at = mo("nv_lieu", "123456")
    assert at.sidebar.radio[0].options == MENU_NV


def test_tc03_sai_mat_khau():
    """TC03 | UC01 | Sai mật khẩu thì báo lỗi, không vào được"""
    at = mo("chu_hang", "saimatkhau")
    assert "Sai tên đăng nhập hoặc mật khẩu" in loi(at)
    assert len(at.sidebar.radio) == 0


def test_tc04_bo_trong_va_mat_khau_luu_dang_bam(csdl):
    """TC04 | UC01 | Bỏ trống tên đăng nhập bị từ chối; mật khẩu trong CSDL được lưu dạng băm"""
    at = mo("", "")
    assert "Sai tên đăng nhập hoặc mật khẩu" in loi(at)
    mk = sql(csdl, "SELECT mat_khau_hash FROM TaiKhoan WHERE ten_dang_nhap = 'chu_hang'")[0][0]
    assert mk != "123456" and len(mk) == 64


# ================================================================ UC02 – Quản lý sản phẩm (TC05–TC12)
def test_tc05_xem_danh_sach_20_san_pham_gia_vnd():
    """TC05 | UC02 | Xem danh sách: 20 sản phẩm, giá hiển thị đủ VNĐ (170.000 VNĐ/kg, 85.000 VNĐ/0,5 kg)"""
    at = mo(menu="Sản phẩm")
    b = bang(at, 0)
    assert len(b) == 20
    ba_khia = b[b["Tên"] == "Ba khía muối Rạch Gốc"].iloc[0]
    assert ba_khia["Giá 1 kg"] == "170.000 VNĐ" and ba_khia["Giá 0,5 kg"] == "85.000 VNĐ"


def test_tc06_tim_san_pham_theo_ten():
    """TC06 | UC02 | Tìm 'mực' ra đúng 3 loại khô mực; tìm chuỗi không có thì báo không tìm thấy"""
    at = mo(menu="Sản phẩm")
    ctl(at, "text_input", key="sp_tim").set_value("mực").run()
    assert sorted(bang(at, 0)["Tên"]) == ["Khô mực câu loại 1", "Khô mực loại 2", "Khô mực loại 3"]
    ctl(at, "text_input", key="sp_tim").set_value("khong co hang nay").run()
    assert any("Không tìm thấy sản phẩm" in i.value for i in at.info)


def test_tc07_nhan_vien_chi_xem_khong_sua():
    """TC07 | UC02 | Nhân viên xem và tìm được nhưng không có form thêm, sửa giá, xóa"""
    at = mo("nv_ha", menu="Sản phẩm")
    assert len(bang(at, 0)) == 20
    assert len(at.text_input) == 1                    # chỉ có ô tìm kiếm
    assert not [b for b in at.button if b.label in ("Lưu giá mới", "Xóa sản phẩm")]


def test_tc08_them_san_pham_hop_le(csdl):
    """TC08 | UC02 | Chủ cửa hàng thêm sản phẩm mới hợp lệ"""
    at = mo(menu="Sản phẩm")
    ctl(at, "text_input", "Mã sản phẩm (ví dụ SP21)").input("sp21")
    ctl(at, "text_input", "Tên sản phẩm").input("Khô cá thác lác")
    ctl(at, "text_input", "Nhóm hàng (Khô cá, Tôm khô, Mắm, Ba khía, Khô mực...)").input("Khô cá")
    ctl(at, "number_input", "Giá bán 1 kg (VNĐ)").set_value(300000)
    nut(at, "Thêm sản phẩm").click().run()
    assert sql(csdl, "SELECT ten, gia_ban FROM SanPham WHERE ma = 'SP21'") == [("Khô cá thác lác", 300000)]


@pytest.mark.parametrize("ma, gia, thong_bao", [
    ("SP01", 300000, "đã tồn tại"),
    ("SP22", 1500, "bội số của 1.000"),
    ("SP22", 0, "bội số của 1.000"),
])
def test_tc09_them_san_pham_sai(csdl, ma, gia, thong_bao):
    """TC09 | UC02 | Thêm sản phẩm bị chặn: trùng mã, giá không phải bội số 1.000, giá bằng 0"""
    at = mo(menu="Sản phẩm")
    ctl(at, "text_input", "Mã sản phẩm (ví dụ SP21)").input(ma)
    ctl(at, "text_input", "Tên sản phẩm").input("Sản phẩm thử")
    ctl(at, "text_input", "Nhóm hàng (Khô cá, Tôm khô, Mắm, Ba khía, Khô mực...)").input("Khô cá")
    ctl(at, "number_input", "Giá bán 1 kg (VNĐ)").set_value(gia)
    nut(at, "Thêm sản phẩm").click().run()
    assert any(thong_bao in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM SanPham")[0][0] == 20


def test_tc10_sua_gia_hoa_don_cu_giu_gia_cu(csdl):
    """TC10 | UC02 | Sửa giá bán: giá mới áp dụng từ bây giờ, hóa đơn cũ vẫn giữ giá cũ"""
    at = mo(menu="Sản phẩm")
    sb = ctl(at, "selectbox", key="sp_sua")
    sb.set_value(chon_option(sb, "SP01 –"))
    at.run()
    ctl(at, "number_input", key="sp_gia_1").set_value(180000)
    nut(at, "Lưu giá mới").click().run()
    assert sql(csdl, "SELECT gia_ban FROM SanPham WHERE ma = 'SP01'")[0][0] == 180000
    assert sql(csdl, "SELECT COUNT(*) FROM ChiTietHoaDon WHERE san_pham_id = 1 AND don_gia = 170000")[0][0] > 0


def test_tc11_khong_xoa_san_pham_da_co_lo_hoac_hoa_don(csdl):
    """TC11 | UC02 | Sản phẩm đã có lô nhập hoặc hóa đơn thì không xóa được"""
    at = mo(menu="Sản phẩm")
    sb = ctl(at, "selectbox", key="sp_xoa")
    sb.set_value(chon_option(sb, "SP01 –"))
    nut(at, "Xóa sản phẩm").click().run()
    assert any("không xóa được" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM SanPham")[0][0] == 20


def test_tc12_xoa_san_pham_chua_phat_sinh(csdl):
    """TC12 | UC02 | Sản phẩm chưa có lô nhập, chưa có hóa đơn thì xóa được"""
    sql(csdl, "INSERT INTO SanPham (ma, ten, nhom, gia_ban) VALUES ('SP99', 'Hàng thử', 'Khô cá', 100000)")
    at = mo(menu="Sản phẩm")
    sb = ctl(at, "selectbox", key="sp_xoa")
    sb.set_value(chon_option(sb, "SP99 –"))
    nut(at, "Xóa sản phẩm").click().run()
    assert sql(csdl, "SELECT COUNT(*) FROM SanPham WHERE ma = 'SP99'")[0][0] == 0


# ================================================================ UC03 – Nhập hàng và chốt lô (TC13–TC21)
def nhap_form(at, so_luong, han=None, gia=None):
    ctl(at, "number_input", "Số lượng nhập (kg)").set_value(so_luong)
    if han:
        at.date_input[1].set_value(han)
    if gia is not None:
        ctl(at, "number_input", "Giá nhập 1 kg (VNĐ), để 0 nếu chưa biết").set_value(gia)
    nut(at, "Lưu lô nhập").click().run()


def test_tc13_nhap_hang_hop_le_han_mac_dinh_1_nam(csdl):
    """TC13 | UC03 | Nhập 100 kg: tạo lô mới, còn lại = số nhập, hạn dùng mặc định 11/11/2027"""
    at = mo(menu="Nhập hàng và chốt lô")
    nhap_form(at, 100.0)
    lo = sql(csdl, "SELECT so_luong_nhap, so_luong_con_lai, han_dung, trang_thai, nguoi_nhap_id, gia_nhap "
                   "FROM NhapHang ORDER BY id DESC LIMIT 1")[0]
    assert lo == (100.0, 100.0, "2027-11-11", "dang_ban", 1, None)


@pytest.mark.parametrize("so_luong", [0.0, 0.7])
def test_tc14_nhap_so_luong_khong_hop_le(csdl, so_luong):
    """TC14 | UC03 | Số lượng nhập bằng 0 hoặc không phải bội số của 0,5 kg thì báo lỗi"""
    at = mo(menu="Nhập hàng và chốt lô")
    nhap_form(at, so_luong)
    assert any("bội số của 0,5 kg" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM NhapHang")[0][0] == 41


def test_tc15_han_dung_phai_sau_ngay_nhap(csdl):
    """TC15 | UC03 | Hạn dùng trùng hoặc trước ngày nhập thì báo lỗi"""
    at = mo(menu="Nhập hàng và chốt lô")
    nhap_form(at, 50.0, han=date(2026, 11, 11))
    assert any("Hạn dùng phải sau ngày nhập" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM NhapHang")[0][0] == 41


def test_tc16_nhan_vien_nhap_hang_khong_thay_gia_nhap(csdl):
    """TC16 | UC03 | Nhân viên nhập được hàng nhưng không thấy ô giá nhập và cột giá nhập; lô lưu giá trống"""
    at = mo("nv_lieu", menu="Nhập hàng và chốt lô")
    assert not [w for w in at.number_input if "Giá nhập" in w.label]
    assert "Giá nhập 1 kg" not in bang(at, 0).columns
    nhap_form(at, 20.0)
    lo = sql(csdl, "SELECT nguoi_nhap_id, gia_nhap FROM NhapHang ORDER BY id DESC LIMIT 1")[0]
    assert lo == (2, None)


def test_tc17_chu_nhap_hang_kem_gia_nhap_va_cap_nhat_sau(csdl):
    """TC17 | UC03 | Chủ cửa hàng nhập kèm giá nhập; lô nhân viên nhập chưa có giá thì cập nhật sau được"""
    at = mo(menu="Nhập hàng và chốt lô")
    nhap_form(at, 30.0, gia=145000)
    assert sql(csdl, "SELECT gia_nhap FROM NhapHang ORDER BY id DESC LIMIT 1")[0][0] == 145000
    lo_chua_gia = sql(csdl, "SELECT id FROM NhapHang WHERE gia_nhap IS NULL ORDER BY id LIMIT 1")[0][0]
    at = mo(menu="Nhập hàng và chốt lô")
    sb = ctl(at, "selectbox", key="gn_lo")
    sb.set_value(chon_option(sb, "nhập 2026-11-09"))
    ctl(at, "number_input", key="gn_gia").set_value(561000)
    nut(at, "Lưu giá nhập").click().run()
    assert sql(csdl, "SELECT gia_nhap FROM NhapHang WHERE id = ?", (lo_chua_gia,))[0][0] == 561000


def test_tc18_chot_lo_con_1kg_ghi_mau_thu_va_hao_hut(csdl):
    """TC18 | UC03 | Chốt lô còn 1 kg với 0,6 kg mẫu thử: hao hụt 0,4 kg, lô đóng, nhân viên chốt cũng được"""
    lo_id = sql(csdl, "SELECT id FROM NhapHang WHERE san_pham_id = ? AND so_luong_con_lai = 1.0", (sp_id(csdl, "SP08"),))[0][0]
    at = mo("nv_ha", menu="Nhập hàng và chốt lô")
    sb = ctl(at, "selectbox", key="chot_lo")
    sb.set_value(chon_option(sb, "Khô cá lóc đồng"))
    at.run()
    ctl(at, "number_input", key="chot_mau").set_value(0.6)
    nut(at, "Chốt lô").click().run()
    lo = sql(csdl, "SELECT trang_thai, mau_thu, hao_hut, ly_do_chot, so_luong_con_lai, nguoi_chot_id, ngay_chot "
                   "FROM NhapHang WHERE id = ?", (lo_id,))[0]
    assert lo == ("da_chot", 0.6, 0.4, "het_hang", 0.0, 3, "2026-11-11")


def test_tc19_mau_thu_lon_hon_so_con_lai_bi_chan(csdl):
    """TC19 | UC03 | Số kg mẫu thử lớn hơn số còn lại của lô thì báo lỗi, lô không đổi"""
    at = mo(menu="Nhập hàng và chốt lô")
    sb = ctl(at, "selectbox", key="chot_lo")
    sb.set_value(chon_option(sb, "Khô cá lóc đồng"))
    at.run()
    ctl(at, "number_input", key="chot_mau").set_value(1.5)
    nut(at, "Chốt lô").click().run()
    assert any("không được lớn hơn" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM NhapHang WHERE trang_thai = 'dang_ban' AND so_luong_con_lai = 1.0")[0][0] >= 1


def test_tc20_chot_lo_het_han_ghi_hang_bo(csdl):
    """TC20 | UC03 | Chốt lô đã hết hạn: toàn bộ 7 kg còn lại ghi là hàng bỏ, không có mẫu thử"""
    lo_id = sql(csdl, "SELECT id FROM NhapHang WHERE han_dung = '2026-11-05' AND trang_thai = 'dang_ban'")[0][0]
    at = mo(menu="Nhập hàng và chốt lô")
    sb = ctl(at, "selectbox", key="chot_lo")
    sb.set_value(chon_option(sb, "ĐÃ HẾT HẠN"))
    at.run()
    nut(at, "Chốt lô").click().run()
    lo = sql(csdl, "SELECT trang_thai, mau_thu, hao_hut, ly_do_chot, so_luong_con_lai FROM NhapHang WHERE id = ?", (lo_id,))[0]
    assert lo == ("da_chot", 0.0, 7.0, "het_han", 0.0)


def test_tc21_chi_lo_con_1kg_hoac_het_han_moi_duoc_chot():
    """TC21 | UC03 | Danh sách lô chờ chốt chỉ gồm lô còn <= 1 kg hoặc đã hết hạn, lô còn nhiều hàng không có"""
    at = mo(menu="Nhập hàng và chốt lô")
    ds = ctl(at, "selectbox", key="chot_lo").options
    assert len(ds) == 2
    assert any("Khô cá lóc đồng" in o for o in ds) and any("ĐÃ HẾT HẠN" in o for o in ds)


# ================================================================ UC04 – Lập hóa đơn (TC22–TC34)
def test_tc22_hoa_don_khach_le_khong_so_dien_thoai(csdl):
    """TC22 | UC04 | Khách không cho số điện thoại: ghi là Khách lẻ; 2,5 kg ba khía = 425.000 VNĐ; trừ kho 2,5 kg"""
    truoc = con_lai_tong(csdl, "SP01")
    at = mo("nv_lieu", menu="Lập hóa đơn")
    them_hang(at, "SP01", 2.5)
    assert at.metric[0].value == "425.000 VNĐ"
    luu_hoa_don(at)
    hd = hoa_don_cuoi(csdl)
    assert hd == (336, 1, "tai_quay", "tien_mat", 2, 425000, "hoan_thanh")
    assert con_lai_tong(csdl, "SP01") == pytest.approx(truoc - 2.5)
    assert any("Đã lưu hóa đơn số 336" in s.value for s in at.success)


def test_tc23_khach_si_mua_tu_10kg_giam_5_phan_tram(csdl):
    """TC23 | UC04 | Khách sỉ mua đúng 10 kg một loại: giảm 5% (ba khía: 10 x 170.000 x 0,95 = 1.615.000 VNĐ)"""
    at = mo(menu="Lập hóa đơn")
    chon_khach(at, "0918000002")
    them_hang(at, "SP01", 10.0)
    assert at.metric[0].value == "1.615.000 VNĐ"
    luu_hoa_don(at)
    ct = sql(csdl, "SELECT giam_gia, thanh_tien FROM ChiTietHoaDon WHERE hoa_don_id = 336")
    assert ct == [(5, 1615000)]


def test_tc24_khach_si_duoi_10kg_khong_giam(csdl):
    """TC24 | UC04 | Khách sỉ mua 9,5 kg: không giảm (9,5 x 170.000 = 1.615.000 VNĐ, giảm 0%)"""
    at = mo(menu="Lập hóa đơn")
    chon_khach(at, "0918000002")
    them_hang(at, "SP01", 9.5)
    luu_hoa_don(at)
    assert sql(csdl, "SELECT giam_gia, thanh_tien FROM ChiTietHoaDon WHERE hoa_don_id = 336") == [(0, 1615000)]


def test_tc25_khach_le_mua_10kg_khong_giam(csdl):
    """TC25 | UC04 | Khách lẻ mua 10 kg: không giảm 5% (chỉ khách sỉ trong danh sách mới được giảm)"""
    at = mo(menu="Lập hóa đơn")
    them_hang(at, "SP01", 10.0)
    assert at.metric[0].value == "1.700.000 VNĐ"
    luu_hoa_don(at)
    assert sql(csdl, "SELECT giam_gia, thanh_tien FROM ChiTietHoaDon WHERE hoa_don_id = 336") == [(0, 1700000)]


def test_tc26_so_kg_phai_la_boi_so_cua_0_5(csdl):
    """TC26 | UC04 | Nhập 1,3 kg bị chặn: chỉ bán theo bội số của 0,5 kg"""
    at = mo(menu="Lập hóa đơn")
    them_hang(at, "SP01", 1.3)
    assert any("bội số của 0,5 kg" in e for e in loi(at))
    assert len(at.dataframe) == 0


def test_tc27_khong_ban_qua_ton_va_kg_cuoi_lo_khong_ban():
    """TC27 | UC04 | Khô mực loại 3 tồn bán được 8 kg (lô còn 9 kg, 1 kg cuối giữ làm mẫu): 8,5 kg bị chặn, 8 kg được"""
    at = mo(menu="Lập hóa đơn")
    them_hang(at, "SP14", 8.5)
    assert any("chỉ còn 8 kg" in e for e in loi(at))
    them_hang(at, "SP14", 8.0)
    assert at.metric[0].value == "5.600.000 VNĐ"


def test_tc28_ban_theo_lo_gan_het_han_truoc(csdl):
    """TC28 | UC04 | Bán 35 kg khô cá sặc bổi: lấy 29 kg lô cũ (hạn 15/01/2027) rồi 6 kg lô mới; lô cũ còn 1 kg"""
    at = mo(menu="Lập hóa đơn")
    them_hang(at, "SP04", 35.0)
    luu_hoa_don(at)
    ct = sql(csdl, "SELECT nh.han_dung, ct.so_luong, ct.thanh_tien FROM ChiTietHoaDon ct "
                   "JOIN NhapHang nh ON nh.id = ct.nhap_hang_id WHERE ct.hoa_don_id = 336 ORDER BY nh.han_dung")
    assert ct == [("2027-01-15", 29.0, 10440000), ("2027-11-03", 6.0, 2160000)]
    assert sql(csdl, "SELECT so_luong_con_lai FROM NhapHang WHERE san_pham_id = 4 ORDER BY han_dung") == [(1.0,), (74.0,)]
    assert hoa_don_cuoi(csdl)[5] == 12600000


def test_tc29_khach_moi_co_so_dien_thoai_duoc_tao_ho_so(csdl):
    """TC29 | UC04 | Số điện thoại chưa có trong danh sách: nhập họ tên, hệ thống tạo hồ sơ khách lẻ mới"""
    at = mo(menu="Lập hóa đơn")
    chon_khach(at, "0903123456", "Lê Văn Thử")
    them_hang(at, "SP03", 1.0)
    luu_hoa_don(at)
    assert sql(csdl, "SELECT ho_ten, loai FROM KhachHang WHERE so_dien_thoai = '0903123456'") == [("Lê Văn Thử", "le")]
    assert hoa_don_cuoi(csdl)[1] == 23


def test_tc30_khach_cu_hien_nhan_khach_si_va_khach_moi():
    """TC30 | UC04 | Nhập số điện thoại khách có sẵn: hiện tên và nhãn (khách sỉ, khách mối)"""
    at = mo("nv_le", menu="Lập hóa đơn")
    chon_khach(at, "0918000002")
    assert any("Lê Thị Bích – Khách sỉ – Khách mối" in s.value for s in at.success)
    chon_khach(at, "0918000005")
    assert any("Phạm Văn Tuấn – Khách sỉ" in s.value and "mối" not in s.value for s in at.success)


@pytest.mark.parametrize("sdt", ["123", "09012345678", "abcdefghij"])
def test_tc31_so_dien_thoai_sai_dinh_dang(csdl, sdt):
    """TC31 | UC04 | Số điện thoại không đủ 10 chữ số hoặc không bắt đầu bằng 0 thì báo lỗi, không lưu được"""
    at = mo(menu="Lập hóa đơn")
    chon_khach(at, sdt)
    them_hang(at, "SP01", 1.0)
    luu_hoa_don(at)
    assert any("10 chữ số" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM HoaDon")[0][0] == 335


def test_tc32_hoa_don_trong_khong_luu_duoc(csdl):
    """TC32 | UC04 | Hóa đơn chưa có sản phẩm thì không lưu được"""
    at = mo(menu="Lập hóa đơn")
    luu_hoa_don(at)
    assert any("chưa có sản phẩm" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM HoaDon")[0][0] == 335


def test_tc33_don_online_can_so_dien_thoai_va_dia_chi(csdl):
    """TC33 | UC04 | Đơn online thiếu địa chỉ bị chặn; có đủ thì lưu kênh online, chuyển khoản, cập nhật địa chỉ khách"""
    at = mo("nv_ha", menu="Lập hóa đơn")
    chon_khach(at, "0918000003")
    them_hang(at, "SP02", 10.0)
    ctl(at, "selectbox", key="hd_kenh_0").set_value("Online").run()
    ctl(at, "selectbox", key="hd_tt_0").set_value("Chuyển khoản").run()
    luu_hoa_don(at)
    assert any("địa chỉ giao" in e for e in loi(at))
    ctl(at, "text_input", key="hd_dc_0").set_value("An Giang").run()
    luu_hoa_don(at)
    assert hoa_don_cuoi(csdl) == (336, 3, "online", "chuyen_khoan", 3, 2850000, "hoan_thanh")


def test_tc34_sau_khi_luu_hoa_don_moi_trong_sach(csdl):
    """TC34 | UC04 | Sau khi lưu, giỏ hàng và các ô nhập được xóa sạch để lập hóa đơn tiếp theo"""
    at = mo(menu="Lập hóa đơn")
    chon_khach(at, "0902000010")
    them_hang(at, "SP01", 1.0)
    luu_hoa_don(at)
    assert ctl(at, "text_input", key="hd_sdt_1").value == ""
    assert len(at.dataframe) == 0 and at.metric[0].value == "0 VNĐ"


def test_tc35_cong_thuc_thanh_tien_la_so_nguyen():
    """TC35 | UC04 | Thành tiền luôn là số nguyên đồng, kể cả khi giảm 5% ở mọi mặt hàng và mọi bội số 0,5 kg"""
    import pandas as pd
    gia = pd.read_sql_query("SELECT gia_ban FROM SanPham", sqlite3.connect(db.duong_dan()))["gia_ban"]
    for g in gia:
        for nua in range(1, 81):
            so = nua / 2
            for giam in (0, 5):
                tien = round(so * 2) * g // 2
                assert thanh_tien(so, g, giam) == pytest.approx(tien * (100 - giam) / 100)
                assert tien * (100 - giam) % 100 == 0


# ================================================================ UC05 – Tra cứu, tổng kết, hủy hóa đơn (TC36–TC44)
def dat_ngay(at, tu, den=None):
    ctl(at, "date_input", key="tc_tu").set_value(tu)
    ctl(at, "date_input", key="tc_den").set_value(den or date(2026, 11, 11))
    at.run()


def test_tc36_tra_cuu_theo_so_dien_thoai(csdl):
    """TC36 | UC05 | Tra cứu theo số điện thoại 0918000005: ra đúng 4 hóa đơn của khách đó"""
    at = mo(menu="Tra cứu hóa đơn")
    ctl(at, "date_input", key="tc_tu").set_value(date(2026, 1, 1))
    ctl(at, "text_input", key="tc_tim").set_value("0918000005").run()
    b = bang(at, 0)
    assert len(b) == 4 and set(b["Khách"]) == {"Phạm Văn Tuấn"}


def test_tc37_tra_cuu_khong_co_ket_qua():
    """TC37 | UC05 | Tra cứu không có hóa đơn nào khớp thì báo rõ"""
    at = mo(menu="Tra cứu hóa đơn")
    ctl(at, "text_input", key="tc_tim").set_value("không có khách này").run()
    assert any("Không có hóa đơn nào khớp" in i.value for i in at.info)


def test_tc38_nhan_vien_chi_thay_hoa_don_cua_minh(csdl):
    """TC38 | UC05 | Nhân viên chỉ thấy hóa đơn do mình lập (Thúy Liễu), không có ô chọn người lập"""
    at = mo("nv_lieu", menu="Tra cứu hóa đơn")
    ctl(at, "date_input", key="tc_tu").set_value(date(2026, 1, 1)).run()
    b = bang(at, 0)
    assert set(b["Người lập"]) == {"Thúy Liễu"}
    assert len(b) == sql(csdl, "SELECT COUNT(*) FROM HoaDon WHERE nguoi_lap_id = 2")[0][0]
    assert not [s for s in at.selectbox if s.key == "tc_nguoi"]


def test_tc39_tong_ket_ngay_tach_tien_mat_chuyen_khoan(csdl):
    """TC39 | UC05 | Tổng kết ngày 11/11/2026: tổng thu từng người lập, tách tiền mặt/chuyển khoản, khớp CSDL"""
    at = mo(menu="Tra cứu hóa đơn")
    b = bang(at, len(at.dataframe) - 1)
    tong = sql(csdl, "SELECT SUM(tong_tien) FROM HoaDon WHERE ngay_lap = '2026-11-11' AND trang_thai = 'hoan_thanh'")[0][0]
    cua_hang = b[b["Người lập"] == "Cả cửa hàng"].iloc[0]
    assert cua_hang["Tổng thu"] == vnd(tong)
    mat = sql(csdl, "SELECT SUM(tong_tien) FROM HoaDon WHERE ngay_lap = '2026-11-11' AND thanh_toan = 'tien_mat' "
                    "AND trang_thai = 'hoan_thanh'")[0][0]
    assert cua_hang["Tiền mặt"] == vnd(mat)


def test_tc40_tong_ket_ngay_nhan_vien_chi_thay_cua_minh(csdl):
    """TC40 | UC05 | Nhân viên xem tổng kết ngày chỉ thấy dòng của mình, không có dòng cả cửa hàng"""
    at = mo("nv_ha", menu="Tra cứu hóa đơn")
    b = bang(at, len(at.dataframe) - 1)
    assert list(b["Người lập"]) == ["Thu Hà"]
    tong = sql(csdl, "SELECT SUM(tong_tien) FROM HoaDon WHERE ngay_lap = '2026-11-11' AND nguoi_lap_id = 3 "
                     "AND trang_thai = 'hoan_thanh'")[0][0]
    assert b["Tổng thu"].iloc[0] == vnd(tong)


def hoa_don_huy_duoc(csdl):
    """Hóa đơn hoàn thành mà mọi lô đều chưa chốt (hủy được)."""
    return sql(csdl, "SELECT h.id, h.ngay_lap FROM HoaDon h WHERE h.trang_thai = 'hoan_thanh' AND NOT EXISTS "
                     "(SELECT 1 FROM ChiTietHoaDon ct JOIN NhapHang nh ON nh.id = ct.nhap_hang_id "
                     " WHERE ct.hoa_don_id = h.id AND nh.trang_thai = 'da_chot') ORDER BY h.id DESC LIMIT 1")[0]


def mo_hoa_don(at, hd_id, ngay):
    d = date.fromisoformat(ngay)
    dat_ngay(at, d, d)
    sb = ctl(at, "selectbox", key="tc_chon")
    sb.set_value(chon_option(sb, f"HĐ {hd_id} –"))
    at.run()


def test_tc41_chu_huy_hoa_don_hang_hoan_ve_lo(csdl):
    """TC41 | UC05 | Chủ cửa hàng hủy hóa đơn có lý do: phiếu chuyển 'đã hủy', hàng hoàn về đúng lô"""
    hd_id, ngay = hoa_don_huy_duoc(csdl)
    dong = sql(csdl, "SELECT nhap_hang_id, so_luong FROM ChiTietHoaDon WHERE hoa_don_id = ?", (hd_id,))
    truoc = {lo: sql(csdl, "SELECT so_luong_con_lai FROM NhapHang WHERE id = ?", (lo,))[0][0] for lo, _ in dong}
    at = mo(menu="Tra cứu hóa đơn")
    mo_hoa_don(at, hd_id, ngay)
    ctl(at, "text_area", key=f"tc_lydo_{hd_id}").set_value("Nhập sai số lượng").run()
    nut(at, key=f"tc_huy_{hd_id}").click().run()
    assert sql(csdl, "SELECT trang_thai, ly_do_huy, nguoi_huy_id FROM HoaDon WHERE id = ?", (hd_id,)) == \
        [("da_huy", "Nhập sai số lượng", 1)]
    for lo, so in dong:
        assert sql(csdl, "SELECT so_luong_con_lai FROM NhapHang WHERE id = ?", (lo,))[0][0] == pytest.approx(truoc[lo] + so)


def test_tc42_huy_hoa_don_phai_co_ly_do(csdl):
    """TC42 | UC05 | Hủy hóa đơn mà bỏ trống lý do thì báo lỗi, hóa đơn không đổi"""
    hd_id, ngay = hoa_don_huy_duoc(csdl)
    at = mo(menu="Tra cứu hóa đơn")
    mo_hoa_don(at, hd_id, ngay)
    nut(at, key=f"tc_huy_{hd_id}").click().run()
    assert any("Phải ghi lý do hủy" in e for e in loi(at))
    assert sql(csdl, "SELECT trang_thai FROM HoaDon WHERE id = ?", (hd_id,))[0][0] == "hoan_thanh"


def test_tc43_khong_huy_hoa_don_co_hang_tu_lo_da_chot(csdl):
    """TC43 | UC05 | Hóa đơn có hàng từ lô đã chốt thì không hủy được (không hoàn hàng về lô đã đóng)"""
    hd_id, ngay = sql(csdl, "SELECT h.id, h.ngay_lap FROM HoaDon h JOIN ChiTietHoaDon ct ON ct.hoa_don_id = h.id "
                            "JOIN NhapHang nh ON nh.id = ct.nhap_hang_id WHERE h.trang_thai = 'hoan_thanh' "
                            "AND nh.trang_thai = 'da_chot' ORDER BY h.id DESC LIMIT 1")[0]
    at = mo(menu="Tra cứu hóa đơn")
    mo_hoa_don(at, hd_id, ngay)
    ctl(at, "text_area", key=f"tc_lydo_{hd_id}").set_value("Thử hủy").run()
    nut(at, key=f"tc_huy_{hd_id}").click().run()
    assert any("lô đã chốt" in e for e in loi(at))
    assert sql(csdl, "SELECT trang_thai FROM HoaDon WHERE id = ?", (hd_id,))[0][0] == "hoan_thanh"


def test_tc44_nhan_vien_khong_huy_duoc_va_hoa_don_da_huy_hien_ly_do(csdl):
    """TC44 | UC05 | Nhân viên không có chức năng hủy; hóa đơn đã hủy hiện ngày hủy và lý do"""
    hd_id, ngay = hoa_don_huy_duoc(csdl)
    at = mo("nv_lieu", menu="Tra cứu hóa đơn")
    assert not [b for b in at.button if b.label == "Hủy hóa đơn"]
    huy_id, ngay_huy = sql(csdl, "SELECT id, ngay_lap FROM HoaDon WHERE trang_thai = 'da_huy' ORDER BY id LIMIT 1")[0]
    at = mo(menu="Tra cứu hóa đơn")
    mo_hoa_don(at, huy_id, ngay_huy)
    assert any("Đã hủy ngày" in i.value and "Lý do" in i.value for i in at.info)
    assert not [b for b in at.button if b.label == "Hủy hóa đơn"]


# ================================================================ UC06 – Thống kê (TC45–TC49)
def test_tc45_doanh_thu_theo_thang_khong_tinh_hoa_don_huy(csdl):
    """TC45 | UC06 | Doanh thu theo tháng khớp CSDL và không tính hóa đơn đã hủy (tháng 10 và 11 có hóa đơn hủy)"""
    at = mo(menu="Thống kê")
    b = bang(at, 0)
    assert len(b) == 12
    for thang in ("01", "10", "11"):
        tong = sql(csdl, "SELECT SUM(tong_tien) FROM HoaDon WHERE substr(ngay_lap, 1, 7) = ? AND trang_thai = 'hoan_thanh'",
                   (f"2026-{thang}",))[0][0]
        assert b[b["Tháng"] == f"T{thang}"]["Doanh thu"].iloc[0] == vnd(tong)
    assert b[b["Tháng"] == "T12"]["Doanh thu"].iloc[0] == "0 VNĐ"


def test_tc46_top_5_san_pham_ban_chay(csdl):
    """TC46 | UC06 | Top 5 sản phẩm bán chạy theo số kg, khớp CSDL"""
    at = mo(menu="Thống kê")
    b = bang(at, 1)
    cau = ("SELECT sp.ten, SUM(ct.so_luong) k FROM ChiTietHoaDon ct JOIN HoaDon h ON h.id = ct.hoa_don_id "
           "JOIN SanPham sp ON sp.id = ct.san_pham_id WHERE h.trang_thai = 'hoan_thanh' "
           "GROUP BY sp.id ORDER BY k DESC, sp.ten LIMIT 5")
    mong_doi = sql(csdl, cau)
    assert list(b["Sản phẩm"]) == [t for t, _ in mong_doi]
    assert list(b["Số kg đã bán"]) == [kg(k) for _, k in mong_doi]


def test_tc47_khach_moi_can_ca_hai_dieu_kien(csdl):
    """TC47 | UC06 | Khách mối: hơn 10 hóa đơn VÀ hơn 30 triệu. Khách đủ số đơn nhưng ít tiền, hoặc nhiều tiền ít đơn thì không phải"""
    at = mo(menu="Thống kê")
    ten = list(bang(at, 2)["Khách"])
    assert "Lê Thị Bích" in ten
    assert "Nguyễn Thị Mai" not in ten           # 11 hóa đơn nhưng chỉ khoảng 1,4 triệu
    assert "Phạm Văn Tuấn" not in ten            # gần 50 triệu nhưng chỉ 4 hóa đơn
    assert la_khach_moi(2) and not la_khach_moi(10) and not la_khach_moi(5) and not la_khach_moi(1)


def test_tc48_mau_thu_tich_luy_va_ty_le_hao_hut(csdl):
    """TC48 | UC06 | Mẫu thử tích lũy và tỷ lệ hao hụt theo sản phẩm khớp tổng trong CSDL"""
    at = mo(menu="Thống kê")
    b = bang(at, 3)
    mau = sql(csdl, "SELECT SUM(mau_thu) FROM NhapHang WHERE trang_thai = 'da_chot' AND ly_do_chot = 'het_hang' "
                    "AND substr(ngay_chot, 1, 4) = '2026'")[0][0]
    assert any(kg(mau) in m.value for m in at.metric)
    assert "Tỷ lệ hao hụt trên số nhập" in b.columns and len(b) >= 10


def test_tc49_nhan_vien_khong_vao_duoc_thong_ke_va_khach_hang():
    """TC49 | UC06 | Nhân viên không thấy menu Thống kê và Khách hàng (phân quyền)"""
    at = mo("nv_le")
    assert "Thống kê" not in at.sidebar.radio[0].options and "Khách hàng" not in at.sidebar.radio[0].options


# ================================================================ UC07 – Cảnh báo kho (TC50–TC54)
def test_tc50_san_pham_sap_het_hang_dung_ngay_20kg(csdl):
    """TC50 | UC07 | Sắp hết hàng khi tồn <= 20 kg: khô mực loại 1 (đúng 20 kg) và loại 3 (8 kg) có, loại 2 (20,5 kg) không"""
    at = mo("nv_lieu", menu="Cảnh báo kho")
    ten = list(bang(at, 0)["Sản phẩm"])
    assert "Khô mực câu loại 1" in ten and "Khô mực loại 3" in ten
    assert "Khô mực loại 2" not in ten


def test_tc51_lo_sap_het_han_dung_ngay_45():
    """TC51 | UC07 | Lô sắp hết hạn khi còn <= 45 ngày: lô hạn 26/12/2026 (45 ngày) có, lô hạn 27/12/2026 (46 ngày) không"""
    at = mo(menu="Cảnh báo kho")
    b = bang(at, 1)
    assert "Khô cá kèo" in list(b["Sản phẩm"])
    assert not (b["Hạn dùng"] == "2026-12-27").any()
    assert b[b["Sản phẩm"] == "Khô cá kèo"]["Số ngày còn lại"].iloc[0] == 45


def test_tc52_lo_da_het_han_duoc_liet_ke_va_khong_tinh_vao_ton():
    """TC52 | UC07 | Lô khô cá đù đã hết hạn 05/11/2026 (còn 7 kg) được liệt kê và không cộng vào tồn bán được"""
    at = mo(menu="Cảnh báo kho")
    b = bang(at, 2)
    assert list(b["Sản phẩm"]) == ["Khô cá đù"] and b["Còn lại"].iloc[0] == "7 kg"
    at = mo(menu="Sản phẩm")
    b = bang(at, 0)
    assert b[b["Tên"] == "Khô cá đù"]["Tồn bán được"].iloc[0] == "53 kg"      # chỉ tính lô còn hạn (54 kg - 1 kg cuối)


def test_tc53_lo_cho_chot_con_1kg():
    """TC53 | UC07 | Lô còn <= 1 kg (khô cá lóc đồng) được liệt kê ở mục lô chờ chốt; 1 kg cuối không tính vào tồn bán được"""
    at = mo(menu="Cảnh báo kho")
    b = bang(at, 3)
    assert "Khô cá lóc đồng" in list(b["Sản phẩm"])
    at = mo(menu="Sản phẩm")
    b = bang(at, 0)
    assert b[b["Tên"] == "Khô cá lóc đồng"]["Tồn bán được"].iloc[0] == "49 kg"


def test_tc54_chi_so_tong_hop_tren_dau_trang():
    """TC54 | UC07 | Bốn chỉ số tổng hợp ở đầu trang khớp với số dòng của bốn bảng bên dưới"""
    at = mo(menu="Cảnh báo kho")
    so = [int(m.value) for m in at.metric]
    assert so == [len(bang(at, i)) for i in range(4)]


# ================================================================ UC08 – Quản lý khách hàng (TC55–TC61)
def test_tc55_danh_sach_khach_nhan_khach_moi():
    """TC55 | UC08 | Danh sách 22 khách; chỉ khách đủ điều kiện được gắn nhãn khách mối"""
    at = mo(menu="Khách hàng")
    b = bang(at, 0)
    assert len(b) == 22
    assert b[b["Họ tên"] == "Lê Thị Bích"]["Khách mối"].iloc[0] == "Có"
    assert b[b["Họ tên"] == "Phạm Văn Tuấn"]["Khách mối"].iloc[0] == ""
    assert b[b["Họ tên"] == "Khách lẻ"]["Khách mối"].iloc[0] == ""


def test_tc56_them_khach_hop_le(csdl):
    """TC56 | UC08 | Thêm khách mới hợp lệ (khách sỉ ở Sóc Trăng)"""
    at = mo(menu="Khách hàng")
    ctl(at, "text_input", "Họ tên").input("Trương Thị Thanh")
    ctl(at, "text_input", "Số điện thoại").input("0903999888")
    ctl(at, "text_input", "Địa chỉ (tỉnh/thành)").input("Sóc Trăng")
    ctl(at, "selectbox", key="kh_loai_moi").set_value("Khách sỉ")
    nut(at, "Thêm khách").click().run()
    assert sql(csdl, "SELECT ho_ten, dia_chi, loai FROM KhachHang WHERE so_dien_thoai = '0903999888'") == \
        [("Trương Thị Thanh", "Sóc Trăng", "si")]


@pytest.mark.parametrize("sdt, thong_bao", [("0918000002", "đã có trong danh sách"), ("12345", "10 chữ số")])
def test_tc57_them_khach_trung_hoac_sai_so_dien_thoai(csdl, sdt, thong_bao):
    """TC57 | UC08 | Thêm khách bị chặn khi số điện thoại trùng hoặc sai định dạng"""
    at = mo(menu="Khách hàng")
    ctl(at, "text_input", "Họ tên").input("Người thử")
    ctl(at, "text_input", "Số điện thoại").input(sdt)
    nut(at, "Thêm khách").click().run()
    assert any(thong_bao in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM KhachHang")[0][0] == 22


def test_tc58_danh_dau_khach_si_theo_danh_sach_chi_hang(csdl):
    """TC58 | UC08 | Chủ cửa hàng đổi loại khách từ lẻ sang sỉ; khách đó mua 10 kg được giảm 5%"""
    at = mo(menu="Khách hàng")
    sb = ctl(at, "selectbox", key="kh_chon")
    sb.set_value(chon_option(sb, "0902000011"))
    at.run()
    ctl(at, "selectbox", key="kh_lo_11").set_value("Khách sỉ")
    nut(at, "Lưu thay đổi").click().run()
    assert sql(csdl, "SELECT loai FROM KhachHang WHERE id = 11")[0][0] == "si"
    at = mo("nv_lieu", menu="Lập hóa đơn")
    chon_khach(at, "0902000011")
    them_hang(at, "SP03", 10.0)
    luu_hoa_don(at)
    assert sql(csdl, "SELECT giam_gia FROM ChiTietHoaDon WHERE hoa_don_id = 336") == [(5,)]


def test_tc59_khach_le_dung_chung_khong_sua_khong_xoa():
    """TC59 | UC08 | 'Khách lẻ' dùng chung không nằm trong danh sách sửa/xóa"""
    at = mo(menu="Khách hàng")
    assert len(ctl(at, "selectbox", key="kh_chon").options) == 21
    assert not [o for o in ctl(at, "selectbox", key="kh_chon").options if o.startswith("Khách lẻ –")]


def test_tc60_xoa_khach_chua_mua_va_khong_xoa_khach_da_mua(csdl):
    """TC60 | UC08 | Khách chưa có hóa đơn xóa được; khách đã có hóa đơn thì không xóa được"""
    sql(csdl, "INSERT INTO KhachHang (ho_ten, so_dien_thoai, loai) VALUES ('Khách mới thử', '0903777666', 'le')")
    at = mo(menu="Khách hàng")
    sb = ctl(at, "selectbox", key="kh_chon")
    sb.set_value(chon_option(sb, "0903777666"))
    at.run()
    nut(at, "Xóa khách này").click().run()
    assert sql(csdl, "SELECT COUNT(*) FROM KhachHang WHERE so_dien_thoai = '0903777666'")[0][0] == 0
    at = mo(menu="Khách hàng")
    sb = ctl(at, "selectbox", key="kh_chon")
    sb.set_value(chon_option(sb, "0918000002"))
    at.run()
    nut(at, "Xóa khách này").click().run()
    assert any("không xóa được" in e for e in loi(at))
    assert sql(csdl, "SELECT COUNT(*) FROM KhachHang WHERE so_dien_thoai = '0918000002'")[0][0] == 1


def test_tc61_lich_su_mua_hang_cua_khach(csdl):
    """TC61 | UC08 | Xem lịch sử mua của khách: số dòng bằng số hóa đơn của khách trong CSDL"""
    at = mo(menu="Khách hàng")
    sb = ctl(at, "selectbox", key="kh_ls")
    sb.set_value(chon_option(sb, "0918000002"))
    at.run()
    b = bang(at, len(at.dataframe) - 1)
    assert len(b) == sql(csdl, "SELECT COUNT(*) FROM HoaDon WHERE khach_hang_id = 2")[0][0]
