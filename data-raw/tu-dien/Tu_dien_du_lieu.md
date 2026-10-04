# Tu_dien_du_lieu — Từ điển dữ liệu v1

> Sao Việt Contact Center (hư cấu) · kỳ 07/09–20/09/2026. Tải file này vào **Project “Vận hành & Chấm công”** — custom instructions yêu cầu Claude dùng định nghĩa ở đây.


**Phiên bản:** v1 · Kỳ dữ liệu 07/09–20/09/2026 · Trạng thái: chờ duyệt.

**⬇️ Tải bản hoàn chỉnh:** [Tu_dien_du_lieu.md](/data/tu-dien/Tu_dien_du_lieu.md) (để tải vào Project) · [Tu_dien_du_lieu.xlsx](/data/tu-dien/Tu_dien_du_lieu.xlsx) (để sửa trong Excel). Nội dung đúng như các bảng dưới đây.

## 1. Call log — `call_log_2026-09.csv`

*Grain:* 1 cuộc gọi, hoặc 1 chặng chuyển tiếp (khi `ma_cuoc_goi_goc` có giá trị) · 29.515 dòng · Khóa chính: `ma_cuoc_goi` (phải duy nhất sau khi bỏ trùng) · Nguồn: tổng đài.

| Tên cột | Ý nghĩa | Kiểu | Nguồn | Quy tắc hợp lệ |
|---|---|---|---|---|
| `ma_cuoc_goi` | Mã định danh cuộc gọi/chặng | Chuỗi `CG` + 6 số | Tổng đài | Không trống; duy nhất; đúng mẫu `CG\d{6}` |
| `thoi_diem_bat_dau` | Thời điểm bắt đầu, giờ Việt Nam (UTC+7) | Ngày giờ `YYYY-MM-DD HH:MM:SS` | Tổng đài | Đúng 1 định dạng; dạng `…T…Z` là UTC → +7 giờ; nằm trong kỳ (kể cả rạng sáng ngày sau kỳ nếu thuộc ca D) |
| `huong` | Hướng gọi | `IN` / `OUT` | Tổng đài | Chỉ 2 giá trị; `OUT` ↔ hàng đợi OB-BAOHIEM, `IN` ↔ IB-CSKH |
| `ma_agent` | Mã tổng đài của agent xử lý | Chuỗi `EXT` + 4 số | Tổng đài | Viết hoa, không dấu cách; có trong bảng nối mã; **được trống khi ABANDONED**; trống khi đã ANSWERED là lỗi |
| `hang_doi` | Hàng đợi/chiến dịch | `OB-BAOHIEM` / `IB-CSKH` | Tổng đài | Khớp với `huong` và `du_an` |
| `du_an` | Mã dự án | `TS-BH` / `CS-VT` | Tổng đài | Có trong danh sách dự án |
| `ma_khach_hang` | Mã khách đã ẩn danh | Chuỗi `KH` + 5 số | Tổng đài (đã ẩn danh) | Không trống; **không** chứa số điện thoại/tên thật |
| `thoi_gian_cho_giay` | Thời gian chờ (đổ chuông ra / chờ trong hàng đợi vào) | Số nguyên, giây | Tổng đài | > 0; thực tế 3–240 |
| `thoi_gian_dam_thoai_giay` | Thời gian nói chuyện với khách | Số nguyên, giây | Tổng đài | 0–7.200; > 0 khi ANSWERED/CONNECTED; = 0 với các trạng thái khác; > 7.200 → treo line |
| `thoi_gian_giu_may_giay` | Thời gian giữ máy (hold) | Số nguyên, giây | Tổng đài | ≥ 0; thực tế 0–120; chỉ > 0 khi ANSWERED/CONNECTED |
| `thoi_gian_acw_giay` | Thời gian xử lý sau cuộc gọi (After Call Work) | Số nguyên, giây | Tổng đài | ≥ 0 (5 dòng âm là lỗi); thực tế tối đa 180 |
| `trang_thai_ket_noi` | Kết quả kết nối kỹ thuật | IN: `ANSWERED`/`ABANDONED`; OUT: `CONNECTED`/`NO_ANSWER`/`BUSY`/`FAILED` | Tổng đài | Giá trị thuộc đúng bộ của hướng gọi |
| `ghi_chu_ket_qua` | Kết quả nghiệp vụ agent gõ tay | Chuỗi tự do (48 giá trị) | Agent | Được trống khi NO_ANSWER/ABANDONED; sẽ chuẩn hóa thành mã 2 cấp ở buổi 2 |
| `ma_cuoc_goi_goc` | Mã cuộc ban đầu của chặng chuyển tiếp | Chuỗi hoặc trống | Tổng đài | Trống là bình thường; nếu có phải tồn tại trong `ma_cuoc_goi`, và cuộc gốc ghi chú “Chuyển tiếp” |

