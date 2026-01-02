"""Caldera Agent 관리 유틸리티."""
import time
import requests
from modules.core.config import get_caldera_url, get_caldera_api_key


class AgentManager:
    """Caldera Agent 관리 클래스."""

    def __init__(self, caldera_url=None, api_key=None):
        """
        Args:
            caldera_url: Caldera 서버 URL (None이면 환경변수에서 로드).
            api_key: Caldera API 키 (None이면 환경변수에서 로드).
        """
        self.caldera_url = (caldera_url or get_caldera_url()).rstrip("/")
        self.api_key = api_key or get_caldera_api_key()

    def _headers(self):
        """API 요청 헤더 생성."""
        return {"KEY": self.api_key, "Content-Type": "application/json"}

    def get_agents(self, timeout=10):
        """
        모든 에이전트 목록 조회.

        Args:
            timeout: 요청 타임아웃(초).

        Returns:
            list: 에이전트 목록.
        """
        url = f"{self.caldera_url}/api/v2/agents"
        r = requests.get(url, headers=self._headers(), timeout=timeout)
        r.raise_for_status()
        return r.json()

    def kill_all_agents(self):
        """
        모든 에이전트 삭제.

        Returns:
            int: 삭제된 에이전트 수.
        """
        agents = self.get_agents()
        if not agents:
            print("[INFO] 삭제할 agent 없음")
            return 0

        print(f"[INFO] 삭제 대상 agent 수: {len(agents)}")

        for a in agents:
            paw = a.get("paw")
            del_url = f"{self.caldera_url}/api/v2/agents/{paw}"
            resp = requests.delete(del_url, headers=self._headers(), timeout=10)
            print(f"[KILL] agent {paw} → HTTP {resp.status_code}")

        print("[OK] 모든 agent 삭제 완료")
        return len(agents)

    def wait_for_agents(self, expected_count=1, timeout=300, check_interval=5):
        """
        에이전트가 생성될 때까지 대기.

        Args:
            expected_count: 기대하는 최소 에이전트 수 (기본값: 1).
            timeout: 최대 대기 시간(초) (기본값: 300초 = 5분).
            check_interval: 체크 간격(초) (기본값: 5초).

        Returns:
            list: 연결된 에이전트 목록.

        Raises:
            TimeoutError: 타임아웃 시간 내에 에이전트가 생성되지 않은 경우.
        """
        print(f"[INFO] 에이전트 대기 중... (최소 {expected_count}개, 최대 {timeout}초)")

        elapsed = 0
        while elapsed < timeout:
            try:
                agents = self.get_agents()
                agent_count = len(agents)

                if agent_count >= expected_count:
                    print(f"[OK] 에이전트 {agent_count}개 확인됨")
                    for agent in agents:
                        paw = agent.get('paw', 'unknown')
                        platform = agent.get('platform', 'unknown')
                        print(f"  - Agent PAW: {paw}, Platform: {platform}")
                    return agents
                else:
                    print(f"  [{elapsed}초] 에이전트 {agent_count}/{expected_count}개 확인됨, 대기 중...")
            except Exception as e:
                print(f"  [{elapsed}초] 에이전트 조회 실패 ({e}), 재시도 중...")

            time.sleep(check_interval)
            elapsed += check_interval

        raise TimeoutError(
            f"타임아웃: {timeout}초 내에 에이전트 {expected_count}개가 생성되지 않았습니다."
        )
