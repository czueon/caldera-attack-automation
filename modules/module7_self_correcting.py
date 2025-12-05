"""
Module 7: Offline Self-Correcting Engine
로컬에서 Operation 로그를 분석하여 실패한 Ability를 자동으로 수정

워크플로우:
1. Caldera 서버에서 Operation Report JSON 다운로드
2. 이 모듈로 로그 분석 + 실패 원인 분류 + LLM 수정
3. 기존 abilities.yml에서 해당 ability 부분을 직접 수정
4. 수정된 abilities를 Caldera 서버로 재업로드
"""

import yaml
import json
import re
import anthropic
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from modules.config import get_anthropic_api_key, get_claude_model


# ============================================================================
# Data Models
# ============================================================================

class FailureType(Enum):
    """실패 유형"""
    SYNTAX_ERROR = "syntax_error"
    MISSING_ENV = "missing_env"
    CALDERA_CONSTRAINT = "caldera_constraint"
    DEPENDENCY_ERROR = "dependency_error"
    UNRECOVERABLE = "unrecoverable"


@dataclass
class FailedAbility:
    """실패한 Ability 정보"""
    ability_id: str
    ability_name: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    failure_type: Optional[FailureType] = None
    tactic: str = ""
    technique_id: str = ""
    technique_name: str = ""


@dataclass
class CorrectionResult:
    """수정 결과"""
    ability_id: str
    ability_name: str
    original_command: str
    fixed_command: str
    failure_type: FailureType
    success: bool
    reason: str = ""


# ============================================================================
# Failure Classifier
# ============================================================================

class FailureClassifier:
    """실패 유형 분류"""

    RULES = {
        "syntax_error": ["syntax error", "parsererror", "parse error", "unexpected token"],
        "missing_env": ["cannot find path", "connection refused", "not found", "invalid uri"],
        "caldera_constraint": ["variable is not defined", "undefined variable", "cannot find variable"],
        "dependency_error": ["access is denied", "access denied", "requires elevation", "privilege", "unauthorized"],
        "unrecoverable": ["not recognized as cmdlet", "command not found", "is not installed"]
    }

    def classify(self, stderr: str, stdout: str) -> FailureType:
        """실패 유형 분류"""
        error_text = (stderr + "\n" + stdout).lower()

        for rule_key, keywords in self.RULES.items():
            if any(keyword in error_text for keyword in keywords):
                return FailureType(rule_key)

        return FailureType.UNRECOVERABLE


# ============================================================================
# LLM Ability Fixer
# ============================================================================

