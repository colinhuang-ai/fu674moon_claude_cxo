# Quy tắc làm sạch call log — v1

> Sao Việt Contact Center (hư cấu). Nguồn: deck Buổi 2 (Lab 2.2, 2.4) + `tu-dien/Tu_dien_du_lieu.md`; hiện thực trong `src/lam_sach.py`.
> **Trạng thái:** bản nháp chờ duyệt · **Ngày hiệu lực:** ____ · **Người duyệt:** ____
> Đổi định nghĩa → nâng phiên bản (v2), ghi ngày và lý do. Không sửa tay trong Excel.

## Nguyên tắc

1. Không sửa file gốc. Kết quả ghi ra file mới (`du_lieu_sach_*.csv`).
2. Chỉ **QT-01** được LOẠI dòng (và dòng bị loại được giữ ở `dong_bi_loai_*.csv`). Các quy tắc khác chỉ gắn cờ hoặc sửa trên cột mới.
3. Ưu tiên gắn cờ hơn loại; không đoán giá trị thay thế.
4. Dòng sai mà chưa có quy tắc → `ma_qt` = `CHUA-CO-QT:<tên>` và liệt kê trong báo cáo; **không tự xử lý**.
5. Tổng kiểm tra: dòng gốc = dòng sạch + dòng loại; cuộc gốc = dòng sạch − chặng chuyển tiếp.

## Thứ tự áp dụng và bảng quy tắc

QT-02 phải chạy trước QT-07 và QT-10 (các quy tắc đó dùng giờ Việt Nam).

| Mã | Quy tắc | Điều kiện nhận diện | Hành động | Lý do | Chỉ số bị ảnh hưởng | Tháng 9 |
|---|---|---|---|---|---|---:|
| QT-01 | Trùng mã cuộc gọi | `ma_cuoc_goi` không trống và đã có ở dòng trước trong cùng file | **LOẠI**, giữ dòng đầu tiên | Xuất file 2 lần; đếm dòng sẽ dư | Mọi chỉ số | 63 |
| QT-02 | Giờ UTC | `thoi_diem_bat_dau` dạng `YYYY-MM-DDTHH:MM:SSZ` | +7 giờ → cột mới `thoi_diem_vn` | UTC lệch 7 tiếng, báo "ngoài giờ" giả | Sản lượng theo giờ/ngày, QT-07, QT-10 | 22 |
| QT-03 | Chặng chuyển tiếp | `ma_cuoc_goi_goc` khác trống | `la_chang_chuyen = 1`; không đếm sản lượng, vẫn tính AHT | Đếm 2 lần cùng một cuộc | Tổng cuộc, tỷ lệ nghe | 48 |
| QT-04 | Nghe/kết nối 0 giây | trạng thái ∈ {`ANSWERED`, `CONNECTED`} và `thoi_gian_dam_thoai_giay` = 0 | Gắn cờ, `tinh_aht = 0` | Có kết nối nhưng không nói chuyện | AHT, liên hệ được | 41 |
| QT-05 | Thời lượng âm | một trong 4 cột thời lượng < 0 | Sửa về 0 + gắn cờ | Lỗi xuất dữ liệu | AHT, phút | 5 |
| QT-06 | Treo line | `thoi_gian_dam_thoai_giay` > 7.200 | `co_treo_line = 1`, `tinh_aht = 0` | Line treo, không phải đàm thoại thật | AHT, phút đàm thoại | 7 |
| QT-07 | Qua nửa đêm / ca D | giờ < giờ kết thúc ca đêm (06:00, theo `danh_muc_ca.csv`) **hoặc** bắt đầu + chờ + đàm thoại + giữ máy qua 00:00 | Thêm cột `ngay_ca` = ngày bắt đầu ca | Ca D vắt 2 ngày, chẻ đôi năng suất | Năng suất ca D, đối soát công | 749 |
| QT-08 | Chuẩn hóa & nối mã agent | `ma_agent` ≠ dạng chuẩn (hoa, không dấu cách); nối `ref/bang_noi_ma.csv` | Sửa → `ma_agent_chuan`, nối `ma_nv`; gắn cờ nếu nối đề xuất hoặc ngoài danh sách | `ext2005`, `EXT 2007` làm mất sản lượng | Sản lượng theo agent | 1.197 |
| QT-09 | Trống mã agent | `ma_agent` trống | `ABANDONED` → hợp lệ; còn lại gắn cờ | Khách bỏ máy khi chờ chưa có agent | AHT, sản lượng theo agent | 551 |
| QT-10 | Outbound ngoài giờ | `huong = OUT` và ngoài `gio_hoat_dong` của dự án (`danh_sach_du_an.csv`: TS-BH 08:00–21:00, T2–T7) | Gắn cờ, báo trưởng ca | Tuân thủ giờ gọi | Tuân thủ | 24 |

