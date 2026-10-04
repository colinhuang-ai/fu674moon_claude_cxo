#!/usr/bin/env python3
"""
pii_anon.py — Anonymize PII cho CSV / XLSX / TXT (tối ưu cho dữ liệu VN).

Phương thức theo cột:
  token      : PREFIX_<HMAC-SHA256[:10]>  — deterministic, giữ được JOIN giữa các file
  pseudonym  : PREFIX_001, _002...        — dễ đọc, nhất quán qua mapping file
  mask       : giữ N ký tự cuối (vd ******5678)
  redact     : thay bằng [REDACTED]
  date_month : cắt ngày về YYYY-MM
  year       : chỉ giữ năm (ngày sinh)
  drop       : xóa cột
  scan       : quét free-text bằng regex (EMAIL, PHONE, CCCD, CMND, CARD, IP) + tên đã biết
  keep       : giữ nguyên

Dùng:
  python pii_anon.py detect  data/*.csv                       # gợi ý cột PII + sinh config mẫu
  python pii_anon.py run     data/*.csv data/*.xlsx -c pii_config.json -o out/
  python pii_anon.py scan-text "Gọi lại 0912 345 678, email a@b.vn"

Khóa HMAC: env PII_ANON_KEY, hoặc --key-file (mặc định .pii_key, tự tạo nếu chưa có).
KHÔNG commit .pii_key và mapping file (chứa giá trị thật → re-identify được).
File gốc không bị sửa; output ghi vào thư mục -o với hậu tố _anon.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import secrets
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------- regex PII (VN)
PATTERNS: dict[str, re.Pattern] = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    # CCCD 12 số (3 số đầu = mã tỉnh 0xx) — chạy trước PHONE
    "CCCD": re.compile(r"(?<!\d)0\d{11}(?!\d)"),
    # Thẻ thanh toán 13-19 số (kiểm Luhn bên dưới)
    "CARD": re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
    # SĐT VN: di động 0[35789]xxxxxxxx, cố định 02x..., +84/84; cho phép dấu cách . -
    "PHONE": re.compile(r"(?<![\d+])(?:\+?84[ .-]?|0)(?:[35789]|2\d)(?:[ .-]?\d){7,8}(?!\d)"),
    # CMND cũ 9 số — dễ false positive, tắt mặc định
    "CMND": re.compile(r"(?<!\d)\d{9}(?!\d)"),
    "IP": re.compile(r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\d)"),
}
DEFAULT_SCAN_TYPES = ["EMAIL", "CCCD", "CARD", "PHONE", "IP"]

NAME_HINTS = {
    "pseudonym": ["ho_ten", "hoten", "ten", "name", "full_name", "khach_hang_ten", "nguoi_lien_he"],
    "mask": ["sdt", "so_dien_thoai", "dien_thoai", "phone", "mobile", "tel",
             "cccd", "cmnd", "so_giay_to", "stk", "so_tai_khoan", "account_no"],
    "redact": ["email", "dia_chi", "address", "ip"],
    "year": ["ngay_sinh", "dob", "birth"],
    "token": ["ma_nv", "ma_nhan_vien", "employee_id", "ma_tong_dai", "ma_agent",
              "ma_khach_hang", "customer_id", "user_id"],
    "date_month": ["ngay_vao_lam", "hire_date"],
}


def luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits][::-1]
    s = sum(d[0::2]) + sum(sum(divmod(x * 2, 10)) for x in d[1::2])
    return s % 10 == 0


def norm_key(v: str, normalize: bool) -> str:
    v = unicodedata.normalize("NFC", str(v)).strip()
    if normalize:  # "ext 2005" == "EXT2005"
        v = re.sub(r"\s+", "", v).upper()
    return v


# ---------------------------------------------------------------- core
class Anonymizer:
    def __init__(self, key: bytes, mapping_path: Path | None, scan_types: list[str]):
        self.key = key
        self.mapping_path = mapping_path
        self.scan_types = scan_types
        self.pseudo: dict[str, dict[str, str]] = defaultdict(dict)  # prefix -> {real: alias}
        self.known_names: dict[str, str] = {}                       # real name -> alias (cho scan)
        self.stats: Counter = Counter()
        if mapping_path and mapping_path.exists():
            data = json.loads(mapping_path.read_text(encoding="utf-8"))
            for p, m in data.get("pseudonym", {}).items():
                self.pseudo[p].update(m)
            self.known_names.update(data.get("known_names", {}))

    # -- methods
    def token(self, v: str, prefix: str, normalize: bool) -> str:
        k = norm_key(v, normalize)
        h = hmac.new(self.key, f"{prefix}|{k}".encode(), hashlib.sha256).hexdigest()[:10]
        return f"{prefix}_{h}"

    def pseudonym(self, v: str, prefix: str, normalize: bool) -> str:
        k = norm_key(v, normalize)
        m = self.pseudo[prefix]
        if k not in m:
            m[k] = f"{prefix}_{len(m) + 1:03d}"
        raw = unicodedata.normalize("NFC", str(v)).strip()
        self.known_names[raw] = m[k]  # giữ dạng gốc để tìm trong free-text
        return m[k]

    @staticmethod
    def mask(v: str, keep_last: int) -> str:
        s = re.sub(r"\s", "", str(v))
        return "*" * max(len(s) - keep_last, 0) + s[-keep_last:] if keep_last else "*" * len(s)

    @staticmethod
    def to_period(v: str, fmt: str) -> str:
        d = pd.to_datetime(v, errors="coerce", dayfirst=False)
        return v if pd.isna(d) else d.strftime(fmt)

    def scan_text(self, text: str) -> str:
        if not text:
            return text
        out = text
        # tên đã biết (từ các cột pseudonym) — dài trước để tránh thay một phần
        for real in sorted(self.known_names, key=len, reverse=True):
            if len(real) >= 4 and real in out:
                self.stats["SCAN:NAME"] += out.count(real)
                out = out.replace(real, self.known_names[real])
        for t in self.scan_types:
            pat = PATTERNS[t]

            def _sub(m, t=t):
                raw = m.group(0)
                if t == "CARD":
                    digits = re.sub(r"\D", "", raw)
                    if not luhn_ok(digits):
                        return raw
                self.stats[f"SCAN:{t}"] += 1
                return f"[{t}]"
            out = pat.sub(_sub, out)
        return out

    # -- apply 1 cell
    def apply(self, v, rule: dict):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return v
        m = rule["method"]
        prefix = rule.get("prefix", "ID")
        normalize = rule.get("normalize", True)
        if m == "keep":
            return v
        if m == "token":
            return self.token(v, prefix, normalize)
        if m == "pseudonym":
            return self.pseudonym(v, prefix, normalize)
        if m == "mask":
            return self.mask(v, rule.get("keep_last", 4))
        if m == "redact":
            return rule.get("text", "[REDACTED]")
        if m == "date_month":
            return self.to_period(v, "%Y-%m")
        if m == "year":
            return self.to_period(v, "%Y")
        if m == "scan":
            return self.scan_text(str(v))
        raise ValueError(f"method không hợp lệ: {m}")

    def save_mapping(self):
        if not self.mapping_path:
            return
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
        self.mapping_path.write_text(json.dumps(
            {"pseudonym": self.pseudo, "known_names": self.known_names},
            ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- dataframe
def anonymize_df(df: pd.DataFrame, cfg: dict, an: Anonymizer, report: dict) -> pd.DataFrame:
    cols_cfg: dict = cfg.get("columns", {})
    auto_scan = cfg.get("auto_scan_unlisted", True)
    out = df.copy()
    # pseudonym chạy trước để known_names có sẵn cho các cột scan
    order = sorted(out.columns, key=lambda c: 0 if cols_cfg.get(c, {}).get("method") == "pseudonym" else 1)
    for col in order:
        rule = cols_cfg.get(col)
        if rule is None:
            if not auto_scan:
                continue
            rule = {"method": "scan"}
        if rule["method"] == "drop":
            out = out.drop(columns=[col])
            report["columns"][col] = {"method": "drop"}
            continue
        before = out[col].copy()
        out[col] = out[col].map(lambda v: an.apply(v, rule))
        changed = int((before != out[col]).sum())
        if rule["method"] != "scan" or changed:
            report["columns"][col] = {"method": rule["method"], "changed_cells": changed}
    return out


def read_csv(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def process_file(p: Path, cfg: dict, an: Anonymizer, outdir: Path) -> dict:
    report = {"file": str(p), "columns": {}}
    suffix = p.suffix.lower()
    dst = outdir / f"{p.stem}_anon{p.suffix}"
    if suffix == ".csv":
        df = read_csv(p)
        report["rows"] = len(df)
        anonymize_df(df, cfg, an, report).to_csv(dst, index=False, encoding="utf-8-sig")
    elif suffix in (".xlsx", ".xlsm", ".xls"):
        sheets = pd.read_excel(p, sheet_name=None, dtype=str, keep_default_na=False)
        report["rows"] = {}
        with pd.ExcelWriter(dst.with_suffix(".xlsx"), engine="openpyxl") as w:
            for name, df in sheets.items():
                report["rows"][name] = len(df)
                sub = {"columns": {}}
                anonymize_df(df, cfg, an, sub).to_excel(w, sheet_name=name, index=False)
                report["columns"][name] = sub["columns"]
    elif suffix in (".txt", ".log", ".md", ".json"):
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        report["rows"] = len(lines)
        dst.write_text("".join(an.scan_text(l) for l in lines), encoding="utf-8")
    else:
        report["skipped"] = f"định dạng không hỗ trợ: {suffix}"
        return report
    report["output"] = str(dst)
    return report


# ---------------------------------------------------------------- detect
def detect(paths: list[Path], sample: int = 2000) -> dict:
    suggestion = {"columns": {}, "auto_scan_unlisted": True, "scan_types": DEFAULT_SCAN_TYPES}
    for p in paths:
        frames = ({p.name: read_csv(p)} if p.suffix.lower() == ".csv"
                  else pd.read_excel(p, sheet_name=None, dtype=str, keep_default_na=False))
        for sheet, df in frames.items():
            print(f"\n== {sheet} ({len(df)} dòng)")
            for col in df.columns:
                vals = df[col].head(sample)
                vals = vals[vals.str.strip() != ""]
                hits = {t: round(float(vals.str.contains(PATTERNS[t]).mean()) * 100, 1)
                        for t in ["EMAIL", "PHONE", "CCCD"]} if len(vals) else {}
                lc = col.lower()
                method = next((m for m, keys in NAME_HINTS.items() if any(k == lc or k in lc for k in keys)), None)
                if not method and hits:
                    top = max(hits, key=hits.get)
                    if hits[top] >= 50:
                        method = "redact" if top == "EMAIL" else "mask"
                    elif hits[top] > 0:
                        method = "scan"
                flag = f"→ {method}" if method else ""
                print(f"  {col:<28} {str({k: v for k, v in hits.items() if v}):<30} {flag}")
                if method and col not in suggestion["columns"]:
                    rule = {"method": method}
                    if method in ("token", "pseudonym"):
                        base = re.sub(r"^(ma|so|id)_", "", lc)
                        rule["prefix"] = re.sub(r"[^A-Z]", "", base.upper())[:8] or "ID"
                        rule["normalize"] = True
                    if method == "mask":
                        rule["keep_last"] = 3
                    suggestion["columns"][col] = rule
    return suggestion


# ---------------------------------------------------------------- CLI
def load_key(key_file: Path) -> bytes:
    import os
    if os.environ.get("PII_ANON_KEY"):
        return os.environ["PII_ANON_KEY"].encode()
    if key_file.exists():
        return key_file.read_text().strip().encode()
    k = secrets.token_hex(32)
    key_file.write_text(k)
    print(f"[!] Đã tạo khóa mới: {key_file} — giữ bí mật, dùng lại khóa này để token nhất quán giữa các lần chạy.",
          file=sys.stderr)
    return k.encode()


def main():
    ap = argparse.ArgumentParser(description="Anonymize PII cho CSV/XLSX/TXT")
    sp = ap.add_subparsers(dest="cmd", required=True)

    d = sp.add_parser("detect", help="Gợi ý cột PII, sinh config mẫu")
    d.add_argument("files", nargs="+", type=Path)
    d.add_argument("--write", type=Path, default=Path("pii_config.suggested.json"))

    r = sp.add_parser("run", help="Anonymize theo config")
    r.add_argument("files", nargs="+", type=Path)
    r.add_argument("-c", "--config", type=Path, required=True)
    r.add_argument("-o", "--outdir", type=Path, default=Path("anon_out"))
    r.add_argument("--key-file", type=Path, default=Path(".pii_key"))
    r.add_argument("--mapping", type=Path, default=Path(".pii_mapping.json"),
                   help="Lưu bảng pseudonym để nhất quán giữa các file/lần chạy (NHẠY CẢM)")

    t = sp.add_parser("scan-text", help="Test regex trên 1 chuỗi")
    t.add_argument("text")
    t.add_argument("--types", nargs="+", default=DEFAULT_SCAN_TYPES)

    a = ap.parse_args()

    if a.cmd == "detect":
        sug = detect(a.files)
        a.write.write_text(json.dumps(sug, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nConfig gợi ý → {a.write} (review trước khi dùng)")
        print("[!] Các cột cần JOIN với nhau (vd ma_tong_dai ↔ ma_agent) phải dùng CÙNG prefix.")
        return

    if a.cmd == "scan-text":
        an = Anonymizer(b"x", None, a.types)
        print(an.scan_text(a.text))
        return

    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    an = Anonymizer(load_key(a.key_file), a.mapping, cfg.get("scan_types", DEFAULT_SCAN_TYPES))
    a.outdir.mkdir(parents=True, exist_ok=True)

    # 2 lượt: lượt 1 nạp tên (pseudonym) từ mọi file để cột scan ở file khác cũng thay được tên
    pseudo_cols = {c for c, r_ in cfg.get("columns", {}).items() if r_["method"] == "pseudonym"}
    for p in a.files:
        if p.suffix.lower() == ".csv":
            df = read_csv(p)
            for c in pseudo_cols & set(df.columns):
                for v in df[c]:
                    if v.strip():
                        r_ = cfg["columns"][c]
                        an.pseudonym(v, r_.get("prefix", "ID"), r_.get("normalize", True))

    reports = [process_file(p, cfg, an, a.outdir) for p in a.files]
    an.save_mapping()
    summary = {"files": reports, "scan_hits": dict(an.stats)}
    (a.outdir / "anon_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    total = 0
    print(f"{'File':<40} {'Dòng':>8}")
    for rp in reports:
        n = rp.get("rows", 0)
        n = sum(n.values()) if isinstance(n, dict) else n
        total += n
        print(f"{Path(rp['file']).name:<40} {n:>8}  {rp.get('skipped', '')}")
    print(f"{'TỔNG':<40} {total:>8}")
    if an.stats:
        print("Scan hits:", dict(an.stats))
    print(f"Report → {a.outdir / 'anon_report.json'}")


if __name__ == "__main__":
    main()
