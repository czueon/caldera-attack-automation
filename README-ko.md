# LLM을 활용한 사이버 위협 인텔리전스 기반 자동 End-to-End 공격 에뮬레이션 및 자가 수정 시스템

<!-- Badges -->
[![Python](https://img.shields.io/badge/Python-3.10.11-3776AB?logo=python)](https://www.python.org/downloads/release/python-31011/)
[![Caldera](https://img.shields.io/badge/MITRE_Caldera-5.3.0-red)](https://caldera.mitre.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Project Page](https://img.shields.io/badge/Project-Page-blue)](https://alpakalee.github.io/caldera-attack-automation)

**저자1<sup>1</sup> · 저자2<sup>1</sup> · 저자3<sup>1</sup> · 저자4<sup>1,2</sup> · 저자5<sup>2</sup>**
<sup>1</sup>소속 기관 1 &nbsp; <sup>2</sup>소속 기관 2

📄 **논문** · 🌐 **[프로젝트 페이지](https://alpakalee.github.io/caldera-attack-automation)** · 🎬 **데모** (준비 중)

[English README](README.md)

---

## 초록 (Abstract)

> *[작성 예정]*

---

## 핵심 실험 결과

> 실험 규모: KISA CTI 보고서 11개 × LLM 4종 × 5회 반복 = 총 220회 실험

| 지표 | 값 |
|------|-----|
| 시나리오당 평균 Ability 수 | **27.3개** |
| 초기 실행 성공률 | 69.63% |
| Self-Correcting 적용 후 최종 성공률 | **84.22%** |
| 성공률 개선량 | **+14.59 pp** |
| 평균 시나리오 생성 시간 | **2.8분** |
| 평균 API 비용 (Claude Sonnet 4.5 기준) | **$0.35** |
| ATT&CK Validity | **94.91%** |
| 최종 공격 목표 달성 | **11/11 (100%)** |

### LLM 모델별 비교

| 모델 | 평균 Ability | 초기 SR (%) | 최종 SR (%) | 개선량 (pp) | 비용 ($) |
|------|------------|-----------|-----------|-----------|---------|
| Claude Sonnet 4.5 | **27.3** | 69.63 | 84.22 | +14.59 | 0.35 |
| GPT-4o | 13.5 | 56.33 | 73.56 | **+17.23** | 0.13 |
| Gemini 2.5 Pro | 13.3 | 71.37 | **87.86** | +16.50 | 0.10 |
| Grok 4 Fast | 17.3 | 58.44 | 73.96 | +15.52 | **0.01** |

---

## 시스템 개요

KISA CTI PDF 보고서를 MITRE Caldera 공격 시나리오로 변환하는 **5단계 파이프라인**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         입력 계층 (Input Layer)                      │
│    CTI 보고서 (PDF)  +  환경 명세 파일 (Markdown)                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│            LLM 기반 공격 시나리오 생성 계층                           │
│  Step 1: PDF 텍스트 추출                                             │
│  Step 2: 추상 공격 흐름 생성  (환경 독립적)                          │
│  Step 3: 구체적 공격 흐름 생성  (환경 적용 + MITRE Technique ID)     │
│  Step 4: Caldera Ability 및 Adversary 생성                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                  Caldera 실행 계층                                   │
│   REST API 업로드  →  Operation 실행  →  결과 수집                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│               Self-Correcting 계층  (Step 5)                        │
│   실패 유형 분류 (5종) → LLM 기반 자동 수정 → 재실행               │
│   최대 3회 재시도 · 재시도마다 VM 스냅샷 복원                      │
└─────────────────────────────────────────────────────────────────────┘
```

<!-- ![시스템 아키텍처](docs/assets/images/system-architecture.png) -->

### 실패 유형 분류

Self-Correcting 엔진은 공격 시뮬레이션 도메인에 특화된 5가지 실패 유형을 자동 분류합니다:

| 유형 | 복구 가능 | 수정 전략 |
|------|:-------:|---------|
| `syntax_error` | ✅ | PowerShell 문법 오류 LLM 수정 |
| `timeout` | ✅ | 타임아웃/대기 로직 조정 |
| `dependency_error` | ✅ | 권한·의존성 문제 LLM 해결 |
| `missing_env` | ✅ | 환경 명세 기반 올바른 값으로 교체 |
| `unrecoverable` | ❌ | 조기 중단 (불필요한 재시도 방지) |

---

## 관련 연구 비교

| 접근방식 | 실행 가능 | 다단계 | 의존관계 보존 | 자동 복구 | CTI 기반 | 저비용 |
|---------|:-------:|:-----:|:-----------:|:-------:|:-------:|:-----:|
| 벤치마크 데이터셋 | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 추상적 공격 모델링 | ❌ | ✅ | △ | ❌ | ✅ | ✅ |
| 고립된 실행 도구 | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 오케스트레이션 프레임워크 | ✅ | ✅ | ❌ | ❌ | ❌ | △ |
| 전문가 큐레이션 | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| AURORA | △ | ✅ | ✅ | ❌ | ✅ | △ |
| **본 연구** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 시스템 요구사항

- Python 3.10.11
- MITRE Caldera 5.3.0 (Ubuntu 20.04 LTS)
- VirtualBox (VM 스냅샷 관리 — SSH 원격 제어)
- LLM API 키 최소 1개: Anthropic / OpenAI / Google / xAI

### 실험 환경

| 구성 요소 | 사양 |
|---------|-----|
| Caldera Server | Ubuntu 20.04 LTS, Caldera 5.3.0 |
| Target PC1 | Windows 10 Pro 1803 (주요 공격 대상) |
| Target PC2 | Windows 10 (측면 이동 거점) |
| Target PC3 | Windows Server 2019 (Active Directory) |
| 주력 LLM | Claude Sonnet 4.5 |

---

## 설치

```bash
git clone https://github.com/alpakalee/caldera-attack-automation.git
cd caldera-attack-automation
pip install -r requirements.txt
cp .env.example .env
# .env 파일을 편집하여 API 키 및 환경 설정 입력
```

---

## 설정 (Configuration)

`.env` 파일 편집:

### LLM API 키
```env
ANTHROPIC_API_KEY=your_key_here   # Claude용
OPENAI_API_KEY=your_key_here      # GPT-4o용
GOOGLE_API_KEY=your_key_here      # Gemini용
XAI_API_KEY=your_key_here         # Grok용

LLM_PROVIDER=claude               # claude | openai | gemini | grok
```

### Caldera 서버
```env
CALDERA_URL=http://your-caldera-server:8888
CALDERA_API_KEY=your_caldera_api_key
```

### VM 설정 (Step 5 실행에 필요)
```env
VM_HOST=your_virtualbox_host_ip
VM_SSH_USER=your_ssh_user
VM_SSH_PASSWORD=your_password
VM_NAME=your_vm_name
VM_SNAPSHOT=clean_snapshot_name
```

전체 옵션은 `.env.example`, 시나리오별 설정은 `run_config_details.md` 참고.

---

## 실행 방법

### 전체 파이프라인 (Step 1–5)

```bash
python main.py \
  --step 1-5 \
  --pdf data/raw/KISA_TTPs_1.pdf \
  --env environment_ttps1.md
```

### 특정 단계만 실행

```bash
# 시나리오 생성만 (실행 제외)
python main.py --step 1-4 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md

# Step 3부터 재개
python main.py --step 3-5 --pdf data/raw/KISA_TTPs_1.pdf --env environment_ttps1.md
```

### 전체 시나리오 일괄 실행 (11개 모두)

```bash
python auto_run.py
```

### 실행 인자

| 인자 | 설명 | 기본값 |
|-----|------|-------|
| `--step` | 실행할 단계 (`1`, `1-5`, `3-5` 등) | `1-5` |
| `--pdf` | KISA CTI PDF 보고서 경로 | 필수 |
| `--env` | 환경 명세 `.md` 파일 경로 | 필수 |
| `--version-id` | 출력 디렉토리 버전 ID | 자동 (타임스탬프) |
| `--llm` | LLM 제공자 (`claude` / `openai` / `gemini` / `grok`) | `.env` 설정값 |

---

## 파이프라인 단계별 설명

| 단계 | 모듈 | 설명 | 출력 |
|------|------|-----|-----|
| 1 | `step1_pdf_processing.py` | CTI PDF에서 텍스트 추출 | `step1_pdf.yaml` |
| 2 | `step2_abstract_flow.py` | 환경 독립적 추상 공격 흐름 생성 | `step2_abstract.yaml` |
| 3 | `step3_concrete_flow.py` | 환경 정보 적용 + MITRE Technique ID 검증 | `step3_concrete.yaml` |
| 4 | `step4_ability_generator.py` | Caldera Ability 및 Adversary 프로파일 생성 | `abilities.yml`, `adversaries.yml` |
| 5 | `step5_self_correcting.py` | 업로드·실행·실패 분류·자동 수정·재시도 | `operation_report.json`, `correction_report.json` |

모든 중간 산출물은 다음 경로에 저장됩니다:
```
data/processed/{pdf_name}/{version_id}/
```

---

## 실험 데이터셋

KISA 발간 CTI 보고서 11개 (2020–2024), 랜섬웨어·APT·워터링홀·AD 공격 등 다양한 유형 포함:

| ID | 보고서 제목 | 주요 공격 유형 | 복잡도 |
|----|-----------|--------------|-------|
| TTPs#1 | 홈페이지를 통한 내부망 장악 사례 분석 | 웹 취약점 + 내부 침투 | Advanced |
| TTPs#2 | 스피어 피싱을 통한 정보 수집 공격망 구성 분석 | 사회 공학 | Expert |
| TTPs#3 | 공격자의 악성코드 활용 전략 분석 | 악성코드 다단계 침투 | Advanced |
| TTPs#4 | 피싱 타깃 정찰과 공격 자원 분석 | 사전 정찰 | Advanced |
| TTPs#5 | AD 환경을 위협하는 공격 패턴 분석 | 디렉터리 서비스 공격 | Expert |
| TTPs#6 | 타겟형 워터링홀 공격 전략 분석 | 웹사이트 침해 | Medium |
| TTPs#7 | SMB Admin Share를 활용한 내부망 이동 전략 분석 | 측면 이동 | Advanced |
| TTPs#8 | Operation GWISIN – 맞춤형 랜섬웨어 공격 전략 | 타깃형 랜섬웨어 | Expert |
| TTPs#9 | 개인의 일상을 감시하는 공격 전략 분석 | 스파이웨어 | Medium |
| TTPs#10 | Operation GoldGoblin – 제로데이 기반 선별적 침투 | 제로데이 + APT | Expert |
| TTPs#11 | Operation An Octopus – 중앙 집중형 관리 솔루션 공격 | 공급망 공격 | Expert |

---

## 프로젝트 구조

```
caldera-attack-automation/
├── main.py                       # 메인 CLI 진입점
├── auto_run.py                   # 일괄 자동화 (11개 전체)
├── requirements.txt
├── .env.example                  # 환경 설정 템플릿
├── run_config_details.md         # 시나리오별 실행 가이드
├── environment_ttps{1-11}.md     # 시나리오별 환경 명세
│
├── modules/
│   ├── ai/                       # LLM 클라이언트 구현체
│   │   ├── base.py               #   추상 기본 클래스
│   │   ├── claude.py             #   Anthropic Claude
│   │   ├── chatgpt.py            #   OpenAI GPT
│   │   ├── gemini.py             #   Google Gemini
│   │   ├── grok.py               #   xAI Grok
│   │   └── factory.py            #   팩토리 패턴
│   ├── caldera/                  # Caldera REST API 연동
│   ├── steps/                    # 파이프라인 단계 구현 (1–5)
│   ├── prompts/                  # LLM 프롬프트 템플릿 (YAML)
│   └── core/                     # 공통 유틸리티
│
├── data/
│   ├── raw/                      # 입력 KISA PDF (11개)
│   ├── mitre/                    # MITRE ATT&CK JSON
│   ├── mapping_table/            # TTP 매핑 및 Ground Truth
│   └── processed/                # 실험 결과 (타임스탬프별)
│
├── config/
│   └── classification_rules.yml  # 실패 유형 분류 규칙
│
├── scripts/                      # 유틸리티 스크립트
└── docs/                         # GitHub Pages (Just the Docs)
```

---

## 데모

> 🎬 데모 영상 준비 중입니다.

---

---

## 라이선스

MIT License — 자세한 내용은 [LICENSE](LICENSE) 참고.

---

## 감사의 글

- [MITRE Caldera](https://caldera.mitre.org/) — 공격 에뮬레이션 플랫폼
- [KISA](https://www.kisa.or.kr/) — CTI 보고서 데이터셋
- [MITRE ATT&CK](https://attack.mitre.org/) — 위협 지식 베이스
