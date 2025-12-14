"""
Module 3: Concrete Attack Flow Generation
Combine abstract flow + environment description (MD) → concrete attack flow (Kill Chain)
"""

import yaml
import os
import re
import difflib
from typing import Dict, List
import sys
from pathlib import Path
from datetime import datetime

# 모듈 패키지를 정상 인식하도록 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
from modules.ai.factory import get_llm_client
from modules.prompts.manager import PromptManager

try:
    from mitreattack.stix20 import MitreAttackData
except ImportError:
    print("[WARNING] mitreattack-python not installed. Run: pip install mitreattack-python==3.0.6")
    MitreAttackData = None


class ConcreteFlowGenerator:
    def __init__(self):
        self.llm = get_llm_client()
        self.prompt_manager = PromptManager()
        self.mitre_data = None

        # Load MITRE ATT&CK data if available
        if MitreAttackData:
            try:
                # 프로젝트 루트 기준 절대 경로로 지정해 상대 경로 오류 방지
                mitre_path = PROJECT_ROOT / "data" / "mitre" / "enterprise-attack.json"
                print(f"  [Loading MITRE ATT&CK data...] ({mitre_path})")
                self.mitre_data = MitreAttackData(str(mitre_path))
                print("  [OK] MITRE ATT&CK data loaded")
            except Exception as e:
                print(f"  [WARNING] Failed to load MITRE ATT&CK data: {e}")
                self.mitre_data = None

    def generate_concrete_flow(self, abstract_flow_file: str,
                              environment_md_file: str,
                              output_file: str = None,
                              version_id: str = None):
        """Generate concrete attack flow by combining abstract flow + environment MD"""
        print("\n[Step 3] Concrete Attack Flow Generation started...")

        # Load abstract flow
        with open(abstract_flow_file, 'r', encoding='utf-8') as f:
            abstract_data = yaml.safe_load(f)

        abstract_flow = abstract_data.get('abstract_flow', {})
        metadata = abstract_data.get('metadata', {})

        # pdf_name, version_id 추출 (경로 → 메타데이터 → 기본값)
        pdf_name = metadata.get('pdf_name')
        if not pdf_name:
            pdf_name = Path(abstract_flow_file).stem.replace("_step2", "")
            if Path(abstract_flow_file).parents:
                pdf_name = Path(abstract_flow_file).parent.parent.name or pdf_name

        derived_version = (
            version_id
            or metadata.get('version_id')
            or Path(abstract_flow_file).parent.name  # data/processed/{pdf}/{version}/
        )
        version_id = derived_version or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Read environment description (Markdown)
        with open(environment_md_file, 'r', encoding='utf-8') as f:
            environment_description = f.read()

        print(f"  Abstract goals: {len(abstract_flow.get('attack_goals', []))}")
        print(f"  Environment description: {len(environment_description)} characters")

        # Extract Caldera payloads from environment description
        caldera_payloads = self._extract_caldera_payloads(environment_description)
        if caldera_payloads:
            print(f"  Caldera payloads found: {', '.join(caldera_payloads)}")

        # Generate concrete flow
        concrete_flow = self._generate_flow(abstract_flow, environment_description)

        # Add MITRE ATT&CK technique IDs
        concrete_flow = self._add_technique_ids(concrete_flow)

        # Save results
        output_data = {
            'metadata': {
                'sources': {
                    'abstract_flow': abstract_flow_file,
                    'environment': environment_md_file
                },
                'pdf_name': pdf_name,
                'version_id': version_id,
                'step': 3,
                'description': 'Concrete attack flow (Kill Chain) with environment-specific details',
                'caldera_payloads': caldera_payloads  # Caldera payload 목록 추가
            },
            'concrete_flow': concrete_flow
        }

        # output_file 미지정 시 data/processed/{pdf}/{version}/{pdf}_step3.yml 사용
        if output_file is None:
            output_file = Path("../../data/processed") / pdf_name / version_id / f"{pdf_name}_step3.yml"

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Concrete flow generation completed -> {output_file}")
        print(f"  - PDF: {pdf_name}")
        print(f"  - Version: {version_id}")
        self._print_summary(concrete_flow)

    def _generate_flow(self, abstract_flow: Dict, environment_description: str) -> Dict:
        """Generate concrete attack flow using Claude (with retry on parse errors)"""
        print("  [Generating concrete attack flow...]")

        abstract_flow_yaml = yaml.dump(abstract_flow, allow_unicode=True)

        prompt = self.prompt_manager.render(
            "step3_generate_flow.yaml",
            abstract_flow=abstract_flow_yaml,
            environment_description=environment_description
        )

        MAX_RETRIES = 3
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    print(f"  [Retry {attempt}/{MAX_RETRIES}] Regenerating flow...")
                    # 재시도 시 프롬프트에 이전 오류 정보 추가
                    retry_prompt = f"{prompt}\n\n[IMPORTANT] Previous attempt failed with error: {last_error}\nPlease generate valid YAML format without syntax errors."
                    response_text = self.llm.generate_text(prompt=retry_prompt, max_tokens=12000)
                else:
                    response_text = self.llm.generate_text(prompt=prompt, max_tokens=12000)

                # YAML 추출 및 파싱
                yaml_text = self._extract_yaml(response_text)

                if not yaml_text or len(yaml_text.strip()) < 10:
                    raise ValueError("Extracted YAML is empty or too short")

                flow = yaml.safe_load(yaml_text)

                # 기본 구조 검증
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
                    print(f"  [INFO] Will retry with error feedback...")
                    continue

            except (ValueError, KeyError, TypeError) as e:
                last_error = f"Structure validation error: {str(e)}"
                print(f"  [ERROR] Attempt {attempt}/{MAX_RETRIES}: {last_error}")

                if attempt < MAX_RETRIES:
                    print(f"  [INFO] Will retry with error feedback...")
                    continue

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                print(f"  [ERROR] Attempt {attempt}/{MAX_RETRIES}: {last_error}")

                if attempt < MAX_RETRIES:
                    print(f"  [INFO] Will retry...")
                    continue

        # 모든 재시도 실패
        print(f"\n  [FATAL] Failed to generate valid concrete flow after {MAX_RETRIES} attempts")
        print(f"  [FATAL] Last error: {last_error}")
        print(f"  [INFO] Saving failed response for debugging...")

        # 디버깅을 위해 실패한 응답 저장
        debug_file = "failed_flow_generation.txt"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Failed Flow Generation Debug Info ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Attempts: {MAX_RETRIES}\n")
                f.write(f"Last Error: {last_error}\n\n")
                f.write(f"=== Last Response ===\n")
                f.write(response_text if 'response_text' in locals() else "No response captured")
                f.write(f"\n\n=== Extracted YAML ===\n")
                f.write(yaml_text if 'yaml_text' in locals() else "No YAML extracted")
            print(f"  [INFO] Debug info saved to: {debug_file}")
        except:
            pass

        raise RuntimeError(f"Failed to generate valid concrete flow after {MAX_RETRIES} attempts. Last error: {last_error}")


    def _add_technique_ids(self, flow: Dict) -> Dict:
        """Add MITRE ATT&CK Technique ID (best match) to nodes using mitreattack-python"""
        if not self.mitre_data:
            print("  [WARNING] MITRE ATT&CK data not available, skipping technique ID assignment")
            return flow

        print("  [Adding MITRE ATT&CK Technique IDs (best match)...]")

        nodes = flow.get('nodes', [])
        techniques_added = 0
        no_technique = 0

        for node in nodes:
            tactic = node.get('tactic', '').lower().replace('-', '_')
            name = node.get('name', '')
            description = node.get('description', '')

            # Get best matching technique (only 1)
            candidates = self._find_technique_candidates(tactic, name, description, top_k=1)

            if candidates:
                # Assign the best technique directly
                best_technique = candidates[0]
                node['technique'] = {
                    'id': best_technique['id'],
                    'name': best_technique['name']
                }
                techniques_added += 1
            else:
                # Use placeholder if no candidates found
                node['technique'] = {
                    'id': 'T0000',
                    'name': 'Unknown'
                }
                no_technique += 1

        print(f"  [OK] Nodes with techniques: {techniques_added}, No technique: {no_technique}")
        return flow

    def _find_technique_candidates(self, tactic: str, name: str, description: str, top_k: int = 1) -> List[Dict]:
        """Find up to top_k matching MITRE ATT&CK techniques; if none, return empty (no forced multi-hit)"""
        if not self.mitre_data:
            return []

        # Normalize tactic name for MITRE ATT&CK
        tactic_mapping = {
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
            'impact': 'impact',
            'reconnaissance': 'reconnaissance'
        }

        mitre_tactic = tactic_mapping.get(tactic, tactic)

        # Get all techniques
        techniques = self.mitre_data.get_techniques()

        # Score all techniques matching the tactic (완화된 스코어링으로 T0000 남발 방지)
        scored_techniques = []

        for tech in techniques:
            # Check if technique belongs to this tactic
            tech_tactics = [phase['phase_name'] for phase in tech.get('kill_chain_phases', [])]

            if mitre_tactic not in tech_tactics:
                continue

            tech_name = tech.get('name', '').lower()
            tech_desc = tech.get('description', '').lower()

            # Calculate matching score (단어 교집합 + 부분 포함 여부를 모두 반영)
            score = 0
            name_lower = name.lower()
            desc_lower = description.lower()

            name_tokens = set(re.findall(r"[a-z0-9]+", name_lower))
            tech_name_tokens = set(re.findall(r"[a-z0-9]+", tech_name))
            desc_tokens = set(re.findall(r"[a-z0-9]+", desc_lower))
            tech_desc_tokens = set(re.findall(r"[a-z0-9]+", tech_desc))

            # Check name similarity (higher weight)
            name_overlap = len(name_tokens & tech_name_tokens)
            score += name_overlap * 3

            # Check description similarity (lower weight)
            desc_overlap = len(desc_tokens & tech_desc_tokens)
            score += min(desc_overlap, 5)

            # Partial substring matches 보너스 (교집합이 적을 때 완화)
            if name_lower and name_lower in tech_name:
                score += 2
            if tech_name and tech_name in name_lower:
                score += 1
            if name_lower and name_lower in tech_desc:
                score += 1
            if desc_lower and desc_lower in tech_desc:
                score += 1

            # Only include if score is reasonable
            if score >= 1:
                scored_techniques.append({
                    'id': tech.get('external_references', [{}])[0].get('external_id', 'T0000'),
                    'name': tech.get('name', 'Unknown'),
                    'score': score
                })

        # Sort by score (descending) and return up to top_k (없으면 빈 리스트 그대로 반환)
        scored_techniques.sort(key=lambda x: x['score'], reverse=True)
        if scored_techniques:
            return scored_techniques[:top_k]

        # Fuzzy fallback: single best match within tactic based on sequence similarity (top 1 only)
        best = None
        best_ratio = 0
        for tech in techniques:
            tech_tactics = [phase['phase_name'] for phase in tech.get('kill_chain_phases', [])]
            if mitre_tactic not in tech_tactics:
                continue
            tech_name_full = tech.get('name', '')
            ratio_name = difflib.SequenceMatcher(None, name_lower, tech_name_full.lower()).ratio()
            ratio_desc = difflib.SequenceMatcher(None, desc_lower, tech.get('description', '').lower()).ratio()
            ratio = max(ratio_name, ratio_desc)
            if ratio > best_ratio:
                best_ratio = ratio
                best = {
                    'id': tech.get('external_references', [{}])[0].get('external_id', 'T0000'),
                    'name': tech.get('name', 'Unknown'),
                    'score': ratio
                }
        # 최소 유사도 임계치 0.2로 너무 엉뚱한 매칭 방지
        if best and best_ratio >= 0.2:
            return [best]

        return []

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML from response"""
        if '```yaml' in text:
            return text.split('```yaml')[1].split('```')[0].strip()
        elif '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        return text

    def _print_summary(self, flow: Dict):
        """Print flow summary"""
        print("\n" + "="*70)
        print("Concrete Attack Flow Summary:")
        print("="*70)

        nodes = flow.get('nodes', [])
        edges = flow.get('edges', [])
        metadata = flow.get('metadata', {})

        print(f"\nTotal Steps: {len(nodes)}")
        print(f"Dependencies: {len(edges)}")
        print(f"Complexity: {metadata.get('complexity', 'Unknown')}")

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

    def _extract_caldera_payloads(self, md_content: str) -> List[str]:
        """Extract Caldera payload files from environment markdown"""
        payloads = []

        # Look for "## Caldera Payload" section
        if '## Caldera Payload' in md_content:
            # Extract section content until next ## or end of file
            section = md_content.split('## Caldera Payload')[1]

            # Stop at next section (##) or end
            if '##' in section:
                section = section.split('##')[0]

            # Extract filenames from "- filename" pattern
            # Match: - cmd.asp, - PrintSpoofer64.exe, etc.
            matches = re.findall(
                r'^-\s+([A-Za-z0-9_.-]+\.(exe|dll|ps1|asp|bat|vbs|sh|zip|tar|gz))',
                section,
                re.MULTILINE | re.IGNORECASE
            )

            for match in matches:
                filename = match[0]
                if filename not in payloads:
                    payloads.append(filename)

        return payloads


def main():
    """Test runner"""
    if len(sys.argv) < 4:
        print("Usage: python step3_concrete_flow.py <abstract_flow.yml> <environment.md> <output.yml>")
        sys.exit(1)

    ConcreteFlowGenerator().generate_concrete_flow(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
