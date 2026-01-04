# ttps3 환경 설명

## 네트워크 구성

### 피해자 컴퓨터: 192.168.56.115 (Windows 10, IIS)
- 유출 대상 파일 위치
    - C:\Users\Public\data\*
    - 유출 행위 시뮬레이션 목적의 더미 데이터가 존재함
- 추가적인 정보 수집시 Users 폴더 하위만 탐색후 C:\Users\Public\data\* 에 저장한다.

- Unquoted 서비스가 실행됨
- C:\Temp\Vuln App\service.exe
- C:\Temp\에 Everyone 쓰기 권한이 부여되어있다.
- 1분마다 재시작 되도록 스케줄 되어있다.

- 계정 정보 접근
  - 관리자 계정을 탈취했다.
    - Username: administrator
    - Password: P@ssw0rd123
  - 관리자 계정을 이용해 Vuln.exe를 실행한다.

### 공격자 서버(192.168.56.1:34444)
  - api 설명
    - GET /agents/*
      - 필요한 스크립트 파일을 * 에 입력하여 공격자 서버에서 파일을 다운받을 수 있음
      - 초기 다운로드 위치는 C:\Users\Public\data\*
      - 목록
        - Keylogger.ps1
          - 정보 수집을 위한 키로거 스크립트
        - SimulatedUSB.ps1
          - USB 이동식 매체를 이용한 시스템 내부 이동을 시뮬레이션한다.
        - Vuln.exe
          - Caldera agent 실행파일

    - POST /upload
      - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
      - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨

---