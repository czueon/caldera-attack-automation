# ttps1 환경 설명

## 네트워크 구성

- 웹 서버(DMZ): 192.168.56.105 (Windows 10, IIS)
- 내부망: 192.168.56.106 (Windows 10, SMB 활성화)

- 공격자 서버: 192.168.56.1:34444 (파일 유출시)

---

## 웹 애플리케이션

- 로그인: http://192.168.56.105/login_process.asp
  - 방식: POST 요청, Body 파라미터 `userid`, `password`
  - 계정: admin / P@ssw0rd!2020

- 파일 업로드: http://192.168.56.105/upload_handler.asp
  - 방식: POST 요청, multipart/form-data
  - 폼 필드 이름: `file`
  - 인증: 로그인 필요
  - 업로드 경로: /uploads/
- 세션 공유가 되지않음 파일 업로드시 로그인과 업로드를 한 동작으로 수행해야함

## 피해자 서버(192.168.56.105)

- 유출 대상 파일 위치
    - C:\Users\Public\data\*
    - 유출 행위 시뮬레이션 목적의 더미 데이터가 존재함

- 정보 수집시 너무 큰 범위를 탐색하지 않도록

---

## 취약점 및 Exploit

1. **ASP 파일 업로드 취약점 (검증 목적)**

- 확장자 검증 없음
- ASP 웹쉘 업로드 가능
- 업로드 후 실행 가능: http://192.168.56.105/uploads/{파일명}
- **본 시나리오에서는 웹쉘을 통한 후속 공격은 수행하지 않음**

- 웹쉘 업로드는 침투 가능성 증명을 위한 단계로만 사용됨

2. **UAC Bypass 환경 및 조건**
- Windows 기본 UAC 설정 유지
- 사용자는 Administrators 그룹 소속
- UAC 프롬프트 우회 가능 환경

본 시나리오에서는:
- 취약점 exploit이 아닌
- Windows 기본 동작을 악용한 UAC bypass (fodhelper.exe) 사용

3. **관리자 권한 sandcat 에이전트 실행**

- UAC bypass 트리거 후
- High Integrity Level PowerShell 컨텍스트 확보

- deploy.ps1을 관리자 권한으로 실행

- 이후 실행되는 ability들은 관리자 권한을 전제로 동작하며, 서비스 등록, 보호된 경로 접근, 시스템 수준 정찰을 시뮬레이션한다.

---

## 내부망 SMB Admin Shares 접근 (192.168.56.106)
   - 계정: admin / P@ssw0rd!2020
   - C$ 공유 접근 가능
   - deploy.ps1을 측면이동 시켜 실행하는 것이 목표

---

## Caldera 환경

### Payload 파일
Caldera 서버에 업로드된 파일 (이용하려면 payload 에 적어줘야합니다.):
- cmd.asp (웹셸)

---

## 공격자 서버(192.168.56.1:34444)

- api 설명
  - GET /agents/deploy.ps1
    - Caldera deploy.ps1 에이전트 스크립트 다운로드
    - 피해자 PC가 직접 요청하여 저장
  - POST /upload
    - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
    - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨

---

## 공격 흐름

로그인 → 웹셸 업로드 → 웹셸과 무관하게 UAC Bypass → 공격자 서버에서 deploy.ps1 다운로드 → 관리자 권한으로 deploy.ps1 실행 → 정보 수집 → 내부망 탐색 → SMB 접근 → 데이터 유출

---
