# Full Court Analytics 2.0

Production-style sports analytics pipeline for daily game projections, market edge detection, and post-game grading.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [Repository Structure](#repository-structure)
- [Data Pipeline](#data-pipeline)
- [Modeling Architecture](#modeling-architecture)
- [Automation Workflow](#automation-workflow)
- [Streamlit Dashboard](#streamlit-dashboard)
- [Installation](#installation)
- [Quickstart (60 Seconds)](#quickstart-60-seconds)
- [Output Contracts](#output-contracts)
- [Notes](#notes)
- [Troubleshooting](#troubleshooting)

## Overview

Full Court Analytics is built as an end-to-end system:

1. Ingest matchup and market data from external sources
2. Build structured daily datasets by sport/date
3. Generate model projections and implied market edges
4. Re-ingest final board data for closing lines and scores
5. Grade SU / ATS / O-U performance
6. Serve outputs in a Streamlit dashboard

Supported sports:
- `ncaab`
- `nba`

## Architecture Diagram

```mermaid
flowchart TD
    A[teamrankings_cache.py] --> B[data/{sport}/{date}/combined_daily.json]
    C[scoresandodds_odds.py] --> D[data/{sport}/{date}/odds_snapshots/*.json]
    E[scoresandodds_board.py] --> D
    D --> F[data/{sport}/{date}/odds_snapshots/index.json]
    B --> G[pipelines/model_pipeline.py]
    F --> G
    G --> H[data/{sport}/{date}/predictions/baseline_v1.json]
    E --> I[latest board snapshot]
    H --> J[pipelines/results_pipeline.py]
    I --> J
    J --> K[data/{sport}/{date}/results/final_results.json]
    H --> L[Streamlit app/pages]
    K --> L
```

## Repository Structure

```text
Full-Court-Analytics-2.0/
  requirements.txt
  README.md
  .gitignore

  scraper/
    scoresandodds_board.py
    scoresandodds_odds.py
    teamrankings_cache.py

  fca/
    io.py
    join.py
    deterministic.py
    features.py
    ml_models.py
    train.py

  pipelines/
    model_pipeline.py
    results_pipeline.py

  app/
    fca_app.py
    pages/
      1_Today.py
      2_Game_Detail.py
      3_Results.py
      4_Model_Health.py
```

## Data Pipeline

The pipeline is date-scoped and file-based.

### 1) Team + matchup ingestion

`scraper/teamrankings_cache.py` builds daily matchup context and writes sport/date artifacts under:

- `data/{sport}/{date}/combined_daily.json`
- related schedule/matchup files

### 2) Odds and board snapshots

Two scrapers support the market pipeline:

- `scraper/scoresandodds_odds.py` for odds snapshots and manifest maintenance
- `scraper/scoresandodds_board.py` for board snapshots (state, scores, closing markets)

Snapshots are stored in:

- `data/{sport}/{date}/odds_snapshots/{HHMMSS}.json`
- `data/{sport}/{date}/odds_snapshots/index.json`

The index manifest enables per-game pregame selection.

### 3) Prediction build

`pipelines/model_pipeline.py`:

- loads combined daily data
- selects pregame snapshot per game (closest snapshot before game start)
- runs deterministic projection logic
- computes market edges
- writes:
  - `data/{sport}/{date}/predictions/baseline_v1.json`

### 4) Results build

`pipelines/results_pipeline.py`:

- loads predictions for the same sport/date
- loads latest board snapshot for that date
- joins by `odds_event_id` (fallback: normalized team names)
- grades SU / ATS / O-U
- writes:
  - `data/{sport}/{date}/results/final_results.json`

## Modeling Architecture

Current baseline model is deterministic and transparent:

- Module: `fca/deterministic.py`
- Core outputs:
  - projected home/away scores
  - projected total
  - projected home spread
- Market comparison:
  - spread edge (`proj_spread_home - market_spread_home`)
  - total edge (`proj_total - market_total`)

Supporting architecture:

- `fca/join.py`: entity normalization + odds joins
- `fca/io.py`: canonical data loading
- `fca/odds_select.py`: pregame snapshot selection logic
- `fca/features.py`, `fca/ml_models.py`, `fca/train.py`: ML expansion points

## Automation Workflow

Typical daily run (example: NCAAB for `2026-03-03`):

### Morning / pregame

```bash
python scraper/teamrankings_cache.py --sport ncaab --date 2026-03-03 --data-dir data
python scraper/scoresandodds_board.py --sport ncaab --date 2026-03-03 --data-dir data
python pipelines/model_pipeline.py --sport ncaab --date 2026-03-03 --data-dir data
```

### After games go final

```bash
python scraper/scoresandodds_board.py --sport ncaab --date 2026-03-03 --data-dir data
python pipelines/results_pipeline.py --sport ncaab --date 2026-03-03 --data-dir data --model-version baseline_v1
```

This produces a fully automated predictions + grading loop without manual line entry.

## Streamlit Dashboard

Run:

```bash
streamlit run app/fca_app.py
```

Dashboard responsibilities:

- Today slate view and projections
- Game-level detail view
- Results and grading view
- Model health/monitoring view

## Installation

```bash
pip install -r requirements.txt
```

## Quickstart (60 Seconds)

Use this exact sequence to run one full cycle on a fresh clone.

```bash
# 1) Install dependencies
pip install -r requirements.txt

# 2) Build daily source data + odds snapshots
python scraper/teamrankings_cache.py --sport ncaab --date 2026-03-03 --data-dir data
python scraper/scoresandodds_board.py --sport ncaab --date 2026-03-03 --data-dir data

# 3) Generate predictions
python pipelines/model_pipeline.py --sport ncaab --date 2026-03-03 --data-dir data

# 4) Re-scrape board after games end, then grade
python scraper/scoresandodds_board.py --sport ncaab --date 2026-03-03 --data-dir data
python pipelines/results_pipeline.py --sport ncaab --date 2026-03-03 --data-dir data --model-version baseline_v1

# 5) Launch dashboard
streamlit run app/fca_app.py
```

## Output Contracts

Primary artifacts:

- Predictions:
  - `data/{sport}/{date}/predictions/baseline_v1.json`
- Results:
  - `data/{sport}/{date}/results/final_results.json`
- Snapshot manifest:
  - `data/{sport}/{date}/odds_snapshots/index.json`

Each output is JSON-first to support reproducible backtesting, downstream dashboards, and future API serving.

## Notes

- `data/` is intentionally git-ignored for production hygiene.
- Design targets operational reliability first: stable joins, deterministic outputs, and explicit file contracts.

## Troubleshooting

### `ModuleNotFoundError: No module named 'fca'`

Cause: Running scripts from a different working directory or without repo root on import path.

Fix:

```bash
# From repo root:
python pipelines/results_pipeline.py --sport ncaab --date 2026-03-03 --data-dir data
```

If needed on Windows PowerShell:

```powershell
$env:PYTHONPATH="."
python pipelines/results_pipeline.py --sport ncaab --date 2026-03-03 --data-dir data
```

### Streamlit pages not appearing

Cause: Streamlit expects pages under `app/pages` when app entrypoint is `app/fca_app.py`.

Fix:

```bash
streamlit run app/fca_app.py
```

Do not run from old root paths like `pages/...`.

### `FileNotFoundError` for predictions/results inputs

Cause: Running steps out of order.

Fix order:

1. `teamrankings_cache.py`
2. `scoresandodds_board.py` (or `scoresandodds_odds.py` as needed)
3. `pipelines/model_pipeline.py`
4. `pipelines/results_pipeline.py`

### Empty grading (`SU/ATS/OU = 0`)

Cause: Board snapshot captured before games reached final state, or join coverage is incomplete.

Fix:

1. Re-run board scrape after games are final.
2. Re-run `pipelines/results_pipeline.py`.
3. Inspect `join_stats` in `final_results.json` for missing matches.

### Windows path issues in JSON pointers

Cause: Mixed slash types in stored snapshot paths.

Fix:

1. Keep snapshot paths normalized as forward slashes in writers.
2. Resolve relative paths from project root in loaders (`Path.cwd()` strategy already used in pipelines).
