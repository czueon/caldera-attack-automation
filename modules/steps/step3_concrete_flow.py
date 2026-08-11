"""
Module 3: Concrete Attack Flow Generation (WITHOUT MITRE Injection)
Combine abstract flow + environment description (MD) → concrete attack flow (Kill Chain)
AI generates technique_id/name from internal knowledge (no MITRE data in prompt)

실험용: MITRE 데이터 미주입 버전
"""

import yaml
import os
import json
import re
import time
from typing import Dict, List, Set
import sys
from pathlib import Path
from datetime import datetime

# 모듈 패키지를 정상 인식하도록 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.ai.factory import get_llm_client
from modules.prompts.manager import PromptManager
from modules.core.knowledge_base import KnowledgeBase
from modules.core.metrics import get_metrics_tracker


class ConcreteFlowGenerator:
    def __init__(self, use_knowledge_base: bool = True):
        """
        Args:
            use_knowledge_base: False면 stage2에서 KB 예시 조회를 건너뛰고 LLM 자체 지식으로만
                명령어를 생성한다 (RQ1 ablation "without knowledge base" 조건용).
        """
        self.llm = get_llm_client()
        self.prompt_manager = PromptManager()
        self.use_knowledge_base = use_knowledge_base
        self.kb = KnowledgeBase() if use_knowledge_base else None
        self.mitre_techniques: Dict[str, Dict] = {}  # OS별 캐시 (검증용)
        self.valid_technique_ids: Dict[str, Set[str]] = {}  # OS별 유효 ID (검증용)

    def _extract_os_from_environment(self, env_description: str) -> str:
        """Extract OS type from environment description"""
        os_match = re.search(r'OS:\s*(Windows|Linux|macOS|Ubuntu|CentOS|Debian)[^\n]*', env_description, re.IGNORECASE)
        if os_match:
            os_str = os_match.group(1).lower()
            if 'windows' in os_str:
                return 'windows'
            elif os_str in ['linux', 'ubuntu', 'centos', 'debian']:
                return 'linux'
            elif 'macos' in os_str or 'mac' in os_str:
                return 'macos'

        # OS 정보 미감지 시 중단
        print("\n" + "="*70)
        print("[ERROR] OS 정보를 환경설명 파일에서 찾을 수 없습니다.")
        print("="*70)
        print("\n환경설명 파일에 다음 형식으로 OS를 명시해주세요:\n")
        print("  ## 공통 환경 정보")
        print("  - OS: Windows 10")
        print("  또는")
        print("  - OS: Ubuntu 22.04")
        print("  또는")
        print("  - OS: macOS Ventura")
        print("\n" + "="*70)
        raise ValueError("OS 정보가 환경설명에 명시되어 있지 않습니다. 환경설명 파일을 수정해주세요.")

    def _load_mitre_for_validation(self, os_type: str = 'windows'):
        """Load pre-parsed MITRE data for validation"""
        if os_type in self.mitre_techniques:
            return

        mitre_dir = PROJECT_ROOT / "data" / "mitre"
        mitre_path = mitre_dir / "v15.1.json"

        if mitre_path.exists():
            try:
                with open(mitre_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                version = data.get('version', 'unknown')
                techniques = data.get('platforms', {}).get(os_type, {})

                self.mitre_techniques[os_type] = techniques
                self.valid_technique_ids[os_type] = set(techniques.keys())

                print(f"  [OK] MITRE v{version} loaded ({len(techniques)} {os_type} techniques)")
            except Exception as e:
                print(f"  [WARNING] Failed to load MITRE data: {e}")
                self.mitre_techniques[os_type] = {}
        else:
            print(f"  [WARNING] MITRE v15.1 data not found at {mitre_path}")
            self.mitre_techniques[os_type] = {}

    def _load_abstract_flow_and_meta(self, abstract_flow_file: str, version_id: str = None):
        """step2 산출물에서 abstract_flow, pdf_name, version_id를 뽑아낸다."""
        with open(abstract_flow_file, 'r', encoding='utf-8') as f:
            abstract_data = yaml.safe_load(f)

        abstract_flow = abstract_data.get('abstract_flow', {})
        metadata = abstract_data.get('metadata', {})

        pdf_name = metadata.get('pdf_name')
        if not pdf_name:
            pdf_name = Path(abstract_flow_file).stem.replace("_step2", "")
            if Path(abstract_flow_file).parents:
                pdf_name = Path(abstract_flow_file).parent.parent.name or pdf_name

        derived_version = (
            version_id
            or metadata.get('version_id')
            or Path(abstract_flow_file).parent.name
        )
        version_id = derived_version or datetime.now().strftime("%Y%m%d_%H%M%S")

        return abstract_flow, pdf_name, version_id

    def _save_step3_output(self, output_file: str, pdf_name: str, version_id: str, os_type: str,
                            concrete_flow: Dict, abstract_flow_file: str, environment_md_file: str,
                            stage: str):
        """stage: 'stage1_only'(기법 선택만) 또는 'complete'(명령어까지 생성 완료)."""
        output_data = {
            'metadata': {
                'sources': {
                    'abstract_flow': abstract_flow_file,
                    'environment': environment_md_file
                },
                'pdf_name': pdf_name,
                'version_id': version_id,
                'step': 3,
                'stage': stage,
                'description': 'Concrete attack flow - AI internal knowledge (NO MITRE injection)',
                'os_type': os_type,
                'experiment': 'without_mitre_injection'
            },
            'concrete_flow': concrete_flow
        }

        if output_file is None:
            output_file = Path("../../data/processed") / pdf_name / version_id / f"{pdf_name}_step3.yml"

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)

        return output_file

    def generate_stage1_only(self, abstract_flow_file: str,
                              environment_md_file: str,
                              output_file: str = None,
                              version_id: str = None):
        """Stage1(기법/tactic/environment_specific 선택)까지만 실행하고 저장. commands는 생성하지 않음.
        with_kb/without_kb처럼 Stage2 조건만 다르고 Stage1 결과는 동일해야 하는 경우, 이 결과를
        재사용하면 Stage1을 중복 생성하지 않고 Stage2(generate_concrete_flow의 stage1_file 인자)로
        바로 넘어갈 수 있다."""
        print("\n[Step 3] Stage1 only (technique selection, no commands)...")

        abstract_flow, pdf_name, version_id = self._load_abstract_flow_and_meta(abstract_flow_file, version_id)

        with open(environment_md_file, 'r', encoding='utf-8') as f:
            environment_description = f.read()

        print(f"  Abstract goals: {len(abstract_flow.get('attack_goals', []))}")
        os_type = self._extract_os_from_environment(environment_description)
        self._load_mitre_for_validation(os_type)

        concrete_flow = self._generate_flow(abstract_flow, environment_description, os_type)
        concrete_flow = self._validate_technique_ids(concrete_flow, os_type)

        output_file = self._save_step3_output(
            output_file, pdf_name, version_id, os_type, concrete_flow,
            abstract_flow_file, environment_md_file, stage='stage1_only'
        )

        print(f"[SUCCESS] Stage1 완료 -> {output_file}")
        print(f"  - PDF: {pdf_name}")
        print(f"  - Version: {version_id}")

    def generate_concrete_flow(self, abstract_flow_file: str,
                              environment_md_file: str,
                              output_file: str = None,
                              version_id: str = None,
                              stage1_file: str = None):
        """Generate concrete attack flow by combining abstract flow + environment MD.

        stage1_file이 주어지면 stage1(기법 선택)을 새로 생성하지 않고 그 파일(generate_stage1_only의
        산출물)에서 concrete_flow를 읽어와 stage2(명령어 생성)부터 시작한다.
        """
        print("\n[Step 3] Concrete Attack Flow Generation started (NO MITRE INJECTION)...")

        abstract_flow, pdf_name, version_id = self._load_abstract_flow_and_meta(abstract_flow_file, version_id)

        # Read environment description (Markdown)
        with open(environment_md_file, 'r', encoding='utf-8') as f:
            environment_description = f.read()

        print(f"  Abstract goals: {len(abstract_flow.get('attack_goals', []))}")
        print(f"  Environment description: {len(environment_description)} characters")

        # Extract OS from environment
        os_type = self._extract_os_from_environment(environment_description)

        tracker = get_metrics_tracker()

        if stage1_file:
            print(f"  [Reusing stage1 result from {stage1_file}]")
            with open(stage1_file, 'r', encoding='utf-8') as f:
                stage1_data = yaml.safe_load(f)
            concrete_flow = stage1_data['concrete_flow']
        else:
            # Load MITRE data for validation only
            self._load_mitre_for_validation(os_type)

            # Stage 1: generate flow with technique selection (no commands yet)
            stage1_start = time.time()
            concrete_flow = self._generate_flow(abstract_flow, environment_description, os_type)
            if tracker:
                tracker.record_phase("step3_stage1_technique_selection", time.time() - stage1_start)

            # Validate AI-generated technique IDs
            concrete_flow = self._validate_technique_ids(concrete_flow, os_type)

        # Stage 2: generate one command per node (KB examples + predecessor outputs)
        stage2_start = time.time()
        concrete_flow = self._generate_commands(concrete_flow, environment_description, os_type)
        if tracker:
            tracker.record_phase("step3_stage2_command_generation", time.time() - stage2_start)

        output_file = self._save_step3_output(
            output_file, pdf_name, version_id, os_type, concrete_flow,
            abstract_flow_file, environment_md_file, stage='complete'
        )

        print(f"[SUCCESS] Concrete flow generation completed -> {output_file}")
        print(f"  - PDF: {pdf_name}")
        print(f"  - Version: {version_id}")
        self._print_summary(concrete_flow)

    def _generate_flow(self, abstract_flow: Dict, environment_description: str, os_type: str) -> Dict:
        """Generate concrete attack flow using LLM (NO MITRE data in prompt)"""
        print(f"  [Generating concrete attack flow ({os_type}) - AI internal knowledge...]")

        abstract_flow_yaml = yaml.dump(abstract_flow, allow_unicode=True)

        # NOTE: mitre_techniques NOT passed to prompt
        prompt = self.prompt_manager.render(
            "step3_generate_flow.yaml",
            abstract_flow=abstract_flow_yaml,
            environment_description=environment_description,
            os_type=os_type.capitalize()
        )

        MAX_RETRIES = 3
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    print(f"  [Retry {attempt}/{MAX_RETRIES}] Regenerating flow...")
                    retry_prompt = f"{prompt}\n\n[IMPORTANT] Previous attempt failed with error: {last_error}\nPlease generate valid YAML format without syntax errors."
                    response_text = self.llm.generate_text(prompt=retry_prompt, max_tokens=12000)
                else:
                    response_text = self.llm.generate_text(prompt=prompt, max_tokens=12000)

                yaml_text = self._extract_yaml(response_text)

                if not yaml_text or len(yaml_text.strip()) < 10:
                    raise ValueError("Extracted YAML is empty or too short")

                yaml_text = self._fix_backslashes(yaml_text)
                flow = yaml.safe_load(yaml_text)

                if not isinstance(flow, dict):
                    raise ValueError(f"Flow must be a dictionary, got {type(flow)}")

                if 'nodes' not in flow or not isinstance(flow.get('nodes'), list):
                    raise ValueError("Flow must contain 'nodes' as a list")

                if len(flow.get('nodes', [])) == 0:
                    raise ValueError("Flow must contain at least one node")

                print(f"  [OK] Generated {len(flow.get('nodes', []))} concrete steps")
                return flow

            except yaml.YAMLError as e:
                last_error = f"YAML parsing error: {str(e)}"
                print(f"  [ERROR] Attempt {attempt}/{MAX_RETRIES}: {last_error}")
                if attempt < MAX_RETRIES:
                    continue

            except (ValueError, KeyError, TypeError) as e:
                last_error = f"Structure validation error: {str(e)}"
                print(f"  [ERROR] Attempt {attempt}/{MAX_RETRIES}: {last_error}")
                if attempt < MAX_RETRIES:
                    continue

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                print(f"  [ERROR] Attempt {attempt}/{MAX_RETRIES}: {last_error}")
                if attempt < MAX_RETRIES:
                    continue

        raise RuntimeError(f"Failed to generate valid concrete flow after {MAX_RETRIES} attempts. Last error: {last_error}")

    def _validate_technique_ids(self, flow: Dict, os_type: str) -> Dict:
        """Validate AI-generated technique IDs (count valid/invalid)"""
        valid_ids = self.valid_technique_ids.get(os_type, set())
        if not valid_ids:
            print("  [WARNING] No valid technique IDs for validation, counting only")

        print("  [Validating AI-generated technique IDs...]")

        nodes = flow.get('nodes', [])
        valid_count = 0
        invalid_count = 0
        missing_count = 0

        for node in nodes:
            technique = node.get('technique', {})

            if not technique:
                node['technique'] = {'id': 'T0000', 'name': 'Unknown'}
                missing_count += 1
                continue

            tech_id = technique.get('id', '')

            if tech_id in valid_ids:
                valid_count += 1
            elif tech_id == 'T0000' or not tech_id:
                missing_count += 1
            else:
                # 조건 B에서는 invalid도 그대로 유지 (실험용)
                invalid_count += 1
                print(f"    [INFO] Unverified ID: {tech_id} for '{node.get('name', 'unknown')}'")

        total = valid_count + invalid_count + missing_count
        valid_rate = (valid_count / total * 100) if total > 0 else 0

        print(f"  [OK] Technique validation: {valid_count} valid ({valid_rate:.1f}%), {invalid_count} unverified, {missing_count} missing")
        return flow

    def _generate_commands(self, flow: Dict, environment_description: str, os_type: str) -> Dict:
        """Stage 2: generate one command per node, in execution order, using KB examples
        and preceding nodes' already-generated commands."""
        print("  [Generating commands per node (Stage 2)...]")

        nodes = flow.get('nodes', [])
        node_dict = {node['id']: node for node in nodes}
        edges = flow.get('edges', [])
        execution_order = flow.get('execution_order') or [n['id'] for n in nodes]
        execution_order = self._resolve_execution_order(execution_order, edges, node_dict)

        predecessors: Dict[str, List[str]] = {}
        for edge in edges:
            predecessors.setdefault(edge['to'], []).append(edge['from'])

        generated: Dict[str, str] = {}

        for node_id in execution_order:
            node = node_dict.get(node_id)
            if not node:
                continue

            command = self._generate_command_for_node(node, node_dict, predecessors, generated,
                                                        environment_description, os_type)
            generated[node_id] = command
            node.setdefault('environment_specific', {})['commands'] = command

        print(f"  [OK] Generated {len(generated)} commands")
        return flow

    def _resolve_execution_order(self, execution_order: List[str], edges: List[Dict],
                                  node_dict: Dict[str, Dict]) -> List[str]:
        """execution_order가 edges의 의존관계(from이 to보다 먼저 와야 함)를 위반하면
        경고를 남기고 위상정렬로 재계산한다. predecessor_commands가 조용히 비는 것을 방지."""
        position = {node_id: i for i, node_id in enumerate(execution_order)}

        violations = []
        for edge in edges:
            src, dst = edge.get('from'), edge.get('to')
            if src not in position or dst not in position:
                continue
            if position[src] >= position[dst]:
                violations.append((src, dst))

        if not violations:
            return execution_order

        print(f"  [WARNING] execution_order violates {len(violations)} edge(s) "
              f"{violations[:5]}{'...' if len(violations) > 5 else ''}; recomputing via topological sort")
        return self._topological_sort(execution_order, edges, node_dict)

    @staticmethod
    def _topological_sort(fallback_order: List[str], edges: List[Dict], node_dict: Dict[str, Dict]) -> List[str]:
        """Kahn's algorithm. 동률/사이클 상황에서는 fallback_order 상의 상대 순서를 최대한 보존."""
        in_degree = {node_id: 0 for node_id in node_dict}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in node_dict}

        for edge in edges:
            src, dst = edge.get('from'), edge.get('to')
            if src in node_dict and dst in node_dict:
                adjacency[src].append(dst)
                in_degree[dst] += 1

        order_rank = {node_id: i for i, node_id in enumerate(fallback_order)}

        def rank(node_id):
            return order_rank.get(node_id, len(fallback_order))

        ready = sorted([n for n in node_dict if in_degree[n] == 0], key=rank)

        result = []
        visited = set()
        while ready:
            ready.sort(key=rank)
            current = ready.pop(0)
            visited.add(current)
            result.append(current)
            for nxt in adjacency[current]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    ready.append(nxt)

        # 사이클 등으로 위상정렬에 포함되지 못한 노드는 원래 순서 그대로 뒤에 붙임 (누락 방지)
        for node_id in fallback_order:
            if node_id not in visited:
                result.append(node_id)
                visited.add(node_id)

        return result

    def _generate_command_for_node(self, node: Dict, node_dict: Dict[str, Dict], predecessors: Dict[str, List[str]],
                                    generated: Dict[str, str], environment_description: str, os_type: str) -> str:
        technique = node.get('technique', {}) or {}
        technique_id = technique.get('id', 'T0000')
        technique_name = technique.get('name', 'Unknown')
        environment_specific = node.get('environment_specific', {}) or {}

        pred_lines = []
        for pred_id in predecessors.get(node['id'], []):
            if pred_id in generated:
                pred_node = node_dict.get(pred_id, {})
                pred_lines.append(f"- [{pred_id}] {pred_node.get('name', '')}: {generated[pred_id]}")
        predecessor_commands = "\n".join(pred_lines) if pred_lines else "None"

        examples = []
        if self.use_knowledge_base and technique_id and technique_id != 'T0000':
            try:
                examples = self.kb.get_example_commands(technique_id, technique_name)
            except Exception as e:
                print(f"    [WARNING] KB lookup failed for {technique_id}: {e}")
        example_commands = self._format_examples(examples) if examples else "None available"

        prompt = self.prompt_manager.render(
            "step3_generate_command.yaml",
            os_type=os_type.capitalize(),
            node_name=node.get('name', ''),
            description=node.get('description', ''),
            tactic=node.get('tactic', 'execution'),
            technique_id=technique_id,
            technique_name=technique_name,
            environment_specific=yaml.dump(environment_specific, allow_unicode=True, sort_keys=False) if environment_specific else "None",
            environment_description=environment_description,
            predecessor_commands=predecessor_commands,
            example_commands=example_commands,
        )

        return self._call_llm_for_command(prompt, node.get('name', node['id']))

    def _call_llm_for_command(self, prompt: str, node_label: str, max_retries: int = 2) -> str:
        for attempt in range(1, max_retries + 1):
            try:
                response_text = self.llm.generate_text(prompt=prompt, max_tokens=500)
                command = response_text.strip()
                command = command.replace('```powershell', '').replace('```cmd', '').replace('```', '').strip()
                if not command:
                    raise ValueError("Empty command generated")
                return command
            except Exception as e:
                print(f"    [WARNING] Command generation for '{node_label}' attempt {attempt}/{max_retries} failed: {e}")

        print(f"    [ERROR] Command generation for '{node_label}' failed after {max_retries} attempts, using stub")
        return "echo 'command generation failed'"

    @staticmethod
    def _format_examples(examples: List[Dict]) -> str:
        lines = []
        for i, ex in enumerate(examples, 1):
            lines.append(f"{i}. [{ex.get('test_name', '')}] ({ex.get('executor_name', '')})\n   {ex.get('command_template', '').strip()}")
        return "\n".join(lines)

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML from response"""
        if '```yaml' in text:
            return text.split('```yaml')[1].split('```')[0].strip()
        elif '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        return text

    def _fix_backslashes(self, yaml_text: str) -> str:
        """Fix Windows path backslash escaping in YAML"""
        def fix_quoted_string(match):
            content = match.group(1)
            normalized = re.sub(r'\\+', r'\\', content)
            fixed = normalized.replace('\\', '\\\\')
            return f'"{fixed}"'

        fixed_yaml = re.sub(r'"([^"]*)"', fix_quoted_string, yaml_text)
        return fixed_yaml

    def _print_summary(self, flow: Dict):
        """Print flow summary"""
        print("\n" + "="*70)
        print("Concrete Attack Flow Summary (WITHOUT MITRE INJECTION):")
        print("="*70)

        nodes = flow.get('nodes', [])
        edges = flow.get('edges', [])

        print(f"\nTotal Steps: {len(nodes)}")
        print(f"Dependencies: {len(edges)}")

        # Technique statistics
        valid_techniques = 0
        unknown_techniques = 0
        for node in nodes:
            tech = node.get('technique', {})
            if tech.get('id', 'T0000') != 'T0000':
                valid_techniques += 1
            else:
                unknown_techniques += 1

        print(f"\nTechnique Mapping:")
        print(f"  With ID: {valid_techniques}")
        print(f"  Unknown: {unknown_techniques}")

        if 'execution_order' in flow:
            print(f"\nExecution Order:")
            for i, node_id in enumerate(flow['execution_order'], 1):
                node = next((n for n in nodes if n['id'] == node_id), None)
                if node:
                    technique = node.get('technique', {})
                    if technique and technique.get('id') != 'T0000':
                        technique_str = f"{technique['id']} ({technique.get('name', 'Unknown')})"
                        print(f"  {i}. {node.get('name', 'Unknown')} [{node.get('tactic', 'unknown')}] ({technique_str})")
                    else:
                        print(f"  {i}. {node.get('name', 'Unknown')} [{node.get('tactic', 'unknown')}] (no technique)")

        print("\n" + "="*70)


def main():
    """Test runner"""
    if len(sys.argv) < 4:
        print("Usage: python step3_concrete_flow.py <abstract_flow.yml> <environment.md> <output.yml>")
        sys.exit(1)

    ConcreteFlowGenerator().generate_concrete_flow(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
