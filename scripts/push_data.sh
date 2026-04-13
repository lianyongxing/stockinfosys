#!/bin/bash
set -e

REPO_DIR="/Users/yxlian/Desktop/quant2"
cd "$REPO_DIR"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY

echo "开始合并数据..."
PYTHONPATH="$REPO_DIR" python -c "
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from ann_report_web.merge_all import merge_all

output_dir = Path('ann_report/output')
merged_path = Path('ann_report_web/data/all_records.jsonl')
merged_path.parent.mkdir(parents=True, exist_ok=True)
records, update_time = merge_all(output_dir, merged_path)

data = list(records)
data.sort(key=lambda r: (r.get('_date', ''), r.get('stock_name', '')), reverse=True)
output = {'records': data, 'update_time': update_time}
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False)
print(f'data.json: {len(data)} records')
"

DATE_STR=$(date +%Y-%m-%d)
git add ann_report/output/ ann_report_web/data/all_records.jsonl data.json
git commit -m "Update data: $DATE_STR" || echo "没有新数据需要提交"
git push origin main

echo "完成！"