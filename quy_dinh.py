"""Các quy định nghiệp vụ lấy từ chị Hằng, gom về một chỗ (mã QĐ khớp với báo cáo, mục 1.3)."""

BUOC_KG = 0.5            # QĐ2: chỉ bán theo bội số của 0,5 kg
NGUONG_SI = 10           # QĐ3: khách sỉ mua từ 10 kg một loại trong một hóa đơn thì được giảm
GIAM_SI = 5              # QĐ3: giảm 5% giá bán lẻ
KG_CUOI = 1              # QĐ7: 1 kg cuối của lô không bán, dành làm mẫu thử
NGUONG_TON = 20          # QĐ6: cảnh báo sắp hết hàng khi tồn <= 20 kg
HAN_CANH_BAO_NGAY = 45   # QĐ6: cảnh báo sắp hết hạn khi còn <= 45 ngày
HAN_DUNG_MAC_DINH = 365  # QĐ5: hạn dùng 1 năm
MOI_SO_HD = 10           # QĐ8: khách mối: hơn 10 hóa đơn trong năm ...
MOI_TONG_TIEN = 30_000_000   # ... và tổng mua hơn 30 triệu VNĐ (năm dương lịch)
