"""
Caldera API - Upload Abilities and Adversaries

기능:
1. abilities.yml 파싱 → Caldera API 업로드
2. adversaries.yml 파싱 → Caldera API 업로드
3. 업로드된 UUID 추적 파일 생성
"""

import requests
import yaml
import json
from pathlib import Path
from typing import List, Dict


class CalderaUploader:
    def __init__(self, base_url="http://localhost:8888", api_key="ADMIN123"):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'KEY': api_key})

        # 업로드된 ID 추적
        self.uploaded_ability_ids = []
        self.uploaded_adversary_ids = []

    def upload_abilities(self, abilities_file: str) -> List[str]:
        """Abilities 업로드"""
        print("\n" + "="*70)
        print("Abilities 업로드 시작")
        print("="*70)

        with open(abilities_file, 'r', encoding='utf-8') as f:
            abilities = yaml.safe_load(f)

        if not abilities:
            print("  [ERROR] No abilities found in file")
            return []

        print(f"  Total abilities to upload: {len(abilities)}")

        uploaded_ids = []
        for i, ability in enumerate(abilities, 1):
            ability_id = ability.get('ability_id')
            name = ability.get('name', 'Unknown')

            print(f"\n  [{i}/{len(abilities)}] Uploading: {name}")
            print(f"    ID: {ability_id}")

            # API 호출
            url = f"{self.base_url}/api/v2/abilities"
            response = self.session.post(
                url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(ability)
            )

            if response.status_code == 200:
                print(f"    [OK] Success")
                uploaded_ids.append(ability_id)
                self.uploaded_ability_ids.append(ability_id)
            else:
                print(f"    [FAILED] Status: {response.status_code}")
                print(f"    Error: {response.text[:200]}")

        print(f"\n{'='*70}")
        print(f"Abilities 업로드 완료: {len(uploaded_ids)}/{len(abilities)} 성공")
        print(f"{'='*70}")

        return uploaded_ids

    def upload_adversaries(self, adversaries_file: str) -> List[str]:
        """Adversaries 업로드"""
        print("\n" + "="*70)
        print("Adversaries 업로드 시작")
        print("="*70)

        with open(adversaries_file, 'r', encoding='utf-8') as f:
            adversaries = yaml.safe_load(f)

        if not adversaries:
            print("  [ERROR] No adversaries found in file")
            return []

        print(f"  Total adversaries to upload: {len(adversaries)}")

        uploaded_ids = []
        for i, adversary in enumerate(adversaries, 1):
            adversary_id = adversary.get('adversary_id')
            name = adversary.get('name', 'Unknown')
            ability_count = len(adversary.get('atomic_ordering', []))

            print(f"\n  [{i}/{len(adversaries)}] Uploading: {name}")
            print(f"    ID: {adversary_id}")
            print(f"    Abilities: {ability_count}")

            # API 호출
            url = f"{self.base_url}/api/v2/adversaries"
            response = self.session.post(
                url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(adversary)
            )

            if response.status_code == 200:
                print(f"    [OK] Success")
                uploaded_ids.append(adversary_id)
                self.uploaded_adversary_ids.append(adversary_id)
            else:
                print(f"    [FAILED] Status: {response.status_code}")
                print(f"    Error: {response.text[:200]}")

        print(f"\n{'='*70}")
        print(f"Adversaries 업로드 완료: {len(uploaded_ids)}/{len(adversaries)} 성공")
        print(f"{'='*70}")

        return uploaded_ids

    def save_tracking_file(self, output_file: str):
        """업로드된 ID 추적 파일 저장"""
        tracking_data = {
            'abilities': self.uploaded_ability_ids,
            'adversaries': self.uploaded_adversary_ids,
            'metadata': {
                'total_abilities': len(self.uploaded_ability_ids),
                'total_adversaries': len(self.uploaded_adversary_ids)
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(tracking_data, f, allow_unicode=True, sort_keys=False)

        print(f"\n[OK] Tracking file saved: {output_file}")
        print(f"  - Abilities: {len(self.uploaded_ability_ids)}")
        print(f"  - Adversaries: {len(self.uploaded_adversary_ids)}")


def main():
    """Upload abilities and adversaries to Caldera"""
    import sys
    import os
    import argparse

    parser = argparse.ArgumentParser(description="Upload abilities and adversaries to Caldera")
    parser.add_argument("--caldera-dir", type=str, help="Caldera output directory (e.g., data/processed/20251203_142900/caldera)")
    parser.add_argument("--abilities", type=str, help="Path to abilities.yml file")
    parser.add_argument("--adversaries", type=str, help="Path to adversaries.yml file")

    args = parser.parse_args()

    # caldera-dir이 주어진 경우 자동으로 파일 경로 생성
    if args.caldera_dir:
        caldera_dir = Path(args.caldera_dir)
        abilities_file = str(caldera_dir / "abilities.yml")
        adversaries_file = str(caldera_dir / "adversaries.yml")
    elif args.abilities and args.adversaries:
        abilities_file = args.abilities
        adversaries_file = args.adversaries
    else:
        print("Usage:")
        print("  Option 1: python upload_to_caldera.py --caldera-dir <caldera_directory>")
        print("  Option 2: python upload_to_caldera.py --abilities <abilities.yml> --adversaries <adversaries.yml>")
        print("\nExample:")
        print("  python upload_to_caldera.py --caldera-dir data/processed/20251203_142900/caldera")
        print("  python upload_to_caldera.py --abilities data/processed/20251203_142900/caldera/abilities.yml --adversaries data/processed/20251203_142900/caldera/adversaries.yml")
        sys.exit(1)

    # 파일 존재 확인
    if not Path(abilities_file).exists():
        print(f"[ERROR] File not found: {abilities_file}")
        sys.exit(1)

    if not Path(adversaries_file).exists():
        print(f"[ERROR] File not found: {adversaries_file}")
        sys.exit(1)

    # Uploader 생성
    uploader = CalderaUploader()

    # Abilities 업로드
    uploader.upload_abilities(abilities_file)

    # Adversaries 업로드
    uploader.upload_adversaries(adversaries_file)

    # 추적 파일은 같은 디렉토리에 저장
    caldera_dir = Path(abilities_file).parent
    tracking_file = caldera_dir / "uploaded_ids.yml"
    uploader.save_tracking_file(str(tracking_file))

    print("\n" + "="*70)
    print("[SUCCESS] Upload completed successfully!")
    print("="*70)
    print(f"\nTo delete uploaded items, run:")
    print(f"  python delete_from_caldera.py {tracking_file}")


if __name__ == "__main__":
    main()
