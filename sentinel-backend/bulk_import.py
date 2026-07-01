import json
import requests
import time

API_URL = "http://localhost:8000/api/classify"
SIGNALS_URL = "http://localhost:8000/api/distress-signals"

with open("data/distress_dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# fetch already classified texts from db
existing_response = requests.get(SIGNALS_URL)
existing = existing_response.json()
already_classified = {s["raw_text"] for s in existing}

print(f"→ {len(already_classified)} already classified, skipping those\n")

correct = 0
total = 0
results = []

def classify_with_retry(payload, retries=3):
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, json=payload, timeout=30)
            result = response.json()
            if result.get("classification") != "ERROR":
                return result
            print(f"  retry {attempt+1}/{retries}...")
            time.sleep(5)
        except Exception as e:
            print(f"  retry {attempt+1}/{retries} failed: {e}")
            time.sleep(5)
    return result

for i, item in enumerate(dataset):
    if item["text"] in already_classified:
        print(f"⏭ [{i+1}/{len(dataset)}] already classified, skipping")
        continue

    total += 1
    payload = {
        "text": item["text"],
        "country": item["country"],
        "source": "curated_dataset"
    }

    result = classify_with_retry(payload)
    predicted = result.get("classification", "ERROR")
    expected = item["expected"]
    match = predicted == expected

    if match:
        correct += 1

    results.append({
        "text": item["text"][:50],
        "expected": expected,
        "predicted": predicted,
        "match": match
    })

    status = "✓" if match else "✗"
    print(f"{status} [{i+1}/{len(dataset)}] expected={expected} predicted={predicted}")

    time.sleep(3)

if total > 0:
    accuracy = (correct / total) * 100
    print(f"\n{'='*50}")
    print(f"NEW ACCURACY: {correct}/{total} = {accuracy:.1f}%")
    print(f"{'='*50}")
else:
    print("\n→ All messages already classified, nothing new to process")

mismatches = [r for r in results if not r["match"]]
if mismatches:
    print("\nMismatches:")
    for m in mismatches:
        print(f"  Expected {m['expected']}, got {m['predicted']}: {m['text']}")