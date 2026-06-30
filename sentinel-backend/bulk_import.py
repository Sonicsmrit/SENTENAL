import json
import requests
import time

API_URL = "http://localhost:8000/api/classify"

with open("data/distress_dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

correct = 0
total = len(dataset)
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
    print(f"{status} [{i+1}/{total}] expected={expected} predicted={predicted}")
    
    time.sleep(3)  # slower pace, avoid rate limit

accuracy = (correct / total) * 100
print(f"\n{'='*50}")
print(f"ACCURACY: {correct}/{total} = {accuracy:.1f}%")
print(f"{'='*50}")

mismatches = [r for r in results if not r["match"]]
if mismatches:
    print("\nMismatches:")
    for m in mismatches:
        print(f"  Expected {m['expected']}, got {m['predicted']}: {m['text']}")