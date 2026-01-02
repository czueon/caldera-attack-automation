# ttps5 환경 설명

## 네트워크 구성

- Domain Controller: 192.168.56.140 (Windows Server 2022, AD DS)
- 거점 PC: 192.168.56.130 (Windows 10, 도메인 조인)
- 내부 서버: 192.168.56.131 (Windows 10, SMB 활성화, 도메인 조인)

- 공격자 서버: 192.168.56.1:34444

---

## 도메인 정보

- 도메인: victimcorp.local
- NetBIOS: VICTIMCORP

---

## 계정 정보

### 도메인 계정
| 계정 | 비밀번호 | 권한 |
|------|----------|------|
| VICTIMCORP\Administrator | P@ssw0rd!2020 | Domain Admin |
| VICTIMCORP\itadmin | ITAdmin123! | Domain Admin (탈취 대상) |
| VICTIMCORP\user1 | User1234! | Domain User (거점 PC 사용자) |

---

## 거점 PC (192.168.56.130)

- 기본 로그인: VICTIMCORP\user1
- Administrators 그룹 소속 (UAC bypass 가능)

- 웹 서버 구성
    - index.html
      - 내부 포털 메인 페이지. 직원 디렉터리 및 보안정책 페이지로 이동.
    - staff.html
      - 직원 이름, 부서, 직급, 이메일 패턴: firstname.lastname@victimcorp.com
    - security.html
      - 비밀번호 정책
      - MFA 적용 기준
      - OWA(Outlook Web Access) 사용 여부 등

- 유출 대상 파일 위치
    - C:\Users\Public\data\*

---

## 내부망 SMB Admin Shares 접근 (192.168.56.131)
   - 계정: VICTIMCORP\itadmin / ITAdmin123!
   - C$ 공유 접근 가능
   - sandcat_ttps5.ps1을 측면이동 시켜 실행하는 것이 목표

---

## 공격자 서버 (192.168.56.1:34444)

- api 설명
    - GET /login?user=xxxx
      - 피싱 링크 클릭 이벤트 기록
    - GET /agents/sandcat_ttps5.ps1
      - Caldera sandcat_ttps5.ps1 에이전트 파일 다운로드
    - POST /upload
      - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
      - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨

---

## 에이전트 설치 및 권한 상승 흐름

### 에이전트 다운로드 (일반 사용자 권한)

- 피해자는 피싱 링크 클릭 후 공격자 서버에 접속했다고 가정
- sandcat_ttps5.ps1을 로컬에 다운로드

예시 동작:
- C:\Users\Public\sandcat_ttps5.ps1 에 저장

---

## UAC Bypass 환경 및 조건

- Windows 기본 UAC 설정 유지
- 사용자는 Administrators 그룹 소속
- UAC 프롬프트 우회 가능 환경

- 본 시나리오에서는:
  - 취약점 exploit이 아닌
  - Windows 기본 동작을 악용한 UAC bypass (fodhelper.exe) 사용

---

## 관리자 권한 sandcat 에이전트 실행

- UAC bypass 트리거 후
- High Integrity Level PowerShell 컨텍스트 확보

- sandcat_ttps5.ps1을 관리자 권한으로 실행

- 이후 실행되는 ability들은 관리자 권한을 전제로 동작하며, 서비스 등록, 보호된 경로 접근, 시스템 수준 정찰을 시뮬레이션한다.

---
