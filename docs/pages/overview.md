---
layout: default
title: Overview
nav_order: 2
---

# System Overview
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Problem

Existing adversary emulation approaches each have critical limitations:

| Approach | Limitation |
|----------|-----------|
| Benchmark Datasets | Cannot be re-executed for defense validation |
| Abstract Attack Models | Not executable; no concrete commands |
| Isolated Execution Tools (Atomic Red Team) | No multi-step dependency chains |
| Orchestration Frameworks (Caldera) | No automatic CTI-to-scenario conversion |
| Expert-curated Emulation (ATT&CK Evals) | Requires months of expert work per scenario |
| AURORA | Requires manual intervention during execution; no failure recovery |

None of the existing approaches satisfy all six requirements simultaneously: **executable, multi-step, dependency-preserved, auto-recovery, CTI-based, low-cost**.

---

## Architecture

The system consists of four functional layers orchestrated by `main.py`:

### Layer 1: Input

- **CTI Report (PDF)**: KISA threat intelligence reports describing real attack incidents, annotated with MITRE ATT&CK mappings
- **Environment Specification (Markdown)**: User-authored file describing the target environment — IP addresses, OS versions, installed software, user accounts, network topology

### Layer 2: LLM-based Scenario Generation (Steps 1–4)

A 4-step progressive concretization pipeline:

```
Step 1: PDF Text Extraction
  └─ pdfplumber extracts text page-by-page → YAML

Step 2: Abstract Attack Flow
  └─ 3-phase LLM strategy:
     (1) Overview extraction (first 3,000 chars)
     (2) Chunked goal extraction (8,000-char chunks)
     (3) Synthesis: dedup + reorder + MITRE Tactic mapping

Step 3: Concrete Attack Flow
  └─ LLM combines abstract goals + environment spec
     → PowerShell commands + explicit dependency edges
     → execution_order via LLM semantic reasoning
     → MITRE Technique ID generation + validation (ATT&CK v15.1)

Step 4: Caldera Ability & Adversary Generation
  └─ Each concrete node → Caldera Ability YAML (UUID, tactic, technique, psh command)
  └─ All abilities → Adversary YAML (atomic_ordering by execution_order)
```

### Layer 3: Caldera Execution

- Upload Abilities via `POST /api/v2/abilities`
- Upload Adversary via `POST /api/v2/adversaries`
- Create and start Operation via `POST /api/v2/operations`
- Poll for completion (5-second intervals)
- Collect results: exit code, stdout, stderr per ability

A separate Attacker Server (`환경 설계/attacker_server/server.py`) runs on port **34444** to serve payload files (Caldera agent, web shell, tools) to target VMs. This is independent of the Caldera server.

### Layer 4: Self-Correction (Step 5)

See [Self-Correction]({{ site.baseurl }}/pages/self-correction) for detailed documentation.

---

## Key Innovation: LLM Semantic Dependency Matching

Unlike AURORA's PDDL-based symbolic planning (string matching for precondition-effect linking), this system uses **LLM semantic reasoning** to determine dependency edges between attack steps.

This means expressions like `credentials_obtained` and `password_dumped` are correctly identified as semantically equivalent — even across different languages or phrasings — without requiring predefined predicate vocabularies.

**Example (TTPs#1):** The LLM determined that the PrintSpoofer privilege escalation node is a prerequisite for four subsequent nodes (scheduled task creation, malicious service creation, process injection, etc.), creating a branching dependency structure — entirely from natural language analysis.

---

## Comparison with AURORA

| Dimension | AURORA | Ours |
|-----------|--------|------|
| Automation level | Requires manual intervention during execution | Fully automated after setup |
| Failure recovery | None — chain halts on first error | Domain-specific 5-type classification + LLM fix |
| Dependency matching | String-based PDDL predicate matching | LLM semantic reasoning |
| Intermediate artifacts | Not publicly available | All YAML outputs saved and reproducible |
| LLM comparison | Single model | 4 models (Claude, GPT-4o, Gemini, Grok) |