## 2. Trạng thái agent — `trang_thai_agent_2026-09.csv`

*Grain:* 1 sự kiện đổi trạng thái; trạng thái kéo dài đến sự kiện kế tiếp của cùng agent · 2.214 dòng · Khóa: (`ma_agent`, `thoi_diem`) · Nguồn: tổng đài.

| Tên cột | Ý nghĩa | Kiểu | Nguồn | Quy tắc hợp lệ |
|---|---|---|---|---|
| `ma_agent` | Mã tổng đài của agent | Chuỗi `EXT` + 4 số | Tổng đài | Viết hoa, không dấu cách, có trong bảng nối mã |
| `thoi_diem` | Thời điểm đổi trạng thái | Ngày giờ `YYYY-MM-DD HH:MM:SS` | Tổng đài | Đúng định dạng; tăng dần theo từng agent; nằm trong cửa sổ ca được xếp (ca D có LOGOUT sang ngày hôm sau) |
| `trang_thai` | Trạng thái mới | `LOGIN` / `READY` / `NOT_READY` / `LOGOUT` | Tổng đài | Mỗi ca: bắt đầu bằng LOGIN, kết thúc bằng LOGOUT; tổng LOGIN = tổng LOGOUT (215 = 215) |
| `ly_do` | Lý do không sẵn sàng | Họp đầu ca / Nghỉ giữa ca / Vệ sinh / Uống nước / Hỏi trưởng ca / Lỗi hệ thống / Việc riêng | Agent chọn | **Bắt buộc** khi NOT_READY (892/892 có); trống ở LOGIN/READY/LOGOUT là hợp lệ |

## 3. Chấm công — `cham_cong_2026-09.csv`

*Grain:* 1 lượt quẹt vân tay, **không phân vào/ra** · 449 dòng · Khóa: (`ma_nv`, `thoi_diem_quet`) · Nguồn: máy chấm công.

| Tên cột | Ý nghĩa | Kiểu | Nguồn | Quy tắc hợp lệ |
|---|---|---|---|---|
| `ma_nv` | Mã nhân viên HR | Chuỗi `NV` + 4 số | Máy chấm công | Có trong danh sách agent; không có dữ liệu trước ngày vào làm |
| `thoi_diem_quet` | Thời điểm quẹt | Ngày giờ `YYYY-MM-DD HH:MM:SS` | Máy chấm công | Đúng định dạng; 2 lượt cùng người cách nhau < 5 phút = quẹt đúp (lấy lượt đầu/cuối tùy vào/ra); vào/ra xác định bằng ghép lịch ca |
| `thiet_bi` | Mã máy chấm công | `MCC-01` / `MCC-02` | Máy chấm công | Thuộc danh mục thiết bị |

## 4. Bảng nối mã hoàn chỉnh

Số cuộc tính trên call log gốc (chưa bỏ trùng). “Trạng thái” = số sự kiện trong nhật ký trạng thái agent; “Quẹt” = số lượt trong file chấm công.

