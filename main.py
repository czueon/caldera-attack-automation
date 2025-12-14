"""
KISA TTPs → Caldera Adversary Pipeline
전체 파이프라인 실행 엔트리포인트

실행 모드:
- 일반 모드: --step 1~5 또는 범위 지정 (예: 1~3)
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# 모듈 임포트
from modules.steps.step1_pdf_processing import PDFProcessor
from modules.steps.step2_abstract_flow import AbstractFlowExtractor
from modules.steps.step3_concrete_flow import ConcreteFlowGenerator
from modules.steps.step4_ability_generator import AbilityGenerator
from modules.steps.step5_self_correcting import OfflineCorrector
from modules.caldera.uploader import CalderaUploader
from modules.caldera.executor import CalderaExecutor
from modules.caldera.reporter import CalderaReporter
from modules.caldera.agent_manager import AgentManager
from modules.core.config import get_caldera_url, get_caldera_api_key, get_llm_provider
from modules.core.metrics import init_metrics, get_metrics_tracker
from modules.ai.factory import get_llm_client
from scripts import vm_reload
import yaml


def parse_step_range(step_arg):
    """
    --step 인자 파싱

    Examples:
        "1"     → [1]
        "1~3"   → [1, 2, 3]
        "2~5"   → [2, 3, 4, 5]
        "all"   → [1, 2, 3, 4, 5]
    """
    if step_arg == "all":
        return [1, 2, 3, 4, 5]

    if "~" in step_arg:
        # 범위 지정
        start, end = step_arg.split("~")
        start = int(start)
        end = int(end)

        if start > end:
            raise ValueError(f"Invalid range: {start}~{end} (start > end)")

        # 범위 생성
        steps = list(range(start, end + 1))
        return steps
    else:
        # 단일 step
        try:
            return [int(step_arg)]
        except ValueError:
            raise ValueError(f"Invalid step: {step_arg}")


def main():
    parser = argparse.ArgumentParser(
        description="KISA TTPs 보고서를 Caldera adversary profile로 변환",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Step 선택
    parser.add_argument(
        "--step",
        type=str,
        required=True,
        help="""Step 선택 (단일 또는 범위):
  1      : PDF 처리 (텍스트 추출)
  2      : 추상 공격 흐름 추출 (환경 독립적)
  3      : 구체적 공격 흐름 생성 (환경 적용, Technique 자동 선택)
  4      : Caldera Ability 생성
  5      : Caldera 자동화 (업로드 → 실행 → Self-Correcting)
  all    : 전체 실행 (1~5)

  범위 지정:
  1~3    : Step 1, 2, 3 실행
  3~5    : Step 3, 4, 5 실행
