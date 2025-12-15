# KISA TTP to Caldera Adversary Automation

KISA 위협 인텔리전스 보고서(PDF)를 자동으로 분석하여 MITRE Caldera 공격 시뮬레이션용 Adversary Profile을 생성하고, 실행 결과를 기반으로 AI가 자동으로 수정하는 완전 자동화 파이프라인입니다.

## 주요 기능

- **완전 자동화**: PDF 입력부터 Caldera 실행, 결과 분석까지 전 과정 자동화
- **AI 기반 분석**: Claude Sonnet 4.5를 활용한 지능형 TTP 추출 및 명령어 생성
- **MITRE ATT&CK 통합**: mitreattack-python 기반 자동 Technique 매핑
- **환경 맞춤형**: 특정 환경 설정에 맞춘 구체적 PowerShell 명령어 생성
- **Self-Correcting**: 실패한 Ability를 AI가 자동 분석 및 수정 후 재실행 (최대 3회)
  - 누적 수정 이력을 활용한 지능형 재시도
  - 실패 원인 분류 및 맞춤형 수정 전략
- **VM 자동 관리**: 재시도마다 VM 스냅샷 복원으로 깨끗한 환경 보장
- **성공률 추적**: 초기 실행 대비 수정 후 성공률 개선 현황 자동 출력
- **메트릭 추적**: LLM 토큰 사용량, 비용, 실행 시간 자동 기록

## 시스템 아키텍처

```
┌─────────────────────┐
│  KISA PDF Report    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 1             │  PDF 텍스트 추출
│  PDF Processing     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 2             │  환경 독립적 추상 공격 흐름 생성
│  Abstract Flow      │  - Attack goals 추출
│                     │  - MITRE tactics 매핑
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 3             │  환경별 구체화 및 Technique 자동 선택
│  Concrete Flow      │  - 환경 설명 결합
│                     │  - 최적 MITRE Technique 자동 선택
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 4             │  Caldera Ability 생성
│  Ability Generator  │  - PowerShell 명령어 생성
│                     │  - YAML 형식 변환
│                     │  - Adversary profile 생성
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 5             │  Caldera 자동화 & Self-Correcting
│  Automation         │  5-1. 업로드 (Abilities + Adversary)
│                     │  5-2. Operation 실행
│                     │  5-3. 결과 수집
│                     │  5-4. AI 기반 자동 수정
│                     │  5-5. 재업로드 및 재실행
│                     │  5-6. 성공률 비교 출력
└─────────────────────┘
```

## 설치

### 1. Python 환경 설정

```bash
# Python 3.10.11 필요
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 입력:

```bash
# LLM 설정
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-4-20250514

# Caldera 설정
CALDERA_URL=http://your-caldera-server:8888
CALDERA_API_KEY=your_caldera_api_key_here

# VM 관리 설정 (선택사항 - Step 5 자동 재부팅용)
VBOX_VM_NAME=YourVMName
VBOX_SNAPSHOT_NAME=CleanSnapshot
VBOX_VM_NAME_lateral=LateralVMName  # Lateral movement VM (있는 경우)
VBOX_SNAPSHOT_NAME_lateral=LateralCleanSnapshot

# SSH 설정 (VirtualBox 원격 제어용 - 선택사항)
VBOX_SSH_HOST=your-vbox-host
VBOX_SSH_PORT=22
VBOX_SSH_USER=your-username
VBOX_SSH_PASSWORD=your-password
```

## 사용 방법

### 전체 파이프라인 자동 실행

```bash
python main.py --step all --pdf "data/raw/report.pdf" --env "environment_description.md"
```

이 명령어는 다음을 자동으로 수행합니다:
1. PDF 분석
2. 추상/구체 공격 흐름 생성
3. Caldera Ability 생성
4. Caldera 업로드 및 Operation 실행
5. 실패 분석 및 자동 수정
6. 수정된 Ability 재업로드 및 재실행
7. 성공률 비교 출력

### 단계별 실행

```bash
# Step 1: PDF 처리
python main.py --step 1 --pdf "data/raw/report.pdf"

# Step 2: 추상 공격 흐름 생성
python main.py --step 2

# Step 3: 구체적 공격 흐름 생성 (환경 설명 필수)
python main.py --step 3 --env "environment_description.md"

# Step 4: Caldera Ability 생성
python main.py --step 4 --env "environment_description.md"

