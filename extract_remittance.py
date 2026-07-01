import csv
import json
import os

CSV_PATH = os.path.join("remittance-data", "knomad-bilateral", "WB_KNOMAD_WIDEF.csv")
OUTPUT_DIR = "remittance-data"

YEAR_COLS = list(range(40, 64))  # columns 40-63 = years 2000-2023

def parse_value(val):
    """Parse CSV value to float or None"""
    v = val.strip().strip('"')
    if v == "" or v == "..":
        return None
    try:
        return float(v)
    except ValueError:
        return None

def extract_remittance_by_country():
    """Extract bilateral remittance estimates to Nepal, by sending country, per year"""
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 64:
                continue
            indicator = row[5].strip().strip('"')
            comp1 = row[10].strip().strip('"')
            if indicator == "WB_KNOMAD_BRE" and comp1 == "WB_KNOMAD_NPL":
                sending_country = row[22].strip().strip('"')
                sending_code = row[4].strip().strip('"')
                for ci in YEAR_COLS:
                    year = header[ci].strip().strip('"')
                    val = parse_value(row[ci])
                    if val is not None:
                        rows.append({
                            "country": sending_country,
                            "country_code": sending_code,
                            "amount_usd_million": round(val, 2),
                            "amount_usd": round(val * 1_000_000),
                            "period": year
                        })
    return rows

def extract_migrant_stock():
    """Extract bilateral migrant stock estimates for Nepal, by destination country"""
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 64:
                continue
            indicator = row[5].strip().strip('"')
            ref_area = row[4].strip().strip('"')
            if indicator == "WB_KNOMAD_MIG" and ref_area == "NPL":
                dest_country_label = row[28].strip().strip('"')
                # Extract destination name from label like "Destination: Malaysia"
                dest_parts = dest_country_label.replace("Destination: ", "").replace(" destination: ", "")
                dest_code_raw = row[10].strip().strip('"')
                dest_code = dest_code_raw.replace("WB_KNOMAD_", "")
                for ci in YEAR_COLS:
                    year = header[ci].strip().strip('"')
                    val = parse_value(row[ci])
                    if val is not None:
                        rows.append({
                            "country": dest_parts,
                            "country_code": dest_code,
                            "migrant_stock": int(val),
                            "period": year
                        })
    return rows

# --- Extract remittance data ---
print("Extracting remittance data...")
remittance = extract_remittance_by_country()
remittance_file = os.path.join(OUTPUT_DIR, "remittance_by_country_annual.json")
with open(remittance_file, "w", encoding="utf-8") as f:
    json.dump(remittance, f, indent=2, ensure_ascii=False)
print(f"  -> {len(remittance)} records written to {remittance_file}")

# --- Extract migrant stock data ---
print("Extracting migrant stock data...")
migrants = extract_migrant_stock()
migrants_file = os.path.join(OUTPUT_DIR, "migrant_stock_by_country_annual.json")
with open(migrants_file, "w", encoding="utf-8") as f:
    json.dump(migrants, f, indent=2, ensure_ascii=False)
print(f"  -> {len(migrants)} records written to {migrants_file}")

# --- Summary ---
print("\n--- Remittance Summary (Top senders, 2023) ---")
rem_2023 = [r for r in remittance if r["period"] == "2023"]
rem_2023.sort(key=lambda x: x["amount_usd"], reverse=True)
for r in rem_2023[:15]:
    amt_b = r["amount_usd"] / 1e9
    print(f"  {r['country']:25s} (${amt_b:.2f}B)")

print(f"\n--- Migrant Stock Summary (Top destinations, 2023) ---")
mig_2023 = [m for m in migrants if m["period"] == "2023"]
mig_2023.sort(key=lambda x: x["migrant_stock"], reverse=True)
for m in mig_2023[:15]:
    print(f"  {m['country']:25s} {m['migrant_stock']:>8,}")