"""
    )

    # 입력 파일
    parser.add_argument(
        "--pdf",
        type=str,
        help="입력 PDF 파일 경로 (Step 1에서 필수)"
    )

    parser.add_argument(
        "--env",
        type=str,
        help="환경 설명 MD 파일 경로 (Step 3에서 필수)"
    )

    parser.add_argument(
        "--agent-paw",
        type=str,
        default=None,
        help="Caldera Agent PAW (생략 시 모든 에이전트 대상, 예: agent123)"
    )

    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Step 5에서 업로드 단계 건너뛰기 (이미 업로드된 경우)"
    )

    parser.add_argument(
        "--skip-execution",
        action="store_true",
        help="Step 5에서 자동 실행 건너뛰기 (수동으로 Operation 실행 후 리포트만 사용)"
    )

    parser.add_argument(
        "--operation-name",
        type=str,
        help="Step 5에서 사용할 Operation 이름 (기본: Auto-Operation-<timestamp>)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="중간 결과 저장 디렉토리 (기본: data/processed)"
    )

    # 버전 ID (미지정 시 타임스탬프 자동 생성)
    parser.add_argument(
        "--version-id",
        type=str,
        default=None,
        help="결과 버전 ID (예: 20251209_153000). 생략 시 현재 시각으로 자동 생성."
    )

    args = parser.parse_args()

    print("="*70)
    print("KISA TTPs → Caldera Adversary Pipeline")
    print("="*70)

    # Step 파싱
    try:
        steps = parse_step_range(args.step)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"실행 Step: {', '.join(map(str, steps))}")
    print("="*70)

    # pdf 파일명 기반 스템과 version_id 결정
    if not args.pdf:
        print("[ERROR] --pdf 인자가 필요합니다 (결과 경로 규칙: data/processed/{pdf_stem}/{version_id}/)")
        sys.exit(1)

    pdf_stem = Path(args.pdf).stem
    version_id = args.version_id or datetime.now().strftime("%Y%m%d_%H%M%S")

    # 결과 루트: data/processed/{pdf_stem}/{version_id}
    base_dir = Path(args.output_dir) / pdf_stem / version_id
    base_dir.mkdir(parents=True, exist_ok=True)

    # 스텝별 기본 출력 경로 (파일명은 step1.yml, step2.yml, step3.yml)
    step1_output = base_dir / "step1.yml"
    step2_output = base_dir / "step2.yml"
    step3_output = base_dir / "step3.yml"
    caldera_output_dir = base_dir / "caldera"

    print(f"결과 저장 루트: {base_dir}")
    print(f"  - PDF: {pdf_stem}")
    print(f"  - Version ID: {version_id}")
    print("="*70)

    # 메트릭 추적 초기화
    try:
        llm_provider = get_llm_provider()
        llm_client = get_llm_client()
        llm_model = getattr(llm_client, 'model', '') or getattr(llm_client, 'model_name', '')
    except:
        llm_provider = "unknown"
        llm_model = "unknown"

    tracker = init_metrics(
        experiment_id=version_id,
        pdf_name=pdf_stem,
        llm_provider=llm_provider,
        llm_model=llm_model
    )

    print(f"\n[메트릭 추적] LLM Provider: {llm_provider}, Model: {llm_model}")
    print("="*70)

    # Step 1: PDF Processing
    if 1 in steps:
        if not args.pdf:
            print("[ERROR] Step 1 실행 시 --pdf 인자가 필요합니다")
            sys.exit(1)

        print("\n[Step 1] PDF Processing")
        print("-" * 70)

        tracker.start_step("Step 1: PDF Processing")
        try:
            processor = PDFProcessor()
            # version_id를 명시적으로 전달하여 동일 버전으로 연결
            processor.process_pdf(args.pdf, output_path=str(step1_output), version_id=version_id)
            tracker.end_step(success=True)
        except Exception as e:
            tracker.end_step(success=False, error_message=str(e))
            raise

    # Step 2: Abstract Flow Extraction
    if 2 in steps:
        print("\n[Step 2] Abstract Attack Flow Extraction")
        print("-" * 70)

        if not Path(step1_output).exists():
            print(f"[ERROR] {step1_output} 파일이 없습니다. Step 1을 먼저 실행하세요.")
            sys.exit(1)

        tracker.start_step("Step 2: Abstract Flow Extraction")
        try:
            extractor = AbstractFlowExtractor()
            extractor.extract_abstract_flow(str(step1_output), str(step2_output), version_id=version_id)
            tracker.end_step(success=True)
        except Exception as e:
            tracker.end_step(success=False, error_message=str(e))
            raise

    # Step 3: Concrete Flow Generation with Technique Selection
    if 3 in steps:
        if not args.env:
            print("[ERROR] Step 3 실행 시 --env 인자가 필요합니다")
            print("예: --env environment_description.md")
            sys.exit(1)

        print("\n[Step 3] Concrete Attack Flow Generation (with Technique Selection)")
        print("-" * 70)

        if not Path(step2_output).exists():
            print(f"[ERROR] {step2_output} 파일이 없습니다. Step 2를 먼저 실행하세요.")
            sys.exit(1)

        if not Path(args.env).exists():
            print(f"[ERROR] {args.env} 파일이 없습니다.")
            sys.exit(1)

        tracker.start_step("Step 3: Concrete Flow Generation")
        try:
            generator = ConcreteFlowGenerator()
            generator.generate_concrete_flow(str(step2_output), args.env, str(step3_output), version_id=version_id)
            tracker.end_step(success=True)
        except Exception as e:
            tracker.end_step(success=False, error_message=str(e))
            raise

    # Step 4: Caldera Ability Generation
    if 4 in steps:
        print("\n[Step 4] Caldera Ability Generation")
        print("-" * 70)

        if not Path(step3_output).exists():
            print(f"[ERROR] {step3_output} 파일이 없습니다. Step 3을 먼저 실행하세요.")
            sys.exit(1)

        tracker.start_step("Step 4: Caldera Ability Generation")
        try:
            generator = AbilityGenerator()
            generator.generate_abilities(str(step3_output), str(caldera_output_dir))
            tracker.end_step(success=True)
        except Exception as e:
            tracker.end_step(success=False, error_message=str(e))
            raise

    # Step 5: Caldera Automation (Upload → Execute → Self-Correct)
    if 5 in steps:
        tracker.start_step("Step 5: Caldera Automation")

        print("\n[Step 5] Caldera 자동화 (업로드 → 실행 → Self-Correcting)")
        print("-" * 70)

        # Agent Manager 초기화
        agent_manager = AgentManager()

        print("\n[5-pre] Caldera agent 정리")
        print("-" * 70)
        try:
            agent_manager.kill_all_agents()
        except Exception as e:
            print(f"[WARNING] agent 정리 실패: {e}")
            print("계속 진행합니다...")

        # VM 재부팅
        print("\n[5-0] VM 재부팅")
        print("-" * 70)
        try:
            controller = vm_reload.VBoxController()
            controller.restore_and_boot_all()
        except Exception as e:
            print(f"  [WARNING] VM 재부팅 실패: {str(e)}")
            print("  계속 진행합니다...")

        abilities_file = caldera_output_dir / "abilities.yml"
        adversaries_file = caldera_output_dir / "adversaries.yml"

        if not Path(abilities_file).exists():
            print("[ERROR] abilities.yml 파일이 없습니다. Step 4를 먼저 실행하세요.")
            sys.exit(1)

        if not Path(adversaries_file).exists():
            print("[ERROR] adversaries.yml 파일이 없습니다. Step 4를 먼저 실행하세요.")
            sys.exit(1)

        # 환경 설명 파일 확인
        if not args.env or not Path(args.env).exists():
            print("[ERROR] --env 인자로 환경 설명 파일을 지정해야 합니다.")
            sys.exit(1)

        # 5-1. Caldera 업로드
        uploaded_adversary_id = None
        if not args.skip_upload:
            print("\n[5-1] Caldera 업로드")
            print("-" * 70)

            uploader = CalderaUploader()
            uploader.upload_abilities(str(abilities_file))
            adversary_ids = uploader.upload_adversaries(str(adversaries_file))

            if not adversary_ids:
                print("[ERROR] Adversary 업로드 실패")
                sys.exit(1)

            uploaded_adversary_id = adversary_ids[0]
            print(f"\n[OK] Adversary 업로드 완료: {uploaded_adversary_id}")
        else:
            # adversaries.yml에서 ID 읽기
            with open(adversaries_file, 'r', encoding='utf-8') as f:
                adversaries = yaml.safe_load(f)
                if adversaries:
                    uploaded_adversary_id = adversaries[0].get('adversary_id')
            print(f"\n[SKIP] 업로드 건너뜀. Adversary ID: {uploaded_adversary_id}")

        # 5-2. Operation 실행
        operation_report_file = None
        if not args.skip_execution:
            print("\n[5-2] Operation 생성 및 실행")
            print("-" * 70)

            if args.agent_paw:
                print(f"  대상 Agent: {args.agent_paw}")
            else:
                print("  대상 Agent: 모든 연결된 에이전트")

            operation_name = args.operation_name or f"Auto-Operation-{version_id}"

            executor = CalderaExecutor(get_caldera_url(), get_caldera_api_key())

            # Operation 생성
            print(f"  Operation 생성 중: {operation_name}")
            op_id = executor.create_operation(operation_name, uploaded_adversary_id, args.agent_paw)
            print(f"  [OK] Operation ID: {op_id}")

            # Operation 시작
            print(f"  Operation 시작 중...")
            executor.start_operation(op_id)
            print(f"  [OK] Operation 실행 시작")

            # 완료 대기
            print(f"  Operation 완료 대기 중...")
            executor.wait_for_completion(op_id, timeout=None)
            print(f"  [OK] Operation 완료")

            # 5-3. 결과 수집
            print("\n[5-3] 결과 수집")
            print("-" * 70)

            reporter = CalderaReporter()
            report = reporter.collect_full_outputs(op_id)

            if not report:
                print("[ERROR] Operation 결과 수집 실패")
                sys.exit(1)

            # 리포트 저장
            operation_report_file = caldera_output_dir / "operation_report.json"
            reporter.save_report(report, str(operation_report_file))
            print(f"\n[OK] 리포트 저장: {operation_report_file}")
        else:
            print("\n[SKIP] 자동 실행 건너뜀")
            print("[INFO] 수동으로 Operation을 실행한 후,")
            print("[INFO] operation_report.json을 caldera/ 디렉토리에 저장하세요.")

            # 기존 리포트 파일 확인
            operation_report_file = caldera_output_dir / "operation_report.json"
            if not Path(operation_report_file).exists():
                print(f"\n[ERROR] {operation_report_file} 파일이 없습니다.")
                print("[INFO] Operation 실행 후 리포트를 저장하고 다시 실행하세요.")
                sys.exit(1)

        # 5-4. Self-Correcting (최대 3회 재시도)
        print("\n[5-4] Self-Correcting (실패한 Ability 수정 - 최대 3회 재시도)")
        print("-" * 70)

        # 첫 번째 실행 통계 저장 (Self-Correcting 전 초기 리포트 확보)
        with open(operation_report_file, 'r', encoding='utf-8') as f:
            first_report = json.load(f)

        # 첫 번째 실행 통계 계산
        first_stats = first_report.get('statistics', {})
        first_total = first_stats.get('total_abilities', 0)
        first_success = first_stats.get('success', 0)
        first_failed = first_stats.get('failed', 0)

        print(f"\n[초기 실행 결과] 전체: {first_total}, 성공: {first_success}, 실패: {first_failed}")

        # 재시도 루프 변수 초기화
        MAX_RETRIES = 3
        retry_count = 0
        all_retry_stats = []  # 각 재시도의 통계 저장
        termination_reason = None
        current_report_file = operation_report_file

        # 누적 correction_report 초기화
        cumulative_correction_report = {
            "initial_execution": {
                "total": first_total,
                "success": first_success,
                "failed": first_failed,
                "success_rate": (first_success / first_total * 100) if first_total > 0 else 0
            },
            "retry_attempts": [],
            "correction_history": {},
            "termination_reason": None,
            "final_result": None
        }

        # correction_report.json 파일 경로
        cumulative_report_path = caldera_output_dir / "correction_report.json"

        # 재시도 루프
        while retry_count < MAX_RETRIES:
            print(f"\n[재시도 {retry_count + 1}/{MAX_RETRIES}] Self-Correcting 시작")
            print("-" * 70)

            # Self-Correcting 실행
            corrector = OfflineCorrector()
            correction_report = corrector.run(
                abilities_file=str(abilities_file),
                operation_report_file=str(current_report_file),
                env_description_file=args.env,
                output_dir=str(caldera_output_dir),
                correction_history=cumulative_correction_report['correction_history']
            )

            # 수정된 ability 개수 확인
            corrected_count = correction_report.get('summary', {}).get('corrected', 0)
            total_failed = correction_report.get('summary', {}).get('total_failed', 0)

            print(f"  수정 가능한 실패: {corrected_count}/{total_failed}")

            # 현재 재시도 정보를 누적 리포트에 추가
            current_retry_data = {
                "retry_number": retry_count + 1,
                "corrections": correction_report.get('corrections', []),
                "summary": correction_report.get('summary', {}),
                "execution_result": None  # 재실행 후 업데이트됨
            }

            # 종료 조건 체크
            if corrected_count == 0:
                if total_failed == 0:
                    termination_reason = "all_success"
                    print(f"  [종료] 모든 Ability가 성공했습니다.")
                else:
                    termination_reason = "no_recoverable_failures"
                    print(f"  [종료] 수정 가능한 실패가 없습니다 (복구 불가능: {total_failed}개).")

                # 종료 시에도 현재 재시도 정보를 누적 리포트에 추가
                cumulative_correction_report['retry_attempts'].append(current_retry_data)

                # 중간 저장
                with open(cumulative_report_path, 'w', encoding='utf-8') as f:
                    json.dump(cumulative_correction_report, f, indent=2, ensure_ascii=False)
                print(f"  [OK] correction_report 중간 저장: {cumulative_report_path}")

                break

            # 수정된 abilities 재업로드 및 재실행
            print(f"\n  수정된 Ability 재업로드 및 재실행 (재시도 {retry_count + 1})")
            print("  " + "-" * 66)

            # 수정된 abilities 재업로드
            print("  수정된 abilities 재업로드 중...")
            uploader = CalderaUploader()
            uploader.upload_abilities(str(abilities_file))
            print("  [OK] 재업로드 완료")

            print("  " + "-" * 66)
            try:
                agent_manager.kill_all_agents()
            except Exception as e:
                print(f"  [WARNING] agent 정리 실패: {e}")
                print("  계속 진행합니다...")

            # VM 재부팅 (재실행 전)
            print("\n  VM 재부팅 (재실행 전)")
            print("  " + "-" * 66)
            try:
                controller = vm_reload.VBoxController()
                controller.restore_and_boot_all()
            except Exception as e:
                print(f"    [WARNING] VM 재부팅 실패: {str(e)}")
                print("    계속 진행합니다...")

            if not args.skip_execution:
                # 새로운 Operation 생성 및 실행
                operation_name_retry = f"{operation_name}-Retry-{retry_count + 1}"
                print(f"\n  Operation 생성 및 실행 (재시도 {retry_count + 1})")
                print(f"  Operation 이름: {operation_name_retry}")

                executor = CalderaExecutor(get_caldera_url(), get_caldera_api_key())
                op_id_retry = executor.create_operation(operation_name_retry, uploaded_adversary_id, args.agent_paw)
                print(f"  [OK] Operation ID: {op_id_retry}")

                # Operation 시작
                print(f"  Operation 시작 중...")
                executor.start_operation(op_id_retry)
                print(f"  [OK] Operation 실행 시작")

                # 완료 대기
                print(f"  Operation 완료 대기 중...")
                executor.wait_for_completion(op_id_retry, timeout=None)
                print(f"  [OK] Operation 완료")

                # 재실행 결과 수집
                reporter = CalderaReporter()
                retry_report = reporter.collect_full_outputs(op_id_retry)

                if retry_report:
                    # 재실행 리포트 저장 (Path 사용 후 문자열 변환)
                    retry_report_file = caldera_output_dir / f"operation_report_retry_{retry_count + 1}.json"
                    reporter.save_report(retry_report, str(retry_report_file))
                    print(f"  [OK] 재실행 리포트 저장: {retry_report_file}")

                    # 재실행 통계 계산
                    retry_stats = retry_report.get('statistics', {})
                    retry_total = retry_stats.get('total_abilities', 0)
                    retry_success = retry_stats.get('success', 0)
                    retry_failed = retry_stats.get('failed', 0)

                    # 통계 저장
                    all_retry_stats.append({
                        'retry_number': retry_count + 1,
                        'total': retry_total,
                        'success': retry_success,
                        'failed': retry_failed,
                        'success_rate': (retry_success / retry_total * 100) if retry_total > 0 else 0
                    })

                    print(f"  [재시도 {retry_count + 1} 결과] 전체: {retry_total}, 성공: {retry_success}, 실패: {retry_failed}")

                    # 현재 재시도 데이터에 실행 결과 추가
                    current_retry_data['execution_result'] = {
                        'total': retry_total,
                        'success': retry_success,
                        'failed': retry_failed,
                        'success_rate': (retry_success / retry_total * 100) if retry_total > 0 else 0
                    }

                    # 누적 리포트에 현재 재시도 추가
                    cumulative_correction_report['retry_attempts'].append(current_retry_data)

                    # 실패한 ability들을 correction_history에 추가
                    failed_abilities_data = retry_report.get('failed_abilities', [])
                    for failed_ability in failed_abilities_data:
                        ability_id = failed_ability.get('ability_id')
                        if ability_id:
                            # 이력에 추가
                            if ability_id not in cumulative_correction_report['correction_history']:
                                cumulative_correction_report['correction_history'][ability_id] = []

                            cumulative_correction_report['correction_history'][ability_id].append({
                                'attempt': retry_count + 1,
                                'command': failed_ability.get('command', 'N/A'),
                                'failure_type': failed_ability.get('status', 'Unknown'),
                                'error': failed_ability.get('stderr', '') or failed_ability.get('stdout', '')
                            })

                    # 누적 correction_report.json 저장
                    with open(cumulative_report_path, 'w', encoding='utf-8') as f:
                        json.dump(cumulative_correction_report, f, indent=2, ensure_ascii=False)
                    print(f"  [OK] 누적 correction_report 업데이트: {cumulative_report_path}")

                    # 다음 루프를 위해 현재 리포트 파일 업데이트
                    current_report_file = retry_report_file
                    retry_count += 1
                else:
                    print("  [WARNING] 재실행 결과 수집 실패")
                    break
            else:
                print("  [INFO] --skip-execution 옵션으로 자동 재실행을 건너뜁니다.")
                print("  [INFO] 수동으로 재실행 후 결과를 확인하세요.")
                break

        # 최대 재시도 도달 확인
        if retry_count >= MAX_RETRIES and termination_reason is None:
            termination_reason = "max_retries_reached"
            print(f"\n  [종료] 최대 재시도 횟수({MAX_RETRIES}회)에 도달했습니다.")

        # 최종 성공률 비교 출력
        print("\n" + "="*70)
        print("Self-Correcting 최종 결과")
        print("="*70)

        first_rate = (first_success / first_total * 100) if first_total > 0 else 0

        if all_retry_stats:
            # 재시도가 있었던 경우
            print(f"{'구분':<25} {'전체':<10} {'성공':<10} {'실패':<10} {'성공률':<10}")
            print("-"*70)
            print(f"{'초기 실행':<25} {first_total:<10} {first_success:<10} {first_failed:<10} {first_rate:.1f}%")

            for stat in all_retry_stats:
                retry_label = f"재시도 {stat['retry_number']}"
                print(f"{retry_label:<25} {stat['total']:<10} {stat['success']:<10} {stat['failed']:<10} {stat['success_rate']:.1f}%")

            # 최종 개선도 계산
            final_rate = all_retry_stats[-1]['success_rate']
            improvement = final_rate - first_rate
            final_success = all_retry_stats[-1]['success']

            print("-"*70)
            if improvement > 0:
                print(f"최종 개선: +{improvement:.1f}% ({first_success} → {final_success} 성공)")
            elif improvement < 0:
                print(f"최종 변화: {improvement:.1f}%")
            else:
                print(f"최종 변화: 동일")
            print(f"최종 성공률: {final_rate:.1f}% ({final_success}/{first_total} 성공)")
            print(f"재시도 횟수: {retry_count}회")
        else:
            # 재시도가 없었던 경우 (초기 실행 결과가 최종 결과)
            print(f"{'구분':<25} {'전체':<10} {'성공':<10} {'실패':<10} {'성공률':<10}")
            print("-"*70)
            print(f"{'초기 실행 (최종)':<25} {first_total:<10} {first_success:<10} {first_failed:<10} {first_rate:.1f}%")
            print("-"*70)
            print(f"최종 성공률: {first_rate:.1f}% ({first_success}/{first_total} 성공)")
            print(f"재시도: 없음 (수정 가능한 실패 없음)")

        print(f"종료 사유: {termination_reason}")
        print("="*70)

        # 최종 결과를 누적 리포트에 저장
        if all_retry_stats:
            final_stats = all_retry_stats[-1]
            cumulative_correction_report['final_result'] = {
                'total': final_stats['total'],
                'success': final_stats['success'],
                'failed': final_stats['failed'],
                'success_rate': final_stats['success_rate']
            }
        else:
            # 재시도 없음 - 초기 결과가 최종 결과
            cumulative_correction_report['final_result'] = {
                'total': first_total,
                'success': first_success,
                'failed': first_failed,
                'success_rate': (first_success / first_total * 100) if first_total > 0 else 0
            }

        cumulative_correction_report['termination_reason'] = termination_reason

        # 최종 누적 correction_report.json 저장
        with open(cumulative_report_path, 'w', encoding='utf-8') as f:
            json.dump(cumulative_correction_report, f, indent=2, ensure_ascii=False)
        print(f"\n[저장] 최종 correction_report.json: {cumulative_report_path}")

        print("\n[OK] Step 5 완료!")
        tracker.end_step(success=True)

    # 메트릭 최종화 및 저장
    tracker.finalize(success=True)

    # 메트릭 저장
    metrics_file = base_dir / "experiment_metrics.json"
    tracker.save(str(metrics_file))

    # 메트릭 요약 출력
    summary = tracker.get_summary()

    print("\n" + "="*70)
    print("[SUCCESS] 완료!")
    print("="*70)

    print("\n[실험 메트릭 요약]")
    print("-" * 70)
    print(f"총 실행 시간: {summary['duration_formatted']}")
    print(f"LLM 제공자: {summary['llm_provider']}")
    print(f"LLM 모델: {summary['llm_model']}")
    print(f"총 입력 토큰: {summary['total_input_tokens']:,}")
    print(f"총 출력 토큰: {summary['total_output_tokens']:,}")
    print(f"총 토큰: {summary['total_tokens']:,}")
    print(f"예상 비용: ${summary['total_cost_usd']:.4f}")
    print(f"완료된 Step: {summary['steps_completed']}/{summary['steps_completed'] + summary['steps_failed']}")
    print(f"\n메트릭 저장: {metrics_file}")
    print("="*70)

    # 모든 절차 완료 후 VM 종료
    print("\n" + "="*70)
    print("[VM 종료] 실행 중인 VM을 종료합니다...")
    print("="*70)

    try:
        controller = vm_reload.VBoxController()
        controller.shutdown_all()
        print("\n[OK] 모든 VM 종료 완료")
        print("="*70)
    except Exception as e:
        print(f"\n[WARNING] VM 종료 중 오류 발생: {e}")
        print("VM을 수동으로 종료해주세요.")
        print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] 사용자가 중단했습니다.")
        # 메트릭 저장 시도
        tracker = get_metrics_tracker()
        if tracker:
            try:
                tracker.finalize(success=False)
                print("\n[메트릭] 중단 시점까지의 메트릭을 저장합니다...")
            except:
                pass

        # VM 종료 시도
        try:
            print("\n[VM 종료] 중단 시 VM을 종료합니다...")
            controller = vm_reload.VBoxController()
            controller.shutdown_all()
        except:
            pass

        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        # 메트릭 저장 시도
        tracker = get_metrics_tracker()
        if tracker:
            try:
                tracker.finalize(success=False)
                print("\n[메트릭] 실패 시점까지의 메트릭을 저장합니다...")
            except:
                pass

        # VM 종료 시도
        try:
            print("\n[VM 종료] 에러 발생 시 VM을 종료합니다...")
            controller = vm_reload.VBoxController()
            controller.shutdown_all()
        except:
            pass

        sys.exit(1)
