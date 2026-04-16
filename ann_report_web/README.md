# ann_report_web

股权报告提取结果的展示页面。

## 本地开发

```bash
cd ann_report_web
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5001
```

## GitHub Pages 部署

### 首次设置

1. 在 GitHub 仓库 Settings → Pages → Source 选择 **GitHub Actions**
2. 推送代码后，GitHub Actions 自动触发构建并部署
3. 访问 `https://<username>.github.io/<repo>/`

### 部署流程

每次 push 到 `main` 分支：
1. GitHub Actions 运行 `merge_all.py`，将所有日期数据合并
2. 生成静态 `data.json`
3. 部署 `index.html` + `data.json` 到 GitHub Pages
