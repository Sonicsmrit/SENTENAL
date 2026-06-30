import feedparser
import httpx
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.schema import NewsArticle
import os
import requests as req_lib
import time
import random

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

NEWSAPI_QUERIES = [
    ("Qatar", "nepali worker Qatar OR migrant worker Qatar"),
    ("Malaysia", "nepali worker Malaysia OR migrant worker Malaysia"),
    ("UAE", "nepali worker UAE OR migrant worker dubai"),
    ("Saudi Arabia", "nepali worker saudi arabia OR migrant worker saudi"),
    ("South Korea", "nepali worker korea OR migrant worker korea"),
    ("Nepal", "foreign employment nepal OR remittance nepal worker"),
]

def scrape_historical(db: Session):
    if not NEWSAPI_KEY:
        print("✗ NEWSAPI_KEY not set in .env")
        return 0

    new_count = 0
    url = "https://newsapi.org/v2/everything"

    for country, query in NEWSAPI_QUERIES:
        try:
            response = req_lib.get(url, params={
                "q": query,
                "from": "2026-05-30",
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": 30,
                "apiKey": NEWSAPI_KEY,
            })
            data = response.json()

            if data.get("status") != "ok":
                print(f"✗ NewsAPI error for {country}: {data.get('message')}")
                continue

            for art in data.get("articles", []):
                article_url = art.get("url", "")
                title = art.get("title", "")
                content = art.get("description", "") or ""

                if not article_url or not title:
                    continue

                exists = db.query(NewsArticle).filter(NewsArticle.url == article_url).first()
                if exists:
                    continue

                published = None
                if art.get("publishedAt"):
                    published = datetime.fromisoformat(art["publishedAt"].replace("Z", ""))

                article = NewsArticle(
                    title=clean_html(title),
                    content=clean_html(content),
                    source=art.get("source", {}).get("name", "newsapi"),
                    country=country,
                    url=article_url,
                    published_at=published,
                )

                db.add(article)
                new_count += 1

            db.commit()
            print(f"✓ NewsAPI fetched for {country}")

        except Exception as e:
            print(f"✗ Failed NewsAPI for {country}: {e}")
            db.rollback()

    print(f"\n→ Total new historical articles: {new_count}")

    return new_count


FEEDS = {
    "Qatar": [
        ("gulf_news", "https://gulfnews.com/rss/uae"),
        ("al_jazeera", "https://www.aljazeera.com/xml/rss/all.xml"), 
        ("peninsula_qatar", "https://thepeninsulaqatar.com/rss"),
    ],
    "Malaysia": [
        ("the_star", "https://www.thestar.com.my/rss/News"), 
        ("malaymail", "https://www.malaymail.com/feed"),
        ("free_malaysia_today", "https://www.freemalaysiatoday.com/feed/"),
    ],
    "UAE": [
        ("gulf_news", "https://gulfnews.com/rss/uae"),
        ("khaleej_times", "https://www.khaleejtimes.com/rss"),
    ],
    "Saudi Arabia": [
        ("arab_news", "https://www.arabnews.com/rss.xml"),
    ],
    "South Korea": [
        ("korea_herald", "https://www.koreaherald.com/rss/"),
    ],
    "Nepal": [
        ("kathmandu_post", "https://kathmandupost.com/rss"),
        ("my_republica", "https://myrepublica.nagariknetwork.com/rss"),
        ("online_khabar", "https://english.onlinekhabar.com/feed"),
        ("setopati", "https://www.setopati.com/feed"),
    ],
}

STRONG_KEYWORDS = [
    "migrant worker", "foreign worker", "domestic worker", "construction worker",
    "nepali worker", "remittance", "kafala", "wage theft", "passport confiscation",
    "forced labor", "forced labour", "human trafficking", "labor abuse", "labour abuse",
    "foreign employment", "manpower", "recruitment agency", "work visa",
    "overstayed visa", "undocumented worker", "deported worker", "stranded worker",
    "श्रमिक", "कामदार", "वैदेशिक रोजगार", "ज्याला चोरी"
]

WEAK_KEYWORDS = [
    "nepali", "nepal", "worker", "labour", "labor", "killed", "died",
    "detained", "arrested", "rescued", "missing", "embassy", "visa",
    "deportation", "trafficking", "salary", "unpaid", "passport"
]

