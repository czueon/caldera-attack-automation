"""
KISA TTPs → Caldera Adversary Pipeline
전체 파이프라인 실행 엔트리포인트

실행 모드:
- 일반 모드: --step 0~5 또는 범위 지정 (예: 0~2)
"""

import os
import argparse
import sys
from pathlib import Path

# 모듈 임포트
from modules.module0_pdf_processing import PDFProcessor
from modules.module1_abstract_flow import AbstractFlowExtractor
from modules.module2_concrete_flow import ConcreteFlowGenerator
from modules.module3_technique_selection import TechniqueSelector
from modules.module4_ability_generator import AbilityGenerator
from modules.module4_5_ability_splitter import AbilitySplitter
from modules.module5_visualization import KillChainVisualizer


def parse_step_range(step_arg):
    """
    --step 인자 파싱

    Examples:
        "0"     → [0]
        "0~3"   → [0, 1, 2, 3]
        "2~5"   → [2, 3, 4, 5]
        "all"   → [0, 1, 2, 3, 4, 5, 5.5, 6]
    """
    if step_arg == "all":
        return [0, 1, 2, 3, 4, 4.5, 5]

    if "~" in step_arg:
        # 범위 지정
        start, end = step_arg.split("~")
        start = int(start)
        end = int(end)

        if start > end:
            raise ValueError(f"Invalid range: {start}~{end} (start > end)")

        # 4.5를 포함하는 범위 처리
        steps = []
        for i in range(start, end + 1):
            steps.append(i)
            if i == 4 and end >= 5:
                steps.append(4.5)

        return steps
    else:
        # 단일 step
        try:
            return [float(step_arg)]
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
  0      : PDF 처리 (텍스트 추출)
  1      : 추상 공격 흐름 추출 (환경 독립적)
  2      : 구체적 공격 흐름 생성 (환경 적용, Technique 후보)
  3      : Technique 최종 선택 (Top 3 → Final 1)
  4      : Caldera Ability 생성
  4.5    : Ability 파일 분할
  5      : Kill Chain 시각화
  all    : 전체 실행

  범위 지정:
  0~2    : Step 0, 1, 2 실행
  2~5    : Step 2, 3, 4, 4.5, 5 실행
"""
    )

    # 입력 파일
    parser.add_argument(
        "--pdf",
        type=str,
        help="입력 PDF 파일 경로 (Step 0에서 필수)"
    )

    parser.add_argument(
        "--env",
        type=str,
        help="환경 설명 MD 파일 경로 (Step 2에서 필수)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="중간 결과 저장 디렉토리 (기본: data/processed)"
    )

    parser.add_argument(
        "--regenerate-ids",
        action="store_true",
        help="Step 4.5에서 ability UUID 재생성"
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

    # 출력 디렉토리 생성
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Step 0: PDF Processing
    if 0 in steps:
        if not args.pdf:
            print("[ERROR] Step 0 실행 시 --pdf 인자가 필요합니다")
            sys.exit(1)

        print("\n[Step 0] PDF Processing")
        print("-" * 70)

        step0_output = f"{args.output_dir}/step0_parsed.yml"
        processor = PDFProcessor()
        processor.process_pdf(args.pdf, step0_output)

    # Step 1: Abstract Flow Extraction
    if 1 in steps:
        print("\n[Step 1] Abstract Attack Flow Extraction")
        print("-" * 70)

        step0_output = f"{args.output_dir}/step0_parsed.yml"
        step1_output = f"{args.output_dir}/step1_abstract_flow.yml"

        if not Path(step0_output).exists():
            print(f"[ERROR] {step0_output} 파일이 없습니다. Step 0을 먼저 실행하세요.")
            sys.exit(1)

        extractor = AbstractFlowExtractor()
        extractor.extract_abstract_flow(step0_output, step1_output)

    # Step 2: Concrete Flow Generation
    if 2 in steps:
        if not args.env:
            print("[ERROR] Step 2 실행 시 --env 인자가 필요합니다")
            print("예: --env templates/environment_description_example.md")
            sys.exit(1)

        print("\n[Step 2] Concrete Attack Flow Generation")
        print("-" * 70)

        step1_output = f"{args.output_dir}/step1_abstract_flow.yml"
        step2_output = f"{args.output_dir}/step2_concrete_flow.yml"

        if not Path(step1_output).exists():
            print(f"[ERROR] {step1_output} 파일이 없습니다. Step 1을 먼저 실행하세요.")
            sys.exit(1)

        if not Path(args.env).exists():
            print(f"[ERROR] {args.env} 파일이 없습니다.")
            sys.exit(1)

        generator = ConcreteFlowGenerator()
        generator.generate_concrete_flow(step1_output, args.env, step2_output)

    # Step 3: Technique Selection
    if 3 in steps:
        print("\n[Step 3] Technique Selection")
        print("-" * 70)

        step2_output = f"{args.output_dir}/step2_concrete_flow.yml"
        step3_output = f"{args.output_dir}/step3_technique_selected.yml"

        if not Path(step2_output).exists():
            print(f"[ERROR] {step2_output} 파일이 없습니다. Step 2를 먼저 실행하세요.")
            sys.exit(1)

        selector = TechniqueSelector()
        selector.select_techniques(step2_output, step3_output)

    # Step 4: Caldera Ability Generation
    if 4 in steps:
        print("\n[Step 4] Caldera Ability Generation")
        print("-" * 70)

        step3_output = f"{args.output_dir}/step3_technique_selected.yml"
        step2_output = f"{args.output_dir}/step2_concrete_flow.yml"

        # Step 3가 없으면 Step 2 사용
        input_file = step3_output if Path(step3_output).exists() else step2_output

        if not Path(input_file).exists():
            print(f"[ERROR] {input_file} 파일이 없습니다.")
            sys.exit(1)

        caldera_output_dir = f"{args.output_dir}/caldera"

        generator = AbilityGenerator()
        generator.generate_abilities(input_file, caldera_output_dir)

    # Step 4.5: Ability Splitting
    if 4.5 in steps:
        print("\n[Step 4.5] Ability File Splitting")
        print("-" * 70)

        abilities_file = f"{args.output_dir}/caldera_abilities/abilities.yml"
        split_output_dir = f"{args.output_dir}/caldera_abilities/individual_abilities"

        if not Path(abilities_file).exists():
            print(f"[ERROR] {abilities_file} 파일이 없습니다. Step 4를 먼저 실행하세요.")
            sys.exit(1)

        splitter = AbilitySplitter()
        splitter.split_abilities(abilities_file, split_output_dir, regenerate_ids=args.regenerate_ids)

    # Step 5: Kill Chain Visualization
    if 5 in steps:
        print("\n[Step 5] Kill Chain Visualization")
        print("-" * 70)

        # 가장 최신 Kill Chain 파일 사용
        step3_output = f"{args.output_dir}/step3_technique_selected.yml"
        step2_output = f"{args.output_dir}/step2_concrete_flow.yml"

        if Path(step3_output).exists():
            input_file = step3_output
        elif Path(step2_output).exists():
            input_file = step2_output
        else:
            print("[ERROR] Kill Chain 파일이 없습니다. Step 2~3 중 하나를 먼저 실행하세요.")
            sys.exit(1)

        visualization_dir = f"{args.output_dir}/visualizations"

        visualizer = KillChainVisualizer()
        visualizer.visualize_killchains(input_file, visualization_dir)

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
