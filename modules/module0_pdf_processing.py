"""
Module 0: PDF Processing
Extract text from PDF reports page by page
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
import pdfplumber
from dotenv import load_dotenv

load_dotenv()


class PDFProcessor:
    """Convert KISA TTPs PDF to structured data (page-based extraction)"""

    def process_pdf(self, pdf_path: str, output_path: str = None) -> Dict[str, Any]:
        """Extract PDF text page by page and save"""
        print(f"[PDF] Processing PDF: {pdf_path}")

        pages_data = self._extract_pages(pdf_path)
        toc_info = self._find_table_of_contents(pages_data)

        result = {
            "metadata": {
                "source": pdf_path,
                "total_pages": len(pages_data)
            },
            "table_of_contents": toc_info,
            "pages": pages_data
        }

        if output_path is None:
            output_path = "data/processed/step0_parsed.yml"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(result, f, allow_unicode=True, sort_keys=False)

        print(f"[SUCCESS] Saved to: {output_path}")
        print(f"  - Total pages: {len(pages_data)}")
        print(f"  - TOC found: {'Yes' if toc_info else 'No'}")
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

    def _find_table_of_contents(self, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find table of contents in first 5 pages"""
        print("  [INFO] Looking for table of contents in first 5 pages...")

        # Search in first 5 pages only
        for page_info in pages_data[:5]:
            text = page_info['text'].lower()
            page_num = page_info['page_number']

            # Common TOC indicators
            toc_keywords = ['목차', 'contents', 'table of contents', '차례']

            if any(keyword in text for keyword in toc_keywords):
                print(f"  [OK] Table of contents found on page {page_num}")
                return {
                    "found": True,
                    "page_number": page_num,
                    "text": page_info['text']
                }

        print("  [WARNING] Table of contents not found")
        return {"found": False}

def main():
    """Test runner"""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python module0_pdf_processing.py <pdf_path>")
        sys.exit(1)

    PDFProcessor().process_pdf(sys.argv[1])


if __name__ == "__main__":
    main()