class AbilityFixer:
    """LLM 기반 Ability 수정"""

    FIX_STRATEGIES = {
        FailureType.SYNTAX_ERROR: """
[Fix Strategy: SYNTAX_ERROR]
- PowerShell 5.1 문법 확인
- 변수 선언 검증
- 특수문자 이스케이프
- 따옴표 사용 수정
""",
        FailureType.MISSING_ENV: """
[Fix Strategy: MISSING_ENV]
- 환경 설명의 실제 값으로 플레이스홀더 교체
- IP, URL, 자격증명을 환경 설명 기준으로 수정
- 경로 존재 여부 확인
""",
        FailureType.CALDERA_CONSTRAINT: """
[Fix Strategy: CALDERA_CONSTRAINT]
- 이전 Ability 변수 의존성 제거
- 명령어를 완전히 자체 포함형으로 수정
- 값을 하드코딩하거나 재계산
""",
        FailureType.DEPENDENCY_ERROR: """
[Fix Strategy: DEPENDENCY_ERROR]
- 권한 상승 필요 여부 확인
- 권한 문제 에러 핸들링 추가
- 높은 권한이 필요없는 대체 방법 사용
""",
        FailureType.UNRECOVERABLE: """
[Fix Strategy: UNRECOVERABLE]
- Windows/PowerShell 기본 cmdlet만 사용
- 외부 도구 의존 제거
- 네이티브 대안으로 교체
"""
    }

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=get_anthropic_api_key())
        self.model = get_claude_model()

    def fix_ability(
        self,
        failed: FailedAbility,
        original_ability: Dict,
        env_description: str
    ) -> Tuple[str, bool]:
        """
        실패한 Ability를 LLM으로 수정

        Returns:
            Tuple[str, bool]: (수정된 명령어, 성공 여부)
        """
        prompt = self._build_prompt(failed, original_ability, env_description)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text
            fixed_command = self._extract_command(text)

            return fixed_command, True

        except Exception as e:
            print(f"    [ERROR] LLM 호출 실패: {e}")
            return "", False

    def _build_prompt(
        self,
        failed: FailedAbility,
        original_ability: Dict,
        env_description: str
    ) -> str:
        """LLM 프롬프트 구성"""

        original_cmd = original_ability.get('executors', [{}])[0].get('command', '')
        strategy = self.FIX_STRATEGIES.get(failed.failure_type, "")

        return f"""당신은 Caldera Ability 수정 전문가입니다.
실패한 Ability의 명령어를 분석하고 수정해야 합니다.

═══════════════════════════════════════════════════════════════════
[실패한 Ability 정보]
═══════════════════════════════════════════════════════════════════
- ID: {failed.ability_id}
- 이름: {failed.ability_name}
- Tactic: {failed.tactic}
- Technique: {failed.technique_id} ({failed.technique_name})

[원본 명령어]
```powershell
{original_cmd}
```

═══════════════════════════════════════════════════════════════════
[실행 결과 - 실패]
═══════════════════════════════════════════════════════════════════
- Exit Code: {failed.exit_code}

[stderr]:
```
{failed.stderr[:1000] if failed.stderr else "(없음)"}
```

[stdout]:
```
{failed.stdout[:1000] if failed.stdout else "(없음)"}
```

═══════════════════════════════════════════════════════════════════
[실패 원인 분류]: {failed.failure_type.value}
═══════════════════════════════════════════════════════════════════
{strategy}

═══════════════════════════════════════════════════════════════════
[환경 설명]
═══════════════════════════════════════════════════════════════════
{env_description}

═══════════════════════════════════════════════════════════════════
[중요 규칙]
═══════════════════════════════════════════════════════════════════
1. 각 Ability는 독립적인 PowerShell 프로세스에서 실행됨 - 변수 공유 없음
2. 환경 설명의 실제 값을 사용할 것
3. PowerShell 5.1 호환성 유지
4. 수정된 명령어만 출력 (설명 불필요)

수정된 PowerShell 명령어를 생성하세요:
```powershell
"""

    def _extract_command(self, text: str) -> str:
        """LLM 응답에서 명령어 추출"""
        match = re.search(r'```(?:powershell)?\s*(.*?)\s*```', text, re.DOTALL)
        command = match.group(1).strip() if match else text.strip()

        # Caldera는 줄바꿈을 공백으로 변환하므로, 줄바꿈을 세미콜론으로 변환
        command = self._normalize_command(command)
        return command

    def _normalize_command(self, command: str) -> str:
        """
        멀티라인 명령어를 Caldera 호환 단일 라인으로 변환

        Caldera는 명령어의 줄바꿈을 공백으로 변환하여 실행하므로,
        PowerShell 구문 에러 방지를 위해 줄바꿈을 세미콜론으로 변환
        """
        lines = command.split('\n')
        normalized_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 이미 세미콜론으로 끝나거나, 블록 시작/끝이면 그대로
            if stripped.endswith((';', '{', '}')):
                normalized_lines.append(stripped)
            # 주석은 그대로 (하지만 단일 라인에서는 문제될 수 있음)
            elif stripped.startswith('#'):
                continue  # 주석 제거
            else:
                normalized_lines.append(stripped + ';')

        # 마지막 불필요한 세미콜론 정리
        result = ' '.join(normalized_lines)
        # };} 같은 패턴 정리
        result = re.sub(r';\s*}', ' }', result)
        # 연속 세미콜론 정리
        result = re.sub(r';+', ';', result)
        # 마지막 세미콜론 제거
        result = result.rstrip(';')

        return result


