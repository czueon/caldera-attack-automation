---
layout: default
title: Installation
nav_order: 3
---

# Installation
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.10.11 | Required |
| MITRE Caldera | 5.3.0 | Ubuntu 20.04 LTS recommended |
| VirtualBox | Any recent | For VM snapshot management |
| LLM API key | — | At least one (Anthropic, OpenAI, Google, or xAI) |

---

## Clone the Repository

```bash
git clone https://github.com/alpakalee/testcaldera.git
cd testcaldera
```

---

## Install Python Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:

| Package | Purpose |
|---------|---------|
| `anthropic>=0.40.0` | Claude API |
| `openai>=1.0.0` | GPT API |
| `google-generativeai>=0.3.0` | Gemini API |
| `pdfplumber==0.11.0` | PDF text extraction |
| `mitreattack-python==3.0.6` | MITRE ATT&CK data |
| `pyyaml==6.0.1` | YAML processing |
| `paramiko==3.4.0` | SSH for VirtualBox control |
| `python-dotenv==1.0.1` | Environment variable loading |

---

## Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your settings. See [Configuration]({{ site.baseurl }}/pages/configuration) for full details.

---

## Set Up MITRE Caldera

Install Caldera on a Linux server (Ubuntu 20.04 LTS recommended):

```bash
git clone https://github.com/mitre/caldera.git --recursive
cd caldera
pip install -r requirements.txt
python server.py --insecure
```

{: .note }
Caldera runs on port **8888** by default.

---

## Set Up the Attacker Server

The pipeline includes a separate lightweight HTTP server (`환경 설계/attacker_server/server.py`) that serves payload files (Caldera agent, web shell, tools) to target VMs. This is **not** Caldera — it runs independently on port **34444**.

```bash
python 환경\ 설계/attacker_server/server.py
```

In the environment specification files (`environment_ttps{1-11}.md`), this server is referenced as:

```
## Attacker Server (192.168.56.1:34444)
- GET /agents/* : Download files required for the victim's PC
```

Configure the attacker server's IP and port in `.env` to match your network setup.

---

## Set Up Target VMs

Each TTP scenario requires specific VM configurations. See `environment_ttps{1-11}.md` for per-scenario requirements.

**General requirements:**
- Windows 10 Pro (PC1, PC2): Caldera agent installed and running
- Windows Server 2019 (PC3, AD): Domain configured per scenario spec
- Clean snapshots saved in VirtualBox (restored between Self-Correcting retries)

{: .warning }
Disable Windows Defender real-time protection on target VMs before running experiments. This is a one-time manual step not covered by the pipeline.

---

## Verify Installation

```bash
# Test LLM connection
python -c "from modules.ai.factory import get_llm_client; print('LLM OK')"

# Test Caldera connection
python -c "
import os, requests
from dotenv import load_dotenv
load_dotenv()
r = requests.get(os.getenv('CALDERA_URL') + '/api/v2/abilities',
                 headers={'KEY': os.getenv('CALDERA_API_KEY')})
print('Caldera OK:', r.status_code)
"
```
