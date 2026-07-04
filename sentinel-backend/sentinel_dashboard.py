"""
SENTINEL — Quick Testing Dashboard
Run with: streamlit run sentinel_dashboard.py
Make sure your FastAPI server is running on http://localhost:8000 first.
"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000/api"

st.set_page_config(page_title="SENTINEL Dashboard", layout="wide")

st.title("🛰️ SENTINEL — Testing Dashboard")
st.caption("Nepal Migrant Worker Intelligence System — internal testing view")

# ---- Sidebar controls ----
with st.sidebar:
    st.header("Actions")

    if st.button("🔄 Recompute Welfare Scores"):
        try:
            r = requests.post(f"{API_BASE}/welfare-scores/compute")
            st.success(f"Computed scores for {len(r.json())} countries")
        except Exception as e:
            st.error(f"Failed: {e}")

    if st.button("📰 Scrape Live News (RSS)"):
        try:
            r = requests.post(f"{API_BASE}/scrape/news")
            st.success(r.json())
        except Exception as e:
            st.error(f"Failed: {e}")

    if st.button("📰 Scrape Historical (NewsAPI)"):
        try:
            r = requests.post(f"{API_BASE}/scrape/historical")
            st.success(r.json())
        except Exception as e:
            st.error(f"Failed: {e}")

    st.divider()
    st.caption("Backend must be running at localhost:8000")

# ---- Tabs ----
tab1, tab2, tab3, tab4 = st.tabs(["🌍 Welfare Scores", "💬 Classifier Test", "📈 Anomaly Detection", "📰 News Feed"])

# ===== TAB 1: Welfare Scores =====
with tab1:
    st.subheader("Country Welfare Scores")

    try:
        r = requests.get(f"{API_BASE}/welfare-scores")
        scores = r.json()

        if not scores:
            st.info("No welfare scores yet. Click 'Recompute Welfare Scores' in the sidebar.")
        else:
            cols = st.columns(len(scores))
            risk_colors = {
                "HIGH": "🔴",
                "ELEVATED": "🟡",
                "STABLE": "🟢",
                "INSUFFICIENT_DATA": "⚪"
            }

            for i, s in enumerate(scores):
                with cols[i]:
                    emoji = risk_colors.get(s["risk_level"], "⚪")
                    score_display = s["score"] if s["score"] is not None else "N/A"
                    st.metric(
                        label=f"{emoji} {s['country']}",
                        value=score_display,
                        delta=s["risk_level"]
                    )

            st.divider()
            st.subheader("Evidence Trail")
            for s in scores:
                emoji = risk_colors.get(s["risk_level"], "⚪")
                with st.expander(f"{emoji} {s['country']} — {s['risk_level']}"):
                    st.write(f"**Score:** {s['score']}")
                    st.write(f"**Evidence:** {s['evidence']}")
                    st.write(f"**Recommended Action:** {s['recommended_action']}")
                    st.write(f"**Urgency:** {s['action_urgency']}")

    except Exception as e:
        st.error(f"Could not reach backend: {e}")

# ===== TAB 2: Classifier Test =====
with tab2:
    st.subheader("Test the Distress Classifier")
    st.caption("Paste a message in Nepali, Romanized Nepali, or English")

    col1, col2 = st.columns(2)
    with col1:
        test_text = st.text_area(
            "Message to classify",
            value="Dai hamlai thik jagah maa liyena, passport liye ko chha",
            height=100
        )
        test_country = st.selectbox(
            "Country",
            ["Qatar", "Malaysia", "UAE", "Saudi Arabia", "South Korea", "Kuwait", "Bahrain"]
        )

        if st.button("Classify Message", type="primary"):
            try:
                r = requests.post(f"{API_BASE}/classify", json={
                    "text": test_text,
                    "country": test_country,
                    "source": "streamlit_test"
                })
                result = r.json()

                with col2:
                    classification = result.get("classification", "ERROR")
                    color = {"SAFE": "green", "DISTRESS": "orange", "CRISIS": "red"}.get(classification, "gray")
                    st.markdown(f"### :{color}[{classification}]")
                    st.write(f"**Confidence:** {result.get('confidence', 'N/A')}")
                    st.write(f"**Signals detected:** {', '.join(result.get('signals_detected', [])) or 'None'}")
                    st.write(f"**Recommended action:** {result.get('recommended_action', 'N/A')}")
            except Exception as e:
                st.error(f"Classification failed: {e}")

    st.divider()
    st.subheader("Recent Classified Signals")
    try:
        r = requests.get(f"{API_BASE}/distress-signals")
        signals = r.json()
        if signals:
            df = pd.DataFrame(signals)[["classification", "confidence", "country", "raw_text", "signals_detected", "classified_at"]]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No classified signals yet.")
    except Exception as e:
        st.error(f"Could not load signals: {e}")

# ===== TAB 3: Anomaly Detection =====
with tab3:
    st.subheader("Remittance Anomaly Detection (Prophet)")

    anomaly_country = st.selectbox(
        "Select country/dataset",
        ["Nepal_Total", "Qatar", "Malaysia", "UAE", "Saudi Arabia", "South Korea"],
        key="anomaly_select"
    )

    if st.button("Run Anomaly Detection"):
        try:
            r = requests.get(f"{API_BASE}/anomaly/{anomaly_country}")
            result = r.json()

            if "error" in result:
                st.warning(result["error"])
            else:
                df = pd.DataFrame(result["historical"])
                df["actual_M"] = (df["actual"] / 1_000_000).round(1)
                df["predicted_M"] = (df["predicted"] / 1_000_000).round(1)

                st.line_chart(df.set_index("year")[["actual_M", "predicted_M"]])

                anomalies = df[df["is_anomaly"] == True]
                if not anomalies.empty:
                    st.warning(f"⚠️ {len(anomalies)} anomaly year(s) detected:")
                    st.dataframe(anomalies[["year", "actual_M", "predicted_M", "deviation_pct"]], use_container_width=True)
                else:
                    st.success("No anomalies detected in this series.")

                st.divider()
                next_pred = result["next_period_prediction"]
                st.metric(
                    "Next Period Forecast",
                    f"${next_pred['predicted_amount']/1_000_000:.1f}M",
                    help=f"Range: ${next_pred['lower_bound']/1_000_000:.1f}M - ${next_pred['upper_bound']/1_000_000:.1f}M"
                )
        except Exception as e:
            st.error(f"Anomaly detection failed: {e}")

# ===== TAB 4: News Feed =====
with tab4:
    st.subheader("Scraped News Articles")
    try:
        r = requests.get(f"{API_BASE}/news")
        articles = r.json()
        if articles:
            for a in articles[:20]:
                with st.expander(f"[{a['country']}] {a['title']}"):
                    st.write(a["content"][:500] + "...")
                    st.caption(f"Source: {a['source']} | Scraped: {a['scraped_at']}")
                    st.markdown(f"[Read full article]({a['url']})")
        else:
            st.info("No news articles yet. Run a scrape from the sidebar.")
    except Exception as e:
        st.error(f"Could not load news: {e}")