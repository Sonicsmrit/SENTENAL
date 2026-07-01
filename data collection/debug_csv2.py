import csv, os

path = os.path.join("remittance-data", "knomad-bilateral", "WB_KNOMAD_WIDEF.csv")
with open(path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    
    # Print column index for each year header
    for i, h in enumerate(header):
        if h in ('2000','2001','2002','2003','2004','2005','2006','2007','2008','2009','2010','2011','2012','2013','2014','2015','2016','2017','2018','2019','2020','2021','2022','2023'):
            print(f"  Header index {i} = {h}")
    
    for row in reader:
        if len(row) > 62:
            ind = row[5].strip('"').strip()
            comp = row[10].strip('"').strip()
            ref = row[4].strip('"').strip()
            if ind == "WB_KNOMAD_BRE" and comp == "WB_KNOMAD_NPL" and ref == "QAT":
                print(f"Row length: {len(row)}")
                for i in range(39, 63):
                    print(f"  [{i}] {header[i]} = '{row[i]}'")
                break
