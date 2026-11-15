# Nhật ký dùng AI – Nhóm 1 (Nguyễn Thị Hồng Thắm, Huỳnh Công Toàn)

> Bảng dưới ghi lại các việc đã nhờ AI (Claude) và những chỗ AI đã hiểu sai rồi được chị Hằng hoặc nhóm sửa lại theo đúng thực tế cửa hàng.

| Ngày | Người dùng | Use case | Nhờ AI làm gì | AI sai ở đâu / mình đã sửa gì | Học được gì |
|---|---|---|---|---|---|
| 05/11/2026 | Thắm | Chương 1 | Rà soát báo cáo, soạn bộ câu hỏi phỏng vấn chị Hằng | AI giả định "chỉ chủ cửa hàng nhập hàng". Chị Hằng cho biết người trực quầy nhập hàng. Đã sửa phân quyền UC03 | Không giả định nghiệp vụ, phải hỏi người dùng thật |
| 06/11/2026 | Thắm | UC03 | Đề xuất cách tính hao hụt | AI đề xuất trừ hao hụt cố định 1%. Nhóm đề xuất ghi hao hụt thật khi chốt lô và chị Hằng đồng ý. Đã đổi sang chốt lô | Quy tắc sát thực tế quan trọng hơn quy tắc đơn giản |
| 07/11/2026 | Toàn | UC03, UC08 | Hiểu "mẫu thử" và "khách mối" | AI hiểu mẫu thử là tặng ngay lúc bán. Chị Hằng đính chính: khách lẻ mua nhiều vào danh sách khách mối, cuối năm tặng combo mẫu thử. Đã đổi cách tính khách mối và thêm bảng mẫu thử tích lũy | Hỏi lại khi câu trả lời có thể hiểu hai cách |
| 08/11/2026 | Toàn | UC04 | Hiểu đơn vị bán | AI cho phép nhập số kg tự do (ví dụ 1,3 kg). Chị Hằng cho biết chỉ bán bội số 0,5 kg. Đã thêm kiểm tra bội số 0,5 | Hỏi người dùng về đơn vị và bước tăng |
| 09/11/2026 | Thắm, Toàn | Toàn bộ | Viết schema, dữ liệu mẫu, mã ứng dụng 8 use case | AI ban đầu tạo cột tồn kho riêng trong bảng SanPham. Nhóm sửa lại: tính tồn động từ các lô đang bán còn hạn (trừ 1 kg mẫu thử), không lưu dư thừa | Thiết kế CSDL chuẩn hóa, tránh lưu dữ liệu dư thừa dễ gây bất nhất khi có nhiều giao dịch |
| 10/11/2026 | Thắm, Toàn | Toàn bộ | Viết 61 test case (67 mục pytest) | Test TC56 chọn nhầm ô cùng nhãn "Loại khách" (lỗi L01 trong file test case). Đã đặt key riêng | Nhãn trùng nhau giữa các tab dễ làm test chọn nhầm |
| 11/11/2026 | Thắm, Toàn | Chương 2, 3 | Vẽ BFD, Use Case, 8 sơ đồ hoạt động, 8 sơ đồ tuần tự, ERD, 8 mockup | Sơ đồ hoạt động Lập hóa đơn ban đầu quá dài, chữ nhỏ. Đã chia thành 3 bước xếp ngang (lỗi L03) | Kiểm tra sơ đồ khi in ra khổ A4 |
| 12/11/2026 | Thắm, Toàn | Báo cáo | Soạn báo cáo Word theo mẫu | AI căn chỉnh lề và bảng chưa đúng quy chuẩn A4 của trường, ngắt trang bị lỗi ở các bảng dài. Nhóm đã điều chỉnh kiểu bảng và cố định bố cục | Kỹ năng định dạng tài liệu học thuật và quản lý bố cục văn bản chuyên nghiệp |
