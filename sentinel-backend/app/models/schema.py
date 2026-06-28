from sqlalchemy import *
from sqlalchemy.sql import func
from app.database import Base


class NewsArticle(Base):

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    source = Column(String)           # "gulf_news", "al_jazeera", "kathmandu_post"
    country = Column(String)          # "Qatar", "Malaysia", "UAE" etc.
    url = Column(String, unique=True)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, server_default=func.now())

class DistressSignal(Base):

    __tablename__ = "distress_signals"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False)
    classification = Column(String)   # "SAFE", "DISTRESS", "CRISIS"
    confidence = Column(Float)
    signals_detected = Column(Text)   # comma separated: "passport confiscation, unpaid wages"
    country = Column(String)
    source = Column(String)           # "whatsapp", "facebook", "manual"
    classified_at = Column(DateTime, server_default=func.now())

class RemittanceRecord(Base):
    __tablename__ = "remittance_records"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, nullable=False)
    amount_usd = Column(Float)
    period = Column(String)           # "2024-Q1", "2024-Q2" etc.
    is_anomaly = Column(Integer, default=0)   # 0 or 1
    anomaly_score = Column(Float)
    recorded_at = Column(DateTime, server_default=func.now())


class WelfareScore(Base):
    __tablename__ = "welfare_scores"

    id = Column(Integer, primary_key=True, index=True)
    
    country = Column(String, nullable=False)
    score = Column(Float)             # 0.0 to 1.0, lower = more dangerous
    risk_level = Column(String)       # "HIGH", "ELEVATED", "STABLE"

    # Evidence trail
    evidence = Column(Text)           # "3 workers reported passport confiscation, remittance dropped 34%"
    contributing_signals = Column(Integer, default=0)  # how many signals fed into this score
    
    # Predictive
    predicted_score_30d = Column(Float)   # where Prophet thinks score is headed
    trend = Column(String)                # "DETERIORATING", "STABLE", "IMPROVING"
    
    # Action
    recommended_action = Column(Text)     # "Immediate: Embassy welfare check..."
    action_urgency = Column(String)       # "IMMEDIATE", "48HR", "MONITOR"

    computed_at = Column(DateTime, server_default=func.now())

