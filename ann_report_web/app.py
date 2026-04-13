"""Flask Web 服务：展示股权报告提取结果。"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "ann_report" / "output"
DATA_DIR = SCRIPT_DIR / "data"
MERGED_PATH = DATA_DIR / "all_records.jsonl"


def load_records() -> tuple[list[dict], str]:
    import sys
    from datetime import datetime, timezone, timedelta
    sys.path.insert(0, str(SCRIPT_DIR.parent))
    from ann_report_web.merge_all import merge_all
    records, update_time = merge_all(OUTPUT_DIR, MERGED_PATH)

    return records, update_time


@app.route("/")
def index():
    return send_file(SCRIPT_DIR / "static" / "index.html")


@app.route("/api/records")
def api_records():
    records, _ = load_records()

    keyword = request.args.get("q", "").strip()
    if keyword:
        records = [r for r in records if _match(r, keyword)]

    stage = request.args.get("stage", "").strip()
    if stage:
        records = [r for r in records if r.get("stage") == stage]

    doc_type = request.args.get("doc_type", "").strip()
    if doc_type:
        records = [r for r in records if r.get("doc_type") == doc_type]

    date_from = request.args.get("date_from", "").strip()
    if date_from:
        records = [r for r in records if r.get("_date", "") >= date_from]

    date_to = request.args.get("date_to", "").strip()
    if date_to:
        records = [r for r in records if r.get("_date", "") <= date_to]

    recipient = request.args.get("recipient", "").strip()
    if recipient:
        records = [r for r in records if recipient in (r.get("_recipients_full", "") or "")]

    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(100, max(10, request.args.get("page_size", 50, type=int)))
    total = len(records)
    start = (page - 1) * page_size
    end = start + page_size
    page_records = records[start:end]

    return jsonify({
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": page_records,
    })


@app.route("/data.json")
def data_json():
    records, update_time = load_records()
    return jsonify({"records": records, "update_time": update_time})

def api_refresh():
    records, update_time = load_records()
    return jsonify({"total": len(records), "message": "刷新成功"})


def _match(record: dict, keyword: str) -> bool:
    k = keyword.lower()
    fields = [
        record.get("stock_name", ""),
        record.get("stock_code", ""),
        record.get("stage", ""),
        record.get("doc_type", ""),
        record.get("_date", ""),
        record.get("content", ""),
        record.get("_price", ""),
        record.get("_recipients_full", ""),
    ]
    parsed = record.get("_parsed") or {}
    for v in parsed.values():
        if isinstance(v, str):
            fields.append(v)
        elif isinstance(v, dict):
            for sv in v.values():
                if isinstance(sv, str):
                    fields.append(sv)
    for field in fields:
        if k in str(field).lower():
            return True
    return False


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
