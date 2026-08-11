"""
지식 베이스 조회 모듈

scripts/build_knowledge_base.py로 생성한 atomic_index.json을 로드해
기법(technique) 기준으로 예시 명령어를 조회한다. 설계 근거는 README 참고.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ATOMIC_INDEX_PATH = PROJECT_ROOT / "data" / "knowledge_base" / "index" / "atomic_index.json"

# step4_ability_generator.py가 executor를 PowerShell로 고정 생성하므로 예시도 이를 우선한다.
EXECUTOR_PRIORITY = ["powershell", "command_prompt"]

# 프롬프트에는 불필요한 필드 (platforms는 이미 windows로 필터링되어 중복, description/cleanup_command는 컨텍스트 절약을 위해 제외)
PROMPT_EXCLUDE_FIELDS = {"description", "platforms", "cleanup_command"}


class KnowledgeBase:
    """ATT&CK technique -> 실행 가능 명령어(atomic test) 조회."""

    def __init__(self, atomic_index_path: Optional[Path] = None):
        self.atomic_index_path = Path(atomic_index_path) if atomic_index_path else DEFAULT_ATOMIC_INDEX_PATH

        self._records: List[Dict] = []
        self._by_technique: Dict[str, List[Dict]] = defaultdict(list)
        self._technique_ids: List[str] = []       # TF-IDF 코퍼스 순서와 동일
        self._technique_names: List[str] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._technique_matrix = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return

        if not self.atomic_index_path.exists():
            raise FileNotFoundError(
                f"Knowledge base index not found: {self.atomic_index_path}\n"
                f"Run `python scripts/build_knowledge_base.py` first."
            )
        with open(self.atomic_index_path, "r", encoding="utf-8") as f:
            self._records = json.load(f)

        seen_names: Dict[str, str] = {}
        for record in self._records:
            self._by_technique[record["technique_id"]].append(record)
            seen_names.setdefault(record["technique_id"], record["technique_name"])

        # 기법 단위 TF-IDF 코퍼스 (technique_name만 사용, test description은 제외)
        self._technique_ids = list(seen_names.keys())
        self._technique_names = list(seen_names.values())
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._technique_matrix = self._vectorizer.fit_transform(self._technique_names)

        self._loaded = True

    def get_examples(self, technique_id: str) -> List[Dict]:
        """동일 기법(technique_id)의 예시 명령어 목록 반환. 없으면 빈 리스트."""
        self._ensure_loaded()
        return list(self._by_technique.get(technique_id, []))

    @staticmethod
    def _to_prompt_dict(record: Dict) -> Dict:
        """프롬프트에 넣을 필드만 남긴 사본 반환 (PROMPT_EXCLUDE_FIELDS 제외)."""
        return {k: v for k, v in record.items() if k not in PROMPT_EXCLUDE_FIELDS}

    @staticmethod
    def _select_examples(records: List[Dict]) -> List[Dict]:
        """test 목록에서 예시 후보 선정. 실행 불가능한 test(command_template 없음)는 제외하고,
        EXECUTOR_PRIORITY 순서로 봤을 때 가장 우선순위 높은 executor의 test를 전부 반환.
        전부 실행 불가능하면 빈 리스트."""
        runnable = [r for r in records if r.get("command_template")]
        if not runnable:
            return []

        for preferred in EXECUTOR_PRIORITY:
            same_executor = [r for r in runnable if r["executor_name"] == preferred]
            if same_executor:
                return same_executor
        return runnable

    def find_similar_technique(self, technique_name: str, exclude_technique_id: str = "", top_k: int = 1) -> List[str]:
        """기법 이름(technique_name) 기준 TF-IDF 코사인 유사도가 가장 높은 technique_id 목록 반환."""
        self._ensure_loaded()
        if not technique_name.strip():
            return []

        query_vec = self._vectorizer.transform([technique_name])
        sims = cosine_similarity(query_vec, self._technique_matrix)[0]

        ranked = sims.argsort()[::-1]
        result = []
        for i in ranked:
            if sims[i] <= 0:
                break
            tid = self._technique_ids[i]
            if tid == exclude_technique_id:
                continue
            result.append(tid)
            if len(result) >= top_k:
                break
        return result

    def get_example_commands(self, technique_id: str, technique_name: str = "") -> List[Dict]:
        """stage2 프롬프트의 {example_commands}에 넣을 예시 목록 반환.

        동일 기법 test가 있으면 그걸 쓰고, 없으면 technique_name으로 가장 유사한 기법의 test를 대신 쓴다.
        기법 하나에 test가 여러 개면(특히 T1685처럼 넓은 기법) 서로 성격이 다른 경우가 많아
        KB에서 하나로 좁히지 않고, 같은 executor(PowerShell 우선)의 test를 전부 넘긴다 —
        최종 선택은 stage2 LLM이 환경/맥락을 보고 한다.
        """
        exact = self.get_examples(technique_id)
        if not exact:
            similar_ids = self.find_similar_technique(technique_name, exclude_technique_id=technique_id, top_k=1)
            exact = self._by_technique[similar_ids[0]] if similar_ids else []

        return [self._to_prompt_dict(r) for r in self._select_examples(exact)]
