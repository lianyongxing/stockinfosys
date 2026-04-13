"""汇总 ann_report/output 下所有日期的 extraction_results.jsonl 到一个文件。"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _extract_json(text: str):
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, count=1)
        text = re.sub(r"```$", "", text).strip()
    for candidate in [text, (re.search(r"\{[\s\S]*\}", text) or type("", (), {"group": lambda s, *a: None})()).group()]:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return None


def _get_field(info: dict | None, *keys, default=""):
    if not isinstance(info, dict):
        return default
    for k in keys:
        v = info.get(k, "")
        if v and str(v).strip():
            return str(v).strip()
    return default


STAGE_ORDER = {
    "预告期": 1,
    "定价期": 2,
    "成交期": 3,
    "合规确认期": 4,
    "定增": 10,
    "未知阶段": 99,
}


def _make_event_key(info: dict | None, stock_code: str, doc_type: str) -> str:
    price = _get_field(info, "每股价格")
    return f"{stock_code}|{doc_type}|{price}"


def _has_valid_price(price: str) -> bool:
    if not price or not isinstance(price, str):
        return False
    price = price.strip()
    if not price:
        return False
    noise = {"未披露", "未提及", "未确定", "待定", "未确定价格", "未确定每股价格",
             "待定价格", "尚未确定", "未注明", "未知", "价格待定", "定价待定"}
    if price in noise:
        return False
    if any(n in price for n in noise):
        return False
    return True


def _enrich_record(record: dict) -> dict:
    info = record.get("_parsed") or {}
    record["_price"] = _get_field(info, "每股价格")
    record["_announce_date"] = _get_field(info, "日期信息", "公告日期")
    record["_est_finish_date"] = _get_field(info, "预计完成日期")
    record["_unlock_date"] = _get_field(info, "解禁日期")
    record["_transferor"] = _get_field(info, "转让方信息", "名称")
    recipients_raw = _get_field(info, "受让方信息")
    if recipients_raw:
        recipients = [r.strip() for r in recipients_raw.split("、") if r.strip()]
        record["_recipients_short"] = "、".join(recipients[:3]) + ("..." if len(recipients) > 3 else "")
        record["_recipients_full"] = "、".join(recipients)
    else:
        record["_recipients_short"] = ""
        record["_recipients_full"] = ""
    return record


def merge_all(output_dir: Path, merged_path: Path) -> list[dict]:
    seen: set[tuple] = set()
    records: list[dict] = []

    date_dirs = sorted([d for d in output_dir.iterdir() if d.is_dir()])
    print(f"扫描 {len(date_dirs)} 个日期目录...")

    for date_dir in date_dirs:
        jsonl_file = date_dir / "extraction_results.jsonl"
        if not jsonl_file.exists():
            continue

        with open(jsonl_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue

                key = (record.get("file", ""), record.get("stock_code", ""))
                if key in seen:
                    continue
                seen.add(key)

                info = _extract_json(record.get("content", ""))
                record["_parsed"] = info
                record["_date"] = date_dir.name
                record = _enrich_record(record)
                records.append(record)

    event_map: dict[str, dict] = {}
    for r in records:
        info = r.get("_parsed")
        stock_code = r.get("stock_code", "")
        doc_type = r.get("doc_type", "")
        stage = r.get("stage", "")
        ek = _make_event_key(info, stock_code, doc_type)
        date = r.get("_date", "")
        stage_order = STAGE_ORDER.get(stage, 99)

        if ek not in event_map:
            event_map[ek] = r
        else:
            existing = event_map[ek]
            existing_stage = existing.get("stage", "")
            existing_order = STAGE_ORDER.get(existing_stage, 99)
            existing_date = existing.get("_date", "")
            if date > existing_date:
                event_map[ek] = r

    records = list(event_map.values())
    before_count = len(records)
    records = [r for r in records if r.get("stage") != "预告期"]
    print(f"过滤预告期后: {before_count} -> {len(records)} 条记录")

    before_price = len(records)
    records = [r for r in records if _has_valid_price(r.get("_price", ""))]
    print(f"过滤无价格后: {before_price} -> {len(records)} 条记录")

    records.sort(key=lambda r: (r.get("_date", ""), r.get("stock_name", "")), reverse=True)

    merged_path.parent.mkdir(parents=True, exist_ok=True)
    with open(merged_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"汇总完成: 共 {len(records)} 条记录 -> {merged_path}")
    return records


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir.parent / "ann_report" / "output"
    merged_path = script_dir / "data" / "all_records.jsonl"

    records = merge_all(output_dir, merged_path)
    print(f"统计: {len(records)} 条记录")


if __name__ == "__main__":
    main()
