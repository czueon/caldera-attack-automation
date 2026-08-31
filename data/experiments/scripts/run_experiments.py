"""
실험 배치 실행기 (CLI 조합 오케스트레이션)

main.py를 서브프로세스로 반복 호출해 두 실험 매트릭스를 순회한다.

1. generate: 11 보고서 x LLM x 지식베이스 유무(with_kb/without_kb) x repeat
   -> 초기 플레이북 생성 + (선택) 초기 실행
2. recover: generate 결과 중 실패가 있었던 것만 골라, 4가지 failure-recovery 조건
   (none/type/history/both)을 각각 적용 -> 실패 복구율 측정

with_kb/without_kb는 같은 step1/step2/stage1(기법 선택) 결과를 공유해야 공정한 비교가 되므로,
(report, llm, repeat) 조합마다 한 번만 생성해서 두 조건 디렉토리로 이어받는다. recover도 generate가
만든 초기 상태를 직접 건드리지 않고 조건별 디렉토리에 복사한 뒤 그 위에서 실행한다. 결과 폴더 구조:

    data/experiments/runs/{llm}/repeat_{n}/{report_pdf_stem}/{run_id}/
      shared/                              step1.yml, step2.yml
      generation/
        with_kb/                           step3.yml, caldera/ (초기 abilities/report)
        without_kb/
      recovery/
        with_kb/{none,type,history,both}/  caldera/ (복사된 초기 상태 + 복구 결과)
        without_kb/{none,type,history,both}/

Usage:
    python data/experiments/scripts/run_experiments.py generate --llms claude,gemini --repeats 5
    python data/experiments/scripts/run_experiments.py recover --manifest data/experiments/manifests/generation_manifest_XXXXXXXX.jsonl
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # data/experiments/scripts/ -> data/experiments/ -> data/ -> repo root
EXPERIMENTS_DIR = PROJECT_ROOT / "data" / "experiments"
RUNS_DIR = EXPERIMENTS_DIR / "runs"
MANIFESTS_DIR = EXPERIMENTS_DIR / "manifests"

REPORTS = [
    {"id": i, "pdf": f"data/raw/KISA_TTPs_{i}.pdf", "env": f"environment_ttps{i}.md"}
    for i in range(1, 12)
]

# 보고서별 VM/스냅샷 매핑. 보고서를 바꿀 때마다 .env의 VBOX_* 값을 여기 맞춰 자동으로 고쳐쓴다 —
# 안 그러면 엉뚱한 보고서의 VM으로 실행돼서 결과가 통째로 무효가 될 수 있다.
REPORT_VBOX_CONFIG = {
    1: {
        "env_updates": {
            "VBOX_VM_NAME": "ttps1", "VBOX_SNAPSHOT_NAME": "ttps1_patch",
            "VBOX_VM_NAME_lateral": "ttps1_2", "VBOX_SNAPSHOT_NAME_lateral": "ttps1_2_patch",
        },
        "env_comments": ["VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    2: {
        "env_updates": {"VBOX_VM_NAME": "ttps2", "VBOX_SNAPSHOT_NAME": "ttps2_patch"},
        "env_comments": ["VBOX_VM_NAME_lateral", "VBOX_SNAPSHOT_NAME_lateral",
                          "VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    3: {
        "env_updates": {"VBOX_VM_NAME": "ttps3", "VBOX_SNAPSHOT_NAME": "ttps3_patch"},
        "env_comments": ["VBOX_VM_NAME_lateral", "VBOX_SNAPSHOT_NAME_lateral",
                          "VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    4: {
        "env_updates": {"VBOX_VM_NAME": "ttps4", "VBOX_SNAPSHOT_NAME": "ttps4_patch"},
        "env_comments": ["VBOX_VM_NAME_lateral", "VBOX_SNAPSHOT_NAME_lateral",
                          "VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    5: {
        "env_updates": {
            "VBOX_VM_NAME": "ttps5", "VBOX_SNAPSHOT_NAME": "ttps5_patch",
            "VBOX_VM_NAME_lateral": "ttps5_2", "VBOX_SNAPSHOT_NAME_lateral": "ttps5_2_patch",
            "VBOX_VM_NAME_ad": "ttps5_ad", "VBOX_SNAPSHOT_NAME_ad": "ttps5_ad_patch",
        },
        "env_comments": [],
    },
    6: {
        "env_updates": {"VBOX_VM_NAME": "ttps6", "VBOX_SNAPSHOT_NAME": "ttps6_patch"},
        "env_comments": ["VBOX_VM_NAME_lateral", "VBOX_SNAPSHOT_NAME_lateral",
                          "VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    7: {
        "env_updates": {
            "VBOX_VM_NAME": "ttps7", "VBOX_SNAPSHOT_NAME": "ttps7_patch",
            "VBOX_VM_NAME_lateral": "ttps7_2", "VBOX_SNAPSHOT_NAME_lateral": "ttps7_2_patch",
        },
        "env_comments": ["VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    8: {
        "env_updates": {
            "VBOX_VM_NAME": "ttps8", "VBOX_SNAPSHOT_NAME": "ttps8_patch",
            "VBOX_VM_NAME_lateral": "ttps8_2", "VBOX_SNAPSHOT_NAME_lateral": "ttps8_2_patch",
            "VBOX_VM_NAME_ad": "ttps8_ad", "VBOX_SNAPSHOT_NAME_ad": "ttps8_ad_patch",
        },
        "env_comments": [],
    },
    9: {
        "env_updates": {"VBOX_VM_NAME": "ttps9", "VBOX_SNAPSHOT_NAME": "ttps9_patch"},
        "env_comments": ["VBOX_VM_NAME_lateral", "VBOX_SNAPSHOT_NAME_lateral",
                          "VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    10: {
        "env_updates": {
            "VBOX_VM_NAME": "ttps10", "VBOX_SNAPSHOT_NAME": "ttps10_patch",
            "VBOX_VM_NAME_lateral": "ttps10_2", "VBOX_SNAPSHOT_NAME_lateral": "ttps10_2_patch",
        },
        "env_comments": ["VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
    11: {
        "env_updates": {
            "VBOX_VM_NAME": "ttps11", "VBOX_SNAPSHOT_NAME": "ttps11_patch",
            "VBOX_VM_NAME_lateral": "ttps11_2", "VBOX_SNAPSHOT_NAME_lateral": "ttps11_2_patch",
        },
        "env_comments": ["VBOX_VM_NAME_ad", "VBOX_SNAPSHOT_NAME_ad"],
    },
}

RQ2_CONDITIONS = {
    "none": {"no_failure_type": True, "no_history": True},
    "type": {"no_failure_type": False, "no_history": True},
    "history": {"no_failure_type": True, "no_history": False},
    "both": {"no_failure_type": False, "no_history": False},
}

CALDERA_STATE_FILES = ("abilities.yml", "adversaries.yml", "operation_report.json")


# ============================================================================
# 공용 유틸
# ============================================================================

def kb_label(use_kb: bool) -> str:
    return "with_kb" if use_kb else "without_kb"


def run_main(args_list, log_path: Path, timeout: Optional[int] = None, desc: str = "") -> int:
    """`python main.py <args_list>` 실행. 원본 stdout/stderr는 전부 로그 파일에 저장하고,
    터미널에는 경과 시간 + 최근 진행 상태 한 줄짜리 진행바만 갱신해서 보여준다
    (main.py 자체 로그가 매우 길어서 그대로 흘리면 배치 진행 상황을 오히려 놓치기 쉬움).
    종료 코드 반환. 타임아웃 시 -1 반환."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "main.py"] + args_list

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"CMD: {' '.join(cmd)}\n{'=' * 80}\n")
        f.flush()

        proc = subprocess.Popen(
            cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )

        timed_out = {"flag": False}
        timer = None
        if timeout:
            def _kill():
                timed_out["flag"] = True
                proc.kill()
            timer = threading.Timer(timeout, _kill)
            timer.start()

        bar_fmt = "    {desc} | {elapsed}"
        with tqdm(total=0, desc=desc, bar_format=bar_fmt, leave=False) as pbar:
            try:
                for line in proc.stdout:
                    f.write(line)
                    f.flush()
                    stripped = line.strip()
                    if stripped.startswith("["):
                        pbar.set_description_str(f"{desc} | {stripped[:70]}", refresh=True)
                proc.wait()
            finally:
                if timer:
                    timer.cancel()

        if timed_out["flag"]:
            f.write(f"\n[TIMEOUT after {timeout}s]\n")
            return -1
        return proc.returncode


