"""Flask Web 服务：展示股权报告提取结果。"""

from __future__ import annotations

import json
from pathlib import Path

import requests
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

@app.route("/stockinfos.json")
def stockinfos_json():
    return send_file(SCRIPT_DIR / "static" / "stockinfos.json", mimetype="application/json")

@app.route("/stock_basics.json")
def stock_basics():
    return send_file(SCRIPT_DIR / "static" / "stock_basics.json")

@app.route("/stockinfos.html")
def stockinfos():
    return send_file(SCRIPT_DIR / "static" / "stockinfos.html")


@app.route("/api/stockinfos", methods=["GET", "POST"])
def api_stockinfos():
    json_path = SCRIPT_DIR / "static" / "stockinfos.json"
    from datetime import datetime, timezone, timedelta
    
    if request.method == "GET":
        if not json_path.exists():
            return jsonify([])
        with open(json_path, encoding="utf-8") as f:
            return jsonify(json.load(f))
    
    data = request.get_json()
    if not data or not data.get("name") or not data.get("content"):
        return jsonify({"error": "缺少名称或内容"}), 400
    
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            items = json.load(f)
    else:
        items = []
    
    name = data["name"].strip()
    content = data["content"].strip()
    tz = timezone(timedelta(hours=8))
    add_date = datetime.now(tz).strftime("%Y-%m-%d")
    
    file_name = f"{name}.md"
    existing = next((i for i, x in enumerate(items) if x["name"] == name), None)
    
    md_header = f"---\n添加日期: {add_date}\n---\n\n"
    full_content = md_header + content
    
    if existing is not None:
        items[existing] = {"name": name, "file": file_name, "content": content, "add_date": add_date}
    else:
        items.append({"name": name, "file": file_name, "content": content, "add_date": add_date})
    
    md_path = SCRIPT_DIR.parent / "stockinfos" / file_name
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    
    return jsonify({"success": True, "items": items})


@app.route("/api/quote")
def api_quote():
    codes = request.args.getlist("codes")
    if not codes:
        return jsonify({"error": "缺少股票代码"}), 400

    sina_codes = []
    for code in codes:
        code = code.strip()
        if not code:
            continue
        if code.startswith("sh") or code.startswith("sz"):
            sina_codes.append(code)
        else:
            if len(code) == 6 and code.isdigit():
                if code[0] in "69":  # 沪市或科创板
                    sina_codes.append(f"sh{code}")
                else:
                    sina_codes.append(f"sz{code}")

    if not sina_codes:
        return jsonify({"error": "无效的股票代码"}), 400

    try:
        url = "https://hq.sinajs.cn/list=" + ",".join(sina_codes)
        response = requests.get(url, timeout=10, headers={
            "Referer": "http://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response.raise_for_status()

        import re
        quotes = {}
        for line in response.text.strip().split("\n"):
            if not line or "hq_str_" not in line:
                continue
            match = re.match(r'var hq_str_(sh|sz)(\d+)="(.*)"', line)
            if not match:
                continue
            market = match.group(1)
            code = match.group(2)
            data = match.group(3)
            if not data:
                continue
            fields = data.split(",")
            if len(fields) < 6:
                continue
            name = fields[0]
            current_price = float(fields[3]) if fields[3] else 0
            pre_close = float(fields[2]) if fields[2] else 0
            change_percent = round(((current_price - pre_close) / pre_close * 100), 2) if pre_close else 0
            quotes[code] = {
                "name": name,
                "price": current_price,
                "change_percent": change_percent
            }

        return jsonify(quotes)
    except requests.Timeout:
        return jsonify({"error": "请求超时"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
