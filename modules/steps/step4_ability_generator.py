"""
Step 4: Caldera Ability Generator (전처리 + 최소 AI)

전략:
1. AI는 command 생성만 담당 (토큰 비용 최소화)
2. executor 구조, payloads 추출, singleton 등은 전처리로 처리
3. 최종 Caldera API 형식으로 변환
"""

import os
import yaml
import uuid
import re
from typing import Dict, List, Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.ai.factory import get_llm_client
from modules.prompts.manager import PromptManager


class AbilityGenerator:
    def __init__(self):
        self.llm = get_llm_client()
        self.prompt_manager = PromptManager()

        # UUID namespace for deterministic UUID generation
        self.uuid_namespace = uuid.UUID('12345678-1234-5678-1234-567812345678')

        # Node type → Tactic 매핑
        self.type_to_tactic = {
            'initial_access': 'initial-access',
            'execution': 'execution',
            'persistence': 'persistence',
            'privilege_escalation': 'privilege-escalation',
            'defense_evasion': 'defense-evasion',
            'credential_access': 'credential-access',
            'discovery': 'discovery',
            'lateral_movement': 'lateral-movement',
            'collection': 'collection',
            'command_and_control': 'command-and-control',
            'exfiltration': 'exfiltration',
            'impact': 'impact'
        }

        # 생성 실패 추적
        self.failed_nodes = []

    def generate_abilities(self, input_file: str, output_dir: str):
        """Caldera Ability 생성 (전처리 + 최소 AI)"""
        print("\n[Step 4] Caldera Ability 생성 시작...")

        # Load concrete flow data from Step 3
        with open(input_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Metadata에서 Caldera payload 목록 가져오기
        metadata = data.get('metadata', {})
        self.known_payloads = metadata.get('caldera_payloads', [])

        if self.known_payloads:
            print(f"  [INFO] Caldera payloads: {', '.join(self.known_payloads)}")
        else:
            print(f"  [WARNING] No Caldera payloads found in metadata")

        # concrete_flow.nodes 구조 처리
        if 'concrete_flow' in data:
            concrete_flow = data['concrete_flow']
            nodes = concrete_flow.get('nodes', [])
            execution_order = concrete_flow.get('execution_order', [])
        else:
            nodes = data.get('nodes', [])
            execution_order = data.get('execution_order', [])

        print(f"  [INFO] {len(nodes)}개 노드 처리 중...")

        # execution_order 확인
        if execution_order:
            print(f"  [INFO] execution_order 사용: {len(execution_order)}개 노드")
        else:
            print(f"  [WARNING] execution_order 없음, nodes 순서 사용")
            execution_order = [node['id'] for node in nodes]

        # Ability 생성 (execution_order 순서대로)
        abilities = []
        node_dict = {node['id']: node for node in nodes}

        for node_id in execution_order:
            node = node_dict.get(node_id)
            if not node:
                print(f"  [WARNING] Node {node_id} not found in nodes")
                continue

            ability = self._create_ability(node)
            if ability:
                abilities.append(ability)

        print(f"  [OK] {len(abilities)}개 Ability 생성 완료")

        # output_dir에서 버전 ID 추출 (예: data/processed/20251203_142900/caldera -> 20251203_142900)
        version_id = self._extract_version_id(output_dir)
        if version_id:
            print(f"  [INFO] 버전 ID: {version_id}")

        # Adversary Profile 생성 (단일)
        adversaries = self._create_adversary_profiles(abilities, nodes, version_id)

        # 결과 저장
        os.makedirs(output_dir, exist_ok=True)

        abilities_file = f"{output_dir}/abilities.yml"
        with open(abilities_file, 'w', encoding='utf-8') as f:
            yaml.dump(abilities, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        adversaries_file = f"{output_dir}/adversaries.yml"
        with open(adversaries_file, 'w', encoding='utf-8') as f:
            yaml.dump(adversaries, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Caldera Ability 생성 완료")
        print(f"  - Abilities: {abilities_file}")
        print(f"  - Adversaries: {adversaries_file}")

        self._print_summary(abilities, adversaries)

    def _create_ability(self, node: Dict) -> Optional[Dict]:
        """단일 Ability 생성 (전처리 방식)"""
        node_id = node['id']
        node_name = node['name']
        node_type = node.get('type', 'execution')

        # Get technique (auto-selected in Step 3)
        technique = node.get('technique', {})
        technique_id = technique.get('id', 'T0000')
        technique_name = technique.get('name', 'Unknown')

        # Get node details
        description = node.get('description', f"Execute {node_name}")
        environment_specific = node.get('environment_specific', {})

        print(f"  [생성 중] {node_id}. {node_name} ({technique_id})")

        # 1. Command 추출 (Step 3에서 생성된 것 사용)
        if 'commands' in environment_specific and environment_specific['commands']:
            existing_commands = environment_specific['commands']
            if isinstance(existing_commands, list):
                command = '\n'.join(existing_commands)
            else:
                command = existing_commands

            print(f"    [OK] Command from Step 3: {command[:80]}..." if len(command) > 80 else f"    [OK] Command: {command}")
        else:
            print(f"  [WARNING] {node_name} No commands found in Step 3 - skipping")
            self.failed_nodes.append({'id': node_id, 'name': node_name, 'reason': 'No commands in Step 3'})
            return None

        # 2. 전처리: Payload 파일 추출
        payloads = self._extract_payloads_from_environment(environment_specific)
        if payloads:
            print(f"    [INFO] Payloads: {', '.join(payloads)}")

        # 3. 전처리: Upload 파일 추출 (exfiltration 타입일 때)
        uploads = self._extract_uploads_from_type(node_type, environment_specific)
        if uploads:
            print(f"    [INFO] Uploads: {', '.join(uploads)}")

        # 4. 전처리: Executor 구조 생성 (API 테스트 결과 기반)
        executor = {
            "name": "psh",  # PowerShell 고정
            "platform": "windows",
            "command": command,
            "timeout": 120 if "privilege" in node_type else 20,
            "payloads": payloads,
            "uploads": uploads,
            "cleanup": []  # 디버깅을 위해 비워둠
        }

        # 5. 전처리: Ability 구조 생성
        ability_id = self._generate_uuid(node_id, node_name)
        # Get tactic from node
        tactic = node.get('tactic', 'execution')

        ability = {
            "ability_id": ability_id,
            "name": node_name,
            "description": description[:200] if len(description) > 200 else description,
            "tactic": tactic,
            "technique_id": technique_id,
            "technique_name": technique_name,
            "singleton": True,  # 모든 ability에 singleton 적용
            "executors": [executor]
        }

        return ability

    def _validate_and_improve_command(self, node: Dict, existing_command: str) -> Optional[str]:
        """기존 command를 AI로 검증/개선 (Caldera 최적화)"""
        node_name = node['name']
        environment_specific = node.get('environment_specific', {})
        payloads = self._extract_payloads_from_environment(environment_specific)

        # Payload 가이드
        payload_guide = ""
        if payloads:
            payload_guide = f"""
**Caldera Payloads (already in agent's working directory):**
{', '.join(payloads)}
- Use .\\filename directly
- DO NOT download again
"""

        prompt = self.prompt_manager.render(
            "step4_validate_command.yaml",
            node_name=node_name,
            existing_command=existing_command,
            payload_guide=payload_guide
        )

        try:
            response_text = self.llm.generate_text(prompt=prompt, max_tokens=500)

            command_text = response_text.strip()
            command_text = command_text.replace('```powershell', '').replace('```cmd', '').replace('```', '').strip()

            # 여전히 거부하면 원본 사용
            if "can't help" in command_text.lower() or "unauthorized" in command_text.lower():
                print(f"    [WARNING] AI refused, using original command")
                return existing_command

            return command_text

        except Exception as e:
            print(f"    [WARNING] Validation failed: {e}, using original")
            return existing_command

    def _generate_command_only(self, node: Dict) -> Optional[str]:
        """AI로 command만 생성 (최소 비용)"""
        node_name = node['name']
        description = node.get('description', '')
        environment_specific = node.get('environment_specific', {})

        # Payload 추출
        payloads = self._extract_payloads_from_environment(environment_specific)

        # environment_specific을 간단한 텍스트로 변환
        env_text = yaml.dump(environment_specific, allow_unicode=True, sort_keys=False) if environment_specific else "No specific environment details"

        # Payload 가이드
        payload_guide = ""
        if payloads:
            payload_guide = f"""
**IMPORTANT - Caldera Payloads (already in agent's working directory):**
{', '.join(payloads)}

**Payload Usage Rules:**
1. Files are ALREADY downloaded by Caldera - use .\\filename directly
2. Example: Copy-Item .\\cmd.asp C:\\inetpub\\wwwroot\\uploads\\cmd.asp
3. DO NOT use Invoke-WebRequest, certutil, or any download commands
4. DO NOT use $env:TEMP or other variables - use current directory (.\\)
5. Keep commands simple - just use the file that's already there
"""

        # Get tactic and technique info
        tactic = node.get('tactic', 'execution')
        technique = node.get('technique', {})
        technique_id = technique.get('id', 'T0000')
        technique_name = technique.get('name', 'Unknown')

        prompt = self.prompt_manager.render(
            "step4_generate_command.yaml",
            node_name=node_name,
            description=description,
            tactic=tactic,
            technique_id=technique_id,
            technique_name=technique_name,
            env_text=env_text,
            payload_guide=payload_guide
        )

        try:
            response_text = self.llm.generate_text(prompt=prompt, max_tokens=500)

            command_text = response_text.strip()
            # 코드 블록 제거
            command_text = command_text.replace('```powershell', '').replace('```cmd', '').replace('```', '').strip()

            return command_text

        except Exception as e:
            print(f"  [WARNING] AI 생성 실패: {e}")
            return None

    def _extract_payloads_from_environment(self, environment_specific: Dict) -> List[str]:
        """Environment에서 payload 직접 추출 (전처리)"""
        payloads = []

        # 1. environment_specific에서 payload/payloads 필드 직접 확인
        if 'payload' in environment_specific:
            payload_value = environment_specific['payload']
            if isinstance(payload_value, str):
                payloads.append(payload_value)
            elif isinstance(payload_value, list):
                payloads.extend(payload_value)

        if 'payloads' in environment_specific:
            payload_list = environment_specific['payloads']
            if isinstance(payload_list, list):
                payloads.extend(payload_list)

        # 2. 중복 제거
        payloads = list(set(payloads))

        return payloads

    def _extract_uploads_from_type(self, node_type: str, environment_specific: Dict) -> List[str]:
        """노드 타입이 exfiltration이면 upload 경로 추출"""
        if 'exfiltration' not in node_type and 'collection' not in node_type:
            return []

        # 수집된 데이터 압축 파일 경로
        uploads = []

        # environment_specific에서 output 경로 찾기
        env_str = yaml.dump(environment_specific, allow_unicode=True)

        # .zip 파일 경로 추출
        zip_patterns = re.findall(r'([A-Za-z]:\\[^\s]+\.zip)', env_str, re.IGNORECASE)
        for path in zip_patterns:
            if path not in uploads:
                uploads.append(path)

        # 기본 경로 (없으면)
        if not uploads:
            uploads.append("C:\\Windows\\Temp\\exfil.zip")

        return uploads

    def _create_adversary_profiles(self, abilities: List[Dict], nodes: List[Dict], version_id: str = "") -> List[Dict]:
        """Adversary Profile 단일 생성

        Args:
            abilities: Ability 목록
            nodes: 노드 목록
            version_id: 버전 식별자 (폴더명에서 추출, 예: "20251203_142900")
        """
        # 모든 ability를 순서대로 포함
        ability_ids = [ability['ability_id'] for ability in abilities]

        # version_id가 있으면 고유한 ID/이름 생성
        if version_id:
            adversary_id = f"kisa-ttp-adversary-{version_id}"
            adversary_name = f"KISA TTP Adversary ({version_id})"
        else:
            adversary_id = "kisa-ttp-adversary"
            adversary_name = "KISA TTP Adversary"

        adversaries = [{
            "adversary_id": adversary_id,
            "name": adversary_name,
            "description": "Auto-generated adversary profile from KISA TTP report",
            "atomic_ordering": ability_ids
        }]

        return adversaries

    def _extract_version_id(self, output_dir: str) -> str:
        """output_dir 경로에서 버전 ID 추출

        예: data/processed/20251203_142900/caldera -> 20251203_142900
            data/processed/TTPS1_20251203/caldera -> TTPS1_20251203
        """
        import re
        from pathlib import Path

        path = Path(output_dir)

        # caldera 폴더면 부모로 이동
        if path.name == 'caldera':
            path = path.parent

        # data/processed/ 하위의 버전 폴더명 추출
        parts = path.parts
        for i, part in enumerate(parts):
            if part == 'processed' and i + 1 < len(parts):
                return parts[i + 1]

        # processed가 없으면 마지막 폴더명 사용
        return path.name if path.name else ""

    def _generate_uuid(self, node_id: str, node_name: str) -> str:
        """Deterministic UUID 생성"""
        unique_string = f"kisa_ttp_node_{node_id}_{node_name}"
        return str(uuid.uuid5(self.uuid_namespace, unique_string))

    def _print_summary(self, abilities: List[Dict], adversaries: List[Dict]):
        """생성 요약 출력"""
        print("\n" + "="*70)
        print("Caldera Ability 생성 요약:")
        print(f"  - 전체 Ability: {len(abilities)}개")
        print(f"  - Adversary Profile: {adversaries[0]['name']} ({len(adversaries[0]['atomic_ordering'])}개 ability)")

        if self.failed_nodes:
            print(f"\n[WARNING] 생성 실패 노드: {len(self.failed_nodes)}개")
            for failed in self.failed_nodes:
                print(f"  - [{failed['id']}] {failed['name']}: {failed['reason']}")

        # Tactic 분포
        tactics = {}
        for ability in abilities:
            tactic = ability.get('tactic', 'unknown')
            tactics[tactic] = tactics.get(tactic, 0) + 1

        print("\nTactic 분포:")
        for tactic, count in sorted(tactics.items()):
            print(f"  - {tactic}: {count}개")

        print("\n주요 Abilities (최대 5개):")
        for ability in abilities[:5]:
            print(f"  - [{ability['ability_id'][:8]}...] {ability['name']}")
            print(f"    Tactic: {ability['tactic']} | Technique: {ability['technique_id']} | Singleton: {ability.get('singleton', False)}")

        print("="*70)


def main():
    """Main entry point"""
    import sys
    if len(sys.argv) < 3:
        print("Usage: python step4_ability_generator.py <step3.yml> <output_dir>")
        sys.exit(1)

    generator = AbilityGenerator()
    generator.generate_abilities(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
