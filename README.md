# quant2

量化投资数据采集与分析系统。

## 项目结构

```
quant2/
├── ann_report/          # 每日公告下载 + PDF解析 + LLM信息抽取
├── ann_report_web/      # 股权报告展示Web界面
├── stockinfos/          # 股票基本面研究报告
├── scripts/             # 定时任务脚本
└── bullet_cli/          # 子弹笔记CLI工具
```

## 功能模块

### 1. ann_report (股权报告采集)

- 自动下载巨潮资讯网公告PDF
- 使用LLM提取定增/询价转让关键信息
- 定时任务自动更新

### 2. ann_report_web (Web展示)

- 股权转让信息查询（按日期/阶段/类型筛选）
- 股票基本面管理
- 股票研究报告（支持新增markdown报告）
- 实时行情获取

### 3. stockinfos (研究报告)

- 股票基本面分析报告（Markdown格式）
- 支持新增/编辑/展示

## 快速开始

```bash
# 安装依赖
pip install -r ann_report_web/requirements.txt

# 启动Web服务
cd ann_report_web
python app.py

# 访问 http://localhost:5002
```

## GitHub Pages

每次push到main分支自动部署：
- https://lianyongxing.github.io/stockinfosys/