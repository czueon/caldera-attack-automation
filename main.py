"""
KISA TTPs → Caldera Adversary Pipeline
전체 파이프라인 실행 엔트리포인트

실행 모드:
- 일반 모드: --step 1~5 또는 범위 지정 (예: 1~3)
"""

import os
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
from modules.core.config import get_caldera_url, get_caldera_api_key
import yaml
import time


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

    # Step 1: PDF Processing
    if 1 in steps:
        if not args.pdf:
            print("[ERROR] Step 1 실행 시 --pdf 인자가 필요합니다")
            sys.exit(1)

        print("\n[Step 1] PDF Processing")
        print("-" * 70)

        processor = PDFProcessor()
        # version_id를 명시적으로 전달하여 동일 버전으로 연결
        processor.process_pdf(args.pdf, output_path=str(step1_output), version_id=version_id)

    # Step 2: Abstract Flow Extraction
    if 2 in steps:
        print("\n[Step 2] Abstract Attack Flow Extraction")
        print("-" * 70)

        if not Path(step1_output).exists():
            print(f"[ERROR] {step1_output} 파일이 없습니다. Step 1을 먼저 실행하세요.")
            sys.exit(1)

        extractor = AbstractFlowExtractor()
        extractor.extract_abstract_flow(str(step1_output), str(step2_output), version_id=version_id)

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

        generator = ConcreteFlowGenerator()
        generator.generate_concrete_flow(str(step2_output), args.env, str(step3_output), version_id=version_id)

    # Step 4: Caldera Ability Generation
    if 4 in steps:
        print("\n[Step 4] Caldera Ability Generation")
        print("-" * 70)

        if not Path(step3_output).exists():
            print(f"[ERROR] {step3_output} 파일이 없습니다. Step 3을 먼저 실행하세요.")
            sys.exit(1)

        generator = AbilityGenerator()
        generator.generate_abilities(str(step3_output), str(caldera_output_dir))

    # Step 5: Caldera Automation (Upload → Execute → Self-Correct)
    if 5 in steps:
        print("\n[Step 5] Caldera 자동화 (업로드 → 실행 → Self-Correcting)")
        print("-" * 70)

        # VM 재부팅
        print("\n[5-0] VM 재부팅")
        print("-" * 70)
        try:
            # scripts 디렉토리를 Python path에 추가
            scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            import vm_reload
            controller = vm_reload.VBoxController()

            vm_name = os.getenv('VBOX_VM_NAME')
            snapshot_name = os.getenv('VBOX_SNAPSHOT_NAME')
            vm_name_lateral = os.getenv('VBOX_VM_NAME_lateral')
            snapshot_name_lateral = os.getenv('VBOX_SNAPSHOT_NAME_lateral')

            # Main VM 복원 및 시작
            if vm_name and snapshot_name:
                print(f"  {vm_name} 스냅샷 복원 및 시작 중...")
                controller.restore_and_start(vm_name, snapshot_name)
                print(f"  [OK] {vm_name} 재부팅 완료")

            # Lateral Movement VM 복원 및 시작
            if vm_name_lateral and snapshot_name_lateral:
                print(f"  {vm_name_lateral} 스냅샷 복원 및 시작 중...")
                controller.restore_and_start(vm_name_lateral, snapshot_name_lateral)
                print(f"  [OK] {vm_name_lateral} 재부팅 완료")

            # VM 부팅 대기
            print("  VM 부팅 대기 중 (30초)...")
            time.sleep(30)
            print("  [OK] 모든 VM 재부팅 완료")

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

        # 5-4. Self-Correcting
        print("\n[5-4] Self-Correcting (실패한 Ability 수정)")
        print("-" * 70)

        # 첫 번째 실행 통계 저장 (Self-Correcting 전 초기 리포트 확보)
        with open(operation_report_file, 'r', encoding='utf-8') as f:
            first_report = json.load(f)

        # 첫 번째 실행 통계 계산
        first_stats = first_report.get('statistics', {})
        first_total = first_stats.get('total_abilities', 0)
        first_success = first_stats.get('success', 0)
        first_failed = first_stats.get('failed', 0)

        corrector = OfflineCorrector()
        correction_report = corrector.run(
            abilities_file=str(abilities_file),
            operation_report_file=str(operation_report_file),
            env_description_file=args.env,
            output_dir=str(caldera_output_dir)
        )

        # 수정된 ability 개수 확인
        corrected_count = correction_report.get('summary', {}).get('corrected', 0)

        if corrected_count > 0:
            print(f"\n[5-5] 수정된 Ability 재업로드 및 재실행")
            print("-" * 70)

            # 수정된 abilities 재업로드
            print("  수정된 abilities 재업로드 중...")
            uploader = CalderaUploader()
            uploader.upload_abilities(str(abilities_file))
            print("  [OK] 재업로드 완료")

            # VM 재부팅 (재실행 전)
            print("\n  VM 재부팅 (재실행 전)")
            print("  " + "-" * 66)
            try:
                # scripts 디렉토리를 Python path에 추가
                scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)

                import vm_reload
                controller = vm_reload.VBoxController()

                vm_name = os.getenv('VBOX_VM_NAME')
                snapshot_name = os.getenv('VBOX_SNAPSHOT_NAME')
                vm_name_lateral = os.getenv('VBOX_VM_NAME_lateral')
                snapshot_name_lateral = os.getenv('VBOX_SNAPSHOT_NAME_lateral')

                # Main VM 복원 및 시작
                if vm_name and snapshot_name:
                    print(f"    {vm_name} 스냅샷 복원 및 시작 중...")
                    controller.restore_and_start(vm_name, snapshot_name)
                    print(f"    [OK] {vm_name} 재부팅 완료")

                # Lateral Movement VM 복원 및 시작
                if vm_name_lateral and snapshot_name_lateral:
                    print(f"    {vm_name_lateral} 스냅샷 복원 및 시작 중...")
                    controller.restore_and_start(vm_name_lateral, snapshot_name_lateral)
                    print(f"    [OK] {vm_name_lateral} 재부팅 완료")

                # VM 부팅 대기
                print("    VM 부팅 대기 중 (30초)...")
                time.sleep(30)
                print("    [OK] 모든 VM 재부팅 완료")

            except Exception as e:
                print(f"    [WARNING] VM 재부팅 실패: {str(e)}")
                print("    계속 진행합니다...")

            if not args.skip_execution:
                # 새로운 Operation 생성 및 실행
                operation_name_retry = f"{operation_name}-Retry"
                print(f"  새 Operation 생성 중: {operation_name_retry}")

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
                    retry_report_file = caldera_output_dir / "operation_report_retry.json"
                    reporter.save_report(retry_report, str(retry_report_file))
                    print(f"  [OK] 재실행 리포트 저장: {retry_report_file}")

                    # 재실행 통계 계산
                    retry_stats = retry_report.get('statistics', {})
                    retry_total = retry_stats.get('total_abilities', 0)
                    retry_success = retry_stats.get('success', 0)
                    retry_failed = retry_stats.get('failed', 0)

                    # 성공률 비교 출력
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
                        print(f"\n✓ 성공률 개선: +{improvement:.1f}% ({first_success} → {retry_success} 성공)")
                    elif improvement < 0:
                        print(f"\n✗ 성공률 감소: {improvement:.1f}%")
                    else:
                        print(f"\n- 성공률 동일")
                    print("="*70)
                else:
                    print("  [WARNING] 재실행 결과 수집 실패")
            else:
                print("  [INFO] --skip-execution 옵션으로 자동 재실행을 건너뜁니다.")
                print("  [INFO] 수동으로 재실행 후 결과를 확인하세요.")
        else:
            print("\n[INFO] 수정된 Ability가 없어 재실행을 건너뜁니다.")

        print("\n[OK] Step 5 완료!")

    print("\n" + "="*70)
    print("[SUCCESS] 완료!")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] 사용자가 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
