# ttps9 환경 설명

## 피해자 PC (192.168.56.190)

- 유출 대상 파일 위치
    - C:\Users\Public\data\*
    - 유출 행위 시뮬레이션 목적의 더미 데이터가 존재함

- 모바일 장치 데이터 위치
    - C:\ProgramData\Phone\Galaxy_Note8\
    - 모바일 장치와 관련된 더미 데이터가 존재함

- 피해자가 피싱 메일을 클릭하여 악성 스크립트 다운로드 및 실행됨
    - 공격자 서버에서 sandcat_ttps9.ps1을 다운로드하고 실행해야 한다.

- 추가 악성코드 다운로드
    - BITSAdmin 사용
    - 다운로드 위치: C:\Users\Public\data\*

---

## 공격자 서버 (192.168.56.1:34444)

- api 설명
    - GET /agents/*
      - 필요한 스크립트 파일을 * 에 입력하여 공격자 서버에서 파일을 다운받을 수 있음
      - 초기 다운로드 위치는 C:\Users\Public\data\*
      - 목록
        - sandcat_ttps9.ps1
          - Caldera agent 실행파일
        - screen_capture.ps1
          - 정보 수집을 위한 화면 캡처 스크립트
        - collect_mobile_data.ps1
          - 모바일 장치 데이터 수집 스크립트

    - POST /upload
      - 피해자 PC에서 수집한 데이터를 HTTP POST 요청을 통해 공격자 서버로 유출하기 위한 엔드포인트
      - multipart/form-data 및 raw binary 업로드를 모두 지원하도록 구성됨

---