# ============================================================================
# Offline Corrector (메인 엔진)
# ============================================================================

class OfflineCorrector:
    """오프라인 Self-Correcting 엔진"""

    def __init__(self):
        self.classifier = FailureClassifier()
        self.fixer = AbilityFixer()

    def run(
        self,
        abilities_file: str,
        operation_report_file: str,
        env_description_file: str,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        Self-Correcting 실행

        Args:
            abilities_file: abilities.yml 파일 경로
            operation_report_file: Operation Report JSON 파일 경로
            env_description_file: 환경 설명 파일 경로
            output_dir: 출력 디렉토리 (None이면 원본 abilities.yml 위치에 저장)

        Returns:
            수정 결과 리포트
        """
        print("=" * 70)
        print("M7: Offline Self-Correcting Engine")
        print("=" * 70)

        # 1. 데이터 로드
        abilities = self._load_yaml(abilities_file)
        env_description = Path(env_description_file).read_text(encoding='utf-8')

        with open(operation_report_file, 'r', encoding='utf-8') as f:
            operation_report = json.load(f)

        print(f"\n[로드 완료] {len(abilities)} abilities")

        # Operation 이름 추출 (새 양식: operation_metadata.name)
        op_name = operation_report.get('operation_metadata', {}).get('name', 'Unknown')
        print(f"[로드 완료] Operation: {op_name}")

        # 2. 실패한 Ability 추출
        failed_abilities = self._extract_failed_abilities(operation_report)
        stats = self._calculate_stats(operation_report)

        print(f"[통계] 전체: {stats['total']}, 성공: {stats['success']}, 실패: {stats['failed']}")

        if not failed_abilities:
            print("\n[완료] 수정이 필요한 실패 ability가 없습니다!")
            return {"corrections": [], "summary": {"total_failed": 0, "corrected": 0, "skipped": 0}}

        # 3. Ability 매핑 생성
        abilities_map = {a['ability_id']: a for a in abilities}

        # 4. 각 실패한 Ability 처리
        print(f"\n[수정 단계] {len(failed_abilities)}개 실패 처리")

        correction_results = []
        modified_ids = set()

        for failed in failed_abilities:
            print(f"\n  [{failed.ability_name}]")

            # 4-1. 실패 유형 분류
            failed.failure_type = self.classifier.classify(failed.stderr, failed.stdout)
            print(f"    실패 유형: {failed.failure_type.value}")

            # 4-2. UNRECOVERABLE이면 스킵
            if failed.failure_type == FailureType.UNRECOVERABLE:
                print(f"    [스킵] 복구 불가능한 에러")
                correction_results.append(CorrectionResult(
                    ability_id=failed.ability_id,
                    ability_name=failed.ability_name,
                    original_command=failed.command,
                    fixed_command="",
                    failure_type=failed.failure_type,
                    success=False,
                    reason="복구 불가능한 에러 유형"
                ))
                continue

            # 4-3. 원본 Ability 조회
            original = abilities_map.get(failed.ability_id)
            if not original:
                print(f"    [경고] 원본 ability를 찾을 수 없음")
                continue

            # 4-4. LLM으로 수정
            print(f"    LLM 수정 중...")
            fixed_cmd, success = self.fixer.fix_ability(failed, original, env_description)

            if success and fixed_cmd:
                # abilities 리스트에서 해당 ability의 command 직접 수정
                original['executors'][0]['command'] = fixed_cmd
                modified_ids.add(failed.ability_id)
                print(f"    [완료] {fixed_cmd[:60]}...")

                correction_results.append(CorrectionResult(
                    ability_id=failed.ability_id,
                    ability_name=failed.ability_name,
                    original_command=failed.command,
                    fixed_command=fixed_cmd,
                    failure_type=failed.failure_type,
                    success=True
                ))
            else:
                correction_results.append(CorrectionResult(
                    ability_id=failed.ability_id,
                    ability_name=failed.ability_name,
                    original_command=failed.command,
                    fixed_command="",
                    failure_type=failed.failure_type,
                    success=False,
                    reason="LLM 수정 실패"
                ))

        # 5. 수정된 abilities.yml 저장
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(abilities_file).parent

        output_path.mkdir(parents=True, exist_ok=True)

        # abilities.yml 저장 (수정된 내용 포함)
        abilities_output = output_path / "abilities.yml"
        with open(abilities_output, 'w', encoding='utf-8') as f:
            yaml.dump(abilities, f, allow_unicode=True, sort_keys=False)

        print(f"\n[저장] abilities.yml: {abilities_output}")

        # 6. 수정 리포트 생성 및 저장
        report = self._generate_report(operation_report, stats, correction_results)

        report_output = output_path / "correction_report.json"
        with open(report_output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"[저장] correction_report.json: {report_output}")

        # 7. 결과 요약
        corrected = len([r for r in correction_results if r.success])
        skipped = len([r for r in correction_results if not r.success])

        print("\n" + "=" * 70)
        print(f"[결과] {corrected}/{len(failed_abilities)} abilities 수정 완료")
        if modified_ids:
            print(f"[수정됨] {', '.join(list(modified_ids)[:3])}{'...' if len(modified_ids) > 3 else ''}")
        print("=" * 70)

        return report

    def _load_yaml(self, file_path: str) -> List[Dict]:
        """YAML 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _extract_failed_abilities(self, operation_report: Dict) -> List[FailedAbility]:
        """
        Operation Report에서 실패한 Ability 추출

        여러 Agent에서 실행된 경우:
        - 모든 Agent에서 실패해야 진짜 실패로 판단
        - 하나라도 성공하면 성공으로 간주 (권한 있는 Agent에서 성공한 것)
        """
        from collections import defaultdict

        results = operation_report.get('results', [])

        # 1. ability_id별로 모든 실행 결과 그룹핑
        by_ability = defaultdict(list)
        for result in results:
            by_ability[result.get('ability_id', '')].append(result)

        # 2. 모든 Agent에서 실패한 ability만 추출
        failed_list = []
        for ability_id, runs in by_ability.items():
            # 하나라도 성공(status == 0)이면 스킵
            if any(r.get('status', 0) == 0 for r in runs):
                continue

            # 모든 Agent에서 실패 → 첫 번째 실패 결과 사용
            result = runs[0]

            exit_code = result.get('exit_code', 1)
            if isinstance(exit_code, str):
                try:
                    exit_code = int(exit_code)
                except ValueError:
                    exit_code = 1

            failed_list.append(FailedAbility(
                ability_id=ability_id,
                ability_name=result.get('ability_name', ''),
                command=result.get('command', ''),
                exit_code=exit_code,
                stdout=result.get('stdout', ''),
                stderr=result.get('stderr', ''),
                tactic=result.get('tactic', ''),
                technique_id=result.get('technique_id', ''),
                technique_name=result.get('technique_name', '')
            ))

        return failed_list

    def _calculate_stats(self, operation_report: Dict) -> Dict:
        """Operation 통계 계산 (새 양식: statistics 또는 results에서 계산)"""
        # 새 양식은 statistics 필드가 있음
        if 'statistics' in operation_report:
            stats = operation_report['statistics']
            return {
                "total": stats.get('total_abilities', 0),
                "success": stats.get('success', 0),
                "failed": stats.get('failed', 0)
            }

        # statistics가 없으면 results에서 계산
        results = operation_report.get('results', [])
        total = len(results)
        success = sum(1 for r in results if r.get('status', 0) == 0)
        failed = total - success

        return {"total": total, "success": success, "failed": failed}

    def _generate_report(
        self,
        operation_report: Dict,
        stats: Dict,
        results: List[CorrectionResult]
    ) -> Dict:
        """수정 리포트 생성"""
        # Operation 이름 추출 (새 양식)
        op_name = operation_report.get('operation_metadata', {}).get('name', '')

        return {
            "timestamp": datetime.now().isoformat(),
            "operation": {
                "name": op_name,
                "stats": stats
            },
            "corrections": [
                {
                    "ability_id": r.ability_id,
                    "ability_name": r.ability_name,
                    "failure_type": r.failure_type.value,
                    "success": r.success,
                    "reason": r.reason,
                    "original_command": r.original_command,
                    "fixed_command": r.fixed_command if r.fixed_command else ""
                }
                for r in results
            ],
            "summary": {
                "total_failed": len(results),
                "corrected": len([r for r in results if r.success]),
                "skipped": len([r for r in results if not r.success])
            }
        }


# ============================================================================
# CLI Entry Point
# ============================================================================

def find_abilities_by_adversary_id(adversary_id: str, base_dir: str = "data/processed") -> Optional[str]:
    """
    adversary_id에서 버전 ID를 추출하여 abilities.yml 경로 찾기

    예: kisa-ttp-adversary-20251203_142900 -> data/processed/20251203_142900/caldera/abilities.yml
    """
    import re

    # adversary_id에서 버전 ID 추출 (kisa-ttp-adversary-{version_id})
    match = re.match(r'kisa-ttp-adversary-(.+)', adversary_id)
    if not match:
        return None

    version_id = match.group(1)

    # abilities.yml 경로 구성
    abilities_path = Path(base_dir) / version_id / "caldera" / "abilities.yml"

    if abilities_path.exists():
        return str(abilities_path)

    return None


def main():
    """CLI 진입점"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="M7: Offline Self-Correcting Engine",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
예시:
  # Report에서 adversary_id로 자동 탐색
  python -m modules.module7_self_correcting --report report.json --env environment_description.md

  # abilities 경로 직접 지정
  python -m modules.module7_self_correcting --abilities data/processed/20251203/caldera/abilities.yml --report report.json --env environment_description.md
"""
    )

    parser.add_argument(
        "--abilities",
        type=str,
        default=None,
        help="abilities.yml 파일 경로 (미지정 시 Report의 adversary_id로 자동 탐색)"
    )

    parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="Operation Report JSON 파일 경로"
    )

    parser.add_argument(
        "--env",
        type=str,
        required=True,
        help="환경 설명 파일 경로 (*.md)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 디렉토리 (기본: abilities.yml과 같은 위치)"
    )

    args = parser.parse_args()

    # Report 파일 확인
    if not Path(args.report).exists():
        print(f"[ERROR] Operation Report를 찾을 수 없음: {args.report}")
        sys.exit(1)

    # abilities 경로 결정
    abilities_file = args.abilities

    if not abilities_file:
        # Report에서 adversary_id 추출하여 자동 탐색
        with open(args.report, 'r', encoding='utf-8') as f:
            report = json.load(f)

        adversary_id = report.get('operation_metadata', {}).get('adversary_id', '')

        if adversary_id:
            print(f"[INFO] Report의 adversary_id: {adversary_id}")
            abilities_file = find_abilities_by_adversary_id(adversary_id)

            if abilities_file:
                print(f"[INFO] abilities.yml 자동 탐색 성공: {abilities_file}")
            else:
                print(f"[ERROR] adversary_id '{adversary_id}'에서 abilities.yml을 찾을 수 없음")
                print(f"[HINT] --abilities 옵션으로 직접 경로를 지정하세요")
                sys.exit(1)
        else:
            print(f"[ERROR] Report에 adversary_id가 없고 --abilities도 지정되지 않음")
            sys.exit(1)

    # 파일 존재 확인
    for path, name in [(abilities_file, "abilities.yml"),
                       (args.env, "환경 설명 파일")]:
        if not Path(path).exists():
            print(f"[ERROR] {name}을(를) 찾을 수 없음: {path}")
            sys.exit(1)

    # 실행
    try:
        corrector = OfflineCorrector()
        corrector.run(
            abilities_file=abilities_file,
            operation_report_file=args.report,
            env_description_file=args.env,
            output_dir=args.output
        )
    except KeyboardInterrupt:
        print("\n[중단됨] 사용자에 의해 취소됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
