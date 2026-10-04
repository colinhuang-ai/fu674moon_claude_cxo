# sanluong-auto

Tự động làm sạch call log hằng ngày cho Sao Việt Contact Center (dữ liệu hư cấu, 2 dự án: TS-BH outbound, CS-VT inbound).
Đầu ra là `du_lieu_sach_<ngày>.csv` + báo cáo số dòng theo từng mã quy tắc (QT-01…QT-10) + tổng kiểm tra.

## Cấu trúc

- `rules/` — nguồn sự thật của quy tắc: `Quy_tac_lam_sach_call_log_v1.md` (văn bản), `Mapping_ma_ket_qua_v1.csv` (ghi chú → mã cấp 2), `lam_sach_config.json` (tham số, đường dẫn tham chiếu)
- `ref/` — bảng tham chiếu: `bang_noi_ma.csv` (ma_tong_dai → ma_nv, có EXT2018 → NV0118), `danh_sach_du_an.csv` (giờ hoạt động), `danh_muc_ca.csv` (ca D qua đêm)
- `data/` — dữ liệu thật/mẫu, **không commit, không sửa**. `call_log_theo_ngay/call_log_<YYYY-MM-DD>.csv`, `bao_cao_tong_dai_2026-09.csv`
- `output/` — kết quả, **không commit**
- `src/lam_sach.py` — áp QT-01…QT-10 + mapping; `src/chay_hang_ngay.py` — điểm vào (chọn ngày, gọi lam_sach, ghi log)
- `tests/` — kiểm tra số liệu trên ngày mẫu đã biết đáp án
- `.env` — `DATA_DIR`, `OUTPUT_DIR` (không commit; mẫu ở `.env.example`)

## Lệnh (chạy từ thư mục `sanluong-auto/`)

```
python src/chay_hang_ngay.py 2026-09-14                  # 1 ngày (không tham số = hôm qua)
python src/lam_sach.py "data/call_log_theo_ngay/*.csv"   # nhiều file
python -m unittest discover -s tests -v                  # test
```

## Quy ước bắt buộc

- Chỉ dùng quy tắc trong `rules/`. Không tự thêm quy tắc, không đoán giá trị thay thế. Gặp trường hợp chưa có quy tắc → để `CHUA-CO-QT:<tên>` và báo người dùng, không tự xử lý.
- Không sửa `data/` và không sửa file gốc. Mọi kết quả ghi vào `output/`.
- Chỉ QT-01 được loại dòng; còn lại gắn cờ hoặc sửa trên cột mới. Ưu tiên gắn cờ hơn loại.
- Đổi quy tắc = nâng phiên bản (v2) trong `rules/`, ghi ngày và lý do; cập nhật `lam_sach.py` và test cùng lúc.
- Trước khi sửa `src/`, chạy test. **Test ngày 14/09 bắt buộc xanh**: 2.302 dòng gốc = 2.296 sạch + 6 trùng (QT-01 = 6), chặng 5, CS-VT 332 cuộc gốc, TS-BH 1.959.
- Tổng kiểm tra tháng 9: 29.515 = 29.452 + 63; cuộc gốc 29.404 (TS-BH 23.866, CS-VT 5.538).
- Không commit `.env`, `data/`, `output/`, file khóa (`*.key`).
- Python + pandas; mã nguồn, tên cột, thông báo bằng tiếng Việt không dấu cho tên biến/cột, có dấu cho chuỗi hiển thị.
