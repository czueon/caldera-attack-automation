"""
Module 2: Abstract Attack Flow Extraction
Extract environment-independent abstract attack flow from KISA report
Uses 2-stage extraction: overview → detailed flow
"""

import yaml
import os
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


class AbstractFlowExtractor:
    def __init__(self):
        self.llm = get_llm_client()
        self.prompt_manager = PromptManager()
        self.chunk_size = 8000  # 청크 크기 (characters)

    def extract_abstract_flow(self, input_file: str, output_file: str = None, version_id: str = None):
        """Extract abstract attack flow from KISA report (PDF parsed data)

        2-stage process:
        1. Extract overview to understand attack theme
        2. Process detailed content in chunks to extract complete attack flow
        """
        print("\n[Step 2] Abstract Attack Flow Extraction started...")

        with open(input_file, 'r', encoding='utf-8') as f:
            step1_data = yaml.safe_load(f)

        metadata = step1_data.get('metadata', {})
        # pdf_name, version_id 우선 추출 (경로 → 메타데이터 → 기본값)
        pdf_name = metadata.get('pdf_name')
        if not pdf_name:
            pdf_name = Path(input_file).stem.replace("_parsed", "")
            # 경로 규칙상 data/processed/{pdf}/{version}/{file} 구조면 상위 폴더에서 가져옴
            if Path(input_file).parents:
                pdf_name = Path(input_file).parent.parent.name or pdf_name

        derived_version = (
            version_id
            or metadata.get('version_id')
            or Path(input_file).parent.name  # data/processed/{pdf}/{version}/
        )
        version_id = derived_version or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Extract pages text from step1
        pages = step1_data.get('pages', [])

        if not pages:
            raise ValueError("No pages found in Step 1 output")

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
                'pdf_name': pdf_name,
                'version_id': version_id,
                'step': 2,
                'description': 'Environment-independent abstract attack flow'
            },
            'abstract_flow': abstract_flow
        }

        # output_file 미지정 시 data/processed/{pdf}/{version}/{pdf}_step2.yml 사용
        if output_file is None:
            output_file = Path("../../data/processed") / pdf_name / version_id / f"{pdf_name}_step2.yml"

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Abstract flow extraction completed -> {output_file}")
        print(f"  - PDF: {pdf_name}")
        print(f"  - Version: {version_id}")
        self._print_summary(abstract_flow)

    def _extract_overview(self, full_text: str) -> str:
        """Stage 1: Extract overview section from report"""
        print("  [Stage 1: Extracting overview...]")

        # Take first 3000 characters for overview
        overview_chunk = full_text[:3000]

        prompt = self.prompt_manager.render(
            "step2_overview.yaml",
            overview_chunk=overview_chunk
        )

        # Generate using LLM
        overview = self.llm.generate_text(prompt=prompt, max_tokens=1500)
        return overview.strip()

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

            # Build prompt using template
            prompt = self._build_chunk_prompt(overview, chunk, i+1, len(chunks), collected_goals)

            # Generate using LLM
            response_text = self.llm.generate_text(prompt=prompt, max_tokens=3000)

            result = self._parse_chunk_response(response_text)

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
            previous_context = f"""# Previously Identified Goals (from earlier chunks)
{goals_summary}
"""

        return self.prompt_manager.render(
            "step2_chunk.yaml",
            overview=overview,
            previous_context=previous_context,
            chunk_num=chunk_num,
            total_chunks=total_chunks,
            chunk=chunk
        )

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

        # Prepare collected goals as YAML string
        collected_goals_yaml = yaml.dump(collected_goals, allow_unicode=True)

        prompt = self.prompt_manager.render(
            "step2_synthesize.yaml",
            overview=overview,
            collected_goals=collected_goals_yaml
        )

        # Generate using LLM
        response_text = self.llm.generate_text(prompt=prompt, max_tokens=4000)

        try:
            yaml_text = self._extract_yaml(response_text)
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
            tactics = [t for t in flow['mitre_tactics'] if t is not None]
            print(f"\nMITRE Tactics: {', '.join(tactics)}")

        if 'required_capabilities' in flow:
            capabilities = [c for c in flow['required_capabilities'] if c is not None]
            print(f"\nRequired Capabilities: {', '.join(capabilities)}")

        print("="*70)


def main():
    """Test runner"""
    if len(sys.argv) < 2:
        print("Usage: python step2_abstract_flow.py <input_yml> [output_yml] [version_id]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else None
    version_id = sys.argv[3] if len(sys.argv) >= 4 else None

    AbstractFlowExtractor().extract_abstract_flow(input_file, output_file, version_id)


if __name__ == "__main__":
    main()
