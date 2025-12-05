"""
Caldera API - Upload Abilities and Adversaries

기능:
1. abilities.yml 파싱 → Caldera API 업로드 (upsert)
2. adversaries.yml 파싱 → Caldera API 업로드 (upsert)
3. 수정된 ability만 업데이트 (--update-corrected)
"""

import sys
import argparse
import requests
import yaml
import json
from pathlib import Path
from typing import List


class CalderaUploader:
    def __init__(self, base_url="http://localhost:8888", api_key="ADMIN123"):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'KEY': api_key,
            'Content-Type': 'application/json'
        })
        self.uploaded_ability_ids = []
        self.uploaded_adversary_ids = []

    def _upsert(self, endpoint: str, item_id: str, data: dict) -> tuple[bool, str]:
        """공통 upsert 로직: 존재하면 PUT, 없으면 POST"""
        check_url = f"{self.base_url}/api/v2/{endpoint}/{item_id}"
        exists = self.session.get(check_url).status_code == 200

        if exists:
            response = self.session.put(check_url, data=json.dumps(data))
            action = "UPDATE"
        else:
            url = f"{self.base_url}/api/v2/{endpoint}"
            response = self.session.post(url, data=json.dumps(data))
            action = "CREATE"

        return response.status_code == 200, action

    def upload_abilities(self, abilities_file: str) -> List[str]:
        """Abilities 업로드 (upsert)"""
        print("\n" + "="*70)
        print("Abilities 업로드")
        print("="*70)

        with open(abilities_file, 'r', encoding='utf-8') as f:
            abilities = yaml.safe_load(f) or []

        if not abilities:
            print("  [ERROR] No abilities found")
            return []

        uploaded_ids = []
        created, updated = 0, 0

        for i, ability in enumerate(abilities, 1):
            ability_id = ability.get('ability_id')
            print(f"  [{i}/{len(abilities)}] {ability.get('name', 'Unknown')}")

            success, action = self._upsert('abilities', ability_id, ability)
            if success:
                print(f"    [OK] {action}")
                uploaded_ids.append(ability_id)
                self.uploaded_ability_ids.append(ability_id)
                created += 1 if action == "CREATE" else 0
                updated += 1 if action == "UPDATE" else 0
            else:
                print(f"    [FAILED]")

        print(f"\n  완료: {len(uploaded_ids)}/{len(abilities)} (신규: {created}, 수정: {updated})")
        return uploaded_ids

    def upload_adversaries(self, adversaries_file: str) -> List[str]:
        """Adversaries 업로드 (upsert)"""
        print("\n" + "="*70)
        print("Adversaries 업로드")
        print("="*70)

        with open(adversaries_file, 'r', encoding='utf-8') as f:
            adversaries = yaml.safe_load(f) or []

        if not adversaries:
            print("  [ERROR] No adversaries found")
            return []

        uploaded_ids = []
        created, updated = 0, 0

        for i, adversary in enumerate(adversaries, 1):
            adversary_id = adversary.get('adversary_id')
            print(f"  [{i}/{len(adversaries)}] {adversary.get('name', 'Unknown')}")

            success, action = self._upsert('adversaries', adversary_id, adversary)
            if success:
                print(f"    [OK] {action}")
                uploaded_ids.append(adversary_id)
                self.uploaded_adversary_ids.append(adversary_id)
                created += 1 if action == "CREATE" else 0
                updated += 1 if action == "UPDATE" else 0
            else:
                print(f"    [FAILED]")

        print(f"\n  완료: {len(uploaded_ids)}/{len(adversaries)} (신규: {created}, 수정: {updated})")
        return uploaded_ids

    def update_corrected_abilities(self, abilities_file: str, correction_report: str) -> List[str]:
        """수정된 Ability만 업데이트"""
        print("\n" + "="*70)
        print("수정된 Abilities 업데이트")
        print("="*70)

        with open(correction_report, 'r', encoding='utf-8') as f:
            report = json.load(f)

        corrected_ids = {
            c['ability_id'] for c in report.get('corrections', [])
            if c.get('success', False)
        }

        if not corrected_ids:
            print("  [INFO] 수정된 ability가 없습니다")
            return []

        with open(abilities_file, 'r', encoding='utf-8') as f:
            abilities = yaml.safe_load(f) or []

        to_update = [a for a in abilities if a.get('ability_id') in corrected_ids]
        updated_ids = []

        for i, ability in enumerate(to_update, 1):
            ability_id = ability.get('ability_id')
            print(f"  [{i}/{len(to_update)}] {ability.get('name', 'Unknown')}")

            url = f"{self.base_url}/api/v2/abilities/{ability_id}"
            response = self.session.put(url, data=json.dumps(ability))

            if response.status_code == 200:
                print(f"    [OK] Updated")
                updated_ids.append(ability_id)
            else:
                print(f"    [FAILED]")

        print(f"\n  완료: {len(updated_ids)}/{len(to_update)}")
        return updated_ids

    def save_tracking_file(self, output_file: str):
        """업로드된 ID 추적 파일 저장"""
        tracking_data = {
            'abilities': self.uploaded_ability_ids,
            'adversaries': self.uploaded_adversary_ids
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(tracking_data, f, allow_unicode=True, sort_keys=False)
        print(f"\n[OK] Tracking file: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload abilities and adversaries to Caldera",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
예시:
  # 전체 업로드 (upsert)
  python upload_to_caldera.py --caldera-dir data/processed/20251203_142900/caldera

  # M7 수정 후 수정된 ability만 업데이트
  python upload_to_caldera.py --caldera-dir data/processed/20251203_142900/caldera --update-corrected
"""
    )
    parser.add_argument("--caldera-dir", type=str, required=True, help="Caldera output directory")
    parser.add_argument("--update-corrected", action="store_true", help="수정된 ability만 업데이트")

    args = parser.parse_args()
    caldera_dir = Path(args.caldera_dir)

    # 파일 경로
    abilities_file = caldera_dir / "abilities.yml"
    adversaries_file = caldera_dir / "adversaries.yml"
    correction_report = caldera_dir / "correction_report.json"

    uploader = CalderaUploader()

    # 모드 1: 수정된 ability만 업데이트
    if args.update_corrected:
        if not correction_report.exists():
            print(f"[ERROR] File not found: {correction_report}")
            sys.exit(1)
        if not abilities_file.exists():
            print(f"[ERROR] File not found: {abilities_file}")
            sys.exit(1)

        uploader.update_corrected_abilities(str(abilities_file), str(correction_report))
        print("\n[SUCCESS] Update completed!")
        return

    # 모드 2: 전체 업로드
    if not abilities_file.exists():
        print(f"[ERROR] File not found: {abilities_file}")
        sys.exit(1)
    if not adversaries_file.exists():
        print(f"[ERROR] File not found: {adversaries_file}")
        sys.exit(1)

    uploader.upload_abilities(str(abilities_file))
    uploader.upload_adversaries(str(adversaries_file))

    tracking_file = caldera_dir / "uploaded_ids.yml"
    uploader.save_tracking_file(str(tracking_file))

    print("\n[SUCCESS] Upload completed!")
    print(f"\nTo delete: python delete_from_caldera.py {tracking_file}")


if __name__ == "__main__":
    main()
