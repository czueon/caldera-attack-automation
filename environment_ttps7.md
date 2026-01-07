# ttps7 환경 설명

## 네트워크 구성

### 피해자 컴퓨터: 192.168.56.165 (Windows 10, IIS)
- 유출 대상 파일 위치
    - C:\Users\Public\data\*
    - 유출 행위 시뮬레이션 목적의 더미 데이터가 존재함
- 추가적인 정보 수집시 Users 폴더 하위만 탐색후 C:\Windows\Temp\* 에 저장한다.

- 일반 유저의 권한으로 C:\Users\Public\victim.exe 가 실행 중이다.

- 일반 유저의 권한으로 VulnService 가 실행 중이다.

- Windows 기본 동작을 악용한 UAC bypass (fodhelper.exe) 사용하여 관리자 권한으로 sandcat_ttps7.ps1을 실행한다.

### 피해자 내부망 컴퓨터: 192.168.56.166 (Windows 10)
- Admin 계정을 탈취했다.
  - Username: administrator
  - Password: P@ssw0rd123

### 공격자 서버(192.168.56.1:34444)
  - api 설명
    - GET /agents/*
      - 필요한 스크립트 파일을 * 에 입력하여 공격자 서버에서 파일을 다운받을 수 있음
      - 초기 다운로드 위치는 C:\Users\Public\data\*
      - 목록
        - payload.dll
          - 인젝션을 위한 dll
        - injector.ps1
          - payload.dll을 실행하여 일반 유저 권한으로 실행 중인 exe를 인젝션할 수 있는 스크립트
        - sandcat_ttps7.ps1
          - Caldera agent 실행파일
        - Keylogger.ps1
          - 정보 수집을 위한 키로거 스크립트
        - screen_capture.ps1
          - 정보 수집을 위한 스크린샷 스크립트
        - clipboard_monitor.ps1
          - 정보 수집을 위한 클립보드 모니터 스크립트

    - POST /upload
      - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
      - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨

---