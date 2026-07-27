---
layout: default
title: Usage
nav_order: 5
---

# Usage
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Quick Start

Run the full pipeline on a single scenario:

```bash
python main.py \
  --step 1-5 \
  --pdf data/raw/KISA_TTPs_1.pdf \
  --env environment_ttps1.md
```

---

## CLI Reference

```
python main.py --step STEPS --pdf PDF_PATH --env ENV_PATH [options]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `--step` | string | yes | Steps to execute: `1`, `2`, `1-5`, `3-5`, etc. |
| `--pdf` | path | yes | Path to KISA CTI PDF file |
| `--env` | path | yes | Path to environment specification Markdown file |
| `--version-id` | string | no | Custom version ID (default: timestamp) |
| `--output-dir` | path | no | Output directory (default: `data/processed`) |
| `--operation-name` | string | no | Caldera operation name (default: auto-generated) |
| `--agent-paw` | string | no | Target specific Caldera agent PAW |
| `--skip-upload` | flag | no | Skip ability upload (if already uploaded) |
| `--skip-execution` | flag | no | Skip execution, use existing operation report |

LLM provider는 `.env`의 `LLM_PROVIDER` 값으로 설정합니다 (`claude` / `openai` / `gemini` / `grok`).

---

## Running Individual Steps

All steps are independently resumable. Previous step outputs must exist in `data/processed/`.

### Step 1: PDF Extraction

```bash
python main.py --step 1 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md
```

Output: `data/processed/KISA_TTPs_1/{version_id}/step1_pdf.yaml`

### Step 2: Abstract Attack Flow

```bash
python main.py --step 2 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md
```

Output: `data/processed/KISA_TTPs_1/{version_id}/step2_abstract.yaml`

### Step 3: Concrete Attack Flow

```bash
python main.py --step 3 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md
```

Output: `data/processed/KISA_TTPs_1/{version_id}/step3_concrete.yaml`

### Step 4: Ability & Adversary Generation

```bash
python main.py --step 4 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md
```

Output: `data/processed/KISA_TTPs_1/{version_id}/abilities.yml`, `adversaries.yml`

### Step 5: Self-Correcting Execution

```bash
python main.py --step 5 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md
```

Output: `data/processed/KISA_TTPs_1/{version_id}/operation_report.json`, `correction_report.json`

---

## Batch Automation (All 11 Scenarios)

Run all scenarios sequentially:

```bash
python auto_run.py
```

This iterates through all 11 KISA TTP scenarios with their corresponding environment configurations and VM snapshot settings.

---

## Step Ranges

You can run arbitrary ranges of steps:

```bash
# Steps 1 through 3 only (no Caldera execution)
python main.py --step 1-3 --pdf ... --env ...

# Steps 3 through 5 (reuse existing step 1-2 outputs)
python main.py --step 3-5 --pdf ... --env ...

# Single step
python main.py --step 2 --pdf ... --env ...
```

{: .note }
When resuming from a later step, specify the same `--version-id` used in the previous run to load the correct intermediate outputs.

---

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/analyze_metrics.py` | Analyze token usage and cost across experiments |
| `scripts/analyze_report.py` | Summarize operation results and success rates |
| `scripts/vm_reload.py` | Manually restore VM snapshots |
| `scripts/upload_to_caldera.py` | Upload abilities/adversaries directly |
| `scripts/delete_from_caldera.py` | Clean up Caldera resources |
| `scripts/get_operation_report.py` | Download operation reports from Caldera |
