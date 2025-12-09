"""
Module 1: PDF Processing
Extract text from PDF reports page by page
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import yaml
import pdfplumber
from dotenv import load_dotenv

load_dotenv()


class PDFProcessor:
    """Convert KISA TTPs PDF to structured data (page-based extraction)"""

    def process_pdf(self, pdf_path: str, output_path: str = None, version_id: str = None) -> Dict[str, Any]:
        """Extract PDF text page by page and save"""
        print(f"[PDF] Processing PDF: {pdf_path}")

        pages_data = self._extract_pages(pdf_path)

        pdf_stem = Path(pdf_path).stem
        # version_id가 없으면 타임스탬프로 생성하여 폴더/파일명에 포함
        version_id = version_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        result = {
            "metadata": {
                "source": pdf_path,
                "pdf_name": pdf_stem,
                "version_id": version_id,
                "total_pages": len(pages_data)
            },
            "pages": pages_data
        }

        if output_path is None:
            # 지정 경로 없으면 data/processed/{pdf이름}/{version_id}/{pdf이름}_parsed.yml로 저장
            output_path = Path("../../data/processed") / pdf_stem / version_id / f"{pdf_stem}_parsed.yml"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(result, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Saved to: {output_path}")
        print(f"  - Total pages: {len(pages_data)}")
        return result

    def _extract_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text from each page separately"""
        with pdfplumber.open(pdf_path) as pdf:
            print(f"  [INFO] Processing {len(pdf.pages)} pages...")

            pages_data = []
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    pages_data.append({
                        "page_number": page_num,
                        "text": text
                    })

            print(f"  [OK] Text extraction completed")
            return pages_data

def main():
    """Test runner"""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python step1_pdf_processing.py <pdf_path> [version_id]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    version_id = sys.argv[2] if len(sys.argv) >= 3 else None
    PDFProcessor().process_pdf(pdf_path, version_id=version_id)


if __name__ == "__main__":
    main()
