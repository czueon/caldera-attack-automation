"""Caldera 리포터 모듈."""
import requests
import json
from typing import Dict, List, Optional
from modules.core.config import get_caldera_url, get_caldera_api_key


class CalderaReporter:
    """Caldera Operation 실행 결과를 수집하는 클래스."""

    def __init__(self):
        self.base_url = get_caldera_url().rstrip('/')
        self.api_key = get_caldera_api_key()
        self.headers = {"KEY": self.api_key}

    def find_operation_id(self, name: str) -> Optional[str]:
        """Operation 이름으로 ID 찾기.

        Args:
            name: Operation 이름.

        Returns:
            Optional[str]: Operation ID 또는 None.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/api/v2/operations",
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            operations = resp.json()

            # 정확한 이름 매칭
            for op in operations:
                if op.get('name') == name:
                    print(f"✓ Found operation: {name}")
                    print(f"  ID: {op['id']}")
                    print(f"  State: {op.get('state')}\n")
                    return op['id']

            # 부분 매칭 시도
            matches = [op for op in operations if name.lower() in op.get('name', '').lower()]
            if matches:
                print(f"⚠ No exact match. Found {len(matches)} partial matches:")
                for i, match in enumerate(matches, 1):
                    print(f"  {i}. {match.get('name')} (ID: {match['id']}, State: {match.get('state')})")

                if len(matches) == 1:
                    print(f"\n✓ Using the only match: {matches[0].get('name')}\n")
                    return matches[0]['id']
                else:
                    print("\n✗ Multiple matches found. Please specify exact name or use operation ID")
                    return None

            print(f"✗ Operation '{name}' not found")
            return None

        except requests.exceptions.RequestException as e:
            print(f"✗ Error connecting to Caldera: {e}")
            return None
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return None

    def collect_full_outputs(self, operation_id: str) -> Dict:
        """모든 link의 output을 수집.

        Args:
            operation_id: Operation ID.

        Returns:
            Dict: 실행 결과 보고서.
        """
        print(f"{'='*70}")
        print(f"Collecting Full Agent Outputs")
        print(f"{'='*70}\n")

        # 1. Operation 기본 정보
        try:
            resp = requests.get(
                f"{self.base_url}/api/v2/operations/{operation_id}",
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            operation = resp.json()

            print(f"[OK] Operation: {operation.get('name')}")
            print(f"  ID: {operation_id}")
            print(f"  State: {operation.get('state')}")
            print(f"  Total links: {len(operation.get('chain', []))}\n")

        except Exception as e:
            print(f"[ERROR] Error fetching operation: {e}")
            return None

        # 2. 각 link의 result 수집
        results = []
        chain = operation.get('chain', [])
        success_count = 0

        print(f"Collecting outputs from {len(chain)} links...\n")

        for i, link in enumerate(chain, 1):
            link_id = link.get('id')
            ability_name = link.get('ability', {}).get('name', 'Unknown')
            status = link.get('status', -1)

            status_icon = "✓" if status == 0 else "✗"
            print(f"{status_icon} [{i:2d}/{len(chain)}] {ability_name}")

            # Link result 조회
            output_data = self._get_link_result(operation_id, link_id)

            if output_data:
                stdout = output_data.get('stdout', '')
                stderr = output_data.get('stderr', '')
                exit_code = output_data.get('exit_code', -1)

                if stdout in ['True', 'False']:
                    stdout = ''

                success_count += 1

                if stdout:
                    preview = stdout[:80].replace('\n', ' ')
                    print(f"      Output: {preview}...")
                elif stderr:
                    preview = stderr[:80].replace('\n', ' ')
                    print(f"      Error: {preview}...")
                else:
                    print(f"      (no output)")
            else:
                # Fallback
                output = link.get('output', {})
                if isinstance(output, dict):
                    stdout = output.get('stdout', '')
                    stderr = output.get('stderr', '')
                    exit_code = output.get('exit_code', -1)
                else:
                    stdout = str(output) if output else ''
                    stderr = ''
                    exit_code = -1

                if stdout in ['True', 'False']:
                    stdout = ''

                print(f"      (using fallback)")

            results.append({
                'link_id': link_id,
                'ability_id': link.get('ability', {}).get('ability_id'),
                'ability_name': ability_name,
                'tactic': link.get('ability', {}).get('tactic'),
                'technique_id': link.get('ability', {}).get('technique_id'),
                'technique_name': link.get('ability', {}).get('technique_name'),
                'command': link.get('command', ''),
                'executor': link.get('executor', ''),
                'paw': link.get('paw'),
                'status': status,
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'start_time': link.get('collect'),
                'finish_time': link.get('finish'),
                'pid': link.get('pid'),
            })

        print(f"\n{'='*70}")
        print(f"✓ Successfully fetched {success_count}/{len(chain)} link results")
        print(f"{'='*70}\n")

        # 3. Report 구성
        report = {
            'operation_metadata': {
                'id': operation.get('id'),
                'name': operation.get('name'),
                'state': operation.get('state'),
                'adversary': operation.get('adversary', {}).get('name'),
                'adversary_id': operation.get('adversary', {}).get('adversary_id'),
                'group': operation.get('group'),
                'planner': operation.get('planner', {}).get('name'),
                'start_time': operation.get('start'),
                'finish_time': operation.get('finish'),
            },
            'agents': self._extract_agents(operation),
            'results': results,
            'statistics': self._calculate_stats(results),
        }

        return report

    def _get_link_result(self, operation_id: str, link_id: str) -> Optional[Dict]:
        """Link의 result를 가져오기."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v2/operations/{operation_id}/links/{link_id}/result",
                headers=self.headers,
                timeout=10
            )

            if resp.status_code == 200:
                data = resp.json()

                if 'result' in data:
                    import base64
                    result_b64 = data['result']
                    try:
                        result_json = base64.b64decode(result_b64).decode('utf-8')
                        result_data = json.loads(result_json)
                        return {
                            'stdout': result_data.get('stdout', ''),
                            'stderr': result_data.get('stderr', ''),
                            'exit_code': int(result_data.get('exit_code', -1)) if result_data.get('exit_code') else -1
                        }
                    except Exception:
                        pass

                if 'stdout' in data or 'stderr' in data:
                    return {
                        'stdout': data.get('stdout', ''),
                        'stderr': data.get('stderr', ''),
                        'exit_code': data.get('exit_code', -1)
                    }

        except Exception:
            pass

        return None

    def _extract_agents(self, operation: Dict) -> List[Dict]:
        """Agent 정보 추출."""
        agents = []
        agent_set = set()

        for link in operation.get('chain', []):
            paw = link.get('paw')
            if paw and paw not in agent_set:
                agent_set.add(paw)
                agents.append({
                    'paw': paw,
                    'platform': link.get('executor', 'unknown'),
                })

        return agents

    def _calculate_stats(self, results: List[Dict]) -> Dict:
        """통계 계산 (ability 단위로 집계 - 여러 agent에서 실행된 경우 하나라도 성공하면 성공)."""
        # Ability 단위로 그룹화
        ability_results = {}
        for r in results:
            ability_id = r.get('ability_id')
            if not ability_id:
                continue

            if ability_id not in ability_results:
                ability_results[ability_id] = {
                    'ability_name': r.get('ability_name'),
                    'statuses': [],
                    'completed': []
                }

            ability_results[ability_id]['statuses'].append(r.get('status'))
            ability_results[ability_id]['completed'].append(bool(r.get('finish_time')))

        # Ability별 성공 여부 판단 (하나라도 성공하면 성공)
        total_abilities = len(ability_results)
        successful_abilities = sum(1 for ab in ability_results.values()
                                   if 0 in ab['statuses'])  # 하나라도 status=0 이면 성공
        completed_abilities = sum(1 for ab in ability_results.values()
                                  if any(ab['completed']))
        failed_abilities = completed_abilities - successful_abilities

        # Link 레벨 통계 (참고용)
        total_links = len(results)
        with_stdout = sum(1 for r in results if r.get('stdout') and r['stdout'] != '')
        with_stderr = sum(1 for r in results if r.get('stderr') and r['stderr'] != '')
        with_any_output = sum(1 for r in results
                              if (r.get('stdout') and r['stdout'] != '')
                              or (r.get('stderr') and r['stderr'] != ''))

        return {
            'total_abilities': total_abilities,
            'completed': completed_abilities,
            'success': successful_abilities,
            'failed': failed_abilities,
            'success_rate': round(successful_abilities / completed_abilities * 100, 2) if completed_abilities > 0 else 0,
            'total_links': total_links,  # 참고: 실제 실행된 link 수
            'with_stdout': with_stdout,
            'with_stderr': with_stderr,
            'with_any_output': with_any_output,
        }

    def save_report(self, report: Dict, filename: str):
        """Report 저장."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        stats = report['statistics']
        print(f"✓ Report saved: {filename}\n")
        print(f"{'='*70}")
        print(f"Final Statistics")
        print(f"{'='*70}")
        print(f"Operation: {report['operation_metadata']['name']}")
        print(f"Total abilities: {stats['total_abilities']}")
        print(f"Success rate: {stats['success_rate']}%")
