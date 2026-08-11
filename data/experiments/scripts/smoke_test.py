"""
최소 단위 스모크 테스트 — 실제 LLM API(+선택적으로 실제 Caldera/VM)를 호출해서
generate/recover 파이프라인의 모든 경로가 정상 동작하는지 한 번씩 확인한다.

- 보고서 1개, LLM 1개
- generate: with_kb / without_kb 각 1회
- recover: (실행까지 포함한 --step일 때) none / type / history / both 각 1회

run_experiments.py의 generate/recover를 그대로 재사용하되, 보고서 1개 · repeat 1회로
범위를 좁혀서 부른다 (별도 로직 없음 — 실제 배치 실행기와 동일한 코드 경로를 탄다).

Usage:
    # 생성만 (VM/Caldera 불필요, LLM API만 호출)
    python data/experiments/scripts/smoke_test.py --report 1 --llm claude --step 1~4

    # 생성 + 실행 + 4가지 복구 조건까지 전부 (VM/Caldera 연결 필요)
    python data/experiments/scripts/smoke_test.py --report 1 --llm claude --step all
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_experiments as re_mod  # noqa: E402


class _Args:
    """cmd_generate/cmd_recover가 기대하는 필드만 채운 최소 네임스페이스."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def main():
    parser = argparse.ArgumentParser(description="generate/recover 전체 경로 스모크 테스트 (실제 API 호출)")
    parser.add_argument("--report", type=int, default=1, help="테스트할 보고서 ID (기본 1)")
    parser.add_argument("--llm", type=str, default="claude", choices=["claude", "openai", "gemini", "grok"])
    parser.add_argument("--step", type=str, default="all",
                         help="main.py --step 값. 'all'/5 포함 시 recover까지 테스트 "
                              "(VM/Caldera 연결 필요). 1~4면 생성만 테스트")
    parser.add_argument("--timeout", type=int, default=None)
    args = parser.parse_args()

    print("=" * 70)
    print(f"스모크 테스트: report={args.report}, llm={args.llm}, step={args.step}")
    print("=" * 70)

    # 1) generate: with_kb / without_kb 각 1회
    manifest_path = re_mod.cmd_generate(_Args(
        llms=args.llm, reports=str(args.report), repeats=1, step=args.step, timeout=args.timeout,
    ))
    gen_rows = [json.loads(l) for l in Path(manifest_path).read_text(encoding="utf-8").splitlines() if l.strip()]

    include_execution = re_mod._step_includes(args.step, 5)

    print("\n" + "=" * 70)
    print("[결과 1/2] generate (with_kb / without_kb)")
    print("=" * 70)
    for row in gen_rows:
        status = "OK" if row["exit_code"] == 0 else f"FAILED(exit={row['exit_code']})"
        extra = ""
        if include_execution:
            succ, tot = row.get("initial_success"), row.get("initial_total")
            rate = f" ({succ / tot * 100:.1f}%)" if tot else ""
            extra = f", 초기 실행: 성공 {succ}/{tot}{rate}"
        print(f"  {re_mod.kb_label(row['use_kb']):12s} -> {status}{extra}")

    if not include_execution:
        print("\n[SKIP] --step에 5가 없어 recover는 테스트하지 않습니다 "
              "(recover를 테스트하려면 --step all 또는 5를 포함한 범위 + 실제 Caldera/VM 필요)")
        _print_summary(gen_rows, [])
        return

    # 2) recover: 실패가 있는 생성 결과에 대해 4가지 조건 각 1회
    failing_rows = [r for r in gen_rows if r["exit_code"] == 0 and (r.get("initial_failed") or 0) > 0]
    if not failing_rows:
        print("\n[INFO] 초기 실행에서 실패한 ability가 없어 recover를 실행할 대상이 없습니다 "
              "(전부 성공했다는 뜻이라 나쁜 소식은 아니지만, recover 경로는 이번엔 검증 못함)")
        _print_summary(gen_rows, [])
        return

    rec_manifest_path = re_mod.cmd_recover(_Args(manifest=str(manifest_path), timeout=args.timeout))
    rec_rows = [json.loads(l) for l in Path(rec_manifest_path).read_text(encoding="utf-8").splitlines() if l.strip()]

    print("\n" + "=" * 70)
    print("[결과 2/2] recover (none / type / history / both)")
    print("=" * 70)
    for row in rec_rows:
        status = "OK" if row["exit_code"] == 0 else f"FAILED(exit={row['exit_code']})"
        rr = f"{row['recovery_rate'] * 100:.1f}%" if row.get("recovery_rate") is not None else "N/A"
        print(f"  kb={re_mod.kb_label(row['use_kb']):12s} condition={row['condition']:8s} -> {status}, recovery_rate={rr}")

    _print_summary(gen_rows, rec_rows)


def _print_summary(gen_rows, rec_rows):
    total = len(gen_rows) + len(rec_rows)
    failed = [r for r in gen_rows + rec_rows if r["exit_code"] != 0]

    print("\n" + "=" * 70)
    if not failed:
        print(f"[SUCCESS] 스모크 테스트 전체 통과 ({total}/{total})")
    else:
        print(f"[FAILED] {len(failed)}/{total}개 케이스 실패")
        for r in failed:
            label = r.get("condition", re_mod.kb_label(r["use_kb"]))
            print(f"  - {label}: exit_code={r['exit_code']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
