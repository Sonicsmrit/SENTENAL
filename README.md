# SENTINEL — Backend

**Nepal Migrant Worker Intelligence & Welfare Monitoring System**

Built for OrchidHackX 2026. This is the FastAPI backend powering SENTINEL's data pipeline, distress classification engine, and remittance anomaly detection.

---

## What This System Does

SENTINEL monitors the wellbeing of Nepali migrant workers abroad by fusing three real data sources into a single intelligence layer:

1. **News scraping** — pulls migrant-worker-relevant articles from Gulf, Malaysian, Korean, and Nepali news sources (RSS + NewsAPI)
2. **Distress signal classification** — uses NVIDIA NIM (Nemotron-3-Super-120B) to classify Nepali/Romanized Nepali text into SAFE / DISTRESS / CRISIS
3. **Remittance anomaly detection** — uses Prophet (Meta) on real World Bank/KNOMAD remittance data to detect abnormal drops or spikes in money sent home, which can signal humanitarian crises before news coverage catches up

These three signals combine into a **Country Welfare Score** for each destination country (Qatar, UAE, Saudi Arabia, Malaysia, South Korea, Kuwait, Bahrain).

---

## Tech Stack

| Layer | Tool |
|---|---|
| API framework | FastAPI |
| Database | SQLite + SQLAlchemy ORM |
| Distress classifier | NVIDIA NIM API (`nvidia/nemotron-3-super-120b-a12b`) |
| Anomaly detection | Prophet (Meta) |
| News scraping | feedparser (RSS) + NewsAPI.org |
| Scheduling | APScheduler *(planned)* |

---

## Project Structure

```
sentinel-backend/
├── main.py                    # FastAPI app entry point
├── .env                       # API keys (not committed)
├── seed_remittance_real.py    # One-time script to load real remittance data
├── bulk_import.py             # Batch-classifies curated distress dataset
├── data/
│   ├── distress_dataset.json          # 30 curated Romanized Nepali test messages
│   ├── remittance_breakdown_final.json # Real World Bank/KNOMAD remittance data (2000-2024)
│   ├── remittance_by_country_annual.json
│   └── migrant_stock_by_country_annual.json
└── app/
    ├── database.py             # SQLite connection + session management
    ├── models/
    │   └── schema.py           # 4 tables: NewsArticle, DistressSignal, RemittanceRecord, WelfareScore
    ├── scrapers/
    │   └── news.py             # RSS + NewsAPI scraping, keyword filtering
    ├── services/
    │   ├── classifier.py       # NIM Nemotron distress classification (few-shot prompting)
    │   └── anomaly.py          # Prophet anomaly detection + welfare score computation
    └── api/
        └── routes.py           # All API endpoints
```

---

## Setup

**1. Clone and create virtual environment**
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
source .venv/bin/activate         # Mac/Linux
```

**2. Install dependencies**
```bash
pip install fastapi uvicorn sqlalchemy aiohttp python-dotenv apscheduler feedparser newspaper3k httpx beautifulsoup4 prophet scikit-learn pandas numpy requests
```

**3. Set up environment variables** — create `.env` in project root:
```
NVIDIA_API_KEY=your_nvidia_nim_key
NEWSAPI_KEY=your_newsapi_key
```

- Get a free NVIDIA NIM key at [build.nvidia.com](https://build.nvidia.com) (use a Free Endpoint model)
- Get a free NewsAPI key at [newsapi.org](https://newsapi.org)

**4. Run the server**
```bash
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

---

## Data Pipeline — Run Order

Run these once after first starting the server to populate the database:

