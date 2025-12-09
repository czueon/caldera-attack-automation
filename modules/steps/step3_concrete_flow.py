"""
Module 3: Concrete Attack Flow Generation
Combine abstract flow + environment description (MD) → concrete attack flow (Kill Chain)
"""

import yaml
import os
import re
from typing import Dict, List
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
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
                print("  [Loading MITRE ATT&CK data...]")
                self.mitre_data = MitreAttackData("enterprise-attack.json")
                print("  [OK] MITRE ATT&CK data loaded")
            except Exception as e:
                print(f"  [WARNING] Failed to load MITRE ATT&CK data: {e}")
                self.mitre_data = None

    def generate_concrete_flow(self, abstract_flow_file: str,
                              environment_md_file: str,
                              output_file: str):
        """Generate concrete attack flow by combining abstract flow + environment MD"""
        print("\n[Step 3] Concrete Attack Flow Generation started...")

        # Load abstract flow
        with open(abstract_flow_file, 'r', encoding='utf-8') as f:
            abstract_data = yaml.safe_load(f)

        abstract_flow = abstract_data.get('abstract_flow', {})

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
                'step': 3,
                'description': 'Concrete attack flow (Kill Chain) with environment-specific details',
                'caldera_payloads': caldera_payloads  # Caldera payload 목록 추가
            },
            'concrete_flow': concrete_flow
        }

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Concrete flow generation completed -> {output_file}")
        self._print_summary(concrete_flow)

    def _generate_flow(self, abstract_flow: Dict, environment_description: str) -> Dict:
        """Generate concrete attack flow using Claude"""
        print("  [Generating concrete attack flow...]")

        abstract_flow_yaml = yaml.dump(abstract_flow, allow_unicode=True)

        prompt = self.prompt_manager.render(
            "step3_generate_flow.yaml",
            abstract_flow=abstract_flow_yaml,
            environment_description=environment_description
        )

        response_text = self.llm.generate_text(prompt=prompt, max_tokens=12000)

        try:
            yaml_text = self._extract_yaml(response_text)
            flow = yaml.safe_load(yaml_text)
            print(f"  [OK] Generated {len(flow.get('nodes', []))} concrete steps")
            return flow
        except Exception as e:
            print(f"  [ERROR] Failed to generate concrete flow: {e}")
            raise


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

    def _find_technique_candidates(self, tactic: str, name: str, description: str, top_k: int = 3) -> List[Dict]:
        """Find top K matching MITRE ATT&CK techniques based on tactic and description"""
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

        # Score all techniques matching the tactic
        scored_techniques = []

        for tech in techniques:
            # Check if technique belongs to this tactic
            tech_tactics = [phase['phase_name'] for phase in tech.get('kill_chain_phases', [])]

            if mitre_tactic not in tech_tactics:
                continue

            tech_name = tech.get('name', '').lower()
            tech_desc = tech.get('description', '').lower()

            # Calculate matching score
            score = 0
            name_lower = name.lower()
            desc_lower = description.lower()

            # Check name similarity (higher weight)
            name_words = set(name_lower.split())
            tech_name_words = set(tech_name.split())
            name_overlap = len(name_words & tech_name_words)
            score += name_overlap * 3

            # Check description similarity (lower weight)
            desc_words = set(desc_lower.split())
            tech_desc_words = set(tech_desc.split())
            desc_overlap = len(desc_words & tech_desc_words)
            score += min(desc_overlap, 5)

            # Only include if score is reasonable
            if score >= 2:
                scored_techniques.append({
                    'id': tech.get('external_references', [{}])[0].get('external_id', 'T0000'),
                    'name': tech.get('name', 'Unknown'),
                    'score': score
                })

        # Sort by score (descending) and return top K
        scored_techniques.sort(key=lambda x: x['score'], reverse=True)
        return scored_techniques[:top_k]

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
        print("Usage: python module4_concrete_flow.py <abstract_flow.yml> <environment.yml> <output.yml>")
        sys.exit(1)

    ConcreteFlowGenerator().generate_concrete_flow(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
