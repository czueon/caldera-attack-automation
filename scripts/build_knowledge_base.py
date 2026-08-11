"""
지식 베이스 빌드 스크립트

Atomic Red Team의 windows-index.yaml을 파싱해 technique_id 기준 정규화된
atomic test 인덱스(atomic_index.json)를 만든다. 상세 설계는 README 참고.

Usage:
    python scripts/build_knowledge_base.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ART_WINDOWS_INDEX_PATH = (
    PROJECT_ROOT / "data" / "knowledge_base" / "atomic-red-team" / "atomics" / "Indexes" / "windows-index.yaml"
)
INDEX_DIR = PROJECT_ROOT / "data" / "knowledge_base" / "index"
ATOMIC_INDEX_PATH = INDEX_DIR / "atomic_index.json"

# ART 자체 라벨(defense-evasion을 세분화한 것) -> 표준 ATT&CK tactic으로 정규화. 상세: README 참고.
ART_TACTIC_NORMALIZE = {"stealth": "defense-evasion", "defense-impairment": "defense-evasion"}


def build_atomic_index() -> List[Dict]:
    """ART windows-index.yaml -> technique_id 기준 정규화된 atomic test 리스트 (windows 플랫폼만, ART가 이미 필터링)"""
    if not ART_WINDOWS_INDEX_PATH.exists():
        raise FileNotFoundError(
            f"ART windows-index.yaml not found: {ART_WINDOWS_INDEX_PATH}\n"
            f"Clone Atomic Red Team first: git clone https://github.com/redcanaryco/atomic-red-team.git "
            f"data/knowledge_base/atomic-red-team"
        )

    with open(ART_WINDOWS_INDEX_PATH, "r", encoding="utf-8") as f:
        art_index = yaml.safe_load(f)

    # technique_id가 여러 tactic 버킷에 중복 등장 -> 버킷 라벨을 모으고, atomic_tests는 한 번만 사용
    tactics_by_technique: Dict[str, set] = {}
    entry_by_technique: Dict[str, Dict] = {}
    for bucket, techniques in art_index.items():
        normalized_tactic = ART_TACTIC_NORMALIZE.get(bucket, bucket)
        for technique_id, entry in techniques.items():
            tactics_by_technique.setdefault(technique_id, set()).add(normalized_tactic)
            entry_by_technique.setdefault(technique_id, entry)  # 내용은 버킷 간 동일하므로 첫 값만 사용

    index: List[Dict] = []
    for technique_id, entry in entry_by_technique.items():
        tech_meta = entry.get("technique", {}) or {}
        technique_name = tech_meta.get("name", "")
        tactics = sorted(tactics_by_technique[technique_id])

        for test in entry.get("atomic_tests", []):
            executor = test.get("executor", {}) or {}
            index.append({
                "technique_id": technique_id,
                "technique_name": technique_name,
                "tactics": tactics,
                "test_name": test.get("name", ""),
                "description": (test.get("description") or "").strip(),
                "platforms": [p.lower() for p in test.get("supported_platforms", [])],
                "executor_name": executor.get("name", ""),
                "command_template": executor.get("command", ""),
                "cleanup_command": executor.get("cleanup_command", ""),
                "elevation_required": bool(executor.get("elevation_required", False)),
                "input_arguments": test.get("input_arguments", {}) or {},
                "dependency_executor_name": test.get("dependency_executor_name", ""),
                "dependencies": test.get("dependencies", []) or [],
            })

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(ATOMIC_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[atomic_index] {len(entry_by_technique)} techniques / {len(index)} tests written to {ATOMIC_INDEX_PATH}")
    return index


def main():
    build_atomic_index()


if __name__ == "__main__":
    main()
