import csv, os

path = os.path.join("remittance-data", "knomad-bilateral", "WB_KNOMAD_WIDEF.csv")
with open(path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    
    results = []
    for row in reader:
        if len(row) > 62:
            ind = row[5].strip('"').strip()
            comp = row[10].strip('"').strip()
            if ind == "WB_KNOMAD_BRE" and comp == "WB_KNOMAD_NPL":
                country = row[22].strip('"')
                code = row[4].strip('"').strip()
                vals = {}
                for i in range(39, 63):
                    y = header[i]
                    v = row[i].strip('"').strip()
                    if v and v != '..':
                        vals[y] = float(v)
                if vals:
                    results.append((country, code, vals))
    
    results.sort(key=lambda x: x[2].get('2023', 0), reverse=True)
    print(f"{'Country':25s} {'Code':5s} {'2021':>12s} {'2022':>12s} {'2023':>12s}")
    print("-" * 70)
    for country, code, vals in results:
        v2021 = vals.get('2021', 0)
        v2022 = vals.get('2022', 0)
        v2023 = vals.get('2023', 0)
        if v2021 > 0 or v2022 > 0 or v2023 > 0:
            print(f"{country:25s} {code:5s} {v2021:>12.2f} {v2022:>12.2f} {v2023:>12.2f}")
    
    print(f"\nTotal countries with any data: {len(results)}")
    print(f"Countries with 2023 data: {sum(1 for _,_,v in results if '2023' in v)}")
    print(f"Countries with 2022 data: {sum(1 for _,_,v in results if '2022' in v)}")
    print(f"Countries with 2021 data: {sum(1 for _,_,v in results if '2021' in v)}")
