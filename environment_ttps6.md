# ttps3 환경 설명

## 네트워크 구성

### 피해자 컴퓨터: 192.168.56.145 (Windows 10, IIS)
- 유출 대상 파일 위치
    - C:\Users\Public\data\*
    - 유출 행위 시뮬레이션 목적의 더미 데이터가 존재함
- 추가적인 정보 수집시 Users 폴더 하위만 탐색후 C:\Users\Public\data\* 에 저장한다.

- 워터링 홀 공격에 의해 피싱 페이지에 접속되어 악성 스크립트 다운로드 및 실행됨
  - 공격자 서버에서 sandcat_ttps6.ps1을 다운로드하고 실행해야한다.

- 이후 mshta.exe를 이용하여 http://192.168.56.1:34444/notice 페이지를 실행시켜 추가적인 악성코드를 다운받는다.

- 이후 정보 수집을 위한 스크립트는 공격자 서버에서 다운받아야한다.

### 공격자 서버(192.168.56.1:34444)
  - api 설명
    - GET /agents/*
      - 필요한 스크립트 파일을 * 에 입력하여 공격자 서버에서 파일을 다운받을 수 있음
      - 초기 다운로드 위치는 C:\Users\Public\data\*
      - 목록
        - sandcat_ttps6.ps1
          - Caldera agent 실행파일
        - Keylogger.ps1
          - 정보 수집을 위한 키로거 스크립트
        - screen_capture.ps1
          - 정보 수집을 위한 스크린샷 스크립트

    - POST /upload
      - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
      - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨

---