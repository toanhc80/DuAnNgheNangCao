# Quản lý cửa hàng đặc sản khô Hằng Trần (Cà Mau)

Dự án nghề nâng cao – Đề 2. Nhóm 1: Nguyễn Thị Hồng Thắm (26310501012), Huỳnh Công Toàn (26310501011). GVHD: ThS Lê Thanh Thoại.

Phần mềm thay cho sổ phiếu tính tiền và Excel: bán hàng theo kg, quản lý kho theo lô nhập (hạn dùng, hao hụt, mẫu thử), phân biệt khách lẻ, khách sỉ, khách mối, cảnh báo kho và thống kê. Tiền tính bằng VNĐ.

**Link ứng dụng:** https://cuahang-hangtran.streamlit.app  **Link GitHub:** https://github.com/hongtham-danc/cuahang-hangtran

## Chạy trên máy

```
pip install -r requirements.txt
streamlit run app.py
```

Lần chạy đầu tiên, ứng dụng tự tạo `database/cuahang.db` từ `schema.sql` và `seed.sql`. Muốn tạo lại từ đầu (xóa dữ liệu đang có): `python init_db.py`.

Tài khoản mẫu (mật khẩu `123456`): `chu_hang` (chủ cửa hàng), `nv_lieu`, `nv_ha`, `nv_le` (nhân viên bán hàng).

Dữ liệu mẫu là dữ liệu giả định: 20 sản phẩm theo bảng giá thật, khách hàng, lô nhập và hóa đơn là dữ liệu giả (ngày tham chiếu 11/11/2026).

## Kiểm thử

```
pip install pytest
pytest -v
```

61 test case (67 mục pytest), mỗi test chạy trên một bản CSDL mới và ngày cố định 11/11/2026. Bảng test case: `docs/TestCase_CuaHangHangTran.xlsx`.

## Cấu trúc và phân công

| File | Nội dung | Người làm |
|---|---|---|
| `app.py`, `auth.py` | UC01 Đăng nhập, menu theo vai trò | Thắm |
| `views/san_pham.py` | UC02 Quản lý sản phẩm | Thắm |
| `views/nhap_hang.py` | UC03 Nhập hàng và chốt lô | Thắm |
| `views/canh_bao.py` | UC07 Xem cảnh báo kho | Thắm |
| `views/lap_hoa_don.py` | UC04 Lập hóa đơn | Toàn |
| `views/tra_cuu.py` | UC05 Tra cứu, tổng kết ngày, hủy hóa đơn | Toàn |
| `views/thong_ke.py` | UC06 Thống kê | Toàn |
| `views/khach_hang.py` | UC08 Quản lý khách hàng | Toàn |
| `db.py`, `ui.py`, `kho.py`, `quy_dinh.py` | Dùng chung: CSDL, giao diện, tính tồn theo lô, các quy định QĐ1–QĐ10 | Cả nhóm |
| `database/schema.sql`, `database/seed.sql` | CSDL và dữ liệu mẫu | Cả nhóm |

Các con số quy định (10 kg, 5%, 20 kg, 45 ngày, 30 triệu…) nằm hết trong `quy_dinh.py`.

## Đưa lên Streamlit Community Cloud

1. Đẩy toàn bộ thư mục này lên một repo GitHub.
2. Vào share.streamlit.io, chọn repo, nhánh `main`, file chạy `app.py`.
3. Bản miễn phí không giữ dữ liệu lâu dài: mỗi lần ứng dụng khởi động lại, CSDL được tạo lại từ `seed.sql`. Khi dùng thật tại cửa hàng cần chạy trên máy của cửa hàng và sao lưu `database/cuahang.db` hằng ngày.
