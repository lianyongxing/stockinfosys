#!/bin/bash
set -e

REPO_DIR="/Users/yxlian/Desktop/quant2"
cd "$REPO_DIR"

echo "开始合并数据..."
PYTHONPATH="$REPO_DIR" python -c "
import json
from pathlib import Path
from ann_report_web.merge_all import merge_all

output_dir = Path('ann_report/output')
merged_path = Path('ann_report_web/data/all_records.jsonl')
merged_path.parent.mkdir(parents=True, exist_ok=True)
records = merge_all(output_dir, merged_path)

data = list(records)
data.sort(key=lambda r: (r.get('_date', ''), r.get('stock_name', '')), reverse=True)
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
print(f'data.json: {len(data)} records')
"

DATE_STR=$(date +%Y-%m-%d)
git add ann_report/output/ ann_report_web/data/all_records.jsonl data.json
git commit -m "Update data: $DATE_STR" || echo "没有新数据需要提交"
git push origin main

echo "完成！"