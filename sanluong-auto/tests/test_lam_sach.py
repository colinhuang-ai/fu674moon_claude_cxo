#!/usr/bin/env python3
"""
Test cho src/lam_sach.py và src/chay_hang_ngay.py.

Hai lớp kiểm tra:
  1. Số liệu tháng 9 phải khớp các con số đã chốt trong deck Buổi 2 (Lab 2.2 / 2.3 / 2.4) và báo cáo tổng đài.
     Cần dữ liệu mẫu trong data/ (không commit); thiếu thì các test này bị bỏ qua.
  2. Từng quy tắc QT-01…QT-10 trên dữ liệu giả lập (có ca biên mà tháng 9 không có).

Chạy từ thư mục sanluong-auto/:  python -m unittest discover -s tests -v     (hoặc: pytest tests)
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import chay_hang_ngay as hn  # noqa: E402
import lam_sach as ls  # noqa: E402

DATA = ROOT / "data"
THEO_NGAY = DATA / "call_log_theo_ngay"
TONG_DAI = DATA / "bao_cao_tong_dai_2026-09.csv"
FILES = sorted(THEO_NGAY.glob("call_log_2026-09-*.csv"))
CO_DU_LIEU = len(FILES) == 15 and TONG_DAI.is_file()   # 07–21/09
KHONG_CO_DU_LIEU = "thiếu data/call_log_theo_ngay/ (15 file 07–21/09) hoặc data/bao_cao_tong_dai_2026-09.csv"

REF = ls.nap_tham_chieu()
RAW = KQ = None


def setUpModule():
    global RAW, KQ
    if CO_DU_LIEU:  # tháng 9 = ghép 15 file ngày (mã trùng chỉ nằm trong cùng ngày)
        RAW = pd.concat([ls.read_csv(f) for f in FILES], ignore_index=True)
        KQ = ls.lam_sach(RAW, REF, "call_log_2026-09 (ghép 15 file ngày)")


def sach_ngay(ngay: str) -> ls.KetQua:
    f = THEO_NGAY / f"call_log_{ngay}.csv"
    return ls.lam_sach(ls.read_csv(f), REF, f.name)


def co(df: pd.DataFrame, token: str) -> pd.Series:
    return df["ma_qt"].str.split(";").map(lambda t: token in t)


def so_cuoc(kq: ls.KetQua, du_an: str) -> int:
    return kq.bao_cao["cuoc_goc_theo_du_an"].get(du_an, 0)


# ---------------------------------------------------------------- 1. số liệu tháng 9 khớp deck
@unittest.skipUnless(CO_DU_LIEU, KHONG_CO_DU_LIEU)
class TestThang9(unittest.TestCase):
    def test_tong_kiem_tra(self):
        bc = KQ.bao_cao
        self.assertEqual((bc["dong_goc"], bc["dong_loai"], bc["dong_sach"]), (29515, 63, 29452))
        self.assertEqual((bc["chang"], bc["cuoc_goc"]), (48, 29404))
        self.assertEqual(bc["cuoc_goc_theo_du_an"], {"CS-VT": 5538, "TS-BH": 23866})
        self.assertTrue(bc["tong_kiem_tra_dat"])
        self.assertEqual(bc["dong_chua_co_qt"], 0, bc["chua_co_quy_tac"])

    def test_so_dong_theo_quy_tac(self):  # Lab 2.2 — kết quả mong đợi chạy thử v1
        qt = {k: v["so_dong"] for k, v in KQ.bao_cao["quy_tac"].items()}
        self.assertEqual({k: qt[k] for k in ["QT-01", "QT-02", "QT-03", "QT-04", "QT-05", "QT-06", "QT-09", "QT-10"]},
                         {"QT-01": 63, "QT-02": 22, "QT-03": 48, "QT-04": 41, "QT-05": 5, "QT-06": 7,
                          "QT-09": 551, "QT-10": 24})
        s = KQ.sach
        self.assertEqual(int(co(s, "QT-08:DINH_DANG").sum()), 590)
        self.assertEqual(int(co(s, "QT-08:NOI_DE_XUAT").sum()), 357)   # EXT2018
        self.assertEqual(int(co(s, "QT-08:NGOAI_DS").sum()), 250)      # EXT2099
        self.assertEqual((int(co(s, "QT-09:HOP_LE").sum()), int(co(s, "QT-09:GAN_CO").sum())), (537, 14))
        q04 = s[co(s, "QT-04")]
        self.assertEqual(q04["huong"].value_counts().to_dict(), {"OUT": 28, "IN": 13})

    def test_utc_khong_doi_ngay_va_chi_toan_ts_bh(self):
        s = KQ.sach
        self.assertEqual(s[co(s, "QT-02")]["du_an"].unique().tolist(), ["TS-BH"])
        self.assertIn("đổi ngày sau khi +7 giờ: 0", KQ.bao_cao["quy_tac"]["QT-02"]["chi_tiet"])

    def test_ca_dem(self):
        s = KQ.sach
        ngay_cuoi = s[s["ngay"] == "2026-09-21"]
        self.assertEqual(len(ngay_cuoi), 78)                              # "78 cuộc ngày 21/09"
        self.assertEqual(ngay_cuoi["ngay_ca"].unique().tolist(), ["2026-09-20"])
        self.assertIn("vắt 0h 11", KQ.bao_cao["quy_tac"]["QT-07"]["chi_tiet"])  # "11 cuộc vắt 0h"

    def test_chi_so_nguon_khop_deck(self):  # Lab 2.3 — San_luong_ngay 14 ngày
        s = KQ.sach
        goc = s[s["la_chang_chuyen"] == 0]
        ts, cs = goc[goc["du_an"] == "TS-BH"], goc[goc["du_an"] == "CS-VT"]
        lien_he = ts[(ts["cap1"] == "Liên hệ được") & ~co(ts, "QT-04")]
        self.assertEqual(len(lien_he), 11481)
        self.assertEqual(int(((ts["cap2"] == "Thành công") & ~co(ts, "QT-04")).sum()), 1255)
        self.assertEqual(int((cs["trang_thai_ket_noi"] == "ANSWERED").sum()), 5001)  # 5.001 / 5.538 = 90,3%

    def test_aht_khop_deck(self):  # CS-VT ≈ 322 s, TS-BH ≈ 186 s
        s = KQ.sach[KQ.sach["tinh_aht"] == 1]
        xl = s["dam_thoai"].astype(int) + s["giu_may"].astype(int) + s["acw"].astype(int)
        aht = xl.groupby(s["du_an"]).mean().round()
        self.assertEqual(aht.to_dict(), {"CS-VT": 322, "TS-BH": 186})

    def test_mapping_phu_het_va_khop_lab_2_1(self):
        cap2 = pd.Series([REF.mapping.get((ls.chuan_ghi_chu(g), t))
                          for g, t in zip(RAW["ghi_chu_ket_qua"], RAW["trang_thai_ket_noi"])])
        self.assertEqual(int(cap2.isna().sum()), 0)
        dem = cap2.value_counts().to_dict()
        mong_doi = {"Thành công": 1259, "Hẹn gọi lại": 2830, "Đang cân nhắc": 1150, "Từ chối": 3493,
                    "Đã có sản phẩm": 651, "Không gọi lại (DNC)": 737, "Sai người": 1056, "Không nghe máy": 8392,
                    "Máy bận": 1888, "Thuê bao": 1302, "Sai số": 801, "Chưa xác định": 357}
        self.assertEqual({k: dem[k] for k in mong_doi}, mong_doi)
        self.assertEqual(sum(mong_doi.values()), 23916)                      # outbound
        self.assertEqual(len(cap2) - sum(mong_doi.values()), 5599)           # inbound; 23.916 + 5.599 = 29.515

    def test_doi_chieu_bao_cao_tong_dai(self):  # tổng đài đếm mã cuộc gọi duy nhất, kể cả chặng chuyển tiếp
        td = ls.read_csv(TONG_DAI)
        mong_doi = {(r.ngay, r.du_an): int(r.tong_cuoc_goi) for r in td.itertuples()}
        s = KQ.sach
        cua_ban = s.groupby(["ngay", "du_an"]).size().to_dict()
        self.assertEqual(cua_ban, mong_doi)
        self.assertEqual(sum(cua_ban.values()) - KQ.bao_cao["chang"], KQ.bao_cao["cuoc_goc"])

    def test_bang_gia_tri_dau_ra(self):
        s = KQ.sach
        self.assertEqual(list(s.columns), ls.COT_RA)
        self.assertTrue((s["dam_thoai"].astype(int) >= 0).all() and (s["acw"].astype(int) >= 0).all())
        self.assertTrue(s["ma_cuoc_goi"].is_unique)
        self.assertEqual(s.loc[s["trang_thai_ket_noi"] == "CONNECTED", "huong"].unique().tolist(), ["OUT"])


@unittest.skipUnless(CO_DU_LIEU, KHONG_CO_DU_LIEU)
class TestTheoNgay(unittest.TestCase):
    """Số tự kiểm của dữ liệu mẫu 14–17/09 (deck slide 21, 25, 27)."""

    def kiem(self, ngay, goc, trung, chang, cs, ts, ty_le_nghe=None):
        kq = sach_ngay(ngay)
        bc = kq.bao_cao
        self.assertEqual((bc["dong_goc"], bc["dong_loai"], bc["dong_sach"], bc["chang"]),
                         (goc, trung, goc - trung, chang))
        self.assertEqual((so_cuoc(kq, "CS-VT"), so_cuoc(kq, "TS-BH")), (cs, ts))
        self.assertTrue(bc["tong_kiem_tra_dat"])
        if ty_le_nghe:
            s = kq.sach
            cs_goc = s[(s["du_an"] == "CS-VT") & (s["la_chang_chuyen"] == 0)]
            self.assertEqual(round(100 * (cs_goc["trang_thai_ket_noi"] == "ANSWERED").mean(), 1), ty_le_nghe)

    def test_14_09(self):
        self.kiem("2026-09-14", 2302, 6, 5, 332, 1959, 88.9)

    def test_15_09(self):
        self.kiem("2026-09-15", 2462, 5, 4, 432, 2021, 91.9)

    def test_16_09(self):
        self.kiem("2026-09-16", 2310, 5, 8, 431, 1866, 90.5)

    def test_17_09(self):
        self.kiem("2026-09-17", 2581, 9, 5, 482, 2085)

    def test_ngay_16_09_ext2099_lan_dau(self):  # "16/09 QT-08 nhảy lên 57 dòng EXT2099"
        s = sach_ngay("2026-09-16").sach
        self.assertEqual(int(co(s, "QT-08:NGOAI_DS").sum()), 57)


# ---------------------------------------------------------------- 2. từng quy tắc trên dữ liệu giả lập
MAC_DINH = dict(
    ma_cuoc_goi="CG100001", thoi_diem_bat_dau="2026-09-08 10:00:00", huong="OUT", ma_agent="EXT2001",
    hang_doi="OB-BAOHIEM", du_an="TS-BH", ma_khach_hang="KH12345", thoi_gian_cho_giay="10",
    thoi_gian_dam_thoai_giay="60", thoi_gian_giu_may_giay="0", thoi_gian_acw_giay="20",
    trang_thai_ket_noi="CONNECTED", ghi_chu_ket_qua="Từ chối", ma_cuoc_goi_goc="",
)
CS_MAC_DINH = dict(MAC_DINH, huong="IN", hang_doi="IB-CSKH", du_an="CS-VT", ma_agent="EXT2012",
                   trang_thai_ket_noi="ANSWERED", ghi_chu_ket_qua="Giải quyết xong")


def chay(*dong: dict) -> ls.KetQua:
    """Mỗi dòng nhận mã cuộc gọi riêng (CG100001, CG100002, …) trừ khi tự truyền ma_cuoc_goi."""
    rows = [dict(MAC_DINH, **{"ma_cuoc_goi": f"CG{100001 + i}", **d}) for i, d in enumerate(dong)]
    return ls.lam_sach(pd.DataFrame(rows, dtype=str), REF, "gia_lap.csv")


class TestTungQuyTac(unittest.TestCase):
    def test_dong_sach_khong_co_qt(self):
        kq = chay({})
        r = kq.sach.iloc[0]
        self.assertEqual((r["ma_qt"], r["tinh_aht"], r["ma_nv"], r["cap1"], r["cap2"]),
                         ("", 1, "NV0101", "Liên hệ được", "Từ chối"))
        self.assertEqual(kq.bao_cao["chua_co_quy_tac"], {})

    def test_qt01_trung_giu_dong_dau(self):
        kq = chay({"ma_cuoc_goi": "CG100001", "ghi_chu_ket_qua": "Từ chối"},
                  {"ma_cuoc_goi": "CG100001", "ghi_chu_ket_qua": "Thành công"},
                  {"ma_cuoc_goi": "CG100002"})
        self.assertEqual(kq.sach["ma_cuoc_goi"].tolist(), ["CG100001", "CG100002"])
        self.assertEqual(kq.sach.iloc[0]["cap2"], "Từ chối")                    # giữ dòng đầu
        self.assertEqual(kq.loai["so_dong_trong_file"].tolist(), [3])           # dòng 3 trong file (dòng 1 = tiêu đề)
        self.assertIn("1 dòng khác nội dung bản đầu", kq.bao_cao["quy_tac"]["QT-01"]["chi_tiet"])
        self.assertTrue(kq.bao_cao["tong_kiem_tra_dat"])

    def test_qt01_ma_trong_khong_coi_la_trung(self):
        kq = chay({"ma_cuoc_goi": ""}, {"ma_cuoc_goi": ""})
        self.assertEqual((len(kq.sach), len(kq.loai)), (2, 0))
        self.assertEqual(kq.bao_cao["chua_co_quy_tac"]["ma_cuoc_goi_sai_mau"]["so_dong"], 2)

    def test_qt02_utc_cong_7_gio_va_doi_ngay(self):
        kq = chay({"thoi_diem_bat_dau": "2026-09-18T01:12:00Z"}, {"thoi_diem_bat_dau": "2026-09-08T20:00:00Z"})
        s = kq.sach
        self.assertEqual(s["thoi_diem_vn"].tolist(), ["2026-09-18 08:12:00", "2026-09-09 03:00:00"])
        self.assertEqual(s["gio"].tolist(), [8, 3])
        self.assertEqual(s["ngay"].tolist(), ["2026-09-18", "2026-09-09"])
        self.assertTrue(co(s, "QT-02").all())
        self.assertIn("đổi ngày sau khi +7 giờ: 1", kq.bao_cao["quy_tac"]["QT-02"]["chi_tiet"])
        # 08:12 trong giờ → cảnh báo "gọi 01:12 sáng" là giả; 03:00 sáng hôm sau thì ngoài giờ thật
        self.assertEqual(co(s, "QT-10").tolist(), [False, True])

    def test_qt03_chang_chuyen_tiep(self):
        s = chay({"ma_cuoc_goi_goc": "CG100000"}, {}).sach
        self.assertEqual(s["la_chang_chuyen"].tolist(), [1, 0])
        self.assertEqual(chay({"ma_cuoc_goi_goc": "CG100000"}).bao_cao["cuoc_goc"], 0)

    def test_qt04_ket_noi_0_giay(self):
        s = chay({"thoi_gian_dam_thoai_giay": "0"},
                 {"thoi_gian_dam_thoai_giay": "0", "trang_thai_ket_noi": "NO_ANSWER", "ghi_chu_ket_qua": ""}).sach
        self.assertEqual(co(s, "QT-04").tolist(), [True, False])    # NO_ANSWER 0 giây là bình thường
        self.assertEqual(s["tinh_aht"].tolist(), [0, 0])

    def test_qt05_thoi_luong_am_ve_0(self):
        s = chay({"thoi_gian_acw_giay": "-58"}).sach.iloc[0]
        self.assertEqual((s["acw"], s["ma_qt"], s["tinh_aht"]), (0, "QT-05", 1))

    def test_qt06_treo_line_bien_7200(self):
        s = chay({"thoi_gian_dam_thoai_giay": "7200"}, {"thoi_gian_dam_thoai_giay": "7201"}).sach
        self.assertEqual(s["co_treo_line"].tolist(), [0, 1])
        self.assertEqual(s["tinh_aht"].tolist(), [1, 0])
        self.assertEqual(co(s, "QT-06").tolist(), [False, True])

    def test_qt07_ngay_ca(self):
        s = chay({"thoi_diem_bat_dau": "2026-09-09 02:00:00"},
                 {"thoi_diem_bat_dau": "2026-09-09 05:59:59"},
                 {"thoi_diem_bat_dau": "2026-09-09 06:00:00"},
                 {"thoi_diem_bat_dau": "2026-09-08 23:59:30", "thoi_gian_cho_giay": "10"}).sach
        self.assertEqual(s["ngay_ca"].tolist(), ["2026-09-08", "2026-09-08", "2026-09-09", "2026-09-08"])
        self.assertEqual(co(s, "QT-07").tolist(), [True, True, False, True])  # dòng 4: vắt 0h, ngay_ca không đổi

    def test_qt08_chuan_hoa_noi_ma(self):
        s = chay({"ma_agent": "ext2005"}, {"ma_agent": "EXT 2007"}, {"ma_agent": "EXT2018"},
                 {"ma_agent": "EXT2099"}, {"ma_agent": "EXT9999"}).sach
        self.assertEqual(s["ma_agent_chuan"].tolist(), ["EXT2005", "EXT2007", "EXT2018", "EXT2099", "EXT9999"])
        self.assertEqual(s["ma_nv"].tolist(), ["NV0105", "NV0107", "NV0118", "", ""])
        self.assertEqual(s["ma_qt"].tolist()[:4], ["QT-08:DINH_DANG", "QT-08:DINH_DANG", "QT-08:NOI_DE_XUAT",
                                                   "QT-08:NGOAI_DS"])
        self.assertEqual(s["ma_qt"][4], "QT-08:NGOAI_DS;CHUA-CO-QT:ma_agent_la")  # mã lạ chưa ai quyết

    def test_qt09_trong_ma_agent(self):
        s = ls.lam_sach(pd.DataFrame([
            dict(CS_MAC_DINH, ma_cuoc_goi="CG200001", ma_agent="", trang_thai_ket_noi="ABANDONED",
                 ghi_chu_ket_qua="", thoi_gian_dam_thoai_giay="0", thoi_gian_acw_giay="0"),
            dict(CS_MAC_DINH, ma_cuoc_goi="CG200002", ma_agent=""),
        ], dtype=str), REF).sach
        self.assertEqual(s["ma_qt"].tolist(), ["QT-09:HOP_LE", "QT-09:GAN_CO"])
        self.assertEqual(s["tinh_aht"].tolist(), [0, 0])
        self.assertEqual(s["cap2"].tolist(), ["Khách bỏ máy", "Giải quyết xong"])

    def test_qt10_ngoai_gio_outbound(self):
        s = chay({"thoi_diem_bat_dau": "2026-09-08 20:59:59"}, {"thoi_diem_bat_dau": "2026-09-08 21:00:00"},
                 {"thoi_diem_bat_dau": "2026-09-08 07:59:59"}, {"thoi_diem_bat_dau": "2026-09-08 08:00:00"},
                 {"thoi_diem_bat_dau": "2026-09-13 10:00:00"}, {"thoi_diem_bat_dau": "2026-09-12 10:00:00"}).sach
        self.assertEqual(co(s, "QT-10").tolist(), [False, True, True, False, True, False])  # T7 trong giờ, CN ngoài
        ib = ls.lam_sach(pd.DataFrame([dict(CS_MAC_DINH, thoi_diem_bat_dau="2026-09-13 23:00:00")], dtype=str), REF)
        self.assertFalse(co(ib.sach, "QT-10").any())   # CS-VT 24/7, và không phải outbound

    def test_chua_co_quy_tac_khong_tu_xu_ly(self):
        kq = chay({"ghi_chu_ket_qua": "gọi lại nha"},
                  {"huong": "XX"},
                  {"ma_khach_hang": "0912345678"},
                  {"thoi_diem_bat_dau": "13/09/2026 10:00"},
                  {"thoi_gian_cho_giay": "abc"},
                  {"trang_thai_ket_noi": "NO_ANSWER", "thoi_gian_dam_thoai_giay": "30", "ghi_chu_ket_qua": ""})
        self.assertEqual(len(kq.sach), 6)    # không loại dòng nào
        mong_doi = {"ghi_chu_chua_co_mapping", "huong_la", "ma_khach_hang_sai_mau", "thoi_diem_sai_dinh_dang",
                    "thoi_luong_khong_phai_so_nguyen", "dam_giu_khi_khong_ket_noi"}
        self.assertTrue(mong_doi <= set(kq.bao_cao["chua_co_quy_tac"]), kq.bao_cao["chua_co_quy_tac"])
        self.assertEqual(kq.sach.iloc[0]["cap2"], "Chưa xác định")
        self.assertEqual(kq.sach.iloc[3]["ngay"], "")        # giờ sai định dạng: không đoán
        self.assertEqual(kq.bao_cao["dong_chua_co_qt"], 6)

    def test_thieu_cot_bat_buoc(self):
        with self.assertRaisesRegex(ValueError, "thiếu cột"):
            ls.lam_sach(pd.DataFrame({"ma_cuoc_goi": ["CG100001"]}), REF)

    def test_khong_sua_du_lieu_vao(self):
        raw = pd.DataFrame([dict(MAC_DINH, thoi_gian_acw_giay="-5", ma_agent="ext2001")], dtype=str)
        truoc = raw.copy()
        ls.lam_sach(raw, REF)
        pd.testing.assert_frame_equal(raw, truoc)


def chay_lenh(script: str, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(ROOT / "src" / script), *args], capture_output=True,
                          text=True, encoding="utf-8", env=env, cwd=ROOT)


@unittest.skipUnless(CO_DU_LIEU, KHONG_CO_DU_LIEU)
class TestDongLenh(unittest.TestCase):
    def test_lam_sach_mot_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = chay_lenh("lam_sach.py", str(THEO_NGAY / "call_log_2026-09-14.csv"), "-o", tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("✔ ĐẠT", r.stdout)
            out = Path(tmp)
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ["bao_cao_2026-09-14.md", "dong_bi_loai_2026-09-14.csv", "du_lieu_sach_2026-09-14.csv"])
            self.assertEqual(len(ls.read_csv(out / "du_lieu_sach_2026-09-14.csv")), 2296)
            self.assertEqual(len(ls.read_csv(out / "dong_bi_loai_2026-09-14.csv")), 6)

    def test_lam_sach_file_khong_ton_tai(self):
        self.assertEqual(chay_lenh("lam_sach.py", "khong_co_file.csv").returncode, 2)

    def test_chay_hang_ngay_khoang_ngay_va_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = chay_lenh("chay_hang_ngay.py", "2026-09-14", "2026-09-16", "-o", tmp, "-d", str(DATA))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = Path(tmp)
            for ngay in ("2026-09-14", "2026-09-15", "2026-09-16"):
                self.assertTrue((out / f"du_lieu_sach_{ngay}.csv").is_file())
            log = (out / "chay_hang_ngay.log").read_text(encoding="utf-8")
            self.assertIn("2026-09-14: gốc 2.302 = sạch 2.296 + loại 6 · chặng 5 · cuộc gốc 2.291", log)
            self.assertEqual(log.count(" OK"), 3)

    def test_chay_hang_ngay_thieu_file_ma_thoat_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = chay_lenh("chay_hang_ngay.py", "2026-09-14", "2026-09-30", "-o", tmp, "-d", str(DATA))
            self.assertEqual(r.returncode, 2)
            self.assertTrue((Path(tmp) / "du_lieu_sach_2026-09-14.csv").is_file())   # ngày có file vẫn chạy
            self.assertIn("2026-09-30: không thấy file", (Path(tmp) / "chay_hang_ngay.log").read_text(encoding="utf-8"))


class TestCauHinh(unittest.TestCase):
    def test_cac_ngay(self):
        self.assertEqual(hn.cac_ngay([]), [date.today() - timedelta(days=1)])
        self.assertEqual(hn.cac_ngay(["2026-09-14"]), [date(2026, 9, 14)])
        self.assertEqual(len(hn.cac_ngay(["2026-09-14", "2026-09-16"])), 3)
        with self.assertRaises(ValueError):
            hn.cac_ngay(["2026-09-16", "2026-09-14"])
        with self.assertRaises(ValueError):
            hn.cac_ngay(["14/09/2026"])

    def test_doc_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / ".env"
            f.write_text("\n".join(['# ghi chú', 'DATA_DIR="du_lieu"', "", "OUTPUT_DIR=ket_qua", "#GOOGLE_SHEET_ID=abc"]),
                         encoding="utf-8")
            env = ls.doc_env(f)
            self.assertEqual(env, {"DATA_DIR": "du_lieu", "OUTPUT_DIR": "ket_qua"})
            self.assertEqual(ls.thu_muc(env, "DATA_DIR", "data"), ls.GOC_DU_AN / "du_lieu")
            self.assertEqual(ls.thu_muc({}, "OUTPUT_DIR", "output"), ls.GOC_DU_AN / "output")
            self.assertEqual(ls.doc_env(Path(tmp) / "khong_co.env").get("DATA_DIR"), os.environ.get("DATA_DIR"))

    def test_tham_chieu_dung_bang_noi_ma_moi(self):
        self.assertEqual(REF.bang_noi_ma["EXT2018"], ("NV0118", False))   # đề xuất chờ HR
        self.assertEqual(REF.bang_noi_ma["EXT2099"], ("", False))
        self.assertEqual(REF.bang_noi_ma["EXT2001"], ("NV0101", True))
        self.assertEqual(len(REF.bang_noi_ma), 20)


if __name__ == "__main__":
    unittest.main()
