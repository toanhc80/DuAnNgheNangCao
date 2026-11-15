-- CSDL Cửa hàng đặc sản khô Hằng Trần (Cà Mau)
-- Tiền: số nguyên, đơn vị VNĐ. Khối lượng: kg (khi bán là bội số của 0,5).
PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS ChiTietHoaDon;
DROP TABLE IF EXISTS HoaDon;
DROP TABLE IF EXISTS NhapHang;
DROP TABLE IF EXISTS SanPham;
DROP TABLE IF EXISTS KhachHang;
DROP TABLE IF EXISTS TaiKhoan;

-- Người dùng phần mềm: chủ cửa hàng (chị Hằng) và 3 nhân viên bán hàng
CREATE TABLE TaiKhoan (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ten_dang_nhap  TEXT    NOT NULL UNIQUE,
    mat_khau_hash  TEXT    NOT NULL,
    ho_ten         TEXT    NOT NULL,
    vai_tro        TEXT    NOT NULL CHECK (vai_tro IN ('chu_cua_hang', 'nhan_vien'))
);

-- Khách hàng. Dòng id = 1 là "Khách lẻ" dùng chung cho khách không cho số điện thoại.
CREATE TABLE KhachHang (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ho_ten         TEXT    NOT NULL,
    so_dien_thoai  TEXT    UNIQUE,                 -- NULL chỉ dành cho "Khách lẻ" dùng chung
    dia_chi        TEXT,                           -- tỉnh/thành, cần cho đơn gửi xe đi tỉnh
    loai           TEXT    NOT NULL DEFAULT 'le' CHECK (loai IN ('le', 'si'))   -- khách sỉ theo danh sách chị Hằng
);

-- 20 mặt hàng. Giá bán tính theo 1 kg, là bội số của 1.000 VNĐ (QĐ1)
CREATE TABLE SanPham (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ma       TEXT    NOT NULL UNIQUE,
    ten      TEXT    NOT NULL,
    nhom     TEXT    NOT NULL,                      -- Ba khía, Mắm, Khô cá, Tôm khô, Khô mực
    gia_ban  INTEGER NOT NULL CHECK (gia_ban > 0 AND gia_ban % 1000 = 0)
);

-- Mỗi dòng là một lô nhập. Tồn kho của sản phẩm = tổng các lô còn bán được (không có cột tồn riêng)
CREATE TABLE NhapHang (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    san_pham_id      INTEGER NOT NULL REFERENCES SanPham(id),
    ngay_nhap        TEXT    NOT NULL,              -- 'YYYY-MM-DD'
    han_dung         TEXT    NOT NULL,
    so_luong_nhap    REAL    NOT NULL CHECK (so_luong_nhap > 0),
    so_luong_con_lai REAL    NOT NULL CHECK (so_luong_con_lai >= 0),
    gia_nhap         INTEGER CHECK (gia_nhap IS NULL OR gia_nhap > 0),   -- VNĐ/kg, chỉ chủ cửa hàng điền và xem
    trang_thai       TEXT    NOT NULL DEFAULT 'dang_ban' CHECK (trang_thai IN ('dang_ban', 'da_chot')),
    mau_thu          REAL,                          -- kg làm mẫu thử khi chốt lô
    hao_hut          REAL,                          -- kg hao hụt (hoặc hàng bỏ) khi chốt lô
    ly_do_chot       TEXT    CHECK (ly_do_chot IS NULL OR ly_do_chot IN ('het_hang', 'het_han')),
    ngay_chot        TEXT,
    nguoi_nhap_id    INTEGER NOT NULL REFERENCES TaiKhoan(id),
    nguoi_chot_id    INTEGER REFERENCES TaiKhoan(id),
    ghi_chu          TEXT
);

CREATE TABLE HoaDon (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ngay_lap       TEXT    NOT NULL,                -- 'YYYY-MM-DD'
    khach_hang_id  INTEGER NOT NULL REFERENCES KhachHang(id),
    kenh           TEXT    NOT NULL CHECK (kenh IN ('tai_quay', 'online')),
    thanh_toan     TEXT    NOT NULL CHECK (thanh_toan IN ('tien_mat', 'chuyen_khoan')),
    nguoi_lap_id   INTEGER NOT NULL REFERENCES TaiKhoan(id),
    tong_tien      INTEGER NOT NULL CHECK (tong_tien >= 0),
    trang_thai     TEXT    NOT NULL DEFAULT 'hoan_thanh' CHECK (trang_thai IN ('hoan_thanh', 'da_huy')),
    ly_do_huy      TEXT,
    nguoi_huy_id   INTEGER REFERENCES TaiKhoan(id),
    ngay_huy       TEXT
);

-- Mỗi dòng là một phần của hóa đơn lấy từ MỘT lô (bán theo lô gần hết hạn trước)
CREATE TABLE ChiTietHoaDon (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hoa_don_id    INTEGER NOT NULL REFERENCES HoaDon(id),
    san_pham_id   INTEGER NOT NULL REFERENCES SanPham(id),
    nhap_hang_id  INTEGER NOT NULL REFERENCES NhapHang(id),
    so_luong      REAL    NOT NULL CHECK (so_luong > 0),
    don_gia       INTEGER NOT NULL CHECK (don_gia > 0),      -- giá 1 kg tại thời điểm bán
    giam_gia      INTEGER NOT NULL DEFAULT 0 CHECK (giam_gia IN (0, 5)),   -- phần trăm
    thanh_tien    INTEGER NOT NULL CHECK (thanh_tien >= 0)
);
