#!/usr/bin/env python3
"""
lam_sach.py — Làm sạch call log theo "Quy tắc làm sạch call log v1" (QT-01 … QT-10).

Thứ tự áp dụng (QT-02 phải chạy trước QT-07 và QT-10):
  QT-01  Trùng mã cuộc gọi          LOẠI — giữ dòng đầu tiên
  QT-02  Giờ UTC (…T…Z)             +7 giờ → cột mới thoi_diem_vn
  QT-03  Chặng chuyển tiếp          gắn cờ la_chang_chuyen, không đếm sản lượng
  QT-04  Nghe/kết nối 0 giây        gắn cờ, loại khỏi AHT
  QT-05  Thời lượng âm              sửa về 0 + gắn cờ
  QT-06  Treo line > 7.200 giây     gắn cờ co_treo_line, loại khỏi AHT và phút
  QT-07  Qua nửa đêm / ca D         thêm cột ngay_ca (ngày bắt đầu ca)
  QT-08  Chuẩn hóa & nối mã agent   sửa, nối sang mã NV, gắn cờ ngoài danh sách
  QT-09  Trống mã agent             ABANDONED hợp lệ, còn lại gắn cờ
  QT-10  Outbound ngoài giờ         gắn cờ, báo trưởng ca

Nguyên tắc: không sửa file gốc · chỉ QT-01 được LOẠI dòng · ưu tiên gắn cờ hơn loại ·
không đoán giá trị thay thế. Dòng sai nhưng chưa có quy tắc → ghi ma_qt = CHUA-CO-QT:<tên>
và liệt kê trong báo cáo, KHÔNG tự xử lý (nâng quy tắc lên v2).

Dùng (từ thư mục sanluong-auto/; hằng ngày dùng chay_hang_ngay.py):
  python src/lam_sach.py data/call_log_theo_ngay/call_log_2026-09-14.csv
  python src/lam_sach.py "data/call_log_theo_ngay/*.csv"          # mỗi file 1 bộ kết quả
  python src/lam_sach.py <file> -o <thư mục>                      # mặc định OUTPUT_DIR trong .env (output/)

Với mỗi file vào ra 3 file trong thư mục kết quả:
  du_lieu_sach_<tag>.csv   dữ liệu sạch, 1 dòng = 1 cuộc gọi (cột ma_qt ghi quy tắc đã tác động)
  dong_bi_loai_<tag>.csv   các dòng QT-01 đã loại (giữ làm bằng chứng)
  bao_cao_<tag>.md         số dòng theo từng mã QT + tổng kiểm tra + danh sách "Chưa có quy tắc"

Quy tắc và tham chiếu: rules/ (Quy_tac_lam_sach_call_log_v1.md, Mapping_ma_ket_qua_v1.csv, lam_sach_config.json)
và ref/ (bang_noi_ma.csv, danh_sach_du_an.csv, danh_muc_ca.csv). Đường dẫn khai báo trong lam_sach_config.json.
Mã thoát: 0 = OK · 1 = tổng kiểm tra không khớp · 2 = lỗi đầu vào.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

GOC_DU_AN = Path(__file__).resolve().parent.parent            # sanluong-auto/
CONFIG_MAC_DINH = GOC_DU_AN / "rules" / "lam_sach_config.json"


def doc_env(path: Path = GOC_DU_AN / ".env") -> dict[str, str]:
    """Đọc KEY=VALUE từ .env (bỏ dòng trống/#); biến môi trường có ưu tiên cao hơn. Không cần python-dotenv."""
    env: dict[str, str] = {}
    if path.is_file():
        for dong in path.read_text(encoding="utf-8").splitlines():
            dong = dong.strip()
            if dong and not dong.startswith("#") and "=" in dong:
                k, v = dong.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in [*env, "DATA_DIR", "OUTPUT_DIR"]:
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def thu_muc(env: dict[str, str], khoa: str, mac_dinh: str) -> Path:
    p = Path(env.get(khoa) or mac_dinh)
    return p if p.is_absolute() else GOC_DU_AN / p

COT_VAO = [
    "ma_cuoc_goi", "thoi_diem_bat_dau", "huong", "ma_agent", "hang_doi", "du_an", "ma_khach_hang",
    "thoi_gian_cho_giay", "thoi_gian_dam_thoai_giay", "thoi_gian_giu_may_giay", "thoi_gian_acw_giay",
    "trang_thai_ket_noi", "ghi_chu_ket_qua", "ma_cuoc_goi_goc",
]

# Thứ tự cột của Du_lieu_sach (A..S) khớp công thức trong deck: C = ngay, D = gio, E = huong,
# F = du_an, J = cap1, P = la_chang_chuyen. Cột bổ sung (ngay_ca) để cuối để không xô lệch chữ cột.
COT_RA = [
    "ma_cuoc_goi", "thoi_diem_vn", "ngay", "gio", "huong", "du_an", "ma_agent_chuan", "ma_nv",
    "trang_thai_ket_noi", "cap1", "cap2", "dam_thoai", "giu_may", "acw", "cho",
    "la_chang_chuyen", "co_treo_line", "tinh_aht", "ma_qt", "ngay_ca",
]

TL = {"cho": "thoi_gian_cho_giay", "dam": "thoi_gian_dam_thoai_giay",
      "giu": "thoi_gian_giu_may_giay", "acw": "thoi_gian_acw_giay"}

QUY_TAC = {
    "QT-01": ("Trùng mã cuộc gọi", "LOẠI — giữ dòng đầu tiên"),
    "QT-02": ("Giờ UTC → +7 tiếng", "Sửa trên cột mới thoi_diem_vn"),
    "QT-03": ("Chặng chuyển tiếp", "Gắn cờ la_chang_chuyen, không đếm sản lượng"),
    "QT-04": ("Nghe/kết nối 0 giây", "Gắn cờ, loại khỏi AHT"),
    "QT-05": ("Thời lượng âm", "Sửa về 0 + gắn cờ"),
    "QT-06": ("Treo line", "Gắn cờ co_treo_line, loại khỏi AHT và phút"),
    "QT-07": ("Qua nửa đêm / ca D", "Thêm cột ngay_ca"),
    "QT-08": ("Chuẩn hóa & nối mã agent", "Sửa, nối, gắn cờ ngoài danh sách"),
    "QT-09": ("Trống mã agent", "ABANDONED hợp lệ, còn lại gắn cờ"),
    "QT-10": ("Outbound ngoài giờ", "Gắn cờ, báo trưởng ca"),
}

MAU_MA_CUOC_GOI = r"CG\d{6}"
MAU_MA_KHACH = r"KH\d{5}"
CAP2_CHUA_XAC_DINH = "Chưa xác định"


# ---------------------------------------------------------------- tham chiếu
@dataclass
class ThamChieu:
    cfg: dict
    bang_noi_ma: dict[str, tuple[str, bool]]             # EXT chuẩn → (mã NV hoặc "", đã khớp) từ ref/bang_noi_ma.csv
    du_an: set[str]
    gio_hoat_dong: dict[str, tuple[int, int, set[int]]]  # dự án → (giây bắt đầu, giây kết thúc, thứ 0=T2..6=CN)
    ca_dem_ket_thuc: int | None                          # giây từ 00:00, None nếu không có ca qua đêm
    mapping: dict[tuple[str, str], str]                  # (ghi chú chuẩn hóa, trạng thái) → mã cấp 2


def read_csv(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def chuan_ma_agent(s: pd.Series) -> pd.Series:
    return s.str.replace(r"\s+", "", regex=True).str.upper()


def chuan_ghi_chu(v: str) -> str:
    v = unicodedata.normalize("NFC", str(v)).strip()
    return "" if v == "(trống)" else v


def giay_trong_ngay(hhmm: str) -> int:
    h, m = hhmm.strip().split(":")
    return int(h) * 3600 + int(m) * 60


def doc_gio_hoat_dong(s: str) -> tuple[int, int, set[int]] | None:
    """'08:00–21:00, T2–T7' → (28800, 75600, {0..5}); '24/7' → None (không giới hạn)."""
    gio = re.search(r"(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})", s)
    if not gio:
        return None
    thu = re.search(r"T(\d)\s*[–-]\s*T(\d)", s)
    ngay = set(range(int(thu.group(1)) - 2, int(thu.group(2)) - 2 + 1)) if thu else set(range(7))
    return giay_trong_ngay(gio.group(1)), giay_trong_ngay(gio.group(2)), ngay


def nap_tham_chieu(config_path: Path = CONFIG_MAC_DINH) -> ThamChieu:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    p = {k: GOC_DU_AN / v for k, v in cfg["tham_chieu"].items()}   # đường dẫn tính từ gốc dự án

    bn = read_csv(p["bang_noi_ma"])
    ext = chuan_ma_agent(bn["ma_tong_dai"])
    if ext.duplicated().any():
        raise ValueError(f"bang_noi_ma: ma_tong_dai trùng: {sorted(ext[ext.duplicated()].unique())}")
    bang_noi_ma = {e: (nv.strip(), tt.strip() == "Khớp")
                   for e, nv, tt in zip(ext, bn["ma_nv"], bn["trang_thai_noi"])}

    da = read_csv(p["danh_sach_du_an"])
    gio = {r.ma_du_an: doc_gio_hoat_dong(r.gio_hoat_dong) for r in da.itertuples()}

    ca = read_csv(p["danh_muc_ca"])
    qua_dem = [giay_trong_ngay(g) for g in ca.loc[ca["qua_dem"] == "Có", "gio_ket_thuc"]]

    mp = read_csv(p["mapping_ma_ket_qua"])
    mapping: dict[tuple[str, str], str] = {}
    for r in mp.itertuples():
        k = (chuan_ghi_chu(r.ghi_chu_goc), r.trang_thai_ket_noi.strip())
        if k in mapping:
            raise ValueError(f"mapping_ma_ket_qua: khóa trùng {k}")
        mapping[k] = r.cap2.strip()

    return ThamChieu(cfg, bang_noi_ma, set(da["ma_du_an"]),
                     {k: v for k, v in gio.items() if v}, max(qua_dem) if qua_dem else None, mapping)


# ---------------------------------------------------------------- core
@dataclass
class KetQua:
    sach: pd.DataFrame
    loai: pd.DataFrame
    bao_cao: dict


def lam_sach(raw: pd.DataFrame, ref: ThamChieu, ten_file: str = "") -> KetQua:
    thieu = [c for c in COT_VAO if c not in raw.columns]
    if thieu:
        raise ValueError(f"thiếu cột bắt buộc: {thieu}")
    cfg = ref.cfg
    raw = raw.copy()
    raw["_dong"] = range(2, len(raw) + 2)  # số dòng trong file gốc (dòng 1 = tiêu đề)

    # ---- QT-01: trùng mã cuộc gọi → LOẠI, giữ dòng đầu tiên (mã trống không coi là trùng nhau)
    trung = raw["ma_cuoc_goi"].ne("") & raw.duplicated("ma_cuoc_goi", keep="first")
    loai = raw.loc[trung]
    d = raw.loc[~trung].reset_index(drop=True)
    khac_noi_dung = 0
    if trung.any():
        dau = raw.drop_duplicates("ma_cuoc_goi", keep="first").set_index("ma_cuoc_goi")[COT_VAO[1:]]
        khac_noi_dung = int((loai[COT_VAO[1:]].to_numpy()
                             != dau.loc[loai["ma_cuoc_goi"]].to_numpy()).any(axis=1).sum())

    ma_qt = pd.Series("", index=d.index)

    def gan(mask: pd.Series, token: str):
        cur = ma_qt[mask]
        ma_qt[mask] = cur.where(cur == "", cur + ";") + token

    # ---- QT-02: giờ UTC (…T…Z) → +7 giờ, ghi vào cột mới
    s = d["thoi_diem_bat_dau"].str.strip()
    la_utc = s.str.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
    la_vn = s.str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    t_utc = pd.to_datetime(s.where(la_utc), format="%Y-%m-%dT%H:%M:%SZ", errors="coerce")
    t_vn = pd.to_datetime(s.where(la_vn), format="%Y-%m-%d %H:%M:%S", errors="coerce")
    tv = t_vn.fillna(t_utc + pd.Timedelta(hours=7))
    la_utc = la_utc & t_utc.notna()
    doi_ngay_utc = int((la_utc & (t_utc.dt.normalize() != (t_utc + pd.Timedelta(hours=7)).dt.normalize())).sum())
    gan(la_utc, "QT-02")

    # ---- QT-03: chặng chuyển tiếp
    chang = d["ma_cuoc_goi_goc"].str.strip().ne("")
    gan(chang, "QT-03")

    # ---- thời lượng (giây): số nguyên; QT-04 / QT-05 / QT-06 dựa trên đây
    so = {k: pd.to_numeric(d[c].str.strip(), errors="coerce") for k, c in TL.items()}
    sai_so = pd.concat([v.isna() | (v % 1 != 0) for v in so.values()], axis=1).any(axis=1)
    so = {k: v.where(v % 1 == 0) for k, v in so.items()}

    # ---- QT-04: ANSWERED/CONNECTED nhưng 0 giây đàm thoại
    ket_noi = d["trang_thai_ket_noi"].isin(cfg["trang_thai_da_ket_noi"])
    qt04 = ket_noi & (so["dam"] == 0)
    gan(qt04, "QT-04")

    # ---- QT-05: thời lượng âm → sửa về 0 + gắn cờ
    am = pd.concat([v < 0 for v in so.values()], axis=1).any(axis=1)
    gan(am, "QT-05")
    sach_so = {k: v.clip(lower=0).astype("Int64") for k, v in so.items()}

    # ---- QT-06: treo line
    treo = so["dam"] > cfg["tham_so"]["treo_line_giay"]
    gan(treo, "QT-06")

    # ---- QT-07: ngày ca = ngày bắt đầu ca; ca D (qua đêm) kết thúc sáng hôm sau
    ngay = tv.dt.normalize()
    giay = tv.dt.hour * 3600 + tv.dt.minute * 60 + tv.dt.second
    sang_ca_d = (giay < ref.ca_dem_ket_thuc) if ref.ca_dem_ket_thuc is not None else pd.Series(False, index=d.index)
    ngay_ca = ngay - pd.to_timedelta(sang_ca_d.astype(int), unit="D")
    ket_thuc = tv + pd.to_timedelta(so["cho"] + so["dam"] + so["giu"], unit="s")
    vat_0h = ket_thuc.notna() & (ket_thuc.dt.normalize() != ngay)
    gan(sang_ca_d | vat_0h, "QT-07")

    # ---- QT-08: chuẩn hóa mã agent (hoa, bỏ khoảng trắng) và nối sang mã NV
    ag_goc = d["ma_agent"]
    ag = chuan_ma_agent(ag_goc)
    dinh_dang = ag_goc.ne("") & ag_goc.ne(ag)
    ma_nv = ag.map(lambda x: ref.bang_noi_ma.get(x, ("", True))[0])
    chua_khop = ag.map(lambda x: not ref.bang_noi_ma.get(x, ("", True))[1])   # trạng thái nối ≠ "Khớp"
    de_xuat = ma_nv.ne("") & chua_khop              # nối theo đề xuất, chờ HR xác nhận (EXT2018)
    ngoai_ds = ag.ne("") & ma_nv.eq("")             # không có mã NV: EXT2099 (đã có quyết định) hoặc mã lạ
    ma_la = ag.ne("") & ~ag.isin(ref.bang_noi_ma)   # mã lạ chưa ai quyết → "Chưa có quy tắc"
    gan(dinh_dang, "QT-08:DINH_DANG")
    gan(de_xuat, "QT-08:NOI_DE_XUAT")
    gan(ngoai_ds, "QT-08:NGOAI_DS")

    # ---- QT-09: trống mã agent — ABANDONED hợp lệ, còn lại gắn cờ
    trong_ag = ag.eq("")
    hop_le = trong_ag & (d["trang_thai_ket_noi"] == "ABANDONED")
    gan(hop_le, "QT-09:HOP_LE")
    gan(trong_ag & ~hop_le, "QT-09:GAN_CO")

    # ---- QT-10: outbound ngoài giờ hoạt động của dự án (giờ + thứ lấy từ danh_sach_du_an.csv)
    ngoai_gio = pd.Series(False, index=d.index)
    ngoai_ngay = pd.Series(False, index=d.index)
    for du_an, (bd, kt, thu) in ref.gio_hoat_dong.items():
        m = (d["huong"] == "OUT") & (d["du_an"] == du_an) & tv.notna()
        dung_thu = tv.dt.dayofweek.isin(thu)
        dung_gio = (giay >= bd) & (giay < kt)
        ngoai_gio |= m & ~(dung_gio & dung_thu)
        ngoai_ngay |= m & ~dung_thu
    gan(ngoai_gio, "QT-10")

    # ---- tinh_aht: cuộc đã nghe/kết nối, có agent, > 0 giây, không treo line, thời lượng hợp lệ
    tinh_aht = ket_noi & (so["dam"] > 0) & ~treo & ag.ne("") & ~sai_so

    # ---- mã kết quả 2 cấp: cấp 1 theo trạng thái kết nối, cấp 2 theo mapping (ghi chú, trạng thái)
    cap1 = d["trang_thai_ket_noi"].map(cfg["cap1_theo_trang_thai"]).fillna("")
    ghi_chu = d["ghi_chu_ket_qua"].map(chuan_ghi_chu)
    cap2 = pd.Series([ref.mapping.get(k) for k in zip(ghi_chu, d["trang_thai_ket_noi"])], index=d.index)
    chua_map = cap2.isna()
    cap2 = cap2.fillna(CAP2_CHUA_XAC_DINH)

    # ---- kiểm tra theo Từ điển dữ liệu ngoài QT-01…QT-10 → "Chưa có quy tắc", không tự xử lý
    huong_cfg = cfg["huong"]
    hop_huong = d["huong"].isin(huong_cfg)
    hang_doi_ky_vong = d["huong"].map(lambda h: huong_cfg.get(h, {}).get("hang_doi"))
    du_an_ky_vong = d["huong"].map(lambda h: huong_cfg.get(h, {}).get("du_an"))
    tt_hop_le = pd.Series([t in huong_cfg.get(h, {}).get("trang_thai", [])
                           for h, t in zip(d["huong"], d["trang_thai_ket_noi"])], index=d.index)
    kiem_tra = {
        "ma_cuoc_goi_sai_mau": ~d["ma_cuoc_goi"].str.fullmatch(MAU_MA_CUOC_GOI),
        "thoi_diem_sai_dinh_dang": tv.isna(),
        "huong_la": ~hop_huong,
        "huong_hang_doi_du_an_khong_khop": hop_huong & ((d["hang_doi"] != hang_doi_ky_vong)
                                                        | (d["du_an"] != du_an_ky_vong)),
        "du_an_la": ~d["du_an"].isin(ref.du_an),
        "trang_thai_khong_thuoc_huong": hop_huong & ~tt_hop_le,
        "ma_khach_hang_sai_mau": ~d["ma_khach_hang"].str.fullmatch(MAU_MA_KHACH),
        "thoi_luong_khong_phai_so_nguyen": sai_so,
        "thoi_gian_cho_bang_0": so["cho"] == 0,
        "dam_giu_khi_khong_ket_noi": ~ket_noi & ((so["dam"] > 0) | (so["giu"] > 0)),
        "ma_agent_la": ma_la,
        "ghi_chu_chua_co_mapping": chua_map,
    }
    chua_co_qt: dict[str, dict] = {}
    for ten, mask in kiem_tra.items():
        if mask.any():
            gan(mask, f"CHUA-CO-QT:{ten}")
            chua_co_qt[ten] = {"so_dong": int(mask.sum()), "vi_du": d.loc[mask, "ma_cuoc_goi"].head(3).tolist()}

    sach = pd.DataFrame({
        "ma_cuoc_goi": d["ma_cuoc_goi"],
        "thoi_diem_vn": tv.dt.strftime("%Y-%m-%d %H:%M:%S").fillna(""),
        "ngay": ngay.dt.strftime("%Y-%m-%d").fillna(""),
        "gio": tv.dt.hour.astype("Int64"),
        "huong": d["huong"],
        "du_an": d["du_an"],
        "ma_agent_chuan": ag,
        "ma_nv": ma_nv,
        "trang_thai_ket_noi": d["trang_thai_ket_noi"],
        "cap1": cap1,
        "cap2": cap2,
        "dam_thoai": sach_so["dam"],
        "giu_may": sach_so["giu"],
        "acw": sach_so["acw"],
        "cho": sach_so["cho"],
        "la_chang_chuyen": chang.astype(int),
        "co_treo_line": treo.astype(int),
        "tinh_aht": tinh_aht.astype(int),
        "ma_qt": ma_qt,
        "ngay_ca": ngay_ca.dt.strftime("%Y-%m-%d").fillna(""),
    })[COT_RA]

    # ---- báo cáo
    goc = ~chang
    theo_du_an = d.loc[goc, "du_an"].value_counts().sort_index().to_dict()
    n_chang = int(chang.sum())
    sl = lambda m: int(m.sum())  # noqa: E731
    dem_ma = lambda m: ", ".join(f"{k}: {fmt(v)}" for k, v in ag[m].value_counts().items())  # noqa: E731
    chi_tiet = {
        "QT-01": [f"{fmt(khac_noi_dung)} dòng khác nội dung bản đầu"] if khac_noi_dung else [],
        "QT-02": [f"đổi ngày sau khi +7 giờ: {fmt(doi_ngay_utc)}"],
        "QT-03": [f"{k} {fmt(v)}" for k, v in d.loc[chang, "du_an"].value_counts().sort_index().items()],
        "QT-04": [f"{k} {fmt(v)}" for k, v in d.loc[qt04, "huong"].value_counts().sort_index(ascending=False).items()],
        "QT-05": [f"{c} {fmt(sl(so[k] < 0))}" for k, c in TL.items() if sl(so[k] < 0)],
        "QT-06": [f"dài nhất {fmt(int(so['dam'].max()))} giây"] if treo.any() else [],
        "QT-07": [f"rạng sáng ca D (ngay_ca ≠ ngay) {fmt(sl(sang_ca_d))}", f"vắt 0h {fmt(sl(vat_0h))}"],
        "QT-08": [x for x in [
            f"sai định dạng {fmt(sl(dinh_dang))}" if dinh_dang.any() else "",
            f"nối đề xuất chờ HR {fmt(sl(de_xuat))} ({dem_ma(de_xuat)})" if de_xuat.any() else "",
            f"ngoài danh sách {fmt(sl(ngoai_ds))} ({dem_ma(ngoai_ds)})" if ngoai_ds.any() else "",
        ] if x],
        "QT-09": [f"hợp lệ (ABANDONED) {fmt(sl(hop_le))}", f"gắn cờ {fmt(sl(trong_ag & ~hop_le))}"],
        "QT-10": [f"trong đó ngoài ngày hoạt động {fmt(sl(ngoai_ngay))}"] if ngoai_gio.any() else [],
    }
    so_dong = {
        "QT-01": int(trung.sum()), "QT-02": sl(la_utc), "QT-03": n_chang, "QT-04": sl(qt04), "QT-05": sl(am),
        "QT-06": sl(treo), "QT-07": sl(sang_ca_d | vat_0h),
        "QT-08": sl(dinh_dang | de_xuat | ngoai_ds), "QT-09": sl(trong_ag), "QT-10": sl(ngoai_gio),
    }
    bao_cao = {
        "file": ten_file,
        "dong_goc": len(raw), "dong_loai": len(loai), "dong_sach": len(sach),
        "chang": n_chang, "cuoc_goc": sl(goc), "cuoc_goc_theo_du_an": theo_du_an,
        "dong_chua_co_qt": int(ma_qt.str.contains("CHUA-CO-QT").sum()),
        "tong_kiem_tra_dat": len(raw) == len(sach) + len(loai) and sum(theo_du_an.values()) == sl(goc),
        "quy_tac": {k: {"ten": QUY_TAC[k][0], "hanh_dong": QUY_TAC[k][1], "so_dong": so_dong[k],
                        "chi_tiet": chi_tiet[k]} for k in QUY_TAC},
        "chua_co_quy_tac": chua_co_qt,
    }
    return KetQua(sach, loai.drop(columns="_dong").assign(so_dong_trong_file=loai["_dong"]), bao_cao)


# ---------------------------------------------------------------- báo cáo markdown
def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def viet_bao_cao(bc: dict, ten_ra: str = "") -> str:
    L = [f"# Báo cáo làm sạch call log — Quy tắc {bc.get('phien_ban', 'v1')}", ""]
    L.append(f"**File:** `{bc['file']}`" + (f" → `{ten_ra}`" if ten_ra else ""))
    L += ["", "## Tổng kiểm tra", "", "| Chỉ tiêu | Số dòng |", "|---|---:|",
          f"| Dòng gốc trong file | {fmt(bc['dong_goc'])} |",
          f"| − QT-01 loại (trùng mã cuộc gọi) | {fmt(bc['dong_loai'])} |",
          f"| = Dòng sạch (Du_lieu_sach) | {fmt(bc['dong_sach'])} |",
          f"| − Chặng chuyển tiếp (QT-03, không đếm sản lượng) | {fmt(bc['chang'])} |",
          f"| = Cuộc gốc | {fmt(bc['cuoc_goc'])} |"]
    L += [f"| &nbsp;&nbsp;{k} | {fmt(v)} |" for k, v in bc["cuoc_goc_theo_du_an"].items()]
    ok = "✔ ĐẠT" if bc["tong_kiem_tra_dat"] else "✘ KHÔNG KHỚP"
    L += ["", f"**Kiểm tra:** {fmt(bc['dong_goc'])} = {fmt(bc['dong_sach'])} + {fmt(bc['dong_loai'])} · "
              f"cuộc gốc = {fmt(bc['dong_sach'])} − {fmt(bc['chang'])} = {fmt(bc['cuoc_goc'])} → **{ok}**",
          "", "## Số dòng bị tác động theo quy tắc", "",
          "| Mã | Quy tắc | Hành động | Số dòng | Chi tiết |", "|---|---|---|---:|---|"]
    for ma, q in bc["quy_tac"].items():
        L.append(f"| {ma} | {q['ten']} | {q['hanh_dong']} | {fmt(q['so_dong'])} | {' · '.join(q['chi_tiet'])} |")
    L += ["", "Một dòng có thể bị nhiều quy tắc tác động (cột `ma_qt` ghi đủ). Chỉ QT-01 loại dòng.",
          "", "## Chưa có quy tắc (không tự xử lý)", ""]
    if bc["chua_co_quy_tac"]:
        L += ["| Kiểm tra | Số dòng | Ví dụ ma_cuoc_goi |", "|---|---:|---|"]
        L += [f"| {k} | {fmt(v['so_dong'])} | {', '.join(v['vi_du'])} |" for k, v in bc["chua_co_quy_tac"].items()]
        L += ["", "→ Duyệt từng nhóm, quyết định xử lý rồi nâng quy tắc lên v2 (ghi ngày, lý do)."]
    else:
        L.append("Không có.")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- CLI
def tag_cua(p: Path) -> str:
    return p.stem[len("call_log_"):] if p.stem.startswith("call_log_") else p.stem


def xu_ly_file(f: Path, ref: ThamChieu, outdir: Path) -> tuple[dict, str]:
    """Làm sạch 1 file call log, ghi 3 file kết quả vào outdir. Trả (báo cáo dạng dict, báo cáo markdown)."""
    kq = lam_sach(read_csv(f), ref, f.name)
    kq.bao_cao["phien_ban"] = ref.cfg["phien_ban"]
    tag = tag_cua(f)
    ten_ra = f"du_lieu_sach_{tag}.csv"
    outdir.mkdir(parents=True, exist_ok=True)
    kq.sach.to_csv(outdir / ten_ra, index=False, encoding="utf-8-sig")
    if len(kq.loai):
        kq.loai.to_csv(outdir / f"dong_bi_loai_{tag}.csv", index=False, encoding="utf-8-sig")
    md = viet_bao_cao(kq.bao_cao, ten_ra)
    (outdir / f"bao_cao_{tag}.md").write_text(md, encoding="utf-8")
    return kq.bao_cao, md


def mo_rong_duong_dan(args: list[str]) -> list[Path]:
    out: list[Path] = []
    for a in args:  # PowerShell không tự bung *.csv → tự bung ở đây
        hit = sorted(glob.glob(a)) if any(c in a for c in "*?[") else [a]
        out += [Path(h) for h in hit]
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Làm sạch call log theo Quy tắc làm sạch v1 (QT-01…QT-10)")
    ap.add_argument("files", nargs="+", help="call log CSV (hỗ trợ *.csv)")
    ap.add_argument("-c", "--config", type=Path, default=CONFIG_MAC_DINH)
    ap.add_argument("-o", "--outdir", type=Path, help="thư mục kết quả (mặc định OUTPUT_DIR trong .env, hoặc output/)")
    a = ap.parse_args()
    outdir = a.outdir or thu_muc(doc_env(), "OUTPUT_DIR", "output")

    files = mo_rong_duong_dan(a.files)
    thieu = [str(f) for f in files if not f.is_file()]
    if not files or thieu:
        print(f"[!] Không tìm thấy file: {thieu or a.files}", file=sys.stderr)
        return 2
    try:
        ref = nap_tham_chieu(a.config)
        ket_qua = []
        for f in files:
            bc, md = xu_ly_file(f, ref, outdir)
            if len(files) == 1:
                print(md)
            ket_qua.append(bc)
    except (ValueError, KeyError, OSError) as e:
        print(f"[!] {e}", file=sys.stderr)
        return 2

    print(f"{'File':<28} {'Gốc':>8} {'Loại':>6} {'Sạch':>8} {'Chặng':>6} {'Cuộc gốc':>9} {'Chưa QT':>8}  Kiểm tra")
    tong = dict.fromkeys(["dong_goc", "dong_loai", "dong_sach", "chang", "cuoc_goc", "dong_chua_co_qt"], 0)
    for bc in ket_qua:
        for k in tong:
            tong[k] += bc[k]
        print(f"{bc['file']:<28} {fmt(bc['dong_goc']):>8} {fmt(bc['dong_loai']):>6} {fmt(bc['dong_sach']):>8} "
              f"{fmt(bc['chang']):>6} {fmt(bc['cuoc_goc']):>9} {fmt(bc['dong_chua_co_qt']):>8}  "
              f"{'✔' if bc['tong_kiem_tra_dat'] else '✘'}")
    if len(ket_qua) > 1:
        print(f"{'TỔNG':<28} {fmt(tong['dong_goc']):>8} {fmt(tong['dong_loai']):>6} {fmt(tong['dong_sach']):>8} "
              f"{fmt(tong['chang']):>6} {fmt(tong['cuoc_goc']):>9} {fmt(tong['dong_chua_co_qt']):>8}")
    if tong["dong_chua_co_qt"]:
        print(f"[!] {fmt(tong['dong_chua_co_qt'])} dòng thuộc 'Chưa có quy tắc' — xem mục cuối báo cáo, chưa tự xử lý.")
    print(f"Kết quả → {outdir}/")
    return 0 if all(bc["tong_kiem_tra_dat"] for bc in ket_qua) else 1


if __name__ == "__main__":
    sys.exit(main())
