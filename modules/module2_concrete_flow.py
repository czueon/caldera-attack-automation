"""
Module 2: Concrete Attack Flow Generation
Combine abstract flow + environment description (MD) → concrete attack flow (Kill Chain)
"""

import yaml
import os
import re
from anthropic import Anthropic
from typing import Dict, List
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.config import get_claude_model, get_anthropic_api_key

try:
    from mitreattack.stix20 import MitreAttackData
except ImportError:
    print("[WARNING] mitreattack-python not installed. Run: pip install mitreattack-python==3.0.6")
    MitreAttackData = None


class ConcreteFlowGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=get_anthropic_api_key())
        self.model = get_claude_model()
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
        print("\n[Step 2] Concrete Attack Flow Generation started...")

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
                'step': 2,
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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=12000,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"""You are a penetration testing expert creating executable attack plans.

# Abstract Attack Goals

{yaml.dump(abstract_flow, allow_unicode=True)}

# Target Environment

{environment_description}

# Task

Map each abstract goal to concrete attack steps using the specific environment details.

## Core Principles

1. **Use Actual Environment Details**
   - Extract all specific values from the environment description (IPs, URLs, credentials, file names, methods, parameters)
   - Every detail mentioned must be captured in the output

2. **Create Executable Steps**
   - Each node must contain enough information to actually execute the attack
   - Include all parameters, paths, and configurations needed

3. **Preserve Information**
   - Don't lose or simplify any environment-specific details
   - If the environment says "POST with userid and password parameters", include exactly that

4. **Tool Selection Priority**
   - **1st Priority**: Use tools/payloads explicitly provided in environment description (Caldera payloads, uploaded files)
   - **2nd Priority**: Use native OS built-in tools (PowerShell, cmd.exe, netstat, systeminfo, etc.)
   - **3rd Priority**: Use simulation/stub commands when actual tools unavailable (e.g., keylogger simulation with echo commands)

5. **Caldera Payload Handling**
   - If environment mentions files in "## Caldera Payload" section, these are ALREADY available to the agent
   - Reference payload files by name only (e.g., "cmd.asp", "PrintSpoofer64.exe")
   - DO NOT include download URLs or methods - Caldera handles file delivery automatically
   - Just describe what to do with the file once it's available (e.g., "copy cmd.asp to uploads folder")

## Output Structure

```yaml
nodes:
  - id: "node_001"
    name: "Attack step name"
    tactic: "MITRE ATT&CK Tactic"
    description: "What this accomplishes"

    environment_specific:
      # Extract ALL details from environment description
      target: "actual IP/hostname"
      url: "actual URL"
      method: "actual HTTP method (POST/GET/etc)"
      params: ["actual", "parameter", "names"]
      credentials:
        username: "actual username"
        password: "actual password"
      payload: "actual filename"
      commands: "PowerShell command in single line"  # IMPORTANT: Generate executable command here
      # Include ANY other details mentioned

edges:
  - from: "node_id"
    to: "node_id"
    dependency_type: "required"

execution_order:
  - "node_001"
  - "node_002"
```

## Examples

**Example 1: Using provided payload**

Environment says: "Caldera payloads: cmd.asp, deploy.ps1. Login at http://192.168.56.105/login_process.asp using POST with userid/password parameters. Credentials: admin/P@ssw0rd!2020"

Correct node:
```yaml
- id: "node_001"
  name: "Web Application Login"
  tactic: "initial-access"
  description: "Authenticate using compromised credentials"
  environment_specific:
    target: "192.168.56.105"
    url: "http://192.168.56.105/login_process.asp"
    method: "POST"
    params: ["userid", "password"]
    credentials:
      username: "admin"
      password: "P@ssw0rd!2020"

- id: "node_002"
  name: "Upload Web Shell"
  tactic: "initial-access"
  description: "Deploy cmd.asp web shell using Caldera payload"
  environment_specific:
    payload: "cmd.asp"  # Caldera automatically downloads to agent working directory
```

**Example 2: Using native OS tools**

Abstract goal: "Compress collected data for exfiltration"
No compression tool in environment description.

Correct node:
```yaml
- id: "node_015"
  name: "Compress Collected Data"
  tactic: "exfiltration"
  description: "Compress data using Windows built-in tools"
  environment_specific:
    command: "Compress-Archive -Path C:\\Windows\\Temp\\exfil\\* -DestinationPath C:\\Windows\\Temp\\data.zip"
    tool: "PowerShell Compress-Archive"  # 2nd priority: native tool
```

**Example 3: Using simulation/stub**

Abstract goal: "Deploy keylogger for credential harvesting"
No keylogger in environment description.

Correct node:
```yaml
- id: "node_020"
  name: "Deploy Keylogger (Simulated)"
  tactic: "credential-access"
  description: "Simulate keylogger deployment"
  environment_specific:
    command: "echo 'keylogger stub' > C:\\Windows\\Temp\\perfcon.dat; Write-Output 'Keylogger installed (simulated)'"
    simulation: true  # 3rd priority: stub simulation
```

**Note**: Technique IDs will be added automatically in post-processing using mitreattack-python.

**Output YAML only. No explanations.**"""
            }]
        )

        try:
            yaml_text = self._extract_yaml(response.content[0].text)
            flow = yaml.safe_load(yaml_text)
            print(f"  [OK] Generated {len(flow.get('nodes', []))} concrete steps")
            return flow
        except Exception as e:
            print(f"  [ERROR] Failed to generate concrete flow: {e}")
            raise

    def _add_technique_ids(self, flow: Dict) -> Dict:
        """Add MITRE ATT&CK Technique ID candidates to nodes using mitreattack-python"""
        if not self.mitre_data:
            print("  [WARNING] MITRE ATT&CK data not available, skipping technique ID assignment")
            return flow

        print("  [Adding MITRE ATT&CK Technique ID candidates (top 3)...]")

        nodes = flow.get('nodes', [])
        candidates_added = 0
        no_candidates = 0

        for node in nodes:
            tactic = node.get('tactic', '').lower().replace('-', '_')
            name = node.get('name', '')
            description = node.get('description', '')

            # Get top 3 technique candidates
            candidates = self._find_technique_candidates(tactic, name, description, top_k=3)

            if candidates:
                node['technique_candidates'] = candidates
                candidates_added += 1
            else:
                # Use placeholder if no candidates found
                node['technique_candidates'] = [
                    {
                        'id': 'T0000',
                        'name': 'Unknown',
                        'score': 0
                    }
                ]
                no_candidates += 1

        print(f"  [OK] Nodes with candidates: {candidates_added}, No candidates: {no_candidates}")
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
                    candidates = node.get('technique_candidates', [])
                    if candidates:
                        top_candidate = candidates[0]
                        candidate_str = f"{top_candidate['id']} (score: {top_candidate['score']})"
                        if len(candidates) > 1:
                            candidate_str += f" +{len(candidates)-1} more"
                        print(f"  {i}. {node.get('name', 'Unknown')} [{node.get('tactic', 'unknown')}] ({candidate_str})")
                    else:
                        print(f"  {i}. {node.get('name', 'Unknown')} [{node.get('tactic', 'unknown')}] (no candidates)")

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
