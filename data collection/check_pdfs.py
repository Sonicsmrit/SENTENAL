import os, json, re
from pypdf import PdfReader

pdf_dir = os.path.join("remittance-data", "nrb-annual-reports")
output_dir = "remittance-data"

# Try to extract text from all PDFs and search for remittance tables
for fname in sorted(os.listdir(pdf_dir)):
    if not fname.endswith(".pdf"):
        continue
    fpath = os.path.join(pdf_dir, fname)
    print(f"\n=== {fname} ===")
    try:
        reader = PdfReader(fpath)
        print(f"  Pages: {len(reader.pages)}")
        
        # Search for "remittance" or "remittance" in each page
        remittance_pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and ("remittance" in text.lower() or "remittance" in text.lower()):
                remittance_pages.append((i, text))
        
        print(f"  Pages mentioning remittance: {len(remittance_pages)}")
        
        # For first 3 remittance pages, show context
        for page_num, text in remittance_pages[:5]:
            # Find lines with "remittance"
            lines = text.split('\n')
            relevant = [l for l in lines if 'remittance' in l.lower() or 'remittance' in l.lower()]
            if relevant:
                print(f"\n  Page {page_num+1} - remittance mentions:")
                for l in relevant[:10]:
                    print(f"    {l.strip()[:120]}")
    except Exception as e:
        print(f"  ERROR: {e}")