| Mã gốc trong dữ liệu | Mã chuẩn | Mã NV | Họ tên | Team | Dự án | Số cuộc | Trạng thái | Quẹt | Trạng thái nối | Bằng chứng / người xác nhận |
|---|---|---|---|---|---|---|---|---|---|---|
| EXT2001 | EXT2001 | NV0101 | Trần Minh Anh | TS-A | TS-BH | 2.398 | 120 | 26 | Khớp | Danh sách agent |
| EXT2002 | EXT2002 | NV0102 | Lê Thu Hà | TS-A | TS-BH | 2.437 | 122 | 24 | Khớp | Danh sách agent |
| EXT2003 | EXT2003 | NV0103 | Phạm Quốc Bảo | TS-A | TS-BH | 2.796 | 120 | 25 | Khớp | Danh sách agent |
| EXT2004 | EXT2004 | NV0104 | Hoàng Ngọc Lan | TS-A | TS-BH | 2.194 | 110 | 23 | Khớp | Danh sách agent |
| EXT2005 | EXT2005 | NV0105 | Vũ Đức Huy | TS-A | TS-BH | 1.976 | 120 | 26 | Khớp | Danh sách agent |
| ext2005 | EXT2005 | NV0105 | Vũ Đức Huy | TS-A | TS-BH | 409 | — | — | Khớp sau chuẩn hóa | Chữ thường ngày 08/09 & 15/09 → báo IT tổng đài |
| EXT2006 | EXT2006 | NV0106 | Đặng Phương Thảo | TS-B | TS-BH | 2.182 | 112 | 24 | Khớp | Danh sách agent |
| EXT2007 | EXT2007 | NV0107 | Bùi Gia Hân | TS-B | TS-BH | 2.012 | 110 | 23 | Khớp | Danh sách agent |
| EXT 2007 | EXT2007 | NV0107 | Bùi Gia Hân | TS-B | TS-BH | 183 | — | — | Khớp sau chuẩn hóa | Dấu cách ngày 09/09 → báo IT tổng đài |
| EXT2008 | EXT2008 | NV0108 | Đỗ Tuấn Kiệt | TS-B | TS-BH | 1.668 | 222 | 24 | Khớp | Danh sách agent (lưu ý: số sự kiện trạng thái gấp đôi người khác — buổi 3) |
| EXT2009 | EXT2009 | NV0109 | Ngô Hải Yến | TS-B | TS-BH | 2.245 | 120 | 26 | Khớp | Danh sách agent |
| EXT2010 | EXT2010 | NV0110 | Nguyễn Văn Long | TS-B | TS-BH | 2.159 | 110 | 24 | Khớp | Danh sách agent |
| EXT2011 | EXT2011 | NV0111 | Trần Khánh Linh | TS-B | TS-BH | 1.006 | 60 | 22 | Khớp | Danh sách agent (bán thời gian, ca PT) |
| EXT2012 | EXT2012 | NV0112 | Lê Thanh Tùng | CS-A | CS-VT | 727 | 126 | 24 | Khớp | Danh sách agent |
| EXT2013 | EXT2013 | NV0113 | Phạm Mai Chi | CS-A | CS-VT | 675 | 118 | 24 | Khớp | Danh sách agent |
| EXT2014 | EXT2014 | NV0114 | Hoàng Hoàng Nam | CS-A | CS-VT | 587 | 100 | 25 | Khớp | Danh sách agent |
| EXT2015 | EXT2015 | NV0115 | Vũ Bích Ngọc | CS-A | CS-VT | 667 | 120 | 24 | Khớp | Danh sách agent |
| EXT2016 | EXT2016 | NV0116 | Đặng Anh Thư | CS-A | CS-VT | 659 | 122 | 23 | Khớp | Danh sách agent |
| EXT2017 | EXT2017 | NV0117 | Bùi Trọng Nhân | CS-A | CS-VT | 709 | 120 | 25 | Khớp — **cần HR kiểm tra ngày vào làm** | HR ghi vào làm 27/09/2026 nhưng có dữ liệu từ 07/09 |
| EXT2018 | EXT2018 | NV0118 | Đỗ Diệu Linh | CS-A | CS-VT | 357 | 62 | 13 | Đề xuất → HR xác nhận | HR trống mã; EXT2018 xuất hiện từ 14/09 = ngày vào làm; cập nhật danh sách agent |
| EXT2019 | EXT2019 | NV0119 | Ngô Công Vinh | CS-A | CS-VT | 665 | 120 | 24 | Khớp | Danh sách agent |
| EXT2099 | EXT2099 | — | (thực tập sinh) | TS | TS-BH | 251 | 0 | 0 | Không có trong HR | Trưởng ca TS xác nhận; đề xuất: tính vào sản lượng dự án, **không** tính KPI cá nhân |
| (trống) | — | — | — | — | CS-VT | 553 | — | — | Không áp dụng | 539 ABANDONED hợp lệ; 14 ANSWERED → IT tổng đài |

Kiểm tra 100%: sau khi áp bảng này, mọi dòng có mã agent đều hoặc nối được sang mã NV, hoặc có quyết định xử lý (EXT2099). Tổng số cuộc trong bảng: 29.515.
