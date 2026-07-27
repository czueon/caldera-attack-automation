---
layout: default
title: Self-Correction
nav_order: 6
---

# Self-Correction Engine
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The Self-Correcting engine (Step 5) automatically recovers from execution failures without human intervention. It is the core innovation of this system, extending general-purpose LLM self-correction to the attack simulation domain.

Three key properties differentiate this from general code self-correction:

1. **Heterogeneous failure types** — attack command failures arise from permission errors, missing environment resources, security tool blocking, C2 connection failures, and timeouts — each requiring different fix strategies
2. **Unrecoverable failures exist** — attempts to exploit software not present on the target cannot be fixed by modifying commands; early identification prevents wasted retries
3. **Non-controlled execution environment** — commands run on a remote target system; execution context is inherently uncertain

---

## Failure Classification

The engine analyzes `stderr` and `exit_code` from each Caldera operation result, matching against predefined patterns in `config/classification_rules.yml`:

| Type | Recoverable | Common Causes | Fix Strategy |
|------|:-----------:|---------------|-------------|
| `syntax_error` | ✅ | PowerShell parser errors, wrong parameter types, incompatible commands | Provide stderr + original command to LLM for syntax fix |
| `timeout` | ✅ | Command exceeds 60s timeout | Adjust wait logic, simplify command |
| `dependency_error` | ✅ | Insufficient privileges, auth failure, service access denied | Provide previous step outputs + context for privilege/dependency resolution |
| `missing_env` | ✅ | Non-existent file paths, wrong IP/URL, network unreachable | Provide environment spec + failure log for value correction |
| `unrecoverable` | ❌ | No pattern match — fundamental environment incompatibility | No retry — immediately classified as final failure |

---

## Correction Process

```
1. Execute operation via Caldera API
2. Collect results (exit_code, stdout, stderr per ability)
3. Extract failed abilities
4. Classify each failure (5 types via pattern matching)
5. For each recoverable failure:
   a. Build LLM prompt with:
      - Failure type and strategy description
      - Original command
      - stderr / stdout
      - Environment specification
      - Correction history (previous attempts)
   b. LLM generates corrected PowerShell command
   c. Update abilities.yml with new command
6. Re-upload modified abilities to Caldera
7. Re-run operation (VM snapshot restored first)
8. Repeat steps 2-7 (max 3 retries)
```

Termination conditions:
- All abilities succeed
- Max retries (3) reached
- No recoverable failures remain

---

## Observed LLM Reasoning Behaviors

Three advanced reasoning patterns were observed across experiments (all 4 LLMs):

### 1. Dependency Compensation

**Case (TTPs#1):** `"Start malicious service"` failed with `dependency_error` (`"The specified service does not exist as an installed service"`). The preceding `"Create malicious service"` step had partially failed.

**LLM response:** Instead of modifying the preceding step, the LLM rewrote the current command to self-contain the dependency:

```powershell
# Before
sc.exe start "WindowsDefenderUpdate"

# After (LLM-generated)
sc.exe create "WindowsDefenderUpdate" binPath= "C:\...\sandcat_ttps1.ps1" start= demand && sc.exe start "WindowsDefenderUpdate"
```

### 2. Context-Aware Adaptation

**Case (TTPs#1):** `"Create malicious Windows service"` failed with `"Access is denied"`.

**LLM response:** By reading the environment spec and understanding that `PrintSpoofer64.exe` was pre-deployed as a SYSTEM-privilege wrapper, the LLM rewrote the command:

```powershell
# Before
sc.exe create "WindowsDefenderUpdate" binPath= "..."

# After (LLM-generated)
C:\Users\Public\data\PrintSpoofer64.exe -c "sc.exe create WindowsDefenderUpdate ..."
```

This required understanding the *semantic role* of a tool in the environment, not just syntax correction.

### 3. Semantic-Equivalent Substitution

**Case:** `"Enumerate domain accounts"` failed with `missing_env`.

**LLM response:** Instead of fixing parameters, the LLM substituted an entirely different approach that achieves the same goal:

```powershell
# Before
net user /domain

# After (LLM-generated)
Get-WmiObject -Class Win32_UserAccount -Filter "Domain='$env:USERDOMAIN'" |
  Select-Object Name,FullName,Description,Domain,SID |
  Format-Table -AutoSize
```

---

## Results

| Metric | Value |
|--------|-------|
| Initial success rate (Claude Sonnet 4.5 avg.) | **69.63%** |
| Final success rate after Self-Correcting | **84.22%** |
| Improvement | **+14.59 pp** |
| Main failure types (% of all failures) | `syntax_error`: 51.5%, `dependency_error`: 24.6% |
| `syntax_error` recovery rate | 41.22% |
| `dependency_error` recovery rate | 27.35% |
| `missing_env` recovery rate | **61.29%** |
| `timeout` recovery rate | 15.38% |
| Average retries per scenario | 2.85 |