```bash
# 1. Seed real remittance data (World Bank/KNOMAD, 2000-2024)
python seed_remittance_real.py

# 2. Scrape live news (RSS feeds)
POST /api/scrape/news

# 3. Pull historical news (last ~27 days via NewsAPI)
POST /api/scrape/historical

# 4. Classify the curated distress dataset
python bulk_import.py

# 5. Compute welfare scores from remittance trends
POST /api/welfare-scores/compute
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/welfare-scores` | All computed welfare scores |
| GET | `/api/welfare-scores/{country}` | Latest score for one country |
| POST | `/api/welfare-scores/compute` | Recompute all welfare scores |
| GET | `/api/distress-signals` | Latest 50 classified messages |
| POST | `/api/classify` | Classify a single message (SAFE/DISTRESS/CRISIS) |
| GET | `/api/news` | Latest scraped news articles |
| POST | `/api/scrape/news` | Trigger live RSS scrape |
| POST | `/api/scrape/historical` | Trigger NewsAPI historical scrape |
| GET | `/api/remittance` | All remittance records |
| GET | `/api/remittance/{country}` | Remittance records for one country |
| GET | `/api/anomaly/{country}` | Prophet anomaly detection for one country's remittance history |

---

## Distress Classifier — How It Works

Uses **few-shot prompting**, not fine-tuning — three labeled examples (SAFE, DISTRESS, CRISIS) are included in every request to calibrate the model, then it classifies new text against that pattern.

```json
POST /api/classify
{
  "text": "Dai hamlai thik jagah maa liyena, passport liye ko chha",
  "country": "Qatar",
  "source": "manual"
}
```

Returns:
```json
{
  "classification": "CRISIS",
  "confidence": 0.93,
  "signals_detected": ["passport confiscation", "restricted movement"],
  "recommended_action": "Embassy alert - immediate welfare check"
}
```

**Validated accuracy: 70.6%** on a 30-message curated dataset covering SAFE/DISTRESS/CRISIS in Romanized Nepali. This is a reasonable baseline for zero/few-shot classification on informal, code-mixed text — not a production-grade number. A real deployment would need labeled training data and a caseworker feedback loop.

---

## Anomaly Detection — How It Works

Prophet is fit on real historical remittance data per country (or national total). It learns the expected trend, then flags any year where actual remittance falls outside the 90% confidence interval — either a sudden drop (potential crisis) or unexplained spike (worth investigating).

```
GET /api/anomaly/Nepal_Total
```

Returns year-by-year actual vs. predicted values, confidence bounds, and a flag for each anomalous year, plus a forecast for the next period.

**Known limitation:** Prophet's linear trend fit performs poorly on the earliest years (2000-2004) where growth was exponential rather than linear. Predictions from ~2015 onward are well-calibrated. This is disclosed here rather than hidden — worth mentioning if asked on stage.

---

## Data Sources

- **News**: Gulf News, Al Jazeera, Khaleej Times, Arab News, Korea Herald, Kathmandu Post, MyRepublica, OnlineKhabar, Setopati, The Star, Malay Mail, Free Malaysia Today, Kuwait Times, Gulf Daily News, plus NewsAPI.org historical search
- **Remittance**: World Bank / KNOMAD bilateral remittance estimates, CESLAM Status of Remittances in Nepal reports, Nepal Rastra Bank macroeconomic bulletins
- **Distress dataset**: 30 manually curated Romanized Nepali messages, patterned after documented cases from Human Rights Watch and ILO reporting (not scraped from private social media groups — see note below)

**Note on data ethics:** We deliberately avoided scraping private Facebook/WhatsApp worker groups. Automated scraping of personal accounts raises consent and platform-policy issues, and Reddit/Twitter API access proved unreliable within the hackathon timeframe. The distress dataset was manually written based on patterns documented in public NGO and news reporting.

---

## What's Not Built Yet

- Nepali text handling could be improved (Devanagari + Romanized mixed input)
- Welfare score currently weights remittance trend only — distress signal volume and news sentiment should be fused in
- APScheduler for automatic 30-minute re-scraping is planned but not wired in
- No authentication/rate limiting — fine for a hackathon demo, not production-ready

---

*Project SENTINEL · OrchidHackX 2026 · Track: AI/ML + Open Innovation*