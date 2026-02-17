"""Test loading documents metadata"""
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.models import DocumentMetadata

DOCUMENTS_METADATA_FILE = Path("./data/documents_metadata.json")

def test_load():
    try:
        with open(DOCUMENTS_METADATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Loaded JSON data: {len(data)} documents")
        
        documents_metadata = {}
        for doc_id, meta in data.items():
            print(f"\nProcessing document {doc_id}:")
            print(f"  filename: {meta['filename']}")
            print(f"  document_type: {meta.get('document_type', 'ESG Report')}")
            print(f"  upload_date: {meta['upload_date']}")
            print(f"  page_count: {meta['page_count']}")
            
            try:
                documents_metadata[doc_id] = DocumentMetadata(
                    filename=meta["filename"],
                    document_type=meta.get("document_type", "ESG Report"),
                    upload_date=datetime.fromisoformat(meta["upload_date"]),
                    page_count=meta["page_count"],
                    year=meta.get("year"),
                    company_name=meta.get("company_name")
                )
                print(f"  SUCCESS: Created DocumentMetadata")
            except Exception as e:
                print(f"  ERROR creating DocumentMetadata: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n\nFinal result: {len(documents_metadata)} documents loaded")
        return documents_metadata
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_load()
