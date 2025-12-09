"""
일회성 스크립트: 재실행 Operation 결과 수집

Self-Correcting 후 재실행된 Operation의 결과를 수집하고 성공률을 비교합니다.

사용법:
    python collect_retry_results.py <타임스탬프_디렉토리>

예시:
    python collect_retry_results.py 20251209_115653
"""

import sys
import json
from pathlib import Path
from modules.caldera.executor import CalderaExecutor
from modules.caldera.reporter import CalderaReporter
from modules.core.config import get_caldera_url, get_caldera_api_key


def find_retry_operation(executor: CalderaExecutor, base_operation_name: str):
    """
    재실행 Operation 찾기

    Caldera API에서 "{base_operation_name}-Retry" 이름의 Operation을 찾습니다.
    """
    url = f"{executor.base_url}/api/v2/operations"
    response = executor.session.get(url)
    response.raise_for_status()

    operations = response.json()
    retry_name = f"{base_operation_name}-Retry"

    for op in operations:
        if op.get('name') == retry_name:
            return op.get('id'), op.get('state')

    return None, None


def main():
    if len(sys.argv) < 2:
        print("사용법: python collect_retry_results.py <타임스탬프_디렉토리>")
        print("예시: python collect_retry_results.py 20251209_115653")
        sys.exit(1)

    timestamp_dir = sys.argv[1]
    base_dir = Path("data/processed") / timestamp_dir / "caldera"

    # 기존 리포트 파일 확인
    first_report_file = base_dir / "operation_report.json"
    if not first_report_file.exists():
        print(f"[ERROR] 초기 operation_report.json을 찾을 수 없습니다: {first_report_file}")
        sys.exit(1)

    print("="*70)
    print("재실행 Operation 결과 수집")
    print("="*70)
    print(f"디렉토리: {base_dir}")
    print()

    # 1. 초기 실행 결과 로드
    with open(first_report_file, 'r', encoding='utf-8') as f:
        first_report = json.load(f)

    first_operation_name = first_report.get('operation_metadata', {}).get('name', '')
    first_stats = first_report.get('statistics', {})
    first_total = first_stats.get('total_abilities', 0)
    first_success = first_stats.get('success', 0)
    first_failed = first_stats.get('failed', 0)

    print(f"[초기 실행] Operation: {first_operation_name}")
    print(f"  전체: {first_total}, 성공: {first_success}, 실패: {first_failed}")

    # 2. Caldera에서 재실행 Operation 찾기
    print(f"\n[검색] 재실행 Operation 찾는 중...")
    executor = CalderaExecutor(get_caldera_url(), get_caldera_api_key())

    retry_op_id, retry_state = find_retry_operation(executor, first_operation_name)

    if not retry_op_id:
        print(f"[ERROR] 재실행 Operation을 찾을 수 없습니다.")
        print(f"[INFO] '{first_operation_name}-Retry' 이름의 Operation이 Caldera에 없습니다.")
        sys.exit(1)

    print(f"  [OK] 재실행 Operation 발견")
    print(f"  ID: {retry_op_id}")
    print(f"  상태: {retry_state}")

    # 3. 완료 대기 (필요한 경우)
    if retry_state not in ['finished', 'cleanup']:
        print(f"\n[대기] Operation이 아직 실행 중입니다. 완료될 때까지 대기합니다...")
        executor.wait_for_completion(retry_op_id, timeout=None)
        print(f"  [OK] Operation 완료")

    # 4. 결과 수집
    print(f"\n[수집] 재실행 결과 수집 중...")
    reporter = CalderaReporter()
    retry_report = reporter.collect_full_outputs(retry_op_id)

    if not retry_report:
        print("[ERROR] 재실행 결과 수집 실패")
        sys.exit(1)

    # 5. 리포트 저장
    retry_report_file = base_dir / "operation_report_retry.json"
    reporter.save_report(retry_report, str(retry_report_file))
    print(f"  [OK] 재실행 리포트 저장: {retry_report_file}")

    # 6. 통계 계산
    retry_stats = retry_report.get('statistics', {})
    retry_total = retry_stats.get('total_abilities', 0)
    retry_success = retry_stats.get('success', 0)
    retry_failed = retry_stats.get('failed', 0)

    # 7. 성공률 비교 출력
    print("\n" + "="*70)
    print("성공률 비교")
    print("="*70)
    print(f"{'구분':<20} {'전체':<10} {'성공':<10} {'실패':<10} {'성공률':<10}")
    print("-"*70)

    first_rate = (first_success / first_total * 100) if first_total > 0 else 0
    retry_rate = (retry_success / retry_total * 100) if retry_total > 0 else 0

    print(f"{'첫 번째 실행':<20} {first_total:<10} {first_success:<10} {first_failed:<10} {first_rate:.1f}%")
    print(f"{'재실행 (수정 후)':<20} {retry_total:<10} {retry_success:<10} {retry_failed:<10} {retry_rate:.1f}%")

    improvement = retry_rate - first_rate
    if improvement > 0:
        print(f"\n성공률 개선: +{improvement:.1f}% ({first_success} → {retry_success} 성공)")
    elif improvement < 0:
        print(f"\n성공률 감소: {improvement:.1f}%")
    else:
        print(f"\n성공률 동일")

    print("="*70)
    print("\n[완료] 결과 수집 완료!")
    print(f"리포트 파일: {retry_report_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[중단됨] 사용자가 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
