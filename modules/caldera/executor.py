"""Caldera API 연동 실행기."""
import time
import requests
from typing import List, Dict, Any, Optional
from modules.core.models import AbilityResult


class CalderaExecutor:
    """Caldera API와 통신하여 Operation을 제어."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'KEY': api_key})

    def create_operation(self, name: str, adversary_id: str, agent_paw: Optional[str] = None) -> str:
        """새로운 Operation 생성.

        Usage:
            Self-Correcting 엔진이 검증을 위해 새로운 공격 작전을 생성할 때 사용됩니다.

        Args:
            name: Operation 이름.
            adversary_id: Adversary 프로파일 ID.
            agent_paw: 에이전트 식별자 (PAW). None이면 모든 에이전트 대상.

        Returns:
            str: 생성된 Operation ID.
        """
        url = f"{self.base_url}/api/v2/operations"
        payload = {
            "name": name,
            "adversary": {"adversary_id": adversary_id},
            "planner": {"planner_id": "atomic"},
            "source": {"id": "basic"},
            "group": "",  # Empty group targets all agents
            "jitter": "1/1"  # No delay between abilities (format: "fraction/seconds")
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()['id']

    def start_operation(self, operation_id: str):
        """Operation 시작 (state를 running으로 변경).

        Usage:
            생성된 Operation을 실제로 실행 상태로 전환할 때 사용됩니다.
        """
        # v2 API에서는 생성 시 바로 시작되거나, 별도 start 호출 필요.
        # 기존 코드 로직 참조: PATCH로 state 변경
        url = f"{self.base_url}/api/v2/operations/{operation_id}"
        payload = {"state": "running"}
        response = self.session.patch(url, json=payload)
        response.raise_for_status()

    def wait_for_completion(self, operation_id: str, timeout: Optional[int] = None) -> bool:
        """Operation 완료 대기.

        Usage:
            실행된 Operation이 끝날 때까지 대기하여 결과를 수집할 시점을 판단할 때 사용됩니다.

        Args:
            operation_id: Operation ID.
            timeout: 최대 대기 시간 (초). None이면 무제한 대기.

        Returns:
            bool: 완료 여부 (True: 완료, False: 타임아웃).
        """
        start_time = time.time()
        url = f"{self.base_url}/api/v2/operations/{operation_id}"

        while True:
            # timeout이 설정되어 있고 초과한 경우
            if timeout is not None and (time.time() - start_time >= timeout):
                return False

            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                state = data.get('state')
                if state in ['finished', 'cleanup']:
                    return True
            time.sleep(5)

    def get_operation_results(self, operation_id: str) -> List[AbilityResult]:
        """Operation 실행 결과 조회.

        Usage:
            완료된 Operation의 각 Ability 실행 성공/실패 여부와 로그를 수집하여 분석할 때 사용됩니다.

        Args:
            operation_id: Operation ID.

        Returns:
            List[AbilityResult]: 실행 결과 목록.
        """
        # 링크 결과 조회
        url = f"{self.base_url}/api/v2/operations/{operation_id}/links"
        response = self.session.get(url)
        response.raise_for_status()
        links = response.json()

        results = []
        for link in links:
            # 결과 객체 생성
            result = AbilityResult(
                link_id=link.get('id'),
                ability_id=link.get('ability', {}).get('ability_id', 'unknown'),
                ability_name=link.get('ability', {}).get('name', 'unknown'),
                command=link.get('command', ''),
                exit_code=link.get('status', -1), # status가 exit code 역할
                stdout=link.get('output', ''),    # output이 stdout/stderr 포함
                stderr="",                        # 별도 분리 안됨
                status=link.get('status', -1)
            )
            results.append(result)
        
        return results
