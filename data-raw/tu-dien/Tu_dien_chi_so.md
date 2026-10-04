# Tu_dien_chi_so — Từ điển chỉ số v1

> Sao Việt Contact Center (hư cấu). Tải file này vào **Project “Vận hành & Chấm công”** — custom instructions yêu cầu Claude dùng định nghĩa ở đây. Công thức chi tiết từng chỉ số: Phụ lục A của ebook.


**⬇️ Tải bản hoàn chỉnh:** [Tu_dien_chi_so.md](/data/tu-dien/Tu_dien_chi_so.md) (để tải vào Project) · [Tu_dien_chi_so.xlsx](/data/tu-dien/Tu_dien_chi_so.xlsx) (để sửa trong Excel).

“Giờ công” = **giờ có mặt** (máy chấm công, lượt đầu/cuối, trừ nghỉ giữa ca). Ngày công gán theo ngày bắt đầu ca. Mọi tỷ lệ nhóm = Σ tử số / Σ mẫu số.

| # | Chỉ số | Công thức (tử / mẫu) | Nguồn | Phạm vi | Chiều | Mục tiêu | Vàng | Đỏ | Chịu trách nhiệm |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Tổng cuộc gọi | Số cuộc gốc sau làm sạch (bỏ trùng, không cộng chặng chuyển tiếp) | Call log | Cả hai | — | — | — | — | Trưởng vận hành |
| 2 | Tỷ lệ nghe máy | Cuộc ANSWERED / cuộc vào hàng đợi | Call log | CS-VT | Cao tốt | ≥ 90% | 85 – < 90% | < 85% | Trưởng vận hành |
| 3 | Cuộc / giờ công | Cuộc do agent xử lý / giờ có mặt | Call log + bảng công | TS-BH | Trong khoảng | 21 – 27 | 18 – < 21 hoặc > 27 | < 18 | Trưởng ca |
| 4 | Cuộc / giờ công | như trên | như trên | CS-VT | Cao tốt | ≥ 6,5 | 5,5 – < 6,5 | < 5,5 | Trưởng ca |
| 5 | Cuộc thành công / giờ công | Cuộc mã “Thành công” của agent có giờ công / giờ có mặt | Call log (mã chuẩn) + bảng công | TS-BH | Cao tốt | 1,3 (xanh ≥ 1,1) | 0,8 – < 1,1 | < 0,8 (hợp đồng tối thiểu 0,6) | Trưởng ca |
| 6 | Tỷ lệ chốt | Cuộc “Thành công” / cuộc “Liên hệ được” | Call log (mã chuẩn) | TS-BH | Cao tốt | 11% (xanh ≥ 10%) | 7 – < 10% | < 7% | Trưởng ca |
| 7 | AHT | (Đàm thoại + giữ máy + ACW) / số cuộc xử lý; bỏ treo line > 7.200 s, 0 giây, trống agent | Call log | TS-BH | Trong khoảng | 170 – 220 s | 150 – < 170 hoặc > 220 – 260 s | < 150 hoặc > 260 s | Trưởng ca |
| 8 | AHT | như trên | Call log | CS-VT | Thấp tốt (có sàn) | ≤ 360 s | > 360 – 420 s | > 420 s | Trưởng ca |
| 9 | Tỷ lệ đăng nhập | Giờ đăng nhập / giờ có mặt (cùng tập ngày) | Trạng thái + bảng công | Cả hai | Cao tốt | ≥ 95% | 90 – < 95% | < 90%; > 100% → ⚪ kiểm tra dữ liệu | Trưởng ca + HR |
| 10 | Tỷ lệ sản xuất | Giờ sản xuất (đàm thoại + giữ máy + ACW) / giờ có mặt | Call log + bảng công | TS-BH | Cao tốt | ≥ 57% | 50 – < 57% | < 50% | Trưởng vận hành |
| 11 | Tỷ lệ sản xuất | như trên | như trên | CS-VT | Cao tốt | ≥ 60% | 55 – < 60% | < 55% | Trưởng vận hành |
| 12 | Occupancy | Giờ sản xuất / giờ READY (chỉ sự kiện trong phiên LOGIN → LOGOUT) | Trạng thái + call log | TS-BH | Trong khoảng | 60 – 80% | 55 – 60% hoặc 80 – 88% | < 55% hoặc > 88% | Trưởng vận hành (xếp ca) |
| 13 | Occupancy | như trên | như trên | CS-VT | Trong khoảng | 75 – 85% | 65 – 75% hoặc 85 – 90% | < 65% hoặc > 90% | Trưởng vận hành (xếp ca) |
| 14 | Shrinkage | (Giờ trả lương theo lịch − giờ READY) / giờ trả lương theo lịch | Lịch ca + trạng thái | Team | Thấp tốt | ≤ 12% (kỳ 2 tuần) | 12 – 20% | > 20%; < 0 → ⚪ làm vượt lịch | Trưởng vận hành |
| 15 | Adherence v1 | (Phút đăng nhập trong khung ca − phút NOT_READY “Việc riêng”) / phút khung ca; bỏ ngày phép đã duyệt | Lịch ca + trạng thái + đơn phép | Cả hai | Cao tốt | ≥ 95% | 90 – < 95% | < 90% | Trưởng ca |
| 16 | Đi muộn | Số ca vào muộn ≥ 5' / người / kỳ | Bảng công + lịch ca | Cả hai | Thấp tốt | 0 | 1 – 3 lần | > 3 lần (Điều 6.1) | HR |
| 17 | Vắng không phép | Số ca không chấm công, không đăng nhập, không có đơn | Bảng công + đơn phép | Cả hai | Thấp tốt | 0 | Đơn chờ duyệt | ≥ 1 | HR |
| 18 | Giờ OT | Giờ làm ngoài ca có đơn đã duyệt; tách “chờ duyệt” và “không đăng ký” | Bảng công + đơn OT | Cả hai | — | — | Chờ duyệt | Ở lại ≥ 30' không có đơn | HR |
| 19 | Chênh lệch công (A) | Giờ có mặt − giờ đăng nhập, theo ca | Bảng công | Cả hai | Thấp tốt | ≤ 30' | 30 – 60' | > 60' | HR + Trưởng ca |
| 20 | Giờ công lãng phí | Σ theo ca max(0; có mặt − đăng nhập − 15'); quy ra tiền × chi phí giờ bình quân (HR xác nhận) | Bảng công | Team / công ty | Thấp tốt | ≤ 2 giờ/team/tuần | 2 – 5 | > 5 | Trưởng vận hành |

**Quy tắc chung v1:** (1) tỷ lệ > 100% không tô màu, gắn ⚪ “kiểm tra dữ liệu”; (2) tỷ lệ nhóm = cộng tử rồi chia tổng mẫu; (3) không so sánh chéo TS-BH với CS-VT; (4) người có cờ dữ liệu hoặc < 8 ca không xếp hạng; (5) phiên bản ghi “v1 – ngày”, đổi định nghĩa phải nâng phiên bản và ghi lý do.
