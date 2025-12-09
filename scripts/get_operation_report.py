#!/usr/bin/env python3
"""
Caldera Full Output Collector - Final Version
UI가 사용하는 실제 endpoint로 모든 output 수집
"""

import requests
import json
import sys
from typing import Dict, List, Optional
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.core.config import get_caldera_url, get_caldera_api_key


class FinalOutputCollector:
    """UI 방식으로 완전한 output 수집"""
    
    def __init__(self):
        base_url = get_caldera_url()
        api_key = get_caldera_api_key()
        self.base_url = base_url.rstrip('/')
        self.headers = {"KEY": api_key}
    
    def find_operation_id(self, name: str) -> Optional[str]:
        """
        Operation 이름으로 ID 찾기
        
        Args:
            name: Operation 이름
            
        Returns:
            Operation ID 또는 None
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
        """
        모든 link의 output을 수집
        Endpoint: /api/v2/operations/{op_id}/links/{link_id}/result
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
            
            print(f"✓ Operation: {operation.get('name')}")
            print(f"  ID: {operation_id}")
            print(f"  State: {operation.get('state')}")
            print(f"  Total links: {len(operation.get('chain', []))}\n")
            
        except Exception as e:
            print(f"✗ Error fetching operation: {e}")
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
            
            # Link result 조회 (UI가 사용하는 endpoint)
            output_data = self._get_link_result(operation_id, link_id)
            
            if output_data:
                stdout = output_data.get('stdout', '')
                stderr = output_data.get('stderr', '')
                exit_code = output_data.get('exit_code', -1)
                
                # True/False는 Caldera의 "No output"이므로 제외
                if stdout in ['True', 'False']:
                    stdout = ''
                
                success_count += 1
                
                # Output 미리보기 (의미있는 output만)
                if stdout:
                    preview = stdout[:80].replace('\n', ' ')
                    print(f"      Output: {preview}...")
                elif stderr:
                    preview = stderr[:80].replace('\n', ' ')
                    print(f"      Error: {preview}...")
                else:
                    print(f"      (no output)")
            else:
                # Fallback: 기본 output 사용
                output = link.get('output', {})
                if isinstance(output, dict):
                    stdout = output.get('stdout', '')
                    stderr = output.get('stderr', '')
                    exit_code = output.get('exit_code', -1)
                else:
                    stdout = str(output) if output else ''
                    stderr = ''
                    exit_code = -1
                
                # True/False는 Caldera의 "No output"이므로 제외
                if stdout in ['True', 'False']:
                    stdout = ''
                
                print(f"      (using fallback)")
            
            # Result 저장
            result = {
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
            }
            
            results.append(result)
        
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
        """
        Link의 result를 가져오기
        Endpoint: /api/v2/operations/{op_id}/links/{link_id}/result
        
        Result는 Base64로 인코딩된 JSON 문자열입니다.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/api/v2/operations/{operation_id}/links/{link_id}/result",
                headers=self.headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                # result 필드에서 Base64 디코딩
                if 'result' in data:
                    import base64
                    result_b64 = data['result']
                    
                    try:
                        # Base64 디코딩
                        result_json = base64.b64decode(result_b64).decode('utf-8')
                        result_data = json.loads(result_json)
                        
                        return {
                            'stdout': result_data.get('stdout', ''),
                            'stderr': result_data.get('stderr', ''),
                            'exit_code': int(result_data.get('exit_code', -1)) if result_data.get('exit_code') else -1
                        }
                    except Exception as decode_error:
                        # Base64 디코딩 실패 시 fallback
                        pass
                
                # Fallback: 직접 stdout/stderr 필드 확인
                if 'stdout' in data or 'stderr' in data:
                    return {
                        'stdout': data.get('stdout', ''),
                        'stderr': data.get('stderr', ''),
                        'exit_code': data.get('exit_code', -1)
                    }
            
        except Exception as e:
            pass
        
        return None
    
    def _extract_agents(self, operation: Dict) -> List[Dict]:
        """Agent 정보 추출"""
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
        """통계 계산"""
        total = len(results)
        completed = sum(1 for r in results if r.get('finish_time'))
        success = sum(1 for r in results if r['status'] == 0)
        failed = completed - success if completed > 0 else 0
        
        # stdout이 있는 것 (True/False는 수집 단계에서 이미 제외됨)
        with_stdout = sum(1 for r in results if r.get('stdout') and r['stdout'] != '')
        
        # stderr이 있는 것 (M7에 중요!)
        with_stderr = sum(1 for r in results if r.get('stderr') and r['stderr'] != '')
        
        # stdout 또는 stderr이 있는 것
        with_any_output = sum(1 for r in results 
                              if (r.get('stdout') and r['stdout'] != '') 
                              or (r.get('stderr') and r['stderr'] != ''))
        
        return {
            'total_abilities': total,
            'completed': completed,
            'success': success,
            'failed': failed,
            'success_rate': round(success / completed * 100, 2) if completed > 0 else 0,
            'with_stdout': with_stdout,
            'with_stderr': with_stderr,
            'with_any_output': with_any_output,
        }
    
    def save_report(self, report: Dict, filename: str):
        """Report 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        stats = report['statistics']
        
        print(f"✓ Report saved: {filename}\n")
        print(f"{'='*70}")
        print(f"Final Statistics")
        print(f"{'='*70}")
        print(f"Operation: {report['operation_metadata']['name']}")
        print(f"Total abilities: {stats['total_abilities']}")
        print(f"Completed: {stats['completed']}")
        print(f"Success: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success rate: {stats['success_rate']}%")
        print(f"\nOutput Statistics:")
        print(f"  With stdout: {stats['with_stdout']}")
        print(f"  With stderr: {stats['with_stderr']}")
        print(f"  With any output: {stats['with_any_output']}/{stats['total_abilities']}")
        print(f"{'='*70}\n")
        
        # Output 샘플 출력
        sample_count = 0
        print("Sample outputs:\n")
        for result in report['results']:
            # output이 있으면 샘플로 출력 (True/False는 수집 시 이미 제외됨)
            if result.get('stdout'):
                print(f"  {result['ability_name']}:")
                stdout_preview = result['stdout'][:150]
                if len(result['stdout']) > 150:
                    stdout_preview += "..."
                print(f"    {stdout_preview}\n")
                sample_count += 1
                if sample_count >= 5:
                    break
        
        if sample_count == 0:
            print("  (No outputs available)\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Collect full agent outputs using UI endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Operation 이름으로 조회
  python final_output_collector.py --name "new-test-2"
  
  # Operation ID로 직접 조회
  python final_output_collector.py --id 8d895fa7-76d5-4438-bdae-33d64483ea61
  
  # 출력 파일 지정
  python final_output_collector.py --name "new-test-2" --output my_report.json
  
  # API key 지정
  python final_output_collector.py --name "new-test-2" --api-key REDADMIN123
        """
    )
    
    # Operation 식별 방법
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument('--name', '-n', help='Operation 이름')
    id_group.add_argument('--id', '-i', help='Operation ID')
    
    parser.add_argument('--output', '-o', default='full_output_report.json',
                        help='Output file (default: full_output_report.json)')
    parser.add_argument('--api-key', '-k', default='ADMIN123', help='API key')
    parser.add_argument('--url', '-u', default='http://localhost:8888', help='Caldera URL')
    
    args = parser.parse_args()
    
    # 수집 시작
    collector = FinalOutputCollector()
    
    # Operation ID 가져오기
    if args.name:
        operation_id = collector.find_operation_id(args.name)
        if not operation_id:
            sys.exit(1)
    else:
        operation_id = args.id
    
    report = collector.collect_full_outputs(operation_id)
    
    if report:
        collector.save_report(report, args.output)
        
        # 실패 케이스 분석 (M7용)
        failures = [r for r in report['results'] if r['status'] != 0]
        if failures:
            print(f"Found {len(failures)} failures for M7 Self-Correcting:\n")
            for failure in failures[:5]:  # 처음 5개만
                print(f"  ✗ {failure['ability_name']}")
                if failure['stderr']:
                    print(f"    Error: {failure['stderr'][:100]}...")
    else:
        print("\n✗ Failed to collect outputs")
        sys.exit(1)


if __name__ == '__main__':
    main()
