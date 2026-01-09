# ttps8 환경 설명

## 도메인 정보

- 도메인: victimcorp.local
- NetBIOS: VICTIMCORP

---

## 계정 정보

### 도메인 계정
| 계정 | 비밀번호 | 권한 |
|------|----------|------|
| VICTIMCORP\Administrator | P@ssw0rd!2020 | Domain Admin (Domain Controller 사용자) |
| VICTIMCORP\user1 | User1234! | Domain User (도메인 클라이언트 사용자) |

---

## 거점 서버 (192.168.56.150)

- 기본 로그인: 로컬 계정 (ttps)
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

- 사전 설정
    - VSS 스냅샷 생성됨
        - Volume: C:\

- 유출 대상 파일 위치
    - C:\Users\Public\data\*

- 랜섬웨어 영향 대상
    - 랜섬노트 생성 위치: C:\Users\Public\data\

---

## Domain Controller (192.168.56.151)

- 도메인: victimcorp.local (DC)
- 기본 로그인: VICTIMCORP\Administrator

- 역할
    - Active Directory Domain Services
    - LSASS 메모리 덤프 대상

- 사전 설정
    - WinRM 활성화
    - VSS 스냅샷 생성됨
        - Volume: C:\

- 랜섬웨어 영향 대상
    - 랜섬노트 생성 위치: C:\Users\Public\data\

---

## 도메인 클라이언트 (192.168.56.152)

- 도메인 가입: victimcorp.local
- 기본 로그인: VICTIMCORP\user1

- 사전 설정
    - WinRM 활성화
    - VSS 스냅샷 생성됨
        - Volume: C:\

- 유출 대상 파일 위치
    - C:\Users\Public\data\*

- 랜섬웨어 영향 대상
    - 랜섬노트 생성 위치: C:\Users\Public\data\

---

## 공격자 서버 (192.168.56.1:34444)

- api 설명
    - GET /agents/*
      - 필요한 스크립트 파일을 * 에 입력하여 공격자 서버에서 파일을 다운받을 수 있음
      - 초기 다운로드 위치는 C:\Users\Public\data\*
      - 목록
        - sandcat_ttps8.ps1
          - Caldera agent 실행파일

    - POST /upload
      - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
      - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨
---

## 권한상승
- sandcat_ttps8.ps1을 로컬에 다운로드
- fodhelper.exe를 이용한 UAC 우회
  - 레지스트리 설정 후 fodhelper.exe 실행 시 자동으로 elevated 권한으로 sandcat_ttps8.ps1이 실행됨
  - 새로운 elevated agent가 자동으로 Caldera 서버에 연결됨
- 이후 실행되는 ability들은 새로 연결된 elevated agent에서 관리자 권한으로 동작

---

## 측면 이동

### 1단계: Domain Controller 침투
- ttps8 (192.168.56.150) → ttps8_ad (192.168.56.151)
  - 하나의 명령으로: New-PSDrive로 credential 연결, Copy-Item으로 파일 복사, Remove-PSDrive로 정리
  - 대상 경로: C:\Users\Public\data\sandcat_ttps8.ps1
  - VICTIMCORP\Administrator credential 사용

- WinRM으로 DC에서 Agent 백그라운드 실행
  - VICTIMCORP\Administrator 권한으로 실행

- DC Agent 연결 대기
  - 반복문으로 Caldera API (GET /api/v2/agents) 호출
  - 192.168.56.151 IP의 Agent가 등록될 때까지 반복
  - 각 시도마다 10초 대기, 최대 60초 타임아웃

### 2단계: Domain Client 침투 (DC Agent에서 실행)
- ttps8_ad (192.168.56.151) → ttps8_2 (192.168.56.152)
  - 하나의 명령으로: New-PSDrive로 credential 연결, Copy-Item으로 파일 복사, Remove-PSDrive로 정리
  - 대상 경로: C:\Users\Public\data\sandcat_ttps8.ps1
  - VICTIMCORP\Administrator credential 사용

- WinRM으로 Client에서 Agent 백그라운드 실행
  - VICTIMCORP\Administrator 권한으로 실행

- Client Agent 연결 대기
  - 반복문으로 Caldera API (GET /api/v2/agents) 호출
  - 192.168.56.152 IP의 Agent가 등록될 때까지 반복
  - 각 시도마다 10초 대기, 최대 60초 타임아웃

### 3단계: 각 시스템에서 공격 수행
- 각 시스템의 Agent가 로컬에서 직접 공격 수행
  - Caldera는 ability의 target IP를 보고 해당 Agent에 자동 할당

---
