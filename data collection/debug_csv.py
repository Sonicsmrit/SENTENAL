import csv, os

path = os.path.join("remittance-data", "knomad-bilateral", "WB_KNOMAD_WIDEF.csv")
with open(path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    print(f"Header cols: {len(header)}")
    print(f"Year columns: {header[40:64]}")
    count_bre = 0
    count_bre_npl = 0
    count_mig_npl = 0
    total = 0
    for row in reader:
        total += 1
        if len(row) > 10:
            ind = row[5].strip('"').strip()
            comp = row[10].strip('"').strip()
            ref = row[4].strip('"').strip()
            if ind == "WB_KNOMAD_BRE":
                count_bre += 1
                if comp == "WB_KNOMAD_NPL":
                    count_bre_npl += 1
                    if count_bre_npl <= 3:
                        from_country = row[22].strip('"')
                        val_2023 = row[62].strip('"')
                        print(f"BRE-NPL: from={from_country} code={ref} 2023=${val_2023}")
            if ind == "WB_KNOMAD_MIG" and ref == "NPL":
                count_mig_npl += 1
                if count_mig_npl <= 3:
                    dest = row[28].strip('"')
                    val_2023 = row[62].strip('"')
                    print(f"MIG-NPL-to: {dest} 2023={val_2023}")

    print(f"\nTotal rows: {total}")
    print(f"Total BRE rows: {count_bre}")
    print(f"BRE rows with NPL destination: {count_bre_npl}")
    print(f"MIG rows with NPL origin: {count_mig_npl}")
