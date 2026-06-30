from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schema import NewsArticle, DistressSignal, RemittanceRecord, WelfareScore
from app.services.classifier import classify_text
from pydantic import BaseModel
from app.scrapers.news import scrape_feeds, scrape_historical, scrape_reddit


router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "system": "SENTINEL"}

@router.get("/welfare-scores")
async def get_welfare_scores(db: Session = Depends(get_db)):

    scores = db.query(WelfareScore).order_by(WelfareScore.computed_at.desc()).all()

    return scores

@router.get("/welfare-scores/{country}")
async def get_country_score(country: str, db: Session = Depends(get_db)):

    score = db.query(WelfareScore).filter(
        WelfareScore.country == country
    ).order_by(WelfareScore.computed_at.desc()).first()

    return score

@router.get("/distress-signals")
async def get_distress_signals(db: Session = Depends(get_db)):

    signals = db.query(DistressSignal).order_by(DistressSignal.classified_at.desc()).limit(50).all()
    return signals

@router.get("/news")
async def get_news(db: Session = Depends(get_db)):

    articles = db.query(NewsArticle).order_by(NewsArticle.scraped_at.desc()).limit(20).all()

    return articles

@router.get("/remittance")
async def get_remittance(db: Session = Depends(get_db)):

    records = db.query(RemittanceRecord).order_by(RemittanceRecord.recorded_at.desc()).all()

    return records

@router.get("/remittance/{country}")
async def get_country_remittance(country: str, db: Session = Depends(get_db)):

    records = db.query(RemittanceRecord).filter(
        RemittanceRecord.country == country
    ).order_by(RemittanceRecord.recorded_at.desc()).all()
    
    return records

@router.post("/scrape/news")
async def trigger_news_scrape(db: Session = Depends(get_db)):
    count = scrape_feeds(db)
    return {"status": "complete", "new_articles": count}

@router.post("/scrape/historical")
async def trigger_historical_scrape(db: Session = Depends(get_db)):
    count = scrape_historical(db)
    return {"status": "complete", "new_articles": count}

class ClassifyRequest(BaseModel):
    text: str
    country: str = "Unknown"
    source: str = "manual"

@router.post("/classify")
async def classify_message(request: ClassifyRequest, db: Session = Depends(get_db)):
    result = classify_text(request.text)
    
    if result["classification"] == "ERROR":
        return result
    
    signal = DistressSignal(
        raw_text=request.text,
        classification=result["classification"],
        confidence=result["confidence"],
        signals_detected=", ".join(result.get("signals_detected", [])),
        country=request.country,
        source=request.source,
    )

    db.add(signal)
    db.commit()
    db.refresh(signal)
    
    return {
        "id": signal.id,
        "classification": result["classification"],
        "confidence": result["confidence"],
        "signals_detected": result.get("signals_detected", []),
        "recommended_action": result.get("recommended_action", "")
    }


@router.post("/scrape/reddit")
async def trigger_reddit_scrape(db: Session = Depends(get_db)):
    count = scrape_reddit(db)
    return {"status": "complete", "new_posts": count}