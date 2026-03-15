---
layout: default
title: Results
nav_order: 7
---

# Experimental Results
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Experimental Setup

- **Dataset**: 11 KISA CTI reports (2020–2024)
- **LLMs**: Claude Sonnet 4.5, GPT-4o, Gemini 2.5 Pro, Grok 4 Fast
- **Repetitions**: 5 runs per report-LLM pair
- **Total experiments**: 220 (11 × 4 × 5)
- **Target environment**: Windows 10 Pro (PC1, PC2), Windows Server 2019 AD (PC3)
- **Caldera version**: 5.3.0

---

## RQ1: Generation Time and Cost

> How much time and cost does the pipeline require to generate an adversary emulation scenario from a CTI report?

### Claude Sonnet 4.5 — Per-Report Breakdown

| ID | Abilities | Total (s) | Generation (s) | Correction (s) | Execution (s) | Cost ($) |
|----|-----------|----------|---------------|---------------|-------------|---------|
| TTPs#1  | 33.6 | 1802.97 | 130.93 |  86.09 | 1398.20 | 0.41 |
| TTPs#2  | 29.4 | 1065.22 | 255.45 |  16.31 |  670.60 | 0.48 |
| TTPs#3  | 23.0 |  927.33 | 107.85 |  19.24 |  645.00 | 0.22 |
| TTPs#4  | 30.4 | 1809.97 | 207.57 |  27.21 | 1394.40 | 0.38 |
| TTPs#5  | 27.2 | 1679.44 | 230.97 |  38.57 | 1187.80 | 0.40 |
| TTPs#6  | 24.2 |  790.28 | 128.84 |  21.14 |  485.40 | 0.26 |
| TTPs#7  | 28.2 | 1452.84 | 166.86 |  23.11 | 1075.40 | 0.30 |
| TTPs#8  | 33.8 | 2275.96 | 185.31 |  63.05 | 1806.00 | 0.47 |
| TTPs#9  | 23.4 |  974.60 | 118.41 |  14.54 |  666.80 | 0.27 |
| TTPs#10 | 22.6 | 1070.45 | 133.67 |   3.29 |  773.00 | 0.28 |
| TTPs#11 | 24.0 | 1494.56 | 161.82 |  31.13 | 1092.60 | 0.39 |
| **Avg** | **27.2** | **1394.87** | **166.15** | **31.24** | **1017.75** | **0.35** |

### LLM Model Comparison

| Model | Avg. Abilities | Total (s) | Generation (s) | Correction (s) | Execution (s) | Cost ($) |
|-------|---------------|----------|---------------|---------------|-------------|---------|
| Claude Sonnet 4.5 | **27.2** | 1394.87 | 166.15 |  31.24 | 1017.75 | 0.35 |
| GPT-4o            |   13.5   |  869.88 |  75.97 |  13.45 |  589.20 | 0.13 |
| Gemini 2.5 Pro    |   13.3   |  948.56 | 221.11 |  79.66 |  426.16 | 0.10 |
| Grok 4 Fast       |   17.2   |  836.95 |  60.83 |  10.36 |  570.29 | **0.01** |

---

## RQ2: Execution Success Rate & Self-Correcting Effect

> What is the execution success rate of generated scenarios, and how much does Self-Correcting improve it?

### Per-Report Success Rate (Claude Sonnet 4.5)

| ID | Chain Length | Initial SR (%) | Final SR (%) | Improvement (pp) | Corrected Abilities (%) | Retries |
|----|-------------|--------------|------------|-----------------|------------------------|--------|
| TTPs#1  | 33.6 | 52.73 | 70.82 | +18.09 | 49.20 | 3.0 |
| TTPs#2  | 29.4 | 73.46 | 96.05 | +22.59 | 27.23 | 2.6 |
| TTPs#3  | 23.0 | 70.26 | 91.26 | +21.00 | 29.74 | 2.8 |
| TTPs#4  | 30.4 | 63.59 | 81.21 | +17.62 | 36.41 | 3.0 |
| TTPs#5  | 27.2 | 64.20 | 77.87 | +13.67 | 36.49 | 3.0 |
| TTPs#6  | 24.2 | 74.08 | 85.20 | +11.13 | 25.92 | 2.8 |
| TTPs#7  | 28.2 | 81.88 | 88.47 |  +6.59 | 18.12 | 3.0 |
| TTPs#8  | 33.8 | 52.51 | 86.28 | +33.77 | 49.43 | 3.0 |
| TTPs#9  | 23.4 | 82.08 | 88.79 |  +6.71 | 17.92 | 2.8 |
| TTPs#10 | 22.6 | 85.88 | 92.00 |  +6.11 | 14.12 | 2.4 |
| TTPs#11 | 24.0 | 65.32 | 68.52 |  +3.20 | 34.68 | 3.0 |
| **Avg** | **27.3** | **69.63** | **84.22** | **+14.59** | **30.84** | **2.85** |

### Failure Type Distribution & Recovery Rate (Claude Sonnet 4.5, 55 runs total)

| Failure Type | Count | Recovery Count | Recovery Rate (%) |
|-------------|-------|---------------|-----------------|
| `syntax_error`     | 245 | 101 | 41.22 |
| `dependency_error` | 117 |  32 | 27.35 |
| `missing_env`      |  31 |  19 | **61.29** |
| `timeout`          |  26 |   4 | 15.38 |
| `unrecoverable`    |  57 |   0 | N/A |
| **Total** (excl. unrecoverable) | **419** | **156** | **37.23** |

### Self-Correcting Effect by LLM Model

