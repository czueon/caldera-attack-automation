"""
Module 3: Technique Selection
Select final MITRE ATT&CK technique from candidates (top 3 → final 1)
"""

import yaml
import os
from anthropic import Anthropic
from typing import Dict, List
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.config import get_claude_model, get_anthropic_api_key


class TechniqueSelector:
    def __init__(self):
        self.client = Anthropic(api_key=get_anthropic_api_key())
        self.model = get_claude_model()

    def select_techniques(self, input_file: str, output_file: str):
        """Select final technique from candidates for each node"""
        print("\n[Step 3] Technique Selection started...")

        # Load Step 2 concrete flow
        with open(input_file, 'r', encoding='utf-8') as f:
            step2_data = yaml.safe_load(f)

        concrete_flow = step2_data.get('concrete_flow', {})
        nodes = concrete_flow.get('nodes', [])

        print(f"  Total nodes: {len(nodes)}")

        # Select final technique for each node
        enhanced_nodes = []
        selected_count = 0
        auto_selected_count = 0

        for node in nodes:
            # 1. Technique 선택
            enhanced_node = self._select_final_technique(node)
            enhanced_nodes.append(enhanced_node)

            if enhanced_node.get('technique'):
                selected_count += 1
                if enhanced_node['technique'].get('id') == enhanced_node.get('technique_candidates', [{}])[0].get('id'):
                    auto_selected_count += 1

        # 2. Commands 일괄 생성 (비어있는 노드만)
        enhanced_nodes = self._fill_missing_commands(enhanced_nodes, step2_data)

        # Update concrete flow with final techniques
        concrete_flow['nodes'] = enhanced_nodes

        # Save results
        output_data = {
            'metadata': {
                'source': input_file,
                'step': 3,
                'description': 'Concrete attack flow with final technique selection'
            },
            'concrete_flow': concrete_flow
        }

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)

        print(f"  [OK] Techniques selected: {selected_count}/{len(nodes)}")
        print(f"  [OK] Auto-selected (top 1): {auto_selected_count}/{selected_count}")
        print(f"[SUCCESS] Technique selection completed -> {output_file}")
        self._print_summary(enhanced_nodes)

    def _select_final_technique(self, node: Dict) -> Dict:
        """Select final technique from candidates based on environment context"""
        candidates = node.get('technique_candidates', [])

        if not candidates:
            # No candidates, add placeholder
            node['technique'] = {
                'id': 'T0000',
                'name': 'Unknown',
                'selection_reason': 'No candidates available'
            }
            # Remove technique_candidates
            if 'technique_candidates' in node:
                del node['technique_candidates']
            return node

        if len(candidates) == 1:
            # Only one candidate, auto-select
            node['technique'] = {
                'id': candidates[0]['id'],
                'name': candidates[0]['name'],
                'selection_reason': 'Only candidate available'
            }
            # Remove technique_candidates after selection
            del node['technique_candidates']
            return node

        # Multiple candidates - use context to select best match
        selected = self._select_best_candidate(
            node.get('name', ''),
            node.get('description', ''),
            node.get('environment_specific', {}),
            candidates
        )

        node['technique'] = selected
        # Remove technique_candidates after selection
        del node['technique_candidates']
        return node

    def _select_best_candidate(self, name: str, description: str,
                               env_specific: Dict, candidates: List[Dict]) -> Dict:
        """Select best technique candidate based on context"""

        # Auto-select if top candidate has significantly higher score
        if len(candidates) >= 2:
            top_score = candidates[0].get('score', 0)
            second_score = candidates[1].get('score', 0)

            # If top candidate score is 50%+ higher than second, auto-select
            if top_score >= second_score * 1.5 and top_score >= 5:
                return {
                    'id': candidates[0]['id'],
                    'name': candidates[0]['name'],
                    'selection_reason': f'High confidence (score: {top_score} vs {second_score})'
                }

        # Use AI to select based on environment context
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Select the most appropriate MITRE ATT&CK technique for this attack step.

# Attack Step

Name: {name}
Description: {description}

Environment Details:
{yaml.dump(env_specific, allow_unicode=True)}

# Candidate Techniques

{yaml.dump(candidates, allow_unicode=True)}

# Task

Select the MOST appropriate technique ID based on:
1. Match with actual actions in environment_specific (commands, tools, methods)
2. Alignment with attack step description
3. MITRE ATT&CK technique definition accuracy

