#!/usr/bin/env python3
"""同步本地股票数据库：从 sw_lv1.xlsx 补全申万行业并导入全量占位符。

Excel 结构：
  lv1/lv2/lv3       股票代码 → 各层级行业 + 行业代码
  lv1_name/lv2_name/lv3_name  行业代码 → 行业名称层级映射
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd


REPO_ROOT       = Path(__file__).resolve().parent.parent
EXCEL_PATH      = REPO_ROOT / "sw_lv1.xlsx"
DB_PATH         = REPO_ROOT / "stocks_db.json"
WEB_DB_PATH     = REPO_ROOT / "ann_report_web" / "static" / "stocks_db.json"
STOCKINFOS_PATH = REPO_ROOT / "ann_report_web" / "static" / "stockinfos.json"


def normalize_code(code: object) -> str:
    return re.sub(r"\D", "", str(code)).zfill(6)


def atomic_write_json(path: Path, data: dict) -> None:
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    json.loads(json_str)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# 行业映射（code6 → 完整三级层级）
# ---------------------------------------------------------------------------

def load_industry_map(xlsx_path: Path) -> dict[str, dict]:
    """从 Excel 构建 normalized_code -> 完整三级行业信息。"""
    xls = pd.ExcelFile(xlsx_path)

    lv1_name_df = pd.read_excel(xls, sheet_name="lv1_name")
    lv2_name_df = pd.read_excel(xls, sheet_name="lv2_name")
    lv3_name_df = pd.read_excel(xls, sheet_name="lv3_name")

    lv1_code_to_name: dict[str, str] = {
        str(r["industry1_code"]).strip(): str(r["industry1_name"]).strip()
        for _, r in lv1_name_df.iterrows()
    }

    lv2_name_map: dict[str, dict] = {}
    for _, r in lv2_name_df.iterrows():
        c2 = str(r["industry2_code"]).strip()
        n1 = str(r["industry1_name"]).strip()
        c1 = next((k for k, v in lv1_code_to_name.items() if v == n1), "")
        lv2_name_map[c2] = {
            "lv2": str(r["industry2_name"]).strip(),
            "lv2_code": c2,
            "lv1": n1,
            "lv1_code": c1,
        }

    lv3_name_map: dict[str, dict] = {}
    for _, r in lv3_name_df.iterrows():
        c3 = str(r["industry3_code"]).strip()
        n2 = str(r["industry2_name"]).strip()
        c2 = next((k for k, v in lv2_name_map.items() if v["lv2"] == n2), "")
        lv2_info = lv2_name_map.get(c2, {})
        lv3_name_map[c3] = {
            "lv3": str(r["industry3_name"]).strip(),
            "lv3_code": c3,
            "lv2": lv2_info.get("lv2", n2),
            "lv2_code": lv2_info.get("lv2_code", c2),
            "lv1": lv2_info.get("lv1", ""),
            "lv1_code": lv2_info.get("lv1_code", ""),
        }

    result: dict[str, dict] = {}

    df1 = pd.read_excel(xls, sheet_name="lv1")
    for _, row in df1.iterrows():
        code = normalize_code(str(row["股票代码"]).split(".")[0])
        if not code or code == "000000":
            continue
        c1 = str(row["industry1_code"]).strip()
        result[code] = {
            "sw_lv1": str(row["申万1级"]).strip(),
            "sw_lv1_code": c1,
            "sw_lv2": "", "sw_lv2_code": "",
            "sw_lv3": "", "sw_lv3_code": "",
        }

    df2 = pd.read_excel(xls, sheet_name="lv2")
    for _, row in df2.iterrows():
        code = normalize_code(str(row["股票代码"]).split(".")[0])
        if not code or code == "000000":
            continue
        c2 = str(row["industry2_code"]).strip()
        lv2_info = lv2_name_map.get(c2, {})
        entry = result.setdefault(code, {"sw_lv1": "", "sw_lv1_code": "", "sw_lv2": "", "sw_lv2_code": "", "sw_lv3": "", "sw_lv3_code": ""})
        entry["sw_lv2"] = str(row["申万2级"]).strip()
        entry["sw_lv2_code"] = c2
        if lv2_info.get("lv1") and not entry.get("sw_lv1"):
            entry["sw_lv1"] = lv2_info["lv1"]
            entry["sw_lv1_code"] = lv2_info.get("lv1_code", "")

    df3 = pd.read_excel(xls, sheet_name="lv3")
    for _, row in df3.iterrows():
        code = normalize_code(str(row["股票代码"]).split(".")[0])
        if not code or code == "000000":
            continue
        c3 = str(row["industry3_code"]).strip()
        lv3_info = lv3_name_map.get(c3, {})
        entry = result.setdefault(code, {"sw_lv1": "", "sw_lv1_code": "", "sw_lv2": "", "sw_lv2_code": "", "sw_lv3": "", "sw_lv3_code": ""})
        entry["sw_lv3"] = str(row["申万3级"]).strip()
        entry["sw_lv3_code"] = c3
        if lv3_info.get("lv2") and not entry.get("sw_lv2"):
            entry["sw_lv2"] = lv3_info["lv2"]
            entry["sw_lv2_code"] = lv3_info.get("lv2_code", "")
        if lv3_info.get("lv1") and not entry.get("sw_lv1"):
            entry["sw_lv1"] = lv3_info["lv1"]
            entry["sw_lv1_code"] = lv3_info.get("lv1_code", "")

    return result


# ---------------------------------------------------------------------------
# 全量占位符导入
# ---------------------------------------------------------------------------

def _add_placeholders(db: dict, xlsx_path: Path, stock_industry: dict) -> int:
    """把 Excel 里所有股票以占位符写入 DB，已存在的跳过。返回新增数量。"""
    stocks = db.setdefault("stocks", {})
    existing_codes = {v.get("code", "") for v in stocks.values()}

    xls = pd.ExcelFile(xlsx_path)
    # 收集每只股票最细粒度的基本信息（lv3 > lv2 > lv1）
    seen: dict[str, dict] = {}
    for sheet, name_col in [("lv3", "申万3级"), ("lv2", "申万2级"), ("lv1", "申万1级")]:
        df = pd.read_excel(xls, sheet_name=sheet)
        for _, row in df.iterrows():
            raw = str(row["股票代码"]).strip()
            if "." not in raw:
                continue
            code6 = normalize_code(raw.split(".")[0])
            if code6 == "000000":
                continue
            if code6 not in seen:
                seen[code6] = {
                    "name": str(row["股票简称"]).strip(),
                    "full_code": raw,
                    "market": raw.split(".")[1],
                }

    added = 0
    for code6, info in seen.items():
        if code6 in existing_codes:
            continue
        full_code = info["full_code"]
        if full_code in stocks:
            continue
        ind = stock_industry.get(code6, {})
        stocks[full_code] = {
            "name": info["name"],
            "code": code6,
            "market": info["market"],
            "full_code": full_code,
            "sw_lv1": ind.get("sw_lv1", ""),
            "sw_lv1_code": ind.get("sw_lv1_code", ""),
            "sw_lv2": ind.get("sw_lv2", ""),
            "sw_lv2_code": ind.get("sw_lv2_code", ""),
            "sw_lv3": ind.get("sw_lv3", ""),
            "sw_lv3_code": ind.get("sw_lv3_code", ""),
            "sw_industry": (ind.get("sw_lv3") or ind.get("sw_lv2") or ind.get("sw_lv1") or ""),
            "industry": "-",
            "business": "-",
            "rating": 0,
            "tags": [],
            "report_file": "",
            "add_date": "",
            "price": "",
            "change_percent": "",
            "market_cap": "-",
            "profit": "-",
            "gross_margin": "-",
            "net_margin": "-",
            "deduct_net_margin": "-",
            "pe": "-",
            "transfer_count": 0,
            "transfer_stages": [],
            "last_transfer_date": "",
        }
        added += 1
    return added


# ---------------------------------------------------------------------------
# SW 行业 + 报告元数据 合并
# ---------------------------------------------------------------------------

def _merge_into(db: dict, stock_industry: dict, report_map: dict) -> tuple[int, int]:
    """就地更新 db 中所有股票的 SW 行业字段和报告元数据。"""
    stocks = db.get("stocks", {})
    matched = 0
    unmatched: list[str] = []

    for stock_code, info in stocks.items():
        code_norm = normalize_code(stock_code.split(".")[0])
        ind = stock_industry.get(code_norm)

        if not ind:
            unmatched.append(f"{stock_code} ({info.get('name', '')})")
        else:
            for field in ("sw_lv1", "sw_lv2", "sw_lv3",
                          "sw_lv1_code", "sw_lv2_code", "sw_lv3_code"):
                val = ind.get(field, "")
                if val:
                    info[field] = val
            info["sw_industry"] = (
                ind.get("sw_lv3") or ind.get("sw_lv2") or ind.get("sw_lv1")
                or info.get("sw_industry", "")
            )
            matched += 1

        report = report_map.get(info.get("name", ""), {})
        if report:
            if report.get("report_file"):
                info["report_file"] = report["report_file"]
            if report.get("industry", "-") not in ("", "-"):
                info["industry"] = report["industry"]
            if report.get("business", "-") not in ("", "-"):
                info["business"] = report["business"]

    if unmatched:
        print(f"  未匹配 ({len(unmatched)}):")
        for item in unmatched[:5]:
            print(f"    {item}")
        if len(unmatched) > 5:
            print(f"    ... 共 {len(unmatched)} 只")
    return matched, len(unmatched)


# ---------------------------------------------------------------------------
# 报告元数据
# ---------------------------------------------------------------------------

def load_report_map(stockinfos_path: Path) -> dict[str, dict]:
    if not stockinfos_path.exists():
        return {}
    with open(stockinfos_path, encoding="utf-8") as f:
        items = json.load(f)
    report_map: dict[str, dict] = {}
    for item in items:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        content = str(item.get("content", ""))
        report_map[name] = {
            "report_file": str(item.get("file", "")).strip(),
            "industry": _extract_industry(content),
            "business": _extract_business(content),
        }
    return report_map


def _extract_industry(content: str) -> str:
    for marker in ["**一句话行业定位**：", "*一句话行业定位*：", "一句话行业定位："]:
        idx = content.find(marker)
        if idx >= 0:
            line = content[idx + len(marker):].splitlines()[0].strip()
            if line:
                return line
    return "-"


def _extract_business(content: str) -> str:
    for marker in ["**主营业务描述**：", "*主营业务描述*：", "主营业务描述："]:
        idx = content.find(marker)
        if idx >= 0:
            tail = content[idx + len(marker):]
            stop = tail.find("\n\n###")
            if stop < 0:
                stop = tail.find("\n###")
            snippet = tail[:stop] if stop >= 0 else tail
            if "\n" in snippet and len(snippet.split("\n")[0].strip()) > 20:
                snippet = snippet.split("\n")[0]
            snippet = re.sub(r"\s+", " ", snippet).strip()
            if snippet:
                return snippet
    return "-"


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> dict:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"未找到数据源: {EXCEL_PATH}")
    print(f"[数据源] {EXCEL_PATH.name}")

    stock_industry = load_industry_map(EXCEL_PATH)
    print(f"  行业数据：{len(stock_industry)} 只股票")

    if not DB_PATH.exists():
        raise FileNotFoundError(f"未找到数据库: {DB_PATH}")

    report_map = load_report_map(STOCKINFOS_PATH)
    print(f"  研究报告：{len(report_map)} 份")

    results = {}
    for label, path in [("root", DB_PATH), ("static", WEB_DB_PATH)]:
        if not path.exists():
            print(f"  跳过 {label}（文件不存在）")
            continue

        with open(path, "r", encoding="utf-8") as f:
            db = json.load(f)

        added = _add_placeholders(db, EXCEL_PATH, stock_industry)
        matched, unmatched_count = _merge_into(db, stock_industry, report_map)

        db.setdefault("stats", {})
        db["stats"]["total_stocks"] = len(db.get("stocks", {}))

        atomic_write_json(path, db)

        total = len(db.get("stocks", {}))
        print(f"[{label}] 新增占位符 {added}, SW匹配 {matched}/{total}")
        results[label] = {
            "added": added,
            "matched": matched,
            "unmatched": unmatched_count,
            "total": total,
        }

    results["source"] = "excel"
    return results


if __name__ == "__main__":
    result = main()
    print("\n完成:", result)
