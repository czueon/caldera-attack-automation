"""
실험 결과 집계 스크립트

`data/experiments/runs/{llm}/repeat_{n}/{pdf_stem}/{run_id}/` 아래의 모든 generation/recovery
결과를 훑어서 report x LLM x repeat x KB조건 x 복구조건 단위로 통계를 집계한다.
run_experiments.py가 남기는 manifest jsonl(요약 지표)에 의존하지 않고, 매번 원본
(abilities.yml, operation_report.json, correction_report.json, experiment_metrics.json)을
직접 파싱해서 계산하므로 manifest가 없거나 낡았어도 항상 최신 원본 기준으로 재계산된다.

정합성 검증(중요): 일부 시나리오는 권한 상승 등을 위해 ability 실행 중 새 agent를 띄우고 기존
agent를 대체하도록 의도적으로 설계돼 있다. 그래서 같은 ability가 2개 agent에서 실행되는 "중복
실행"은 정상적인 현상이며(성공 여부는 "하나라도 성공하면 성공" 규칙으로 정확히 집계됨), 이것만
있는 경우는 이상치로 보지 않는다. 반면 실행 기록 자체가 아예 없는 ability(옛 agent가 교체되는
시점에 결과가 유실된 경우 등)는 그 ability의 성패를 알 수 없다는 실질적인 공백이므로 계속
표시한다. Caldera가 돌려주는 operation_report.json의 'statistics.total_abilities'는 이 유실을
그대로 반영해 실제 생성 개수보다 적게 잡히므로, 이 스크립트는 그 값을 그대로 믿지 않고
abilities.yml에 실제로 몇 개가 "생성"됐는지를 진짜 분모로 삼아 성공률을 다시 계산한다.

Usage:
    python data/experiments/scripts/analyze_experiments.py                          # data/experiments/runs/ 전체 집계
    python data/experiments/scripts/analyze_experiments.py --llm claude --report 1  # 특정 llm/report만
    python data/experiments/scripts/analyze_experiments.py --csv out.csv            # CSV로도 저장
    python data/experiments/scripts/analyze_experiments.py --anomalies-only         # 이상치 있는 case만 출력
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # data/experiments/scripts/ -> data/experiments/ -> data/ -> repo root
RUNS_DIR = PROJECT_ROOT / "data" / "experiments" / "runs"

RECOVERY_CONDITIONS = ["none", "type", "history", "both"]
KB_LABELS = ["with_kb", "without_kb"]

# echo 시뮬레이션(문자열만 출력, 다른 실제 액션 없음) 판별용. 파일에 쓰는 echo(`> file`)나
# 실제 명령 뒤에 상태 메시지로 붙는 echo/Write-Output은 시뮬레이션으로 안 침.
ECHO_RE = re.compile(r'^(echo|write-output|write-host)\b', re.IGNORECASE)
WRAPPER_RE = re.compile(r'^powershell(?:\.exe)?\s+.*?-command\s+"(.*)"\s*$', re.IGNORECASE | re.DOTALL)


def _strip_wrapper(cmd: str) -> str:
    m = WRAPPER_RE.match(cmd)
    return m.group(1) if m else cmd


def classify_echo(cmd: str) -> str:
    """명령어 하나를 'echo_simulation' / 'echo_filewrite' / 'echo_trailing' / 'no_echo'로 분류."""
    inner = _strip_wrapper(cmd)
    statements = [s.strip().strip('"').strip() for s in re.split(r';|&&', inner) if s.strip()]
    if not statements:
        return 'no_echo'
    all_echo = all(ECHO_RE.match(s) for s in statements)
    any_filewrite = any('>' in s for s in statements)
    if all_echo and not any_filewrite:
        return 'echo_simulation'
    if all_echo and any_filewrite:
        return 'echo_filewrite'
    if any(ECHO_RE.match(s) for s in statements):
        return 'echo_trailing'
    return 'no_echo'


def _load_yaml(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_operation(abilities_path: Path, operation_report_path: Path) -> Optional[Dict]:
    """abilities.yml(생성된 진짜 개수) + operation_report.json(Caldera 실행 결과)을 대조해서
    보정된 통계 + 이상치를 계산."""
    abilities = _load_yaml(abilities_path)
    report = _load_json(operation_report_path)
    if abilities is None or report is None:
        return None

    generated_ids = [a["ability_id"] for a in abilities]
    generated_count = len(generated_ids)
    generated_id_set = set(generated_ids)

    results = report.get("results", [])
    total_links = len(results)

    ids_in_results = [r.get("ability_id") for r in results]
    id_counts = Counter(ids_in_results)
    distinct_in_results = len(id_counts)

    duplicated_ids = [i for i, c in id_counts.items() if c > 1]
    missing_ids = sorted(generated_id_set - set(ids_in_results))  # 생성됐는데 링크가 하나도 없는 ability

    # ability_id 기준으로 "하나라도 성공(status==0/exit_code==0)이면 성공" 규칙으로 재집계
    # (Caldera 쪽 reporter.py와 동일한 정책이되, 분모는 abilities.yml 기준 generated_count로 고정)
    success_ids = set()
    for r in results:
        aid = r.get("ability_id")
        if aid is None:
            continue
        if r.get("status") == 0 or r.get("exit_code") == 0:
            success_ids.add(aid)

    corrected_success = len(success_ids & generated_id_set)
    # 누락된 ability(missing_ids)는 실행 기록이 아예 없으므로 성공으로 볼 근거가 없어 실패로 간주
    corrected_failed = generated_count - corrected_success
    corrected_rate = round(corrected_success / generated_count * 100, 2) if generated_count else 0.0

    caldera_stats = report.get("statistics", {})

    # anomalies: 성공률 신뢰도에 실질적으로 영향을 주는 것만 (전부 "missing"에서 비롯됨).
    # notes: 참고 정보일 뿐 문제는 아닌 것 (중복 실행 — 권한 상승 등에서 의도된 agent 교체의
    # 자연스러운 결과이며, "하나라도 성공하면 성공" 규칙으로 이미 정확히 처리됨).
    anomalies = []
    notes = []
    if generated_count != distinct_in_results:
        anomalies.append(
            f"ability 수 불일치: 생성 {generated_count}개 vs 실행결과에 등장한 고유 ability {distinct_in_results}개"
        )
    if duplicated_ids:
        notes.append(f"중복 실행된 ability {len(duplicated_ids)}개 (2개 이상 agent에서 실행 — 정상, agent 교체로 인한 것)")
    if missing_ids:
        anomalies.append(f"실행 기록 자체가 없는 ability {len(missing_ids)}개 (성패를 알 수 없어 실패로 집계)")
    if caldera_stats.get("total_abilities") != generated_count:
        anomalies.append(
            f"Caldera 자체 집계(total_abilities={caldera_stats.get('total_abilities')})가 "
            f"생성 개수({generated_count})와 다름"
        )

    # echo 시뮬레이션 비율 (abilities.yml 커맨드 기준)
    echo_counts = Counter(classify_echo(a["executors"][0].get("command", "")) for a in abilities)

    return {
        "generated_count": generated_count,
        "total_links": total_links,
        "distinct_in_results": distinct_in_results,
        "duplicated_ability_count": len(duplicated_ids),
        "missing_ability_count": len(missing_ids),
        "missing_ability_ids": missing_ids,
        "caldera_total_abilities": caldera_stats.get("total_abilities"),
        "caldera_success": caldera_stats.get("success"),
        "caldera_success_rate": caldera_stats.get("success_rate"),
        "corrected_success": corrected_success,
        "corrected_failed": corrected_failed,
        "corrected_success_rate": corrected_rate,
        "echo_simulation_count": echo_counts.get("echo_simulation", 0),
        "echo_simulation_rate": round(echo_counts.get("echo_simulation", 0) / generated_count * 100, 2) if generated_count else 0.0,
        "anomalies": anomalies,
        "notes": notes,
    }


def load_metrics_summary(metrics_path: Path) -> Dict:
    m = _load_json(metrics_path)
    if not m:
        return {"cost": None, "tokens": None, "duration_seconds": None, "llm_call_seconds": None}
    return {
        "cost": m.get("total_cost"),
        "tokens": m.get("total_tokens"),
        "duration_seconds": m.get("total_duration_seconds"),
        "llm_call_seconds": m.get("total_llm_call_seconds"),
    }


def discover_run_dirs(runs_dir: Path, llm_filter: Optional[str], report_filter: Optional[str]) -> List[Path]:
    """runs_dir 아래에서 {llm}/repeat_{n}/{pdf_stem}/{run_id}/ 디렉토리를 전부 찾는다."""
    run_dirs = []
    if not runs_dir.exists():
        return run_dirs
    for llm_dir in sorted(runs_dir.iterdir()):
        if not llm_dir.is_dir():
            continue
        if llm_filter and llm_dir.name != llm_filter:
            continue
        for repeat_dir in sorted(llm_dir.glob("repeat_*")):
            for pdf_dir in sorted(repeat_dir.iterdir()):
                if not pdf_dir.is_dir():
                    continue
                if report_filter and report_filter not in pdf_dir.name:
                    continue
                for run_dir in sorted(pdf_dir.iterdir()):
                    if (run_dir / "generation").exists():
                        run_dirs.append(run_dir)
    return run_dirs


def analyze_run(run_dir: Path) -> List[Dict]:
    """run_dir(={run_id} 디렉토리) 하나에서 generation 2개 + recovery 최대 8개 row를 만든다."""
    rows = []
    parts = run_dir.parts
    # .../runs/{llm}/repeat_{n}/{pdf_stem}/{run_id}
    llm, repeat_part, pdf_stem, run_id = parts[-4], parts[-3], parts[-2], parts[-1]
    repeat = repeat_part.replace("repeat_", "")

    for kb in KB_LABELS:
        gen_dir = run_dir / "generation" / kb / "caldera"
        abilities_path = gen_dir / "abilities.yml"
        op_report_path = gen_dir / "operation_report.json"
        metrics_path = run_dir / "generation" / kb / "experiment_metrics.json"

        stats = analyze_operation(abilities_path, op_report_path)
        metrics = load_metrics_summary(metrics_path)

        base_row = {
            "llm": llm, "repeat": repeat, "pdf_stem": pdf_stem, "run_id": run_id,
            "kb": kb, "stage": "generation", "condition": "-",
        }
        if stats:
            rows.append({**base_row, **stats, **metrics})
        else:
            rows.append({**base_row, "anomalies": ["generation 결과 파일 없음/파싱 실패"]})

        for cond in RECOVERY_CONDITIONS:
            rec_dir = run_dir / "recovery" / kb / cond / "caldera"
            rec_abilities_path = rec_dir / "abilities.yml"
            rec_metrics_path = run_dir / "recovery" / kb / cond / "experiment_metrics.json"

            if not rec_dir.exists():
                continue

            # recovery/caldera/operation_report.json은 self-correction *시작 전* 초기 상태를
            # 복사해둔 파일이라 최종 결과가 아니다. 최종 상태는 가장 마지막 재시도의
            # operation_report_retry_N.json (재시도가 0번이면 초기 상태 그대로가 최종이므로
            # operation_report.json을 그대로 씀).
            retry_reports = sorted(
                rec_dir.glob("operation_report_retry_*.json"),
                key=lambda p: int(re.search(r'retry_(\d+)', p.stem).group(1)),
            )
            final_report_path = retry_reports[-1] if retry_reports else rec_dir / "operation_report.json"
            if not final_report_path.exists():
                continue

            # 복구 후 abilities.yml이 없으면(수정 안 됐으면) generation의 abilities.yml을 분모로 사용
            rec_stats = analyze_operation(
                rec_abilities_path if rec_abilities_path.exists() else abilities_path,
                final_report_path,
            )
            rec_metrics = load_metrics_summary(rec_metrics_path)

            # correction_report.json의 final_result와 교차 검증 (있으면).
            # final_result는 self-correction이 아직 진행 중(다른 report를 지금 돌리는 중 등)이면
            # 파일에 키는 있지만 값이 null일 수 있어 .get(key, {})가 기본값을 못 돌려준다 ->
            # "or {}"로 한 번 더 감싼다.
            correction = _load_json(rec_dir / "correction_report.json")
            final_result = (correction or {}).get("final_result") or {}

            rec_row = {
                "llm": llm, "repeat": repeat, "pdf_stem": pdf_stem, "run_id": run_id,
                "kb": kb, "stage": "recovery", "condition": cond,
                "final_report_used": final_report_path.name,
                "correction_report_success": final_result.get("success"),
                "correction_report_total": final_result.get("total"),
            }
            if rec_stats:
                if (final_result.get("total") is not None
                        and final_result["total"] != rec_stats["generated_count"]):
                    rec_stats.setdefault("anomalies", []).append(
                        f"correction_report.json final_result.total({final_result['total']})이 "
                        f"생성 개수({rec_stats['generated_count']})와 다름"
                    )
                rows.append({**rec_row, **rec_stats, **rec_metrics})
            else:
                rows.append({**rec_row, "anomalies": ["recovery 결과 파일 없음/파싱 실패"]})

    return rows


def print_summary(rows: List[Dict], anomalies_only: bool):
    print("=" * 100)
    print(f"실험 결과 집계 ({len(rows)}개 row)")
    print("=" * 100)

    header = f"{'LLM':<8}{'repeat':<7}{'report':<16}{'KB':<12}{'단계/조건':<14}{'생성':>5}{'성공':>5}{'성공률':>8}{'echo%':>7}  이상치"
    print(header)
    print("-" * 100)

    anomaly_rows = 0
    for r in rows:
        anomalies = r.get("anomalies", [])
        notes = r.get("notes", [])
        if anomalies:
            anomaly_rows += 1
        if anomalies_only and not anomalies:
            continue

        stage_label = r["stage"] if r["stage"] == "generation" else f"recovery/{r['condition']}"
        gen = r.get("generated_count", "-")
        succ = r.get("corrected_success", "-")
        rate = r.get("corrected_success_rate")
        rate_str = f"{rate:.1f}%" if isinstance(rate, (int, float)) else "-"
        echo_rate = r.get("echo_simulation_rate")
        echo_str = f"{echo_rate:.1f}%" if isinstance(echo_rate, (int, float)) else "-"
        remark_str = " / ".join(anomalies + [f"[참고] {n}" for n in notes])

        print(f"{r['llm']:<8}{r['repeat']:<7}{r['pdf_stem']:<16}{r['kb']:<12}{stage_label:<14}"
              f"{gen!s:>5}{succ!s:>5}{rate_str:>8}{echo_str:>7}  {remark_str}")

    print("-" * 100)
    print(f"이상치 있는 row: {anomaly_rows}/{len(rows)}")
    print("=" * 100)


def write_csv(rows: List[Dict], csv_path: Path):
    fieldnames = [
        "llm", "repeat", "pdf_stem", "run_id", "kb", "stage", "condition",
        "generated_count", "total_links", "distinct_in_results",
        "duplicated_ability_count", "missing_ability_count",
        "caldera_total_abilities", "caldera_success", "caldera_success_rate",
        "corrected_success", "corrected_failed", "corrected_success_rate",
        "echo_simulation_count", "echo_simulation_rate",
        "cost", "tokens", "duration_seconds", "llm_call_seconds",
        "anomalies", "notes",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            row = dict(r)
            row["anomalies"] = "; ".join(row.get("anomalies", []))
            row["notes"] = "; ".join(row.get("notes", []))
            writer.writerow(row)
    print(f"\n[저장] CSV: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="data/experiments/runs/ 전체 결과 집계 + 이상치 탐지")
    parser.add_argument("--runs-dir", type=str, default=str(RUNS_DIR), help="집계할 runs 디렉토리")
    parser.add_argument("--llm", type=str, default=None, help="특정 llm만 (claude/openai/gemini/grok)")
    parser.add_argument("--report", type=str, default=None, help="pdf_stem에 포함된 문자열로 필터 (예: KISA_TTPs_1)")
    parser.add_argument("--csv", type=str, default=None, help="결과를 저장할 CSV 경로")
    parser.add_argument("--anomalies-only", action="store_true", help="이상치 있는 row만 출력")
    args = parser.parse_args()

    runs_dir = Path(args.runs_dir)
    run_dirs = discover_run_dirs(runs_dir, args.llm, args.report)
    if not run_dirs:
        print(f"[WARNING] {runs_dir} 아래에서 실행 결과를 찾지 못했습니다.")
        sys.exit(0)

    all_rows = []
    for run_dir in run_dirs:
        all_rows.extend(analyze_run(run_dir))

    print_summary(all_rows, args.anomalies_only)

    if args.csv:
        write_csv(all_rows, Path(args.csv))


if __name__ == "__main__":
    main()
