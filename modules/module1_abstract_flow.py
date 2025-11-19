"""
Module 1: Abstract Attack Flow Extraction
Extract environment-independent abstract attack flow from KISA report
Uses 2-stage extraction: overview → detailed flow
"""

import yaml
import os
from anthropic import Anthropic
from typing import Dict, List
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.config import get_claude_model, get_anthropic_api_key


class AbstractFlowExtractor:
    def __init__(self):
        self.client = Anthropic(api_key=get_anthropic_api_key())
        self.model = get_claude_model()
        self.chunk_size = 8000  # 청크 크기 (characters)

    def extract_abstract_flow(self, input_file: str, output_file: str):
        """Extract abstract attack flow from KISA report (PDF parsed data)

        2-stage process:
        1. Extract overview to understand attack theme
        2. Process detailed content in chunks to extract complete attack flow
        """
        print("\n[Step 1] Abstract Attack Flow Extraction started...")

        with open(input_file, 'r', encoding='utf-8') as f:
            step0_data = yaml.safe_load(f)

        # Extract pages text from step0
        pages = step0_data.get('pages', [])

        if not pages:
            raise ValueError("No pages found in Step 0 output")

        # Combine all page texts
        full_text = "\n\n".join([page.get('text', '') for page in pages])

        print(f"  Total pages: {len(pages)}")
        print(f"  Total text length: {len(full_text)} characters")

        # Stage 1: Extract overview section for context
        overview = self._extract_overview(full_text)
        print(f"  Overview extracted: {len(overview)} characters")

        # Stage 2: Extract abstract attack flow from full content (chunked)
        abstract_flow = self._extract_flow_chunked(overview, full_text)

        # Save results
        output_data = {
            'metadata': {
                'source': input_file,
                'step': 1,
                'description': 'Environment-independent abstract attack flow'
            },
            'abstract_flow': abstract_flow
        }

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Abstract flow extraction completed -> {output_file}")
        self._print_summary(abstract_flow)

    def _extract_overview(self, full_text: str) -> str:
        """Stage 1: Extract overview section from report"""
        print("  [Stage 1: Extracting overview...]")

        # Take first 3000 characters for overview
        overview_chunk = full_text[:3000]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"""Extract the overview/summary section from this KISA threat intelligence report.

# Report Beginning
{overview_chunk}

# Task
Find and extract the overview section that describes:
- Attack scenario name/title
- Main attack objectives
- High-level attack flow summary

Output ONLY the overview text, nothing else."""
            }]
        )

        overview = response.content[0].text.strip()
        return overview

    def _extract_flow_chunked(self, overview: str, full_text: str) -> Dict:
        """Stage 2: Extract abstract attack flow by processing content iteratively in chunks"""
        print("  [Stage 2: Extracting abstract attack flow...]")

        # Split full text into chunks
        chunks = [full_text[i:i+self.chunk_size]
                 for i in range(0, len(full_text), self.chunk_size)]

        print(f"  Total chunks: {len(chunks)}")

        # Process chunks iteratively
        collected_goals = []

        for i, chunk in enumerate(chunks):
            print(f"    Processing chunk {i+1}/{len(chunks)}...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": self._build_chunk_prompt(overview, chunk, i+1, len(chunks), collected_goals)
                }]
            )

            result = self._parse_chunk_response(response.content[0].text)

            # Add newly found goals
            if result.get('new_goals'):
                collected_goals.extend(result['new_goals'])
                print(f"      Found {len(result['new_goals'])} new goals")

            # If report indicates completion, stop early
            if result.get('report_complete'):
                print(f"  [OK] Report analysis complete at chunk {i+1}/{len(chunks)}")
                break

        # Final synthesis: combine all goals into structured flow
        print(f"  [Synthesizing {len(collected_goals)} goals into abstract flow...]")
        abstract_flow = self._synthesize_flow(overview, collected_goals)

        return abstract_flow

    def _build_chunk_prompt(self, overview: str, chunk: str, chunk_num: int,
                           total_chunks: int, collected_goals: list) -> str:
        """Build prompt for chunk-by-chunk extraction"""

        previous_context = ""
        if collected_goals:
            goals_summary = "\n".join([f"  - [{g.get('tactic', 'unknown')}] {g.get('goal', 'Unknown')}"
                                      for g in collected_goals])
            previous_context = f"""
# Previously Identified Goals (from earlier chunks)
{goals_summary}
"""

        return f"""You are analyzing a KISA threat intelligence report chunk-by-chunk to extract attack goals.

# Overview
{overview}

{previous_context}
# Current Chunk ({chunk_num}/{total_chunks})
{chunk}

# Task
Analyze this chunk and identify any **NEW** attack goals not yet found.

For each new goal found:
1. What tactical objective does it represent?
2. Which MITRE ATT&CK tactic does it map to?
3. Brief description of its role in the attack chain

Focus on:
- Goals NOT already in the "Previously Identified Goals" list
- Environment-independent objectives (no IPs, URLs, credentials, specific tools)
- MITRE ATT&CK tactics: reconnaissance, initial-access, execution, persistence, privilege-escalation, defense-evasion, credential-access, discovery, lateral-movement, collection, command-and-control, exfiltration, impact

## Output Format (JSON only)

```json
{{
  "new_goals": [
    {{
      "goal": "Clear description of attack objective",
      "tactic": "MITRE ATT&CK tactic name",
      "description": "Brief explanation"
    }}
  ],
  "report_complete": true/false
}}
```

- `new_goals`: Array of NEW goals found in this chunk (empty array [] if none)
- `report_complete`: true if this chunk indicates end of attack description, false otherwise

**Output JSON only. No explanations.**"""

    def _parse_chunk_response(self, text: str) -> dict:
        """Parse JSON response from chunk analysis"""
        import json

        try:
            # Extract JSON
            if '```json' in text:
                json_text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                json_text = text.split('```')[1].split('```')[0].strip()
            else:
                json_text = text.strip()

            return json.loads(json_text)
        except Exception as e:
            print(f"      [WARNING] Failed to parse chunk response: {e}")
            return {"new_goals": [], "report_complete": False}

    def _synthesize_flow(self, overview: str, collected_goals: list) -> Dict:
        """Synthesize collected goals into final abstract flow structure"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"""You are organizing attack goals into a structured, logically-ordered abstract attack flow.