def _parse_steps(step_arg: str) -> list:
    """main.py의 --step 표기를 정수 리스트로 변환 ('all' -> [1,2,3,4,5] 등)."""
    if step_arg == "all":
        return [1, 2, 3, 4, 5]
    if "~" in step_arg:
        start, end = (int(x) for x in step_arg.split("~"))
        return list(range(start, end + 1))
    return [int(step_arg)]


def _step_includes(step_arg: str, step_num: int) -> bool:
    """main.py의 --step 표기(`~` 구분, 예: '1~4', 'all')에 특정 step 번호가 포함되는지."""
    return step_num in _parse_steps(step_arg)


def _generation_step_arg(step_arg: str) -> Optional[str]:
    """공유 step1/2를 이미 만들어뒀으므로, KB 조건별 호출에는 1,2를 뺀 나머지 범위만 넘긴다.
    (그대로 넘기면 main.py의 Step1/Step2가 '이미 파일 있으면 스킵' 없이 무조건 재실행되면서
    복사해둔 shared/step1.yml, step2.yml을 덮어써버려서 KB on/off가 서로 다른 입력을 갖게 됨)"""
    remaining = [s for s in _parse_steps(step_arg) if s >= 3]
    if not remaining:
        return None
    if len(remaining) == 1:
        return str(remaining[0])
    return f"{remaining[0]}~{remaining[-1]}"


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _print_timing_summary(base_dir: Path, label: str, verbose: bool = False):
    """main.py가 저장한 experiment_metrics.json을 읽어 LLM 호출 시간 vs 나머지 시간을
    터미널에 한 줄로 요약해서 보여준다 (main.py 자체 출력은 로그 파일에만 저장됨).
    verbose=True면 Step/phase별 세부 내역까지 풀어서 보여준다 (기본은 꺼둠 — 필요하면
    experiment_metrics.json을 직접 열어보는 게 나음)."""
    metrics_path = base_dir / "experiment_metrics.json"
    if not metrics_path.exists():
        return
    try:
        m = _read_json(metrics_path)
    except Exception as e:
        print(f"    [WARNING] experiment_metrics.json 파싱 실패: {e}")
        return

    total = m.get("total_duration_seconds", 0.0)
    llm = m.get("total_llm_call_seconds", 0.0)
    other = max(0.0, total - llm)
    print(f"    [시간] {label}: 총 {_format_seconds(total)} "
          f"(LLM 호출 {_format_seconds(llm)} / 나머지 {_format_seconds(other)})")

    if verbose:
        for step in m.get("steps", []):
            step_llm = step.get("total_llm_call_seconds", 0.0)
            step_total = step.get("duration_seconds", 0.0)
            print(f"      - {step['step_name']}: {_format_seconds(step_total)} (LLM {_format_seconds(step_llm)})")
            for phase in step.get("phase_timings", []):
                print(f"          · {phase['label']}: {_format_seconds(phase['duration_seconds'])}")


