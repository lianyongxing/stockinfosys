# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo combines three largely independent Python projects around A-share market workflows:

- `ann_report/`: downloads CNInfo announcements, saves PDFs by date, runs LLM extraction, and writes per-day JSONL/merged outputs.
- `ann_report_web/`: Flask app and static site assets for browsing extracted announcement records plus manually managed stock research data.
- `bullet_cli/`: a separate terminal stock-watching CLI. There is an older root package and a newer packaged implementation under `bullet_cli/new_bullet_cli/`.

The top-level `stockinfos/`, `stocks_db.json`, and `ann_report_web/static/user_data/` directories are content/data stores used by the web app rather than standalone Python packages.

## Common commands

### Web app (`ann_report_web`)

Install and run locally:

```bash
pip install -r ann_report_web/requirements.txt
python ann_report_web/app.py
```

The READMEs disagree on the port (`5001` vs `5002`); check the current `app.run(...)` in `ann_report_web/app.py` before assuming the local URL.

### Announcement pipeline (`ann_report`)

Install package in editable mode:

```bash
pip install -e ann_report
```

Set local config first:

```bash
cp ann_report/.env.example ann_report/.env
```

Run the daily pipeline:

```bash
python ann_report/main.py
```

Run a single date:

```bash
python ann_report/main.py -s 2025-09-08
```

Run a date range:

```bash
python ann_report/main.py -s 2025-01-01 -e 2025-09-08
```

Download only, skip LLM extraction:

```bash
python ann_report/main.py -s 2025-09-08 --no-extract
```

Rebuild merged announcement data without starting Flask:

```bash
python ann_report_web/merge_all.py
```

### Scheduled jobs and data publishing

Set up or remove the local scheduled job used by this repo:

```bash
bash ann_report/scripts/setup_cron.sh
bash ann_report/scripts/remove_cron.sh
```

Run the daily automation script manually:

```bash
bash scripts/daily.sh
```

That script runs `python -m ann_report.main`, rebuilds `data.json`, then commits and pushes generated data.

### `bullet_cli`

Legacy install path from the repo root subproject:

```bash
python bullet_cli/setup.py install
```

Common usage:

```bash
bullet add <stock keyword>
bullet remove
bullet fly --interval 3 --fish
bullet --help
```

For the newer packaged implementation under `bullet_cli/new_bullet_cli/`, install dev dependencies and run tests from that subdirectory:

```bash
pip install -e .[dev]
pytest
pytest tests/test_api/test_eastmoney.py
pytest tests/test_core/test_config.py
```

## Testing and verification

There is no single repo-wide test/lint/build entrypoint or top-level config like `Makefile`, `pytest.ini`, `tox.ini`, or `ruff.toml`.

What exists today:

- `bullet_cli/new_bullet_cli/` has the only structured automated test suite and its pytest config lives in `bullet_cli/new_bullet_cli/pyproject.toml`.
- Repo-root files like `test_api.py`, `test_extract_gemini.py`, and `test_list_models.py` are ad hoc scripts for manual API/model checks, not an integrated test harness.
- GitHub Pages deployment is defined in `.github/workflows/deploy.yml` and effectively serves as the production build recipe for the static announcement dataset.

## High-level architecture

### 1. Announcement ingestion flow

The `ann_report` package is a linear pipeline:

1. `ann_report/main.py` parses date arguments and iterates day by day.
2. `ann_report/download.py` queries CNInfo, filters for target announcement titles, and downloads PDFs into `ann_report/output/YYYY-MM-DD/`.
3. `ann_report/extract.py` reads PDF text, skips obviously irrelevant files, sends relevant content to the configured LLM, and appends one JSON object per PDF into `extraction_results.jsonl`.
4. `ann_report/merge.py` writes `extraction_merged.json` for that day.

Configuration is centralized in `ann_report/config.py`, which loads `ann_report/.env` and resolves model/provider, prompt file, request interval, and output path.

### 2. Aggregation layer between ingestion and UI

`ann_report_web/merge_all.py` is the bridge between raw extraction output and anything user-facing.

It scans every dated directory under `ann_report/output/`, parses the LLM JSON-like payloads from `extraction_results.jsonl`, enriches records with derived fields, deduplicates by event, filters out records such as `预告期` or items without usable prices, sorts the final list, and writes `ann_report_web/data/all_records.jsonl`.

When working on record display bugs or filtering behavior, this file is usually as important as the Flask routes or frontend code because many “UI” fields are actually derived here.

### 3. Web app data model

`ann_report_web/app.py` mixes dynamic aggregation endpoints with file-backed CRUD-style endpoints.

There is also a stray `api_refresh()` function in this file without an `@app.route(...)` decorator. Treat it as dead or unfinished code unless it gets wired up explicitly.

There are two distinct data families:

- Announcement data: `/api/records` and `/data.json` call `load_records()`, which reruns `merge_all(...)` against `ann_report/output` and `ann_report_web/data/all_records.jsonl`.
- Research/user-managed data: stock basics, quotes, report metadata, and stock DB files are read from or written to JSON under `ann_report_web/static/` and `ann_report_web/static/user_data/`, with some writes mirrored to repo-root files such as `stocks_db.json`.

This means the app is not purely database-backed: many mutations are direct file writes, so changes to JSON schema or paths affect both API handlers and checked-in content.

### 4. Static deployment path

Production Pages deployment is not a Flask deployment.

`.github/workflows/deploy.yml` installs `ann_report_web` requirements, runs `ann_report_web.merge_all.merge_all(...)` in a one-off Python command to generate a top-level `data.json`, then publishes the repository contents as a GitHub Pages artifact. If a change only works in Flask but does not preserve this static generation path, Pages will drift from local behavior.

### 5. Content-driven research pages

`stockinfos/` stores Markdown reports. The web app’s `/api/sync-reports` endpoint scans that directory, updates `stockinfos/dates.json`, and rebuilds `ann_report_web/static/stockinfos.json`. For report-listing or report-editing issues, inspect both the Markdown source directory and the generated JSON metadata.

## Notes for future edits

- Treat `ann_report/output/`, `ann_report_web/data/`, top-level `data.json`, and JSON files under `ann_report_web/static/` as generated-or-content artifacts that are part of the app’s behavior, not disposable temp files.
- Be careful when changing file paths: the same data may be referenced by local Flask routes, scheduled shell scripts, and the GitHub Pages workflow.
- The repo currently contains hardcoded Gemini API keys and proxy defaults in parts of the announcement pipeline; if behavior differs across machines, inspect `ann_report/config.py` and `ann_report/extract.py` before assuming configuration is fully externalized.
