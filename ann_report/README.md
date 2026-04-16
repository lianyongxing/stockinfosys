# ann_report

每日公告下载 + PDF 解析 + LLM 信息抽取（巨潮资讯）。

## 安装

```bash
pip install -e ann_report
```

## 配置

```bash
cp ann_report/.env.example ann_report/.env
```

配置文件 `ann_report/.env`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini API Key | （必填） |
| `MODEL_NAME` | 模型名称 | `gemma-4-31b-it` |
| `REQUEST_INTERVAL` | LLM 请求间隔（秒） | `3.0` |
| `OUTPUT_DIR` | 输出目录 | `./output` |
| `PROMPT_PATH` | Prompt 文件路径 | `ask_prompt.txt` |

## 使用

```bash
# 处理今日
python ann_report/main.py

# 指定单日
python ann_report/main.py -s 2025-09-08

# 日期范围（刷存量）
python ann_report/main.py -s 2025-01-01 -e 2025-09-08

# 仅下载，不提取
python ann_report/main.py -s 2025-09-08 --no-extract
```

## 输出结构

每个日期目录包含：

```
output/YYYY-MM-DD/
├── *.pdf                      # 下载的 PDF 文件
├── extraction_results.jsonl   # 原始提取结果（每行一个 JSON）
└── extraction_merged.json     # 合并去重后的结果
```

## 定时任务

```bash
cd ann_report
bash scripts/setup_cron.sh  # 设置每天 23:30 自动采集
bash scripts/remove_cron.sh  # 卸载定时任务
```