# Step 5: Caldera 자동화 (업로드 → 실행 → Self-Correcting)
python main.py --step 5 --env "environment_description.md"
```

### 범위 지정 실행

```bash
# Step 1~3 실행
python main.py --step 1~3 --pdf "data/raw/report.pdf" --env "environment_description.md"

# Step 3~5 실행 (이전 단계 결과가 있는 경우)
python main.py --step 3~5 --env "environment_description.md"
```

### 추가 옵션

```bash
# 특정 Agent 대상 실행
python main.py --step 5 --env "environment_description.md" --agent-paw "agent123"

# 업로드 건너뛰기 (이미 업로드된 경우)
python main.py --step 5 --env "environment_description.md" --skip-upload

# 자동 실행 건너뛰기 (수동 실행 후 Self-Correcting만)
python main.py --step 5 --env "environment_description.md" --skip-execution

# Operation 이름 지정
python main.py --step 5 --env "environment_description.md" --operation-name "MyOperation"
```

## 환경 설정 파일 작성

`environment_description.md` 파일에는 대상 환경의 상세 정보를 작성합니다:

```markdown
# 테스트 환경 설명

## 네트워크 구성

- 웹 서버(DMZ): 192.168.56.105 (Windows 10, IIS)
- 내부망: 192.168.56.106 (Windows 10, SMB 활성화)
- Caldera server: 192.168.56.1:8888

## 웹 애플리케이션

- 로그인: http://192.168.56.105/login_process.asp
  - 방식: POST 요청, Body 파라미터 `userid`, `password`
  - 계정: admin / P@ssw0rd!2020

- 파일 업로드: http://192.168.56.105/upload_handler.asp
  - 방식: POST 요청, multipart/form-data
  - 폼 필드 이름: `file`

## 취약점

1. ASP 파일 업로드 취약점 (확장자 검증 없음)
2. PrintSpoofer 권한 상승 (SeImpersonatePrivilege 활용)
3. SMB Admin Shares 접근 가능

## Caldera Payload

- cmd.asp (웹셸)
- PrintSpoofer64.exe
- vcruntime140.dll
- deploy.ps1
```

## 출력 결과

모든 결과는 `data/processed/YYYYMMDD_HHMMSS/` 디렉토리에 타임스탬프와 함께 저장됩니다:

```
data/processed/20251209_025808/
├── step1_parsed.yml                    # PDF 파싱 결과
├── step2_abstract_flow.yml             # 추상 공격 흐름
├── step3_concrete_flow.yml             # 구체적 공격 흐름
├── step4_abilities.yml                 # Ability 중간 결과
└── caldera/
    ├── abilities.yml                       # Caldera Abilities (Self-Correcting 수정됨)
    ├── adversaries.yml                     # Caldera Adversary Profile
    ├── operation_report.json               # 초기 실행 결과
    ├── operation_report_retry_1.json       # 재시도 1 결과
    ├── operation_report_retry_2.json       # 재시도 2 결과
    ├── operation_report_retry_3.json       # 재시도 3 결과 (최대 3회)
    ├── correction_report.json              # 누적 Self-Correcting 리포트
    └── experiment_metrics.json             # 실험 메트릭 (토큰, 비용, 시간)
```

### 성공률 비교 출력 예시

```
======================================================================
Self-Correcting 최종 결과
======================================================================
구분                      전체        성공        실패        성공률
----------------------------------------------------------------------
초기 실행                 34          18          16          52.9%
재시도 1                  34          26          8           76.5%
재시도 2                  34          28          6           82.4%
재시도 3                  34          30          4           88.2%
----------------------------------------------------------------------
최종 개선: +35.3% (18 → 30 성공)
최종 성공률: 88.2% (30/34 성공)
재시도 횟수: 3회
종료 사유: max_retries_reached
======================================================================

