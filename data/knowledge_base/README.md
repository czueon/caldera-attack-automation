# Knowledge Base

ATT&CK 기법(technique)을 실행 가능한 명령어로 매핑한 저장소. Stage1(기법 선택)/Stage2(명령어 생성) 파이프라인에서, 선택된 기법(또는 이름이 가장 유사한 기법)의 예시 명령어를 프롬프트에 포함시키기 위해 사용한다.

## 소스

- **Atomic Red Team** — https://github.com/redcanaryco/atomic-red-team (MIT License)
- 로컬 경로: `data/knowledge_base/atomic-red-team/` (`.gitignore` 처리됨, repo에는 미포함)

```bash
git clone https://github.com/redcanaryco/atomic-red-team.git data/knowledge_base/atomic-red-team
```

재현성을 위해 커밋을 고정한다 (서브모듈은 나중에 고려):

```bash
cd data/knowledge_base/atomic-red-team
git checkout 1ba1dd8d9ce6f74700f7aec2e60de5632f667f03   # 2026-07-19
```

## 인덱스 빌드

```bash
python scripts/build_knowledge_base.py
```

`atomics/Indexes/windows-index.yaml`(ART가 배포하는 windows 플랫폼용 자체 인덱스, tactic별 `{technique_id: {technique, atomic_tests}}`)을 읽어 `data/knowledge_base/index/atomic_index.json`을 생성한다. 개별 `atomics/T*/T*.yaml`을 직접 파싱하지 않는 이유는 이 인덱스가 이미 windows로 필터링돼 있고 기법 name도 항상 채워져 있기 때문.

레코드 스키마:
```json
{
  "technique_id": "T1003.001",
  "technique_name": "OS Credential Dumping: LSASS Memory",
  "tactics": ["credential-access"],
  "test_name": "Dump LSASS.exe Memory using ProcDump",
  "description": "...",
  "platforms": ["windows"],
  "executor_name": "command_prompt",
  "command_template": "...",
  "elevation_required": true,
  "input_arguments": {...},
  "dependencies": [...]
}
```

참고 사항:
- `tactics`는 ART 최상위 버킷 라벨 기반이며(`stealth`/`defense-impairment`는 `defense-evasion`으로 정규화), 참고용 메타데이터일 뿐 조회에는 쓰이지 않는다.
- `windows-index.yaml`엔 test가 0개인 기법 항목도 섞여 있어서, 실제 예시를 낼 수 있는 기법은 268개다 (2026-08-06 기준, test 1,225개: powershell 658 / command_prompt 558 / manual 9).

## 조회 모듈

`modules/core/knowledge_base.py`의 `KnowledgeBase` 클래스로 조회한다.

```python
from modules.core.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
kb.get_examples("T1003.001")                                         # 동일 기법 test 원본 전체 (모든 필드)
kb.get_example_commands("T1003.001")                                 # stage2 프롬프트용 예시 목록
kb.get_example_commands("T1558.999", technique_name="Kerberoasting") # KB에 없는 기법 -> 이름이 가장 유사한 기법으로 대체
```

`get_example_commands(technique_id, technique_name)` 동작:
1. 동일 기법 test가 있으면 사용, 없으면 `technique_name` 기준 **기법 이름 간 TF-IDF 코사인 유사도**로 가장 가까운 기법을 찾아 그 test를 사용 (tactic 제한이나 description은 쓰지 않음 — 검증 결과 기법 이름만 비교하는 쪽이 더 정확했음)
2. 실행 불가능한 test(`command_template` 없음, 예: manual)는 제외
3. 남은 test 중 **PowerShell 우선, 없으면 command_prompt** — 그 executor 그룹 전부를 반환 (한 기법 안에서도 test마다 목적이 크게 다른 경우가 많아 하나로 대표를 좁히지 않고, 최종 선택은 stage2 LLM이 환경/맥락을 보고 하도록 함)
4. 반환 dict에서 `description`/`platforms`/`cleanup_command`는 프롬프트 컨텍스트 절약을 위해 제외 (`PROMPT_EXCLUDE_FIELDS`)

## 파이프라인 연동

`modules/steps/step3_concrete_flow.py`가 내부적으로 stage1/stage2 두 단계로 동작한다 (Step 번호 자체는 그대로 "Step 3"). `#{input_var}` 플레이스홀더는 자동 치환하지 않고, LLM이 예시를 패턴 참고용으로만 보고 실제 환경값을 직접 채워 넣도록 한다.

- **stage1** (`_generate_flow`): 기법(technique)/tactic/environment_specific만 생성. `commands`는 생성하지 않음
- **stage2** (`_generate_commands` → 노드별 `_generate_command_for_node`): `execution_order` 순서대로 노드를 순회하며 `KnowledgeBase.get_example_commands(technique_id, technique_name)`로 예시를 가져오고, 선행 노드(`edges` 기준)의 이미 생성된 명령어와 함께 프롬프트(`step3_generate_command.yaml`)에 담아 명령어 하나를 생성 → `node.environment_specific.commands`에 채움
- 출력 포맷은 기존과 동일해서 `step4_ability_generator.py`는 무수정

### RQ1 ablation (with/without KB)

`ConcreteFlowGenerator(use_knowledge_base=False)` (CLI: `python main.py --step 3 --no-kb ...`)로 stage2의 KB 조회만 끈다. stage1/stage2 분리 구조 자체는 두 조건에서 동일하게 유지되고, `example_commands`가 "None available"로 비는 것만 다르다 — 아키텍처 차이가 아니라 KB 유무만 비교되도록 하기 위함.

## 현재 상태

- [x] 원본 클론 완료 (커밋 고정)
- [x] 인덱스 빌드 (`scripts/build_knowledge_base.py` → `data/knowledge_base/index/atomic_index.json`)
- [x] 조회 모듈 (`modules/core/knowledge_base.py`)
- [x] stage1/stage2 파이프라인 연동 (`modules/steps/step3_concrete_flow.py`, `modules/prompts/templates/step3_generate_command.yaml`)