def _backup_metrics_file(base_dir: Path, backup_name: str):
    """base_dir/experiment_metrics.json을 backup_name으로 복사해둔다.
    _ensure_shared_prep은 같은 shared_dir에 main.py를 두 번(step1-2, stage1) 호출하는데,
    main.py는 매번 base_dir/experiment_metrics.json을 통째로 덮어쓰므로 백업해두지 않으면
    먼저 실행된 쪽의 LLM 비용/시간 기록이 뒤 호출에 의해 사라진다."""
    src = base_dir / "experiment_metrics.json"
    if not src.exists():
        return
    try:
        shutil.copy2(src, base_dir / backup_name)
    except OSError as e:
        print(f"    [WARNING] {backup_name} 백업 실패: {e}")


def _update_env_file(env_updates: dict, env_comments: list):
    """.env의 VBOX_* 값을 갱신 (기존 주석/빈 줄/순서는 보존). backup/auto_run.py의
    update_env_file 로직을 그대로 가져옴. 자식 프로세스(main.py)는 매번 새로 실행되며
    그 시점의 .env를 읽으므로, 여기서 파일만 고쳐두면 이후 subprocess 호출부터 바로 적용됨."""
    env_path = PROJECT_ROOT / ".env"

    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True) if env_path.exists() else []
    all_vbox_keys = set(env_updates.keys()) | set(env_comments)
    written_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            uncommented = stripped.lstrip("#").strip()
            if "=" in uncommented:
                key = uncommented.split("=", 1)[0].strip()
                if key in all_vbox_keys:
                    if key in env_updates and key not in written_keys:
                        new_lines.append(f"{key}={env_updates[key]}\n")
                        written_keys.add(key)
                    elif key in env_comments and key not in written_keys:
                        new_lines.append(f"# {key}=\n")
                        written_keys.add(key)
                    continue
            new_lines.append(line)
        elif "=" in stripped and stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in env_updates and key not in written_keys:
                new_lines.append(f"{key}={env_updates[key]}\n")
                written_keys.add(key)
            elif key in env_comments and key not in written_keys:
                new_lines.append(f"# {key}=\n")
                written_keys.add(key)
            elif key not in all_vbox_keys:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for key, value in env_updates.items():
        if key not in written_keys:
            new_lines.append(f"{key}={value}\n")
    for key in env_comments:
        if key not in written_keys:
            new_lines.append(f"# {key}=\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")


def _apply_report_vbox_config(report_id: int):
    """이 보고서에 맞는 VM/스냅샷으로 .env를 맞추고, 뭘로 맞췄는지 화면에 표시.

    .env 파일만 고쳐두면 충분해 보이지만, main.py는 python-dotenv의 load_dotenv()로
    읽는데 이건 기본적으로 override=False라서 이 run_experiments.py 프로세스(부모)나
    그 상위 셸에 VBOX_VM_NAME 등이 이미 실제 환경변수로 박혀있으면 .env 값을 무시하고
    그 값을 그대로 쓴다. subprocess.Popen은 부모의 os.environ을 그대로 상속하므로,
    여기서 os.environ도 같이 갱신해야 자식 프로세스가 확실히 올바른 값을 받는다.
    """
    config = REPORT_VBOX_CONFIG.get(report_id)
    if not config:
        print(f"  [WARNING] report {report_id}의 VM 설정이 없습니다 — .env를 수정하지 않고 진행합니다")
        return
    _update_env_file(config["env_updates"], config["env_comments"])
    os.environ.update(config["env_updates"])
    for key in config["env_comments"]:
        os.environ.pop(key, None)
    vm = config["env_updates"].get("VBOX_VM_NAME")
    snap = config["env_updates"].get("VBOX_SNAPSHOT_NAME")
    print(f"  [VM 설정] report {report_id} -> VBOX_VM_NAME={vm}, VBOX_SNAPSHOT_NAME={snap}")


def _copy_state_files(src_dir: Path, dst_dir: Path, filenames):
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for filename in filenames:
        src_file = src_dir / filename
        if src_file.exists():
            shutil.copy2(src_file, dst_dir / filename)
            copied.append(filename)
    return copied


