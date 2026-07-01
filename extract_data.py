import csv, os, json

path = os.path.join("remittance-data", "knomad-bilateral", "WB_KNOMAD_WIDEF.csv")
OUTPUT_DIR = "remittance-data"

def parse_val(v):
    v = v.strip('"').strip()
    if v == "" or v == "..":
        return None
    try:
        return float(v)
    except ValueError:
        return None

with open(path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    
    # year column indices (0-indexed)
    year_indices = {}
    for i, h in enumerate(header):
        if h.isdigit() and 2000 <= int(h) <= 2030:
            year_indices[int(h)] = i
    
    remittance_data = []
    migrant_data = []
    
    for row in reader:
        if len(row) < max(year_indices.values()) + 1:
            continue
        
        ind = row[5].strip('"').strip()
        comp1 = row[10].strip('"').strip()
        ref = row[4].strip('"').strip()
        
        # --- Remittance to Nepal ---
        if ind == "WB_KNOMAD_BRE" and comp1 == "WB_KNOMAD_NPL" and ref != "WLD":
            country = row[22].strip('"').strip()
            for year, ci in year_indices.items():
                v = parse_val(row[ci])
                if v is not None:
                    remittance_data.append({
                        "country": country,
                        "country_code": ref,
                        "amount_usd_million": round(v, 2),
                        "amount_usd": round(v * 1_000_000),
                        "period": str(year)
                    })
        
        # --- Migrant stock from Nepal ---
        if ind == "WB_KNOMAD_MIG" and ref == "NPL":
            dest_label = row[28].strip('"').strip()
            dest_name = dest_label.replace("Destination: ", "")
            dest_code_raw = row[10].strip('"').strip()
            dest_code = dest_code_raw.replace("WB_KNOMAD_", "")
            for year, ci in year_indices.items():
                v = parse_val(row[ci])
                if v is not None:
                    migrant_data.append({
                        "country": dest_name,
                        "country_code": dest_code,
                        "migrant_stock": int(v),
                        "period": str(year)
                    })

# Sort by country then year
remittance_data.sort(key=lambda x: (x["country"], x["period"]))
migrant_data.sort(key=lambda x: (x["country"], x["period"]))

# Write remittance JSON
rem_file = os.path.join(OUTPUT_DIR, "remittance_by_country_annual.json")
with open(rem_file, "w", encoding="utf-8") as f:
    json.dump(remittance_data, f, indent=2, ensure_ascii=False)

# Write migrant JSON
mig_file = os.path.join(OUTPUT_DIR, "migrant_stock_by_country_annual.json")
with open(mig_file, "w", encoding="utf-8") as f:
    json.dump(migrant_data, f, indent=2, ensure_ascii=False)

print(f"Remittance records: {len(remittance_data)}")
print(f"  Countries: {len(set(r['country'] for r in remittance_data))}")
print(f"  Year range: {min(r['period'] for r in remittance_data)}-{max(r['period'] for r in remittance_data)}")
print(f"  Total 2021 (World excl): ${sum(r['amount_usd'] for r in remittance_data if r['period']=='2021'):,}")
print()
print(f"Migrant stock records: {len(migrant_data)}")
print(f"  Countries: {len(set(m['country'] for m in migrant_data))}")
print(f"  Year range: {min(m['period'] for m in migrant_data)}-{max(m['period'] for m in migrant_data)}")
print()

# Print top 10 by 2021
print("Top 10 remittance senders to Nepal (2021):")
top = [r for r in remittance_data if r["period"] == "2021"]
top.sort(key=lambda x: x["amount_usd"], reverse=True)
for r in top[:10]:
    b = r["amount_usd"] / 1e9
    print(f"  {r['country']:25s} ${b:.2f}B")
