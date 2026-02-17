"""
Rebuild documents_metadata.json from compliance_reports.json
Run this once to recover document metadata from existing reports
"""
import json
from pathlib import Path
from datetime import datetime

# File paths
REPORTS_FILE = Path("./data/compliance_reports.json")
METADATA_FILE = Path("./data/documents_metadata.json")

def rebuild_metadata():
    """Extract document metadata from compliance reports"""
    
    if not REPORTS_FILE.exists():
        print(f"ERROR: Reports file not found: {REPORTS_FILE}")
        return
    
    print(f"Reading reports from: {REPORTS_FILE}")
    
    with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
        reports_data = json.load(f)
    
    print(f"Found {len(reports_data)} reports")
    
    # Extract unique documents from reports
    documents_metadata = {}
    
    for report_id, report in reports_data.items():
        doc_id = report.get('document_id')
        doc_metadata = report.get('document_metadata', {})
        
        if doc_id and doc_id not in documents_metadata:
            documents_metadata[doc_id] = {
                "filename": doc_metadata.get('filename', 'unknown.pdf'),
                "document_type": doc_metadata.get('document_type', 'ESG Report'),
                "upload_date": doc_metadata.get('upload_date', datetime.now().isoformat()),
                "page_count": doc_metadata.get('page_count', 0),
                "year": doc_metadata.get('year'),
                "company_name": doc_metadata.get('company_name')
            }
            print(f"  - Found document: {documents_metadata[doc_id]['filename']}")
    
    # Save to documents_metadata.json
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(documents_metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\nRebuilt metadata for {len(documents_metadata)} documents")
    print(f"Saved to: {METADATA_FILE}")
    
    return documents_metadata

if __name__ == "__main__":
    print("Rebuilding documents metadata from compliance reports...\n")
    result = rebuild_metadata()
    
    if result:
        print("\nSUCCESS! Documents metadata has been recovered.")
        print("Now restart the backend to load the data.")
    else:
        print("\nFAILED to rebuild metadata.")
