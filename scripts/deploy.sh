#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

pip install -q -r ann_report_web/requirements.txt 2>/dev/null || true

python -c "
import json
from pathlib import Path
from ann_report_web.merge_all import merge_all

output_dir = Path('ann_report/output')
merged_path = Path('ann_report_web/data/all_records.jsonl')
records = merge_all(output_dir, merged_path)

data = list(records)
data.sort(key=lambda r: (r.get('_date', ''), r.get('stock_name', '')), reverse=True)

with open('_site/data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

print(f'data.json generated: {len(data)} records')
"

mkdir -p _site
cp index.html _site/
cp ann_report_web/static/index.html _site/

git add _site/index.html _site/data.json
git commit -m "deploy: update data.json ($(date '+%Y-%m-%d %H:%M'))" || echo "Nothing to commit"
git push
