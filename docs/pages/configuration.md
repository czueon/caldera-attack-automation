---
layout: default
title: Configuration
nav_order: 4
---

# Configuration
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Environment Variables (.env)

Copy `.env.example` to `.env` and fill in your values.

---

## LLM Provider Settings

```env
# Select active provider
LLM_PROVIDER=claude        # claude | openai | gemini | grok

# API Keys (fill in the ones you need)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
XAI_API_KEY=xai-...
```

| Provider | Model Used | Notes |
|----------|-----------|-------|
| `claude` | Claude Sonnet 4.5 | Primary/recommended |
| `openai` | GPT-4o | |
| `gemini` | Gemini 2.5 Pro | |
| `grok` | Grok 4 Fast | |

---

## Caldera Server

```env
CALDERA_URL=http://192.168.x.x:8888
CALDERA_API_KEY=ADMIN123            # Default Caldera admin key
CALDERA_AGENT_TIMEOUT=300           # Seconds to wait for agent connection
```

---

## Target Environment (Windows VMs)

| VM | Role | OS |
|----|------|----|
| PC1 | Primary target (victim) | Windows 10 Pro 1803 |
| PC2 | Lateral movement pivot | Windows 10 |
| PC3 | Active Directory server | Windows Server 2019 |

{: .note }
Pre-configured VirtualBox OVA files for all three VMs will be made available for download after paper publication. Each OVA includes the required software, Caldera agent, and per-scenario snapshots.

---

## VM Configuration

Required for Step 5 (Self-Correcting with snapshot restore):

```env
# VirtualBox Host (SSH access)
VM_HOST=192.168.x.x
VM_SSH_PORT=22
VM_SSH_USER=administrator
VM_SSH_PASSWORD=your_password

# Main target VM
VM_NAME=Windows10_PC1
VM_SNAPSHOT=Clean_Snapshot

# Lateral movement VM (optional, scenario-dependent)
VM_LATERAL_NAME=Windows10_PC2
VM_LATERAL_SNAPSHOT=Clean_Snapshot

# AD Server VM (optional, scenario-dependent)
VM_AD_NAME=WindowsServer2019_AD
VM_AD_SNAPSHOT=Clean_Snapshot
```

---

## Per-Scenario Settings

Each TTP scenario requires specific VM and environment configuration. Refer to `run_config_details.md` for the exact `.env` values for each scenario.

Example for TTPs#1:

```env
# TTPs#1: Homepage-based Internal Network Compromise
VM_NAME=TTPs1_PC1
VM_SNAPSHOT=TTPs1_Clean
CALDERA_AGENT_GROUP=ttps1
```

---

## Environment Specification Files

Each scenario has a corresponding `environment_ttps{N}.md` file that describes:

- **Network topology**: IP addresses, subnet configuration
- **System info**: OS version, installed software, user accounts
- **Pre-deployed tools**: Attack tools already present on the target (e.g., PrintSpoofer64.exe)
- **Vulnerability context**: Known vulnerabilities and misconfigured services

This file is fed directly to the LLM in Step 3 to generate environment-specific PowerShell commands.

{: .tip }
If generated commands reference wrong IPs or paths, update the environment specification file and re-run Step 3 — no prompt editing required.

---

## Output Directory Structure

All pipeline outputs are saved to:

```
data/processed/{pdf_name}/{version_id}/
├── step1_pdf.yaml          # Extracted PDF text
├── step2_abstract.yaml     # Abstract attack flow
├── step3_concrete.yaml     # Concrete attack flow with MITRE IDs
├── abilities.yml           # Caldera Ability definitions
├── adversaries.yml         # Caldera Adversary profile
├── operation_report.json   # Execution results
└── correction_report.json  # Self-Correcting history
```

`version_id` is auto-generated as `YYYYMMDD_HHMMSS` or set via `--version-id`.
