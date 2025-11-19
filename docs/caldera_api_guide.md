# Caldera REST API Guide

Caldera REST API v2 사용법 (Ability/Adversary 업로드)

---

## API 기본 정보

**Base URL**: `http://<caldera-server>:8888/api/v2`

**인증**: API Key 헤더 필요
```
KEY: <your-api-key>
```

**Content-Type**: `application/json`

---

## 1. Ability API

### 1.1 Ability 생성

**Endpoint**: `POST /api/v2/abilities`

**Headers**:
```
Content-Type: application/json
KEY: <your-api-key>
```

**Request Body**: Ability 객체 (YAML → JSON 변환)

**YAML 예제**:
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

**JSON 변환 (API 전송)**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "System Information Discovery",
  "description": "Collect OS version and hostname",
  "tactic": "discovery",
  "technique": {
    "attack_id": "T1082",
    "name": "System Information Discovery"
  },
  "platforms": {
    "windows": {
      "cmd": {
        "command": "systeminfo && hostname",
        "timeout": 60
      }
    }
  }
}
```

**cURL 예제**:
```bash
curl -X POST http://localhost:8888/api/v2/abilities \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d @ability.json
```

**Response**: HTTP 200 + 생성된 Ability 객체

---

### 1.2 Ability 조회

**전체 목록**: `GET /api/v2/abilities`

**특정 Ability**: `GET /api/v2/abilities/{ability_id}`

**cURL 예제**:
```bash
# 전체 목록
curl -X GET http://localhost:8888/api/v2/abilities \
  -H "KEY: YOUR_API_KEY"

# 특정 Ability
curl -X GET http://localhost:8888/api/v2/abilities/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "KEY: YOUR_API_KEY"
```

---

### 1.3 Ability 수정

**Endpoint**: `PATCH /api/v2/abilities/{ability_id}`

**cURL 예제**:
```bash
curl -X PATCH http://localhost:8888/api/v2/abilities/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d '{"description": "Updated description"}'
```

---

### 1.4 Ability 삭제

**Endpoint**: `DELETE /api/v2/abilities/{ability_id}`

**cURL 예제**:
```bash
curl -X DELETE http://localhost:8888/api/v2/abilities/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "KEY: YOUR_API_KEY"
```

---

## 2. Adversary API

### 2.1 Adversary 생성

**Endpoint**: `POST /api/v2/adversaries`

**Request Body**:
```json
{
  "id": "kisa-ttp-adversary",
  "name": "KISA TTP Adversary",
  "description": "KISA 보고서 기반 자동 생성 Adversary Profile",
  "atomic_ordering": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "c3d4e5f6-a7b8-9012-cdef-123456789012"
  ]
}
```

**cURL 예제**:
```bash
curl -X POST http://localhost:8888/api/v2/adversaries \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d @adversary.json
```

**Response**: HTTP 200 + 생성된 Adversary 객체

---

### 2.2 Adversary 조회

**전체 목록**: `GET /api/v2/adversaries`

**특정 Adversary**: `GET /api/v2/adversaries/{adversary_id}`

**cURL 예제**:
```bash
# 전체 목록
curl -X GET http://localhost:8888/api/v2/adversaries \
  -H "KEY: YOUR_API_KEY"

# 특정 Adversary
curl -X GET http://localhost:8888/api/v2/adversaries/kisa-ttp-adversary \
  -H "KEY: YOUR_API_KEY"
```

---

### 2.3 Adversary 수정

**Endpoint**: `PATCH /api/v2/adversaries/{adversary_id}`

**cURL 예제**:
```bash
curl -X PATCH http://localhost:8888/api/v2/adversaries/kisa-ttp-adversary \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d '{"description": "Updated description"}'
```

---

### 2.4 Adversary 삭제

**Endpoint**: `DELETE /api/v2/adversaries/{adversary_id}`

**cURL 예제**:
```bash
curl -X DELETE http://localhost:8888/api/v2/adversaries/kisa-ttp-adversary \
  -H "KEY: YOUR_API_KEY"
```

---

## 3. Payload API

### 3.1 Payload 업로드

**Endpoint**: `POST /api/v2/payloads`

**Headers**:
```
Content-Type: multipart/form-data
KEY: <your-api-key>
```

**Request**: Multipart form with file

**cURL 예제**:
```bash
curl -X POST http://localhost:8888/api/v2/payloads \
  -H "KEY: YOUR_API_KEY" \
  -F "file=@PrintSpoofer64.exe"
```

---

### 3.2 Payload 조회

**Endpoint**: `GET /api/v2/payloads`

**cURL 예제**:
```bash
curl -X GET http://localhost:8888/api/v2/payloads \
  -H "KEY: YOUR_API_KEY"
