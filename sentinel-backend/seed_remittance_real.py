import json
import sys
sys.path.append(".")

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal, init_db
from app.models.schema import RemittanceRecord

init_db()
db = SessionLocal()

with open("data/remittance_breakdown_final.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Countries we care about for SENTINEL
TARGET_COUNTRIES = ["Qatar", "Malaysia", "UAE", "Saudi Arabia", "South Korea", "Kuwait", "Bahrain"]

# map source file's country names to our standard names
NAME_MAP = {
    "UAE": "UAE",
    "United Arab Emirates": "UAE",
    "South Korea": "South Korea",
    "Korea, Rep.": "South Korea",
    "Saudi Arabia": "Saudi Arabia",
    "Qatar": "Qatar",
    "Malaysia": "Malaysia",
    "Kuwait": "Kuwait",
    "Bahrain": "Bahrain",
}

count = 0

# 1. Seed per-country bilateral breakdowns (2021 and 2023 if available)
bilateral = data.get("bilateral_breakdown", {})

for period_key, period_data in bilateral.items():
    year = period_key.split("_")[0]  # "2021_knomad" -> "2021"
    countries = period_data.get("countries", [])
    
    for entry in countries:
        raw_name = entry.get("country", "")
        mapped_name = NAME_MAP.get(raw_name)
        
        if mapped_name not in TARGET_COUNTRIES:
            continue
        
        amount_usd = entry.get("amount_usd_million", 0) * 1_000_000
        period_label = f"{year}-Annual"
        
        exists = db.query(RemittanceRecord).filter(
            RemittanceRecord.country == mapped_name,
            RemittanceRecord.period == period_label
        ).first()
        
        if exists:
            continue
        
        record = RemittanceRecord(
            country=mapped_name,
            amount_usd=amount_usd,
            period=period_label
        )
        db.add(record)
        count += 1

db.commit()

# 2. Also seed total national remittance (all countries combined) year by year
totals = data.get("total_remittance_inflows_usd_million", {})

for year, amount_million in totals.items():
    period_label = f"{year}-Annual"
    amount_usd = amount_million * 1_000_000
    
    exists = db.query(RemittanceRecord).filter(
        RemittanceRecord.country == "Nepal_Total",
        RemittanceRecord.period == period_label
    ).first()
    
    if exists:
        continue
    
    record = RemittanceRecord(
        country="Nepal_Total",
        amount_usd=amount_usd,
        period=period_label
    )
    db.add(record)
    count += 1

db.commit()
db.close()

print(f"→ Seeded {count} real remittance records")