[실험 메트릭 요약]
----------------------------------------------------------------------
총 실행 시간: 45분 32초
LLM 제공자: claude
LLM 모델: claude-sonnet-4-20250514
총 입력 토큰: 234,567
총 출력 토큰: 45,123
총 토큰: 279,690
예상 비용: $8.3940
완료된 Step: 5/5
======================================================================
```

## 프로젝트 구조

```
.
├── README.md
├── requirements.txt
├── main.py                            # 메인 실행 스크립트
├── .env                               # 환경 변수 (API keys)
├── environment_description.md         # 환경 설정 파일
├── collect_retry_results.py           # 재실행 결과 수집 유틸리티
├── modules/
│   ├── ai/
│   │   ├── base.py                    # LLM 베이스 클래스
│   │   ├── claude.py                  # Claude API 클라이언트
│   │   ├── chatgpt.py                 # OpenAI API 클라이언트
│   │   └── factory.py                 # LLM 팩토리 (환경변수 기반)
│   ├── caldera/
│   │   ├── agent_manager.py           # Caldera Agent 관리 (조회/삭제/대기)
│   │   ├── uploader.py                # Caldera 업로드
│   │   ├── executor.py                # Operation 실행 및 제어
│   │   ├── reporter.py                # 결과 수집
│   │   └── deleter.py                 # 리소스 삭제
│   ├── core/
│   │   ├── config.py                  # 환경 변수 로드
│   │   ├── models.py                  # 데이터 모델
│   │   └── metrics.py                 # 실험 메트릭 추적 (토큰, 비용, 시간)
│   ├── prompts/
│   │   ├── manager.py                 # 프롬프트 템플릿 관리
│   │   └── templates/                 # YAML 프롬프트 템플릿
│   │       ├── step2_overview.yaml
│   │       ├── step2_chunk.yaml
│   │       ├── step2_synthesize.yaml
│   │       ├── step3_generate_flow.yaml
│   │       ├── step4_generate_command.yaml
│   │       ├── step4_validate_command.yaml
│   │       └── step5_fix_ability.yaml
│   └── steps/
│       ├── step1_pdf_processing.py    # PDF 처리
│       ├── step2_abstract_flow.py     # 추상 흐름 생성
│       ├── step3_concrete_flow.py     # 구체 흐름 생성 & Technique 자동 선택
│       ├── step4_ability_generator.py # PowerShell 명령어 & Ability 생성
│       └── step5_self_correcting.py   # Self-Correcting 엔진
├── data/
│   ├── raw/                           # 원본 PDF
│   └── processed/                     # 처리 결과 (타임스탬프별)
└── scripts/
    ├── vm_reload.py                   # VM 스냅샷 복원 및 관리
    ├── analyze_metrics.py             # 메트릭 분석 유틸리티
    ├── analyze_report.py              # Operation 리포트 분석
    ├── get_operation_report.py        # Caldera에서 리포트 다운로드
    ├── upload_to_caldera.py           # Caldera 업로드 유틸리티
    └── delete_from_caldera.py         # Caldera 삭제 유틸리티
```

## Self-Correcting 엔진

Step 5의 Self-Correcting 엔진은 실패한 Ability를 자동으로 분석하고 수정합니다.

### 실패 유형 분류

1. **syntax_error**: PowerShell 구문 오류
2. **missing_env**: 환경 설정 값 누락 (IP, 경로 등)
3. **caldera_constraint**: Caldera 제약사항 (변수 의존성 등)
4. **dependency_error**: 권한 부족
5. **unrecoverable**: 복구 불가능 (도구 미설치 등)

### 수정 전략

각 실패 유형에 맞는 전략으로 명령어를 자동 수정:
- 구문 오류 수정 (PowerShell 5.1 호환성)
- 환경 설명 기반 실제 값 대체
- 변수 의존성 제거 (self-contained 명령어로 변환)
- 권한 상승 없는 대체 방법 사용

### 누적 컨텍스트 활용

재시도마다 이전 실패 이력을 LLM에 제공하여 더 나은 수정안 생성:
- 각 Ability별 수정 이력 추적
- 이전 시도의 명령어, 실패 원인, 에러 메시지 누적
- `correction_report.json`에 전체 수정 과정 기록

### 자동 재실행 (최대 3회)

각 재시도마다:
1. 실패한 Ability 분석 및 수정
2. 수정된 Ability 재업로드
3. **VM 스냅샷 복원** (깨끗한 환경 보장)
4. Caldera Agent 정리 및 재연결 대기
5. 새 Operation 실행
6. 결과 수집 및 성공률 비교

종료 조건:
- 모든 Ability 성공 (`all_success`)
- 수정 가능한 실패 없음 (`no_recoverable_failures`)
- 최대 재시도 횟수 도달 (`max_retries_reached`)

## 유틸리티 스크립트

### VM 관리

```bash
# VM 스냅샷 복원 및 시작
python -m scripts.vm_reload