```

---

### 3.3 Payload 삭제

**Endpoint**: `DELETE /api/v2/payloads`

**Request Body**:
```json
{
  "payload": "PrintSpoofer64.exe"
}
```

**cURL 예제**:
```bash
curl -X DELETE http://localhost:8888/api/v2/payloads \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d '{"payload": "PrintSpoofer64.exe"}'
```

---

## 4. Python 예제

### 4.1 Ability 업로드

```python
import requests
import json

CALDERA_SERVER = "http://localhost:8888"
API_KEY = "YOUR_API_KEY"

ability = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "System Information Discovery",
    "description": "Collect OS version and hostname",
    "tactic": "discovery",
    "technique": {
        "attack_id": "T1082",
        "name": "System Information Discovery"
    },
    "platforms": {
        "windows": {
            "cmd": {
                "command": "systeminfo && hostname",
                "timeout": 60
            }
        }
    }
}

response = requests.post(
    f"{CALDERA_SERVER}/api/v2/abilities",
    headers={
        "Content-Type": "application/json",
        "KEY": API_KEY
    },
    data=json.dumps(ability)
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

---

### 4.2 Adversary 업로드

```python
import requests
import json

CALDERA_SERVER = "http://localhost:8888"
API_KEY = "YOUR_API_KEY"

adversary = {
    "id": "kisa-ttp-adversary",
    "name": "KISA TTP Adversary",
    "description": "KISA 보고서 기반 자동 생성 Adversary Profile",
    "atomic_ordering": [
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    ]
}

response = requests.post(
    f"{CALDERA_SERVER}/api/v2/adversaries",
    headers={
        "Content-Type": "application/json",
        "KEY": API_KEY
    },
    data=json.dumps(adversary)
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

---

### 4.3 Payload 업로드

```python
import requests

CALDERA_SERVER = "http://localhost:8888"
API_KEY = "YOUR_API_KEY"

with open("PrintSpoofer64.exe", "rb") as f:
    response = requests.post(
        f"{CALDERA_SERVER}/api/v2/payloads",
        headers={"KEY": API_KEY},
        files={"file": f}
    )

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

---

## 5. 주요 API 엔드포인트 요약

| 리소스 | 메서드 | 엔드포인트 | 설명 |
|--------|--------|------------|------|
| Ability | GET | `/api/v2/abilities` | 전체 목록 조회 |
| Ability | GET | `/api/v2/abilities/{id}` | 특정 Ability 조회 |
| Ability | POST | `/api/v2/abilities` | 새 Ability 생성 |
| Ability | PATCH | `/api/v2/abilities/{id}` | Ability 수정 |
| Ability | DELETE | `/api/v2/abilities/{id}` | Ability 삭제 |
| Adversary | GET | `/api/v2/adversaries` | 전체 목록 조회 |
| Adversary | GET | `/api/v2/adversaries/{id}` | 특정 Adversary 조회 |
| Adversary | POST | `/api/v2/adversaries` | 새 Adversary 생성 |
| Adversary | PATCH | `/api/v2/adversaries/{id}` | Adversary 수정 |
| Adversary | DELETE | `/api/v2/adversaries/{id}` | Adversary 삭제 |
| Payload | GET | `/api/v2/payloads` | 전체 목록 조회 |
| Payload | POST | `/api/v2/payloads` | Payload 업로드 |
| Payload | DELETE | `/api/v2/payloads` | Payload 삭제 |

---

## 6. 일반적인 워크플로우

### Step 1: Payload 업로드
```bash
curl -X POST http://localhost:8888/api/v2/payloads \
  -H "KEY: YOUR_API_KEY" \
  -F "file=@PrintSpoofer64.exe"
```

### Step 2: Ability 생성
```bash
curl -X POST http://localhost:8888/api/v2/abilities \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d @ability.json
```

### Step 3: Adversary 생성
```bash
curl -X POST http://localhost:8888/api/v2/adversaries \
  -H "Content-Type: application/json" \
  -H "KEY: YOUR_API_KEY" \
  -d @adversary.json
```

### Step 4: Operation 실행 (GUI 사용)
Caldera GUI에서:
1. Operations 탭 이동
2. "Create Operation" 클릭
3. Adversary 선택: "KISA TTP Adversary"
4. Agent 그룹 선택
5. "Start Operation"

---

## 요약

- **Ability API**: Ability 생성/조회/수정/삭제
- **Adversary API**: Adversary 생성/조회/수정/삭제
- **Payload API**: Payload 업로드/조회/삭제
- **인증**: 모든 요청에 `KEY` 헤더 필요
- **형식**: JSON (YAML을 JSON으로 변환 필요)
