import pandas as pd
from prophet import Prophet
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.schema import RemittanceRecord, WelfareScore, DistressSignal, NewsArticle
from sqlalchemy import func
from app.services.classifier import agni_evaluate


def run_anomaly_detection(db: Session, country: str = "Nepal_Total"):
    records = db.query(RemittanceRecord).filter(
        RemittanceRecord.country == country
    ).order_by(RemittanceRecord.period).all()

    if len(records) < 5:
        return {"error": "Not enough data points for Prophet (need at least 5)"}

    # build dataframe Prophet expects: columns 'ds' (date) and 'y' (value)
    rows = []
    for r in records:
        year = r.period.split("-")[0]
        rows.append({
            "ds": pd.Timestamp(f"{year}-07-01"),  # Nepal fiscal year mid-point approx
            "y": r.amount_usd
        })

    df = pd.DataFrame(rows).sort_values("ds").reset_index(drop=True)

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.90  # 90% confidence interval
    )
    model.fit(df)

    forecast = model.predict(df)

    # merge actual vs predicted
    df["yhat"] = forecast["yhat"]
    df["yhat_lower"] = forecast["yhat_lower"]
    df["yhat_upper"] = forecast["yhat_upper"]

    df["is_anomaly"] = (df["y"] < df["yhat_lower"]) | (df["y"] > df["yhat_upper"])
    df["deviation_pct"] = ((df["y"] - df["yhat"]) / df["yhat"] * 100).round(2)

    results = []
    for _, row in df.iterrows():
        results.append({
            "year": row["ds"].year,
            "actual": round(row["y"], 2),
            "predicted": round(row["yhat"], 2),
            "lower_bound": round(row["yhat_lower"], 2),
            "upper_bound": round(row["yhat_upper"], 2),
            "is_anomaly": bool(row["is_anomaly"]),
            "deviation_pct": row["deviation_pct"]
        })

    # future prediction (next year)
    future = model.make_future_dataframe(periods=1, freq="YS")
    future_forecast = model.predict(future)
    next_year_prediction = future_forecast.iloc[-1]

    return {
        "country": country,
        "historical": results,
        "next_period_prediction": {
            "predicted_amount": round(next_year_prediction["yhat"], 2),
            "lower_bound": round(next_year_prediction["yhat_lower"], 2),
            "upper_bound": round(next_year_prediction["yhat_upper"], 2)
        }
    }


def compute_welfare_scores(db: Session):
    countries = ["Qatar", "Malaysia", "UAE", "Saudi Arabia", "South Korea", "Kuwait", "Bahrain"]
    computed = []

    for country in countries:
        records = db.query(RemittanceRecord).filter(
            RemittanceRecord.country == country
        ).order_by(RemittanceRecord.period).all()

        remittance_score = 1.0
        remittance_evidence = "No remittance data available"
        pct_change = None
        has_remittance_data = len(records) >= 2

        if has_remittance_data:
            latest = records[-1]
            previous = records[-2]
            pct_change = ((latest.amount_usd - previous.amount_usd) / previous.amount_usd) * 100

            if pct_change <= -25:
                remittance_score = 0.1
            elif pct_change <= -15:
                remittance_score = 0.3
            elif pct_change <= -5:
                remittance_score = 0.6
            else:
                remittance_score = 1.0

            remittance_evidence = f"Remittance changed {pct_change:.1f}% ({previous.period} → {latest.period})"

        signals = db.query(DistressSignal).filter(
            DistressSignal.country == country
        ).all()

        total_signals = len(signals)
        crisis_count = sum(1 for s in signals if s.classification == "CRISIS")
        distress_count = sum(1 for s in signals if s.classification == "DISTRESS")

        has_distress_data = total_signals >= 3

        if not has_distress_data:
            distress_score = None
            distress_evidence = f"Insufficient distress signal data ({total_signals} classified)"
        else:
            severity_ratio = (crisis_count * 3 + distress_count) / (total_signals * 3)
            distress_score = max(0.0, 1.0 - severity_ratio)
            distress_evidence = f"{crisis_count} CRISIS, {distress_count} DISTRESS out of {total_signals} classified signals"

        news_count = db.query(NewsArticle).filter(
            NewsArticle.country == country
        ).count()

        if news_count == 0:
            news_score = 0.8
            news_evidence = "No recent news coverage found"
        elif news_count <= 3:
            news_score = 0.9
            news_evidence = f"{news_count} relevant news articles found"
        elif news_count <= 8:
            news_score = 0.7
            news_evidence = f"{news_count} relevant news articles found"
        else:
            news_score = 0.5
            news_evidence = f"{news_count} relevant news articles found — high coverage volume"

        # --- Case: no data at all ---
        if not has_remittance_data and not has_distress_data:
            welfare_score = WelfareScore(
                country=country,
                score=None,
                risk_level="INSUFFICIENT_DATA",
                evidence=f"{remittance_evidence}. {distress_evidence}. {news_evidence}.",
                contributing_signals=total_signals + news_count,
                trend="UNKNOWN",
                recommended_action="Gather more data before assessment - no reliable signal available",
                action_urgency="MONITOR"
            )
            db.add(welfare_score)
            computed.append({
                "country": country,
                "final_score": None,
                "risk_level": "INSUFFICIENT_DATA",
                "evidence": welfare_score.evidence
            })
            continue

        # --- Composite score ---
        if distress_score is None:
            final_score = (remittance_score * 0.6) + (news_score * 0.4)
        else:
            final_score = (remittance_score * 0.4) + (distress_score * 0.4) + (news_score * 0.2)

        final_score = round(final_score, 3)

        # --- Deterministic risk tier FIRST (this must happen before AGNI, not after) ---
        if final_score < 0.45:
            risk_level = "HIGH_RISK"
        elif final_score < 0.65:
            risk_level = "AT_RISK"
        else:
            risk_level = "STABLE"

        # override: heavy CRISIS ratio always bumps to at least AT_RISK
        if has_distress_data and (crisis_count / total_signals) >= 0.5 and risk_level == "STABLE":
            risk_level = "AT_RISK"

        trend = "DETERIORATING" if (pct_change is not None and pct_change < -5) else "STABLE"

        # --- AGNI writes the narrative (evidence + action + urgency), math above stays authoritative ---
        agni_result = agni_evaluate(
            country=country,
            remittance_evidence=remittance_evidence,
            distress_evidence=distress_evidence,
            news_evidence=news_evidence,
            crisis_count=crisis_count,
            distress_count=distress_count,
            total_signals=total_signals,
            pct_change=pct_change
        )

        combined_evidence = agni_result["evidence_summary"]
        action = agni_result["recommended_action"]
        urgency = agni_result["urgency"]

        welfare_score = WelfareScore(
            country=country,
            score=final_score,
            risk_level=risk_level,
            evidence=combined_evidence,
            contributing_signals=total_signals + news_count,
            trend=trend,
            recommended_action=action,
            action_urgency=urgency
        )
        db.add(welfare_score)

        computed.append({
            "country": country,
            "final_score": final_score,
            "risk_level": risk_level,
            "breakdown": {
                "remittance_score": remittance_score,
                "distress_score": distress_score,
                "news_score": news_score
            },
            "evidence": combined_evidence,
            "analyst_note": agni_result.get("analyst_note", "")
        })

    db.commit()
    return computed