# 환경변수 설정 필요:
# VBOX_VM_NAME, VBOX_SNAPSHOT_NAME
# VBOX_SSH_HOST, VBOX_SSH_USER, VBOX_SSH_PASSWORD
```

### 메트릭 분석

```bash
# 실험 메트릭 분석 (토큰 사용량, 비용 등)
python scripts/analyze_metrics.py data/processed/[experiment_id]/experiment_metrics.json
```

### Operation 리포트 분석

```bash
# Operation 결과 상세 분석
python scripts/analyze_report.py data/processed/[experiment_id]/caldera/operation_report.json
```

### Caldera 리소스 삭제

```bash
# Adversary 삭제
python scripts/delete_from_caldera.py --adversary "KISA TTP Adversary"

# Ability 삭제
python scripts/delete_from_caldera.py --ability "ability-id-here"
```

## 명령어 옵션 상세

### --step
실행할 단계 지정 (필수)
- 단일 단계: `--step 1`, `--step 5`
- 범위: `--step 1~3`, `--step 3~5`
- 전체: `--step all`

### --pdf
입력 PDF 파일 경로 (Step 1 실행 시 필수)

### --env
환경 설명 MD 파일 경로 (Step 3 이상 실행 시 필수)

### --agent-paw
특정 Caldera Agent 지정 (선택사항)
- 생략 시 모든 연결된 에이전트 대상

### --skip-upload
Step 5에서 업로드 단계 건너뛰기
- 이미 업로드된 Ability를 재사용할 때 사용

### --skip-execution
Step 5에서 자동 실행 건너뛰기
- 수동으로 Operation을 실행한 후 Self-Correcting만 수행할 때 사용

### --operation-name
Operation 이름 지정 (선택사항)
- 기본값: `Auto-Operation-<timestamp>`

### --output-dir
출력 디렉토리 지정 (선택사항)
- 기본값: `data/processed`

## 트러블슈팅

### MITRE ATT&CK 데이터 오류

```bash
pip install mitreattack-python==3.0.6
```

### API Key 오류

`.env` 파일에 올바른 API key가 설정되어 있는지 확인:

```bash
ANTHROPIC_API_KEY=sk-ant-...
CALDERA_API_KEY=...
```

### Caldera 연결 오류

Caldera 서버 URL과 API Key 확인:

```bash
curl -H "KEY: your_api_key" http://your-caldera-server:8888/api/v2/abilities
```

### PowerShell 명령어 실행 실패

환경 설명 파일에 충분한 정보가 포함되어 있는지 확인:
- 정확한 IP 주소 및 포트
- 올바른 인증 정보
- 필요한 Payload 파일 목록

Self-Correcting이 자동으로 많은 오류를 수정하지만, 환경 정보가 부정확하면 수정이 불가능합니다.

## 기술적 특징

### PowerShell 5.1 호환
모든 명령어는 Windows PowerShell 5.1 기준으로 생성되며, 최신 PowerShell Core 전용 cmdlet은 사용하지 않습니다.

### 단일 라인 명령어
Caldera 제약으로 모든 명령어는 단일 라인으로 생성됩니다. 여러 명령은 세미콜론으로 연결합니다.

### Self-Contained Abilities
각 Ability는 독립적으로 실행되어 변수를 공유할 수 없습니다. 모든 필요한 값은 명령어 내에 포함됩니다.

### Jitter 설정
Operation 생성 시 jitter를 `1/1`로 설정하여 Ability 간 지연을 최소화합니다.

### 무제한 대기
Operation 완료를 기다릴 때 시간 제한이 없습니다. 완료될 때까지 무한정 대기합니다.

## 제약사항

- **Windows 전용**: 현재 Windows/PowerShell 명령어만 지원
- **PowerShell 5.1**: PowerShell 5.1 호환 명령어만 생성
- **환경 의존성**: 정확한 환경 설명 파일 필수
- **VirtualBox SSH**: VM 자동 관리를 위해 VirtualBox 호스트에 SSH 접근 필요 (선택사항)

## 참고 자료

- [MITRE Caldera](https://github.com/mitre/caldera)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [mitreattack-python](https://github.com/mitre-attack/mitreattack-python)
- [Claude API](https://docs.anthropic.com/)

## 라이선스

MIT License
