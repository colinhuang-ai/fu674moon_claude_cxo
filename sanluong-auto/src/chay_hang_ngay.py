#!/usr/bin/env python3
"""
chay_hang_ngay.py — Điểm vào chạy hằng ngày: chọn ngày → làm sạch call log ngày đó → ghi log.

Dùng (từ thư mục sanluong-auto/):
  python src/chay_hang_ngay.py                          # hôm qua
  python src/chay_hang_ngay.py 2026-09-14               # 1 ngày
  python src/chay_hang_ngay.py 2026-09-14 2026-09-16    # khoảng ngày, gồm cả hai đầu

Đọc   DATA_DIR/call_log_theo_ngay/call_log_<ngày>.csv      (DATA_DIR, OUTPUT_DIR lấy từ .env)
Ghi   OUTPUT_DIR/du_lieu_sach_<ngày>.csv, dong_bi_loai_<ngày>.csv, bao_cao_<ngày>.md
Log   OUTPUT_DIR/chay_hang_ngay.log (nối thêm mỗi lần chạy)

Lên lịch 06:30 (sau ca D): Task Scheduler / cron gọi đúng lệnh trên, không cần tham số.
Mã thoát: 0 = OK · 1 = tổng kiểm tra lệch · 2 = thiếu file / lỗi đầu vào (lấy mã lớn nhất nếu chạy nhiều ngày).
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import lam_sach as ls


def cac_ngay(args: list[str]) -> list[date]:
    if not args:
        return [date.today() - timedelta(days=1)]
    dau, cuoi = date.fromisoformat(args[0]), date.fromisoformat(args[-1])
    if cuoi < dau:
        raise ValueError(f"khoảng ngày ngược: {dau} > {cuoi}")
    return [dau + timedelta(days=i) for i in range((cuoi - dau).days + 1)]


def chay(ngays: list[date], data_dir: Path, outdir: Path, config: Path, log: logging.Logger) -> int:
    ma_thoat = 0
    ref = ls.nap_tham_chieu(config)
    for ngay in ngays:
        f = data_dir / "call_log_theo_ngay" / f"call_log_{ngay}.csv"
        if not f.is_file():
            log.error("%s: không thấy file %s", ngay, f)
            ma_thoat = max(ma_thoat, 2)
            continue
        bc, _ = ls.xu_ly_file(f, ref, outdir)
        thong_bao = (f"{ngay}: gốc {ls.fmt(bc['dong_goc'])} = sạch {ls.fmt(bc['dong_sach'])} + loại "
                     f"{ls.fmt(bc['dong_loai'])} · chặng {ls.fmt(bc['chang'])} · cuộc gốc {ls.fmt(bc['cuoc_goc'])} "
                     f"{bc['cuoc_goc_theo_du_an']} · chưa có QT {ls.fmt(bc['dong_chua_co_qt'])}")
        if not bc["tong_kiem_tra_dat"]:
            log.error("%s — TỔNG KIỂM TRA KHÔNG KHỚP", thong_bao)
            ma_thoat = max(ma_thoat, 1)
        elif bc["dong_chua_co_qt"]:
            log.warning("%s — có dòng 'Chưa có quy tắc', xem bao_cao_%s.md", thong_bao, ngay)
        else:
            log.info("%s — OK", thong_bao)
    return ma_thoat


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Chạy làm sạch call log theo ngày (mặc định: hôm qua)")
    ap.add_argument("ngay", nargs="*", help="YYYY-MM-DD, hoặc 2 ngày = khoảng ngày (gồm cả hai đầu)")
    ap.add_argument("-c", "--config", type=Path, default=ls.CONFIG_MAC_DINH)
    ap.add_argument("-o", "--outdir", type=Path, help="thư mục kết quả (mặc định OUTPUT_DIR trong .env)")
    ap.add_argument("-d", "--data-dir", type=Path, help="thư mục dữ liệu (mặc định DATA_DIR trong .env)")
    a = ap.parse_args()
    if len(a.ngay) > 2:
        ap.error("chỉ nhận 0, 1 hoặc 2 ngày")

    env = ls.doc_env()
    data_dir = a.data_dir or ls.thu_muc(env, "DATA_DIR", "data")
    outdir = a.outdir or ls.thu_muc(env, "OUTPUT_DIR", "output")
    outdir.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("chay_hang_ngay")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(outdir / "chay_hang_ngay.log", encoding="utf-8")):
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
        log.addHandler(h)

    try:
        return chay(cac_ngay(a.ngay), data_dir, outdir, a.config, log)
    except (ValueError, KeyError, OSError) as e:
        log.error("%s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
