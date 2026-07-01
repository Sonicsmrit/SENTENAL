import os
from pypdf import PdfReader

base = os.path.join("remittance-data")

reports = [
    os.path.join(base, "ceslam-status-of-remittances-nepal.pdf"),
]

for fpath in reports:
    fname = os.path.basename(fpath)
    print(f"\n=== {fname} ===")
    try:
        reader = PdfReader(fpath)
        print(f"  Pages: {len(reader.pages)}")
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and ("remittance" in text.lower() or "country" in text.lower() or "destination" in text.lower()):
                lines = text.split('\n')
                # Look for tables with numbers and countries
                country_lines = [l for l in lines if any(c in l for c in ["Saudi", "Qatar", "Malaysia", "UAE", "India"]) and any(c.isdigit() for c in l)]
                if country_lines:
                    print(f"\n  Page {i+1}:")
                    for l in country_lines[:5]:
                        print(f"    {l.strip()[:150]}")
    except Exception as e:
        print(f"  ERROR: {e}")