| Model | Initial SR (%) | Final SR (%) | Improvement (pp) | Avg. Retries |
|-------|--------------|------------|-----------------|-------------|
| Claude Sonnet 4.5 | 69.63 | 84.22 | +14.59 | 2.85 |
| GPT-4o            | 56.33 | 73.56 | **+17.23** | 2.95 |
| Gemini 2.5 Pro    | **71.37** | **87.86** | +16.50 | 2.76 |
| Grok 4 Fast       | 58.44 | 73.96 | +15.52 | 2.95 |

![Self-Correction Effect]({{ site.baseurl }}/assets/images/fig3_rq2_claude_sr_improvement.png)

---

## RQ3: CTI Coverage & ATT&CK Validity

> How faithfully do generated scenarios reproduce the ATT&CK techniques from source CTI reports?

### Per-Report (Claude Sonnet 4.5)

| ID | ATT&CK Validity (%) | CTI Precision (%) | CTI Recall (%) | CTI F1 (%) | Complexity |
|----|--------------------|--------------------|----------------|------------|------------|
| TTPs#1  | 98.69  | 92.56 | 61.03 | 73.56 | Advanced |
| TTPs#2  | 96.55  | 94.69 | 41.54 | 57.75 | Expert   |
| TTPs#3  | 100.00 | 85.33 | 70.43 | 77.17 | Advanced |
| TTPs#4  | 85.37  | 66.97 | 40.57 | 50.53 | Advanced |
| TTPs#5  | 99.31  | 81.83 | 44.50 | 57.65 | Expert   |
| TTPs#6  | 88.02  | 68.69 | 53.04 | 59.86 | Medium   |
| TTPs#7  | 93.04  | 71.59 | 52.59 | 60.64 | Advanced |
| TTPs#8  | 100.00 | 59.81 | 36.92 | 45.66 | Expert   |
| TTPs#9  | 93.96  | 84.63 | 64.55 | 73.24 | Medium   |
| TTPs#10 | 100.00 | 53.78 | 52.94 | 53.36 | Expert   |
| TTPs#11 | 89.03  | 53.77 | 60.00 | 56.71 | Expert   |
| **Avg** | **94.91** | **73.97** | **52.56** | **61.45** | - |

### By LLM Model

| Model | ATT&CK Validity (%) | CTI Precision (%) | CTI Recall (%) | CTI F1 (%) |
|-------|--------------------|--------------------|----------------|------------|
| Claude Sonnet 4.5 | 94.91 | 73.97 | **52.56** | **61.45** |
| GPT-4o            | **95.57** | **77.51** | 36.52 | 49.65 |
| Gemini 2.5 Pro    | 93.75 | 71.21 | 30.37 | 42.58 |
| Grok 4 Fast       | 92.96 | 73.49 | 39.17 | 51.10 |

---

## RQ4: Security & Final Attack Goal Achievement

> Is the test environment sufficiently hardened, and do generated scenarios achieve final attack goals?

### KISA Security Checklist Pass Rate

| System | Pass Rate (%) | Failed Items |
|--------|--------------|-------------|
| Victim (PC1)            | 89.95 | PC-09 (security patches), PC-11 (firewall — intentionally disabled for Caldera agent) |
| Lateral Movement (PC2)  | 89.47 | PC-09 (security patches), PC-11 (firewall — intentionally disabled for Caldera agent) |
| Domain Controller (PC3) | 93.90 | W-01 (admin rename), W-30 (service pack), W-32 (patches), W-33 (antivirus), W-36 (screensaver) |
| **Average**             | **91.11** | — |

### Final Attack Goal Achievement (Claude Sonnet 4.5, 1 random sample per report)

| ID | Complexity | Final Attack Goal | Result |
|----|-----------|------------------|--------|
| TTPs#1  | Advanced | Exfiltration (T1041) | ✅ Exec. |
| TTPs#2  | Expert   | Exfiltration (T1041) | ✅ Exec. |
| TTPs#3  | Advanced | Exfiltration (T1041) | ✅ Exec. |
| TTPs#4  | Advanced | Exfiltration (T1041) | ✅ Exec. |
| TTPs#5  | Expert   | Exfiltration (T1041), Impact (T1486) | ✅ Exec. |
| TTPs#6  | Medium   | Exfiltration (T1041) | ✅ Exec. |
| TTPs#7  | Advanced | Impact (T1486) | ✅ Exec. |
| TTPs#8  | Expert   | Exfiltration (T1041), Impact (T1486) | ✅ Exec. |
| TTPs#9  | Medium   | Exfiltration (T1041) | ✅ Exec. |
| TTPs#10 | Expert   | Exfiltration (T1041) | ✅ Exec. |
| TTPs#11 | Expert   | Exfiltration (T1041) | ✅ Exec. |
| **Total** | — | — | **11 / 11 (100%)** |

---

## RQ5: LLM Model Performance Comparison

> Is there a significant performance difference between LLM models for end-to-end adversary emulation?

| Model | Generation+Correction (s) | Chain Length | Final SR (%) | Improvement (pp) | CTI F1 (%) |
|-------|--------------------------|-------------|------------|-----------------|------------|
| Claude Sonnet 4.5 | 197.39 | **27.2** | 84.22 | 14.59 | **61.45** |
| GPT-4o            |  89.42 |  13.5 | 73.56 | **17.23** | 49.65 |
| Gemini 2.5 Pro    | 300.77 |  13.3 | **87.86** | 16.50 | 42.58 |
| Grok 4 Fast       | **71.19** |  17.2 | 73.96 | 15.52 | 51.10 |

Key observations:
- **Claude Sonnet 4.5**: Longest chain length and highest CTI F1 — best overall CTI reproduction
- **Gemini 2.5 Pro**: Highest final success rate (87.86%) after Self-Correcting
- **GPT-4o**: Highest Self-Correcting improvement (+17.23 pp)
- **Grok 4 Fast**: Fastest generation (71.19s) and lowest cost ($0.01)