def _run_dir(llm: str, repeat: int, pdf_stem: str, run_id: str) -> Path:
    """runs/{llm}/repeat_{n}/{pdf_stem}/{run_id}/"""
    return RUNS_DIR / llm / f"repeat_{repeat}" / pdf_stem / run_id


def _load_generation_results() -> Dict[tuple, dict]:
    """data/experiments/manifests/generation_manifest_*.jsonl 전체를 훑어서
    (report_id, llm, use_kb, repeat) -> 성공(exit_code==0)한 가장 최근 row만 모은다.
    generate를 여러 세션에 나눠 돌려도(중간에 끊기거나 나중에 이어 돌려도) 이 결과로
    "실제로 성공한 조합"을 정확히 판정한다 (폴더 존재 여부만으로는 판정 못 함 —
    예: 같은 repeat라도 with_kb만 성공하고 without_kb는 실패했을 수 있음)."""
    results = {}
    for path in sorted(MANIFESTS_DIR.glob("generation_manifest_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("exit_code") != 0:
                continue
            key = (row["report_id"], row["llm"], row["use_kb"], row["repeat"])
            results[key] = row  # 여러 세션에 걸쳐 중복되면 시간순으로 나중 것이 이김
    return results


def _missing_repeats(results: Dict[tuple, dict], report_id: int, llm: str, target: int) -> List[int]:
    """1..target 중 with_kb/without_kb 둘 다 성공하지 못한 repeat 번호만 골라서 반환.
    repeat_N은 서로 다른 독립 실행을 구분하는 라벨일 뿐 순서에 의미가 없으므로, 이미
    성공한 번호(예: 2·3·5)는 그대로 두고 실패/미실행 번호(예: 1·4)만 다시 실행한다."""
    return [n for n in range(1, target + 1)
            if (report_id, llm, True, n) not in results or (report_id, llm, False, n) not in results]


def _load_recovery_done() -> set:
    """data/experiments/manifests/recovery_manifest_*.jsonl 전체에서 성공(exit_code==0)한
    (report_id, llm, use_kb, repeat, condition) 조합 집합. recover 재개 시 이미 끝난
    조합을 건너뛰기 위해 사용."""
    done = set()
    for path in sorted(MANIFESTS_DIR.glob("recovery_manifest_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("exit_code") != 0:
                continue
            done.add((row["report_id"], row["llm"], row["use_kb"], row["repeat"], row["condition"]))
    return done


def _main_output_dir_and_version(llm: str, repeat: int, sub_version: str) -> tuple:
    """main.py의 --output-dir/--version-id 조합. main.py는 항상
    output_dir/pdf_stem/version_id 순서로 base_dir을 만들기 때문에, pdf_stem 뒤에
    붙는 나머지 경로(run_id/... )를 전부 version_id에 실어서 원하는 트리를 만든다."""
    output_dir = RUNS_DIR / llm / f"repeat_{repeat}"
    return str(output_dir), sub_version


# ============================================================================
# generate: 11 보고서 x LLM x 지식베이스 유무 x repeat
# ============================================================================

@dataclass
class GenerationResult:
    report_id: int
    pdf: str
    env: str
    llm: str
    use_kb: bool
    repeat: int
    run_id: str            # (report, llm, repeat) 한 판의 식별자 -> recover에서 이어받을 때 사용
    exit_code: int
    duration_sec: float
    ran_execution: bool
    initial_total: Optional[int] = None
    initial_success: Optional[int] = None
    initial_failed: Optional[int] = None


def _ensure_shared_prep(report, llm, repeat, run_id, timeout, log_dir, run_label) -> bool:
    """(report, llm, repeat) 한 판의 step1/step2 + stage1(기법 선택)을 shared/에 한 번만 생성한다.
    설계 근거는 모듈 docstring 참고. 성공 여부 반환."""
    pdf_stem = Path(report["pdf"]).stem
    shared_dir = _run_dir(llm, repeat, pdf_stem, run_id) / "shared"

    if (shared_dir / "step3.yml").exists():
        return True  # 이미 있음 (재실행 등)

    output_dir, version_id = _main_output_dir_and_version(llm, repeat, f"{run_id}/shared")

    # 1) step1~2
    cli_args = [
        "--step", "1~2",
        "--pdf", report["pdf"],
        "--llm", llm,
        "--output-dir", output_dir,
        "--version-id", version_id,
    ]
    log_path = log_dir / f"{pdf_stem}__{run_id}__shared_step1-2.log"
    print(f"  [shared step1-2] {run_label} -> {shared_dir}")

    exit_code = run_main(cli_args, log_path, timeout=timeout, desc=f"{run_label} shared step1-2")
    if exit_code == 0:
        _print_timing_summary(shared_dir, "shared step1-2")
        # step1-2와 stage1은 같은 shared_dir에 experiment_metrics.json을 각자 덮어써서 저장하므로
        # (main.py가 매번 base_dir/experiment_metrics.json을 통째로 새로 씀), 여기서 백업해두지
        # 않으면 바로 다음 stage1 호출이 끝나자마자 step1-2의 LLM 비용/시간 기록이 사라짐.
        _backup_metrics_file(shared_dir, "experiment_metrics_step1-2.json")
    if exit_code != 0:
        print(f"    [ERROR] step1-2 생성 실패 (exit={exit_code}), log: {log_path}")
        return False

    # 2) stage1 (기법 선택만, KB와 무관)
    cli_args = [
        "--step", "3",
        "--stage1-only",
        "--pdf", report["pdf"],
        "--env", report["env"],
        "--llm", llm,
        "--output-dir", output_dir,
        "--version-id", version_id,
    ]
    log_path = log_dir / f"{pdf_stem}__{run_id}__shared_stage1.log"
    print(f"  [shared stage1] {run_label} -> {shared_dir}")

    exit_code = run_main(cli_args, log_path, timeout=timeout, desc=f"{run_label} shared stage1")
    if exit_code == 0:
        _print_timing_summary(shared_dir, "shared stage1")
        _backup_metrics_file(shared_dir, "experiment_metrics_stage1.json")
    if exit_code != 0:
        print(f"    [ERROR] stage1 생성 실패 (exit={exit_code}), log: {log_path}")
        return False
    return True


def cmd_generate(args):
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = EXPERIMENTS_DIR / "logs" / "generation"
    manifest_path = MANIFESTS_DIR / f"generation_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    llms = [x.strip() for x in args.llms.split(",") if x.strip()]
    include_execution = _step_includes(args.step, 5)
    if include_execution:
        print("[INFO] --step에 5가 포함되어 있어 --skip-correction을 자동으로 붙입니다 "
              "(generate는 초기 실행 성공률만 필요, self-correcting은 recover에서 별도 처리)")

    reports = REPORTS
    if getattr(args, "reports", None):
        wanted_ids = {int(x.strip()) for x in args.reports.split(",") if x.strip()}
        reports = [r for r in REPORTS if r["id"] in wanted_ids]

    gen_step = _generation_step_arg(args.step)
    if gen_step is None:
        print(f"[WARNING] --step {args.step}에 3 이상이 없어 KB 조건별로 실행할 게 없습니다 "
              "(step1/2 생성만 하고 종료)")

    prior_results = _load_generation_results()
    repeat_lists = {
        (report["id"], llm): _missing_repeats(prior_results, report["id"], llm, args.repeats)
        for report in reports for llm in llms
    }
    total_runs = sum(len(r) for r in repeat_lists.values()) * 2
    skipped = sum(1 for r in repeat_lists.values() if len(r) == 0)
    if skipped:
        print(f"[INFO] {skipped}개 report+llm 조합은 이미 --repeats {args.repeats}만큼 실행되어 건너뜁니다")
    run_idx = 0

    with open(manifest_path, "w", encoding="utf-8") as manifest_f:
        for report in reports:
            pdf_stem = Path(report["pdf"]).stem
            _apply_report_vbox_config(report["id"])
            for llm in llms:
                for repeat in repeat_lists[(report["id"], llm)]:
                    run_id = f"run_{datetime.now().strftime('%H%M%S')}"
                    run_label = f"report={report['id']} llm={llm} repeat={repeat}"

                    shared_ok = _ensure_shared_prep(report, llm, repeat, run_id, args.timeout, log_dir, run_label)

                    for use_kb in (True, False):
                        run_idx += 1

                        if not shared_ok:
                            result = GenerationResult(
                                report_id=report["id"], pdf=report["pdf"], env=report["env"], llm=llm,
                                use_kb=use_kb, repeat=repeat, run_id=run_id,
                                exit_code=-1, duration_sec=0.0, ran_execution=include_execution,
                            )
                            manifest_f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
                            continue

                        shared_dir = _run_dir(llm, repeat, pdf_stem, run_id) / "shared"
                        gen_dir = _run_dir(llm, repeat, pdf_stem, run_id) / "generation" / kb_label(use_kb)
                        _copy_state_files(shared_dir, gen_dir, ("step1.yml", "step2.yml"))
                        # step3.yml(shared stage1 결과)은 이름이 겹치지 않게 step3_stage1.yml로 복사해서
                        # --stage1-file로 넘긴다 (gen_dir의 step3.yml은 stage2까지 끝난 최종 결과용)
                        gen_dir.mkdir(parents=True, exist_ok=True)
                        stage1_file = gen_dir / "step3_stage1.yml"
                        shutil.copy2(shared_dir / "step3.yml", stage1_file)

                        if gen_step is None:
                            exit_code, duration = 0, 0.0
                        else:
                            output_dir, version_id = _main_output_dir_and_version(
                                llm, repeat, f"{run_id}/generation/{kb_label(use_kb)}"
                            )
                            cli_args = [
                                "--step", gen_step,
                                "--stage1-file", str(stage1_file),
                                "--pdf", report["pdf"],
                                "--env", report["env"],
                                "--llm", llm,
                                "--output-dir", output_dir,
                                "--version-id", version_id,
                            ]
                            if not use_kb:
                                cli_args.append("--no-kb")
                            if include_execution:
                                cli_args.append("--skip-correction")

                            log_path = log_dir / f"{pdf_stem}__{run_id}__{kb_label(use_kb)}.log"
                            print(f"[{run_idx}/{total_runs}] {run_label} kb={use_kb} -> {gen_dir}")

                            start = time.time()
                            exit_code = run_main(cli_args, log_path, timeout=args.timeout,
                                                  desc=f"[{run_idx}/{total_runs}] {run_label} kb={use_kb}")
                            duration = time.time() - start
                            if exit_code == 0:
                                _print_timing_summary(gen_dir, f"generation/{kb_label(use_kb)}")

                        result = GenerationResult(
                            report_id=report["id"], pdf=report["pdf"], env=report["env"], llm=llm,
                            use_kb=use_kb, repeat=repeat, run_id=run_id,
                            exit_code=exit_code, duration_sec=duration, ran_execution=include_execution,
                        )

                        if include_execution and exit_code == 0:
                            report_path = gen_dir / "caldera" / "operation_report.json"
                            if report_path.exists():
                                try:
                                    stats = _read_json(report_path).get("statistics", {})
                                    result.initial_total = stats.get("total_abilities")
                                    result.initial_success = stats.get("success")
                                    result.initial_failed = stats.get("failed")
                                except Exception as e:
                                    print(f"  [WARNING] operation_report.json 파싱 실패: {e}")

                        manifest_f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
                        manifest_f.flush()

                        status = "OK" if exit_code == 0 else f"FAILED(exit={exit_code})"
                        print(f"  -> {status} in {duration:.0f}s")

    print(f"\n[DONE] generate 매트릭스 실행 완료. manifest: {manifest_path}")
    return manifest_path


# ============================================================================
# recover: generate 결과 중 실패가 있었던 세트에 4가지 recovery 조건 적용
# ============================================================================

@dataclass
class RecoveryResult:
    report_id: int
    llm: str
    use_kb: bool
    repeat: int
    run_id: str
    condition: str
    exit_code: int
    duration_sec: float
    pre_failed: Optional[int] = None
    post_success: Optional[int] = None
    post_failed: Optional[int] = None
    recovery_rate: Optional[float] = None


def cmd_recover(args):
    manifest_path = Path(args.manifest)
    gen_rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    candidates = [r for r in gen_rows if r.get("exit_code") == 0 and (r.get("initial_failed") or 0) > 0]

    if getattr(args, "reports", None):
        wanted_ids = {int(x.strip()) for x in args.reports.split(",") if x.strip()}
        candidates = [r for r in candidates if r["report_id"] in wanted_ids]
    if getattr(args, "llms", None):
        wanted_llms = {x.strip() for x in args.llms.split(",") if x.strip()}
        candidates = [r for r in candidates if r["llm"] in wanted_llms]
    if getattr(args, "kb", None):
        wanted_kb = {x.strip() for x in args.kb.split(",") if x.strip()}
        candidates = [r for r in candidates if kb_label(r["use_kb"]) in wanted_kb]

    conditions = dict(RQ2_CONDITIONS)
    if getattr(args, "conditions", None):
        wanted_conditions = {x.strip() for x in args.conditions.split(",") if x.strip()}
        conditions = {k: v for k, v in RQ2_CONDITIONS.items() if k in wanted_conditions}

    print(f"[INFO] generate 결과 {len(gen_rows)}개 중 필터 적용 후 {len(candidates)}개 세트에 "
          f"{len(conditions)}가지 recovery 조건({','.join(conditions)}) 적용")

    recovery_done = _load_recovery_done()

    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = EXPERIMENTS_DIR / "logs" / "recovery"
    out_manifest_path = MANIFESTS_DIR / f"recovery_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    report_by_id = {r["id"]: r for r in REPORTS}
    total_runs = len(candidates) * len(conditions)
    run_idx = 0
    skipped = 0

    last_report_id = None
    with open(out_manifest_path, "w", encoding="utf-8") as manifest_f:
        for row in candidates:
            pdf_stem = Path(row["pdf"]).stem
            report = report_by_id[row["report_id"]]
            gen_dir = _run_dir(row["llm"], row["repeat"], pdf_stem, row["run_id"]) / "generation" / kb_label(row["use_kb"])
            src_caldera_dir = gen_dir / "caldera"

            if row["report_id"] != last_report_id:
                _apply_report_vbox_config(row["report_id"])
                last_report_id = row["report_id"]

            for condition, flags in conditions.items():
                run_idx += 1

                done_key = (row["report_id"], row["llm"], row["use_kb"], row["repeat"], condition)
                if done_key in recovery_done:
                    skipped += 1
                    continue

                rec_dir = (_run_dir(row["llm"], row["repeat"], pdf_stem, row["run_id"])
                           / "recovery" / kb_label(row["use_kb"]) / condition)
                dst_caldera_dir = rec_dir / "caldera"

                # generate의 초기 상태를 복사본으로 떠서 그 위에서만 수정 (원본 보존)
                copied = _copy_state_files(src_caldera_dir, dst_caldera_dir, CALDERA_STATE_FILES)
                if "abilities.yml" not in copied or "adversaries.yml" not in copied:
                    print(f"  [WARNING] {gen_dir}: abilities/adversaries.yml 없음, 건너뜀")
                    continue

                output_dir, version_id = _main_output_dir_and_version(
                    row["llm"], row["repeat"],
                    f"{row['run_id']}/recovery/{kb_label(row['use_kb'])}/{condition}"
                )
                cli_args = [
                    "--step", "5",
                    "--pdf", row["pdf"],
                    "--env", report["env"],
                    "--llm", row["llm"],
                    "--output-dir", output_dir,
                    "--version-id", version_id,
                    # 주의: --skip-upload는 쓰지 않는다. generate가 끝나면 서버에 올렸던
                    # ability/adversary를 항상 삭제하므로, 로컬에 복사된 adversary_id를 그대로
                    # 재사용하면 존재하지 않는 adversary를 참조하게 되어 0-ability Operation이 됨.
                    # 재사용해야 할 건 서버 리소스가 아니라 operation_report.json(실패 기록)뿐.
                    "--skip-initial-execution",  # 초기 실행만 재사용, 재시도 재실행은 정상 수행 (재업로드는 함)
                ]
                if flags["no_failure_type"]:
                    cli_args.append("--no-failure-type")
                if flags["no_history"]:
                    cli_args.append("--no-history")

                log_path = log_dir / f"{pdf_stem}__{row['run_id']}__{kb_label(row['use_kb'])}__{condition}.log"
                print(f"[{run_idx}/{total_runs}] report={row['report_id']} llm={row['llm']} "
                      f"kb={row['use_kb']} condition={condition} -> {rec_dir}")

                start = time.time()
                exit_code = run_main(
                    cli_args, log_path, timeout=args.timeout,
                    desc=f"[{run_idx}/{total_runs}] report={row['report_id']} kb={row['use_kb']} {condition}"
                )
                duration = time.time() - start
                if exit_code == 0:
                    _print_timing_summary(rec_dir, f"recovery/{kb_label(row['use_kb'])}/{condition}")

                result = RecoveryResult(
                    report_id=row["report_id"], llm=row["llm"], use_kb=row["use_kb"], repeat=row["repeat"],
                    run_id=row["run_id"], condition=condition, exit_code=exit_code, duration_sec=duration,
                    pre_failed=row.get("initial_failed"),
                )

                if exit_code == 0:
                    correction_report_path = dst_caldera_dir / "correction_report.json"
                    if correction_report_path.exists():
                        try:
                            cr = _read_json(correction_report_path)
                            final = cr.get("final_result") or {}
                            result.post_success = final.get("success")
                            result.post_failed = final.get("failed")
                            pre_failed = row.get("initial_failed") or 0
                            if pre_failed and result.post_failed is not None:
                                recovered = pre_failed - result.post_failed
                                result.recovery_rate = recovered / pre_failed
                        except Exception as e:
                            print(f"  [WARNING] correction_report.json 파싱 실패: {e}")

                manifest_f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
                manifest_f.flush()

                status = "OK" if exit_code == 0 else f"FAILED(exit={exit_code})"
                rr = f"{result.recovery_rate * 100:.1f}%" if result.recovery_rate is not None else "N/A"
                print(f"  -> {status} in {duration:.0f}s, recovery_rate={rr}")

    if skipped:
        print(f"[INFO] 이미 성공했던 {skipped}건은 건너뛰었습니다")
    print(f"\n[DONE] recover 매트릭스 실행 완료. manifest: {out_manifest_path}")
    return out_manifest_path


# ============================================================================
# full: 보고서 하나씩 generate -> recover까지 순서대로 끝낸다.
# (generate를 전체 보고서에 대해 다 끝내고 나서 recover를 한꺼번에 도는 방식은, 중간에
#  끊기면 이미 끝낸 generate 결과에 대한 recover가 하나도 안 된 상태로 남는다. 그래서
#  보고서 단위로 매듭지어서, 중간에 끊겨도 그 보고서만 다시 이어 하면 되게 한다.)
# ============================================================================

def cmd_full(args):
    reports = REPORTS
    if getattr(args, "reports", None):
        wanted_ids = {int(x.strip()) for x in args.reports.split(",") if x.strip()}
        reports = [r for r in REPORTS if r["id"] in wanted_ids]

    for report in reports:
        print(f"\n{'#' * 70}\n# report {report['id']}: generate\n{'#' * 70}")
        cmd_generate(argparse.Namespace(
            llms=args.llms, reports=str(report["id"]), repeats=args.repeats,
            step=args.step, timeout=args.timeout,
        ))

        print(f"\n{'#' * 70}\n# report {report['id']}: recover\n{'#' * 70}")
        rows = [row for key, row in _load_generation_results().items() if key[0] == report["id"]]
        if not rows:
            print(f"[WARNING] report {report['id']}: 성공한 generate 결과가 없어 recover를 건너뜁니다")
            continue

        # "generation_manifest_*" 패턴은 _load_generation_results()가 다시 훑는 대상이라,
        # 여기서 만드는 recover 입력용 파일은 다른 접두사를 써서 안 섞이게 한다.
        report_manifest = MANIFESTS_DIR / f"recover_input_report{report['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        with open(report_manifest, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        cmd_recover(argparse.Namespace(
            manifest=str(report_manifest), reports=str(report["id"]), llms=None, kb=None,
            timeout=args.timeout,
        ))

    print("\n[DONE] 지정된 보고서 전체를 순서대로 generate+recover 완료")


# ============================================================================
# errors: 지금까지 쌓인 모든 manifest에서 실패(exit_code != 0)한 case를 모아 보여준다.
# ============================================================================

def cmd_errors(args):
    pdf_by_report = {r["id"]: Path(r["pdf"]).stem for r in REPORTS}

    def _find_logs(log_dir: Path, pdf_stem: str, run_id: str):
        return sorted(log_dir.glob(f"{pdf_stem}__{run_id}__*.log"))

    gen_failures = []
    for path in sorted(MANIFESTS_DIR.glob("generation_manifest_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("exit_code") != 0:
                gen_failures.append(row)

    rec_failures = []
    for path in sorted(MANIFESTS_DIR.glob("recovery_manifest_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("exit_code") != 0:
                rec_failures.append(row)

    print(f"[generate 실패] {len(gen_failures)}건")
    log_dir = EXPERIMENTS_DIR / "logs" / "generation"
    for row in gen_failures:
        pdf_stem = pdf_by_report[row["report_id"]]
        logs = _find_logs(log_dir, pdf_stem, row["run_id"])
        print(f"  report={row['report_id']} llm={row['llm']} kb={row['use_kb']} repeat={row['repeat']} "
              f"exit={row['exit_code']}")
        for log in logs:
            print(f"    log: {log}")

    print(f"\n[recover 실패] {len(rec_failures)}건")
    log_dir = EXPERIMENTS_DIR / "logs" / "recovery"
    for row in rec_failures:
        pdf_stem = pdf_by_report[row["report_id"]]
        logs = _find_logs(log_dir, pdf_stem, row["run_id"])
        print(f"  report={row['report_id']} llm={row['llm']} kb={row['use_kb']} repeat={row['repeat']} "
              f"condition={row['condition']} exit={row['exit_code']}")
        for log in logs:
            print(f"    log: {log}")

    if not gen_failures and not rec_failures:
        print("[OK] 지금까지 실패한 case 없음")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="지식베이스(generate) / failure-recovery(recover) ablation 배치 실행기")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("generate", help="11 보고서 x LLM x 지식베이스 유무 x repeat 매트릭스 실행")
    p1.add_argument("--llms", type=str, default="claude", help="쉼표로 구분된 LLM 목록 (예: claude,gemini)")
    p1.add_argument("--reports", type=str, default=None,
                     help="쉼표로 구분된 보고서 ID만 실행 (예: 1 또는 1,3,5). 미지정 시 11개 전부")
    p1.add_argument("--repeats", type=int, default=5,
                     help="report+llm 조합마다 1~N회차를 채운다 (기본 5). 이미 성공한 회차는 번호에 "
                          "상관없이 건너뛰고 실패/미실행 회차만 다시 실행하므로, 같은 명령을 다시 "
                          "실행하면 안전하게 이어서 채워진다")
    p1.add_argument("--step", type=str, default="1~4",
                     help="main.py --step 값 (기본 1~4: 생성만, VM/Caldera 불필요). "
                          "5를 포함하면 --skip-correction이 자동으로 붙어 초기 실행 결과만 저장됨")
    p1.add_argument("--timeout", type=int, default=None, help="실행당 타임아웃(초)")
    p1.set_defaults(func=cmd_generate)

    p2 = sub.add_parser("recover", help="generate manifest에서 실패 있는 세트에 4가지 recovery 조건 적용 (VM/Caldera 필요)")
    p2.add_argument("--manifest", type=str, required=True, help="generate 실행으로 생성된 manifest jsonl 경로")
    p2.add_argument("--reports", type=str, default=None, help="쉼표로 구분된 보고서 ID만 재실행 (예: 1)")
    p2.add_argument("--llms", type=str, default=None, help="쉼표로 구분된 LLM만 재실행 (예: openai)")
    p2.add_argument("--kb", type=str, default=None, help="with_kb,without_kb 중 쉼표로 구분해서 지정 (예: with_kb)")
    p2.add_argument("--conditions", type=str, default=None,
                     help="none,type,history,both 중 쉼표로 구분해서 지정 (미지정 시 4개 전부)")
    p2.add_argument("--timeout", type=int, default=None)
    p2.set_defaults(func=cmd_recover)

    p3 = sub.add_parser("full", help="보고서 하나씩 generate -> recover까지 끝내고 다음 보고서로 (VM/Caldera 필요)")
    p3.add_argument("--llms", type=str, default="claude", help="쉼표로 구분된 LLM 목록 (예: claude,gemini)")
    p3.add_argument("--reports", type=str, default=None,
                     help="쉼표로 구분된 보고서 ID만 실행 (예: 1 또는 1,3,5). 미지정 시 11개 전부")
    p3.add_argument("--repeats", type=int, default=5, help="report+llm 조합마다 1~N회차를 채운다 (실패/미실행 회차만 재실행)")
    p3.add_argument("--step", type=str, default="all", help="main.py --step 값 (기본 all)")
    p3.add_argument("--timeout", type=int, default=None, help="실행당 타임아웃(초)")
    p3.set_defaults(func=cmd_full)

    p4 = sub.add_parser("errors", help="지금까지 쌓인 manifest에서 실패(exit_code != 0)한 case + 로그 경로를 보여줌")
    p4.set_defaults(func=cmd_errors)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