# Overview
{overview}

# Collected Attack Goals (in discovery order, NOT logical order)
{yaml.dump(collected_goals, allow_unicode=True)}

# Task
Reorganize these goals into a **logically correct attack flow** that respects dependencies and privilege requirements.

## Critical Ordering Rules

### 1. Privilege Dependencies
- Actions requiring elevated privileges MUST come AFTER privilege escalation
- Example: If lateral movement needs admin rights, privilege escalation must precede it
- Example: If data collection requires system privileges, escalation must come first

### 2. Logical Attack Progression
Follow typical attack lifecycle order:
1. **Reconnaissance** (if present) - Information gathering
2. **Initial Access** - Entry point establishment
3. **Execution** - Running code on target
4. **Persistence** - Maintaining access (early persistence)
5. **Privilege Escalation** - Gaining higher privileges
6. **Defense Evasion** - Avoiding detection (can be ongoing)
7. **Credential Access** - Stealing credentials (after escalation for better access)
8. **Discovery** - Internal reconnaissance (after gaining foothold)
9. **Lateral Movement** - Spreading to other systems (requires credentials/privileges)
10. **Collection** - Gathering target data (after reaching targets)
11. **Exfiltration** - Stealing data out (after collection)
12. **Impact** - Final damage (if present)

**Note**: Exclude "Command and Control" tactic - C2 infrastructure is provided by Caldera framework

### 3. Dependency Analysis
- If goal A provides resources needed for goal B → A must precede B
- Examples:
  * Credential harvesting → Lateral movement (credentials enable movement)
  * Discovery → Lateral movement (need to know targets before moving)
  * Collection → Exfiltration (need to collect before exfiltrating)

### 4. Merge Similar Goals
- If multiple goals represent the same tactical objective, merge or deduplicate them
- Keep the most descriptive version

## Required Output Structure

```yaml
attack_goals:
  # Goals reorganized in LOGICAL attack order (not discovery order!)
  # Consider privilege requirements and dependencies
  - goal: "..."
    tactic: "..."
    description: "..."

mitre_tactics:
  # Ordered list of unique tactics in chronological flow order
  - "tactic1"
  - "tactic2"

attack_flow_summary:
  # One-line chronological summary
  # Format: "Stage1 → Stage2 → Stage3 → ..."

required_capabilities:
  # General capability categories needed (alphabetical order)
  - "capability1"
  - "capability2"
```

## Example Reordering

**Input (discovery order):**
- Lateral movement to internal systems
- Privilege escalation to admin
- Data collection
- Initial access via web app

**Output (logical order):**
- Initial access via web app
- Privilege escalation to admin
- Lateral movement to internal systems (now has admin rights)
- Data collection

**Important**: Your output must reflect the ACTUAL goals provided, not the example. Reorder them logically while preserving all goals.

**Output YAML only. No explanations.**"""
            }]
        )

        try:
            yaml_text = self._extract_yaml(response.content[0].text)
            flow = yaml.safe_load(yaml_text)
            print(f"  [OK] Synthesized flow with {len(flow.get('attack_goals', []))} goals")
            return flow
        except Exception as e:
            print(f"  [ERROR] Failed to synthesize flow: {e}")
            raise

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
        print("Abstract Attack Flow Summary:")
        print("="*70)

        if 'attack_flow_summary' in flow:
            print(f"\nFlow: {flow['attack_flow_summary']}")

        if 'attack_goals' in flow:
            print(f"\nAttack Goals ({len(flow['attack_goals'])}):")
            for i, goal in enumerate(flow['attack_goals'], 1):
                print(f"  {i}. [{goal.get('tactic', 'unknown')}] {goal.get('goal', 'Unknown')}")

        if 'mitre_tactics' in flow:
            print(f"\nMITRE Tactics: {', '.join(flow['mitre_tactics'])}")

        if 'required_capabilities' in flow:
            print(f"\nRequired Capabilities: {', '.join(flow['required_capabilities'])}")

        print("="*70)


def main():
    """Test runner"""
    if len(sys.argv) < 3:
        print("Usage: python module2_abstract_flow.py <input_yml> <output_yml>")
        sys.exit(1)

    AbstractFlowExtractor().extract_abstract_flow(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
