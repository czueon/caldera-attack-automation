"""
Caldera API - Delete Abilities and Adversaries

기능:
1. uploaded_ids.yml 읽기
2. 추적된 Adversaries 삭제 (먼저)
3. 추적된 Abilities 삭제 (나중)
"""

import requests
import yaml
from pathlib import Path
from typing import List


class CalderaDeleter:
    def __init__(self, base_url="http://localhost:8888", api_key="ADMIN123"):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'KEY': api_key})

        # 삭제 통계
        self.deleted_abilities = 0
        self.deleted_adversaries = 0
        self.failed_abilities = 0
        self.failed_adversaries = 0

    def delete_adversaries(self, adversary_ids: List[str]):
        """Adversaries 삭제 (먼저 삭제해야 함)"""
        if not adversary_ids:
            print("\n  No adversaries to delete")
            return

        print("\n" + "="*70)
        print("Adversaries 삭제 시작")
        print("="*70)
        print(f"  Total adversaries to delete: {len(adversary_ids)}")

        for i, adversary_id in enumerate(adversary_ids, 1):
            print(f"\n  [{i}/{len(adversary_ids)}] Deleting adversary: {adversary_id[:8]}...")

            url = f"{self.base_url}/api/v2/adversaries/{adversary_id}"
            response = self.session.delete(url)

            if response.status_code == 200:
                print(f"    [OK] Deleted successfully")
                self.deleted_adversaries += 1
            elif response.status_code == 404:
                print(f"    [WARNING] Not found (already deleted?)")
                self.deleted_adversaries += 1
            else:
                print(f"    [FAILED] Status: {response.status_code}")
                print(f"    Error: {response.text[:200]}")
                self.failed_adversaries += 1

        print(f"\n{'='*70}")
        print(f"Adversaries 삭제 완료: {self.deleted_adversaries} 성공, {self.failed_adversaries} 실패")
        print(f"{'='*70}")

    def delete_abilities(self, ability_ids: List[str]):
        """Abilities 삭제"""
        if not ability_ids:
            print("\n  No abilities to delete")
            return

        print("\n" + "="*70)
        print("Abilities 삭제 시작")
        print("="*70)
        print(f"  Total abilities to delete: {len(ability_ids)}")

        for i, ability_id in enumerate(ability_ids, 1):
            print(f"\n  [{i}/{len(ability_ids)}] Deleting ability: {ability_id[:8]}...")

            url = f"{self.base_url}/api/v2/abilities/{ability_id}"
            response = self.session.delete(url)

            if response.status_code == 200:
                print(f"    [OK] Deleted successfully")
                self.deleted_abilities += 1
            elif response.status_code == 404:
                print(f"    [WARNING] Not found (already deleted?)")
                self.deleted_abilities += 1
            else:
                print(f"    [FAILED] Status: {response.status_code}")
                print(f"    Error: {response.text[:200]}")
                self.failed_abilities += 1

        print(f"\n{'='*70}")
        print(f"Abilities 삭제 완료: {self.deleted_abilities} 성공, {self.failed_abilities} 실패")
        print(f"{'='*70}")

    def print_summary(self):
        """삭제 요약 출력"""
        print("\n" + "="*70)
        print("삭제 요약")
        print("="*70)
        print(f"  Adversaries: {self.deleted_adversaries} 삭제, {self.failed_adversaries} 실패")
        print(f"  Abilities: {self.deleted_abilities} 삭제, {self.failed_abilities} 실패")
        print("="*70)


def main():
    """Delete abilities and adversaries from Caldera"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python delete_from_caldera.py <uploaded_ids.yml>")
        print("\nExample:")
        print("  python delete_from_caldera.py data/processed/caldera/uploaded_ids.yml")
        sys.exit(1)

    tracking_file = sys.argv[1]

    # 파일 존재 확인
    if not Path(tracking_file).exists():
        print(f"[ERROR] File not found: {tracking_file}")
        sys.exit(1)

    # 추적 파일 로드
    with open(tracking_file, 'r', encoding='utf-8') as f:
        tracking_data = yaml.safe_load(f)

    ability_ids = tracking_data.get('abilities', [])
    adversary_ids = tracking_data.get('adversaries', [])

    print("\n" + "="*70)
    print("Caldera 삭제 시작")
    print("="*70)
    print(f"  Tracking file: {tracking_file}")
    print(f"  Adversaries to delete: {len(adversary_ids)}")
    print(f"  Abilities to delete: {len(ability_ids)}")

    # 확인
    confirm = input("\n[WARNING] 정말 삭제하시겠습니까? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("\n[CANCELLED] 삭제 취소")
        sys.exit(0)

    # Deleter 생성
    deleter = CalderaDeleter()

    # 순서 중요: Adversaries 먼저 삭제 (Abilities를 참조하므로)
    deleter.delete_adversaries(adversary_ids)

    # Abilities 삭제
    deleter.delete_abilities(ability_ids)

    # 요약 출력
    deleter.print_summary()

    # 추적 파일 삭제 여부 확인
    delete_tracking = input(f"\n추적 파일도 삭제하시겠습니까? ({tracking_file}) (yes/no): ")
    if delete_tracking.lower() in ['yes', 'y']:
        Path(tracking_file).unlink()
        print(f"[OK] Tracking file deleted: {tracking_file}")

    print("\n[SUCCESS] Deletion completed!")


if __name__ == "__main__":
    main()
