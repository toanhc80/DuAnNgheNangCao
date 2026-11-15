"""UC01 – Đăng nhập: băm mật khẩu, kiểm tra tài khoản."""
import hashlib

from db import query


def hash_password(mat_khau):
    # Không bao giờ lưu mật khẩu gốc, chỉ lưu chuỗi băm SHA-256
    return hashlib.sha256(mat_khau.encode()).hexdigest()


def kiem_tra_dang_nhap(ten, mat_khau):
    """Trả về dict thông tin tài khoản nếu đúng, None nếu sai."""
    df = query("SELECT id, ten_dang_nhap, ho_ten, vai_tro FROM TaiKhoan "
               "WHERE ten_dang_nhap = ? AND mat_khau_hash = ?", (ten.strip(), hash_password(mat_khau)))
    if df.empty:
        return None
    return df.iloc[0].to_dict()
