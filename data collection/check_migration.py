import os
from pypdf import PdfReader

base = os.path.join("remittance-data")
fpath = os.path.join(base, "diaspora-data", "Nepal-Labour-Migration-Report-2024.pdf")

print(f"=== Nepal Labour Migration Report 2024 ===")
try:
    reader = PdfReader(fpath)
    print(f"  Pages: {len(reader.pages)}")
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and ("remittance" in text.lower() or "labour approval" in text.lower()):
            lines = text.split('\n')
            # Look for country tables
            country_lines = [l for l in lines if any(c in l for c in ["Saudi", "Qatar", "Malaysia", "UAE", "India", "Korea", "Japan"]) and any(c.isdigit() for c in l)]
            if country_lines:
                print(f"\n  Page {i+1}:")
                for l in country_lines[:5]:
                    print(f"    {l.strip()[:180]}")
except Exception as e:
    print(f"  ERROR: {e}")