Một dòng có thể bị nhiều quy tắc tác động; cột `ma_qt` ghi đủ, ngăn bằng `;`. Mã con: `QT-08:DINH_DANG` (590),
`QT-08:NOI_DE_XUAT` (357, EXT2018 → NV0118 chờ HR), `QT-08:NGOAI_DS` (250, EXT2099), `QT-09:HOP_LE` (537), `QT-09:GAN_CO` (14).

## Cột sinh ra

| Cột | Ý nghĩa |
|---|---|
| `thoi_diem_vn`, `ngay`, `gio` | Giờ Việt Nam (sau QT-02), ngày, giờ 0–23 |
| `ngay_ca` | Ngày bắt đầu ca (QT-07). Ca D sau 00:00 thuộc ngày hôm trước |
| `ma_agent_chuan`, `ma_nv` | Mã tổng đài chuẩn hóa; mã nhân viên HR (trống nếu ngoài danh sách) |
| `cap1`, `cap2` | Mã kết quả 2 cấp. `cap1` theo `trang_thai_ket_noi` (xem `lam_sach_config.json`), `cap2` theo `Mapping_ma_ket_qua_v1.csv` |
| `dam_thoai`, `giu_may`, `acw`, `cho` | Thời lượng giây sau QT-05 |
| `la_chang_chuyen`, `co_treo_line` | Cờ QT-03, QT-06 |
| `tinh_aht` | 1 nếu ANSWERED/CONNECTED, có agent, đàm thoại > 0 và ≤ 7.200 |
| `ma_qt` | Các quy tắc đã tác động |

AHT = (`dam_thoai` + `giu_may` + `acw`) / số dòng có `tinh_aht = 1`.

## Kiểm tra theo Từ điển dữ liệu (ngoài QT-01…QT-10)

Không có quy tắc xử lý → chỉ báo cáo, gắn `CHUA-CO-QT:<tên>`: `ma_cuoc_goi_sai_mau`, `thoi_diem_sai_dinh_dang`,
`huong_la`, `huong_hang_doi_du_an_khong_khop`, `du_an_la`, `trang_thai_khong_thuoc_huong`, `ma_khach_hang_sai_mau`,
`thoi_luong_khong_phai_so_nguyen`, `thoi_gian_cho_bang_0`, `dam_giu_khi_khong_ket_noi`, `ma_agent_la`, `ghi_chu_chua_co_mapping`.

## Điểm cần duyệt

1. **QT-07:** mọi cuộc lúc 00:00–05:59 gán `ngay_ca` = ngày hôm trước (738 dòng đổi ngày). Deck Buổi 2 chỉ nêu "11 cuộc vắt 0h · 78 cuộc ngày 21/09" — hai nhóm này nằm trong 738 dòng.
2. **QT-04:** 28 cuộc OUT kết nối 0 giây vẫn có `cap1 = Liên hệ được`. Số "11.481 liên hệ được" của deck đã trừ nhóm này; muốn khớp phải loại dòng có `QT-04` khi đếm.
3. **Mapping v1:** dựng lại từ số liệu deck (tổng 12 mã cấp 2 khớp), chưa đối chiếu với file Mapping lưu trong Project. `cap1` cho inbound ("Được nghe", "Bỏ máy") do tool tự đặt.
4. **EXT2018 → NV0118:** đề xuất chờ HR. Khi HR xác nhận, đổi `trang_thai_noi` thành `Khớp` trong `ref/bang_noi_ma.csv`.

## Tổng kiểm tra tháng 9

29.515 = 29.452 + 63 · cuộc gốc = 29.452 − 48 = 29.404 (TS-BH 23.866 · CS-VT 5.538). Tổng đài đếm theo mã duy nhất nên chênh +48 ở CS-VT chính là 48 chặng chuyển tiếp.