Output JSON only:
```json
{{
  "selected_id": "T####",
  "reason": "Brief reason (1 sentence)"
}}
```"""
                }]
            )

            # Parse response
            import json
            text = response.content[0].text
            if '```json' in text:
                json_text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                json_text = text.split('```')[1].split('```')[0].strip()
            else:
                json_text = text.strip()

            result = json.loads(json_text)
            selected_id = result.get('selected_id', candidates[0]['id'])
            reason = result.get('reason', 'AI-selected based on context')

            # Find selected candidate
            selected_candidate = next((c for c in candidates if c['id'] == selected_id), candidates[0])

            return {
                'id': selected_candidate['id'],
                'name': selected_candidate['name'],
                'selection_reason': reason
            }

        except Exception as e:
            # Fallback to top candidate
            print(f"    [WARNING] AI selection failed for {name}: {e}")
            return {
                'id': candidates[0]['id'],
                'name': candidates[0]['name'],
                'selection_reason': f'Fallback to top candidate (AI error: {str(e)[:50]})'
            }

    def _fill_missing_commands(self, nodes: List[Dict], step2_data: Dict) -> List[Dict]:
        """비어있는 commands를 일괄 생성"""
        # 비어있는 노드 찾기
        missing_nodes = []
        for node in nodes:
            env_specific = node.get('environment_specific', {})
            commands = env_specific.get('commands', '')
            if not commands or commands.strip() == '':
                missing_nodes.append(node)

        if not missing_nodes:
            print(f"  [OK] All nodes have commands")
            return nodes

        print(f"  [INFO] {len(missing_nodes)} nodes missing commands - generating...")

        # 환경 설명 추출 (Step 2 metadata에서)
        metadata = step2_data.get('metadata', {})

        # AI에게 전체 노드 정보 전달하여 commands 생성
        filled_nodes = self._generate_missing_commands_batch(missing_nodes, metadata)

        # 원본 노드 리스트 업데이트
        filled_dict = {node['id']: node for node in filled_nodes}
        updated_nodes = []
        for node in nodes:
            if node['id'] in filled_dict:
                updated_nodes.append(filled_dict[node['id']])
            else:
                updated_nodes.append(node)

        return updated_nodes

    def _generate_missing_commands_batch(self, missing_nodes: List[Dict], metadata: Dict) -> List[Dict]:
        """비어있는 노드들의 commands를 일괄 생성"""
        nodes_yaml = yaml.dump(missing_nodes, allow_unicode=True, sort_keys=False)

        prompt = f"""Generate PowerShell commands for nodes missing commands field.

# Nodes Missing Commands
{nodes_yaml}

# Requirements
1. **Single Line**: All commands MUST be ONE line (use semicolons, no line breaks)
2. **PowerShell 5.1**: Avoid -Form, -SkipCertificateCheck
3. **Self-Contained**: Include ALL steps in one command (no variable sharing)
4. **Use Environment Details**: Use information from environment_specific field

# Output Format
Return YAML with ONLY the node id and commands field:

```yaml
- id: "node_001"
  commands: "$var=value;Invoke-Command ..."
- id: "node_002"
  commands: "Copy-Item ...;Invoke-WebRequest ..."
```

**Output YAML only. No explanations.**
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            # YAML 추출
            import re
            text = response.content[0].text.strip()
            if '```yaml' in text:
                yaml_text = text.split('```yaml')[1].split('```')[0].strip()
            elif '```' in text:
                yaml_text = text.split('```')[1].split('```')[0].strip()
            else:
                yaml_text = text

            generated_commands = yaml.safe_load(yaml_text)

            # 생성된 commands를 원본 노드에 병합
            command_dict = {item['id']: item.get('commands', '') for item in generated_commands}

            filled_nodes = []
            for node in missing_nodes:
                node_id = node['id']
                if node_id in command_dict and command_dict[node_id]:
                    if 'environment_specific' not in node:
                        node['environment_specific'] = {}
                    # 탭과 불필요한 공백 제거 (정규식)
                    raw_command = command_dict[node_id]
                    # 1. 탭을 공백으로 변환
                    clean_command = raw_command.replace('\t', ' ')
                    # 2. 줄바꿈을 공백으로 변환
                    clean_command = re.sub(r'\s*\n\s*', ' ', clean_command)
                    # 3. 연속된 공백을 하나로 축소
                    clean_command = re.sub(r'\s+', ' ', clean_command)
                    # 4. 앞뒤 공백 제거
                    clean_command = clean_command.strip()

                    node['environment_specific']['commands'] = clean_command
                    print(f"    [OK] Generated commands for {node.get('name', node_id)}")
                else:
                    print(f"    [WARNING] No commands generated for {node.get('name', node_id)}")
                filled_nodes.append(node)

            return filled_nodes

        except Exception as e:
            print(f"    [ERROR] Batch command generation failed: {e}")
            return missing_nodes


    def _print_summary(self, nodes: List[Dict]):
        """Print technique selection summary"""
        print("\n" + "="*70)
        print("Technique Selection Summary:")
        print("="*70)

        # Count selection methods
        high_confidence = 0
        ai_selected = 0
        auto_selected = 0
        fallback = 0

        for node in nodes:
            technique = node.get('technique', {})
            reason = technique.get('selection_reason', '')

            if 'High confidence' in reason:
                high_confidence += 1
            elif 'AI-selected' in reason:
                ai_selected += 1
            elif 'Only candidate' in reason or 'No candidates' in reason:
                auto_selected += 1
            elif 'Fallback' in reason:
                fallback += 1

        print(f"\nSelection Methods:")
        print(f"  High Confidence (score-based): {high_confidence}")
        print(f"  AI-Selected (context-based): {ai_selected}")
        print(f"  Auto-Selected (single candidate): {auto_selected}")
        print(f"  Fallback (error handling): {fallback}")

        # Show some examples
        print(f"\nSample Selections:")
        for i, node in enumerate(nodes[:5], 1):
            technique = node.get('technique', {})
            print(f"  {i}. {node.get('name', 'Unknown')}")
            print(f"     → {technique.get('id', 'T0000')} ({technique.get('name', 'Unknown')})")
            print(f"     Reason: {technique.get('selection_reason', 'N/A')}")

        print("\n" + "="*70)


def main():
    """Test runner"""
    if len(sys.argv) < 3:
        print("Usage: python module3_technique_selection.py <input.yml> <output.yml>")
        sys.exit(1)

    TechniqueSelector().select_techniques(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