BLOCKLIST = [
    "messi", "football", "cricket", "rugby", "fifa", "world cup",
    "monsoon", "rain", "weather", "flood", "earthquake", "quake",
    "music", "singer", "concert", "film", "movie", "actor",
    "election", "parliament", "minister", "political party",
    "putin", "ukraine", "russia", "israel", "gaza",
    "plane crash", "skydiver", "parachute",
    "stock market", "cryptocurrency", "bitcoin",
]

def is_relevant(title: str, content: str) -> bool:
    title_lower = title.lower()
    
    # blocklist check on title first
    if any(word in title_lower for word in BLOCKLIST):
        return False
    
    text = (title + " " + content).lower()
    
    # match if ANY strong keyword found
    if any(kw.lower() in text for kw in STRONG_KEYWORDS):
        return True
    
    # OR if TWO or more weak keywords found
    weak_matches = sum(1 for kw in WEAK_KEYWORDS if kw.lower() in text)
    return weak_matches >= 2



def clean_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    clean = clean.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&#8217;', "'")
    return clean.strip()


def scrape_feeds(db: Session):
    new_count = 0
    
    for country, feeds in FEEDS.items():
        for source_name, feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    title = entry.get("title", "")
                    content = entry.get("summary", "")
                    url = entry.get("link", "")
                    
                    if not url:
                        continue
                    
                    # skip if already in db
                    exists = db.query(NewsArticle).filter(NewsArticle.url == url).first()
                    if exists:
                        continue
                    
                    # only store relevant articles
                    if not is_relevant(title, content):
                        continue
                    
                    # parse published date
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    
                    article = NewsArticle(
                        title=clean_html(title),
                        content=clean_html(content),
                        source=source_name,
                        country=country,
                        url=url,
                        published_at=published,
                    )
                    db.add(article)
                    new_count += 1
                
                db.commit()
                print(f"✓ Scraped {source_name} for {country}")
                
            except Exception as e:
                print(f"✗ Failed {source_name} for {country}: {e}")
                db.rollback()
    
    print(f"\n→ Total new articles stored: {new_count}")
    return new_count


REDDIT_HEADERS = {
    "User-Agent": "sentinel-research/1.0 (hackathon project)"
}

REDDIT_SEARCHES = [
    ("Nepal", "qatar worker"),
    ("Nepal", "malaysia job"),
    ("Nepal", "passport liyo"),
    ("Nepal", "salary aayena"),
    ("NepalSocial", "foreign employment"),
    ("Nepal", "kafala"),
]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

def get_reddit_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.reddit.com/",
    }

def scrape_reddit(db: Session):
    new_count = 0

    for subreddit, query in REDDIT_SEARCHES:
        try:
            url = f"https://old.reddit.com/r/{subreddit}/search.json"
            params = {
                "q": query,
                "restrict_sr": 1,
                "limit": 25,
                "sort": "new"
            }
            response = req_lib.get(url, headers=get_reddit_headers(), params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"✗ Reddit returned {response.status_code} for r/{subreddit} '{query}'")
                continue

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                p = post.get("data", {})
                title = p.get("title", "")
                selftext = p.get("selftext", "")
                permalink = p.get("permalink", "")
                
                if not permalink:
                    continue
                
                full_url = f"https://reddit.com{permalink}"

                exists = db.query(NewsArticle).filter(NewsArticle.url == full_url).first()
                if exists:
                    continue

                article = NewsArticle(
                    title=clean_html(title),
                    content=clean_html(selftext)[:2000],
                    source=f"reddit_r_{subreddit}",
                    country="Nepal",
                    url=full_url,
                    published_at=datetime.fromtimestamp(p.get("created_utc", 0)) if p.get("created_utc") else None,
                )
                db.add(article)
                new_count += 1

            db.commit()
            print(f"✓ Reddit scraped r/{subreddit} for '{query}'")
            time.sleep(random.uniform(3, 6))

        except Exception as e:
            print(f"✗ Failed Reddit r/{subreddit} '{query}': {e}")
            db.rollback()

    print(f"\n→ Total new Reddit posts: {new_count}")
    return new_count