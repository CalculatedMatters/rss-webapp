#!/usr/bin/env python3
"""
Client Mentions Monitor — Single-file Streamlit App
- Core RSS scan engine (HTTP retries, parsing, matching, relevance scoring)
- Premium styling
- Streamlit UI with caching and CSV export
"""

import re
import time
import html
import json
import logging
import unicodedata
import concurrent.futures
import functools
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import md5
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import streamlit as st
import pandas as pd
import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rss-monitor")

# ---------------------------------------------------------------------
# Data sources and clients
# ---------------------------------------------------------------------
CURATED_DEFAULT_FEEDS = [
    "https://www.billboard.com/feed/",
    "https://pitchfork.com/feed/feed-news/rss",
    "https://www.rollingstone.com/music/feed/",
    "https://www.nme.com/news/music/feed",
    "https://consequenceofsound.net/feed/",
    "https://www.stereogum.com/feed/",
    "https://www.musicbusinessworldwide.com/feed/",
    "https://musicfeeds.com.au/feed/",
    "https://www.themusic.com.au/feed.rss",
    "https://tonedeaf.thebrag.com/feed/",
    "https://heavymag.com.au/feed/",
    "https://aaabackstage.com/feed/",
    "https://beat.com.au/music/feed/",
    "https://www.theguardian.com/music/australian-music/rss",
    "https://australianmusician.com.au/feed/",
    "https://www.noise11.com/feed/",
    "https://au.rollingstone.com/feed/",
]

DEFAULT_CLIENTS = [
    "Aaron Bull", "A.S. Bull & M.T. Wilson", "Aashna Gulabani", "Adam Hyde",
    "Adam Hyde Productions", "Alexander Burnett", "Long Life Music", "Alex Lloyd",
    "Table Music Trust", "Allex Conley", "Andrew Bryan", "Stop Start",
    "Andrew Cook", "Andrew Kent", "A. Charles Kent and Associates", "Andy Golledge",
    "Angela Henley", "Angus Dowling", "Eureka Music", "Ashleigh Maher",
    "AW Noise Limited", "Benedict East", "Benemusicc Limited", "Benjamin Michael Lee",
    "Ben Lee", "Benjamin O'Leary", "Drax Project", "Boby Andonov",
    "Kid Brother", "Bonnie Fraser", "Brae Luafalealo", "Brita McVeigh",
    "Caitlin McGregor", "Cameron Robertson", "Good Chicken", "Caroline Knight",
    "Cathie Corby", "Matt Corby", "Matthew Corby", "Charlene Collins",
    "Chloe Melick", "Christopher Gilks", "Claire Edwardes", "Clara Baker",
    "Cooking Vinyl Publishing", "Crooked Industries", "Daine Wright", "Daniel Gordon",
    "Dann Hume", "Flightless Bird", "David Le'aupepe", "Macsta Music Management",
    "Volkanik", "David Potter", "Deanna Adams", "Demetrius Savelio",
    "Savage Entertainment", "Dominic Beckett", "Dominic Kim", "Triple One Music",
    "Dominik Borzestowski", "DV Touring", "Eamon Sandwith", "Chatcorp",
    "Eli Matthewson", "Elizabeth Ryan", "Ella Easton", "Emily Copeland",
    "Ennaria Rourke", "Eve Woodhouse", "EYO Limited", "Fan Plus International",
    "Gareth Stuckey", "Gigpiglet Productions", "Georgina Luxton Alba", "Gerbz",
    "Gillian Stannard", "Glenn Shorrock", "Swan Song", "Goat Entertainment",
    "Gregg Donovan", "Gwilym Griffiths", "Good Authority Agency", "Haiku Entertainment",
    "Hannah Cameron", "Fire In Your Eyes", "Harmonie Henderson-Brown", "Third Eye Therapies",
    "Harry Day", "MK Recordings", "Harry White", "Heath Bradby",
    "Fidelity Corporation", "Hebbes Music Group", "Hinenui-Terangi Tairua", "Hugh Baillie",
    "Huon Lamb-Kelly", "I Am Giant", "Ian Jones", "Ione Skye Lee",
    "Weirder Together", "Irene Rose-Shorrock", "Emery Way", "Jack Crowther",
    "Babe Rainbow", "Jack McLaine", "Jack Williment", "James Foster",
    "James Ivey", "Jay Ryves", "Jayden Seeley", "Jeanavive McGregor",
    "Jessica Cerro", "Jessica Day", "John Corby", "John Mravunac",
    "Joji Malani", "Broth Records", "Jonathan Toogood", "Hideo Fuji Enterprises",
    "Jordan O'Connell", "Jordan Rakei", "Domestic Music Concepts", "International Music Concepts",
    "Joseph Wenceslao", "Josh Pyke", "Joshua Pyke", "Moonduck Holdings",
    "Timshel Trust", "Joshua Szeps", "On The Stoop", "Julie Jamieson",
    "Jung Kim", "Karina Wykes", "Karnivool", "Kayla Bonnici",
    "Kaylee Bell", "Kent O'Connell", "Jacinta O'Connell", "Dynamic Matters",
    "Kora Limited", "Kristy Pinder", "Kristyna Higgins", "Slick Productions",
    "Ladyhawke", "Larissa Lambert", "Laurence Pike", "Leisure Partnership",
    "Lucas O'Connell", "Luca Durante", "Luke Mulligan", "Circa 41",
    "Marie Devita", "Marie Pangaud", "Spicy Key Chain", "Glass Beams",
    "Marlin's Dreaming", "Martin Guilfoyle", "Martin Novosel", "Serious Business Corporation",
    "Killphonic Rights", "Massive Entertainment", "Matthew Boggis", "Number One Enterprises",
    "Matthew Carins", "Matt Corby Enterprises", "Rainbow Valley Records", "Mathew Morris",
    "Across The Line Consulting", "Matthew Weston", "The Syndicate Films", "Matthew Wilson",
    "Maxwell Dunn", "Mosy Recordings", "Melisa Bester", "Melita Hodge",
    "Six Boroughs Management", "Six Boroughs Media", "Michael Easton", "Grove Law",
    "Michael Rich", "Stand Atlantic", "Stand Atlantic Fellowship", "Boy Soda",
    "Molly Millington", "Sumner", "Millionaire Millington", "Molly Payton",
    "Muroki Githinji", "Nathan Hudson", "RLT Music", "Future Classic",
    "Nicholas Littlemore", "Nicky Fats", "Nicole Davis", "Nicole Michel-Millar",
    "Nicole Millar", "Nina Gilks", "Niriko McLure", "Belmont Street Entertainment",
    "Oliver Rush", "Opossom", "Parker & Mr French", "Paul Harris",
    "Peter Mayes", "38 Ten Group", "Philip Jamieson", "Burning Daggers",
    "Philip Knight", "Peking Duk", "Reuben Styles", "Yoga The Band",
    "Robin Covell", "Worthy Of The Name", "Rory Adams", "Ryan D'Sylva",
    "Brain Wax", "Ryan Henderson", "Hollow Coves", "Sally McCausland",
    "Samantha White", "Samuel Thomson", "Sarah Croxall", "Sarah Stewart",
    "Sarah Tran", "SC Funk Group", "Scout Eastment", "Sean Szeps",
    "Shane Carn", "Elevator Media", "Sharlee Curnow", "Peach PRC",
    "Simon Day", "Rinang", "Simon Price", "SLR Limited",
    "Sophie Andrews", "Buneaux", "Sophie Chugg", "Stephen De Wilde",
    "Teeks", "Tex Perkins", "The Black Seeds", "Thelma Plumbe",
    "Plumdog Billionaire", "Thirsty Merc", "Thomas Easton", "Tienne Simons",
    "Timothy Fitzmaurice", "Tom Hobden", "Tom Larkin", "Lazy Empire",
    "Jetz Digital", "Unknown Mortal Orchestra", "Vivien Fantin", "Wayne Covell",
    "West Thebarton", "William Gunns", "Billy Gunns", "Nathan McLay",
    "Peter Quinlan", "Tony Adams", "William Hyde", "Williamo The Collective",
    "Wonder Music Company", "Xavier James", "New Levels", "Yasmin Mund",
    "Yumi Zouma", "Zoe Seiler"
]

# ---------------------------------------------------------------------
# HTTP session with robust retries (urllib3 v1/v2 compatible)
# ---------------------------------------------------------------------
def _retry_obj():
    base_kwargs = dict(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        raise_on_status=False,
    )
    try:
        # urllib3 v2
        return Retry(allowed_methods=frozenset(["GET", "HEAD"]), **base_kwargs)
    except TypeError:
        # urllib3 v1
        return Retry(method_whitelist=frozenset(["GET", "HEAD"]), **base_kwargs)

def build_http_session() -> requests.Session:
    s = requests.Session()
    retries = _retry_obj()
    adapter = HTTPAdapter(max_retries=retries, pool_connections=15, pool_maxsize=25)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "ClientMentionsBot/2.0"})
    return s

HTTP = build_http_session()

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "igshid"
}

def canonicalise_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        q = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
        norm = parsed._replace(
            scheme=(parsed.scheme or "https"),
            netloc=parsed.netloc.lower(),
            fragment="",
            query=urlencode(q, doseq=True),
        )
        return urlunparse(norm)
    except Exception:
        return url or ""

def simple_retry(max_attempts=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@simple_retry(max_attempts=3, delay=2)
def robust_get(url: str, timeout: Tuple[int, int] = (5, 15)) -> Tuple[bytes, Optional[str]]:
    resp = HTTP.get(url, timeout=timeout)
    resp.raise_for_status()
    enc = resp.encoding or getattr(resp, "apparent_encoding", None)
    return resp.content, enc

def decode_bytes_best_effort(data: bytes, apparent_encoding: Optional[str]) -> str:
    for enc in (apparent_encoding, "utf-8", "utf-8-sig", "latin-1"):
        if not enc:
            continue
        try:
            return data.decode(enc, errors="replace")
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")

def parse_datetime_from_entry(entry) -> Optional[datetime]:
    dt_fields = [
        getattr(entry, "published_parsed", None),
        getattr(entry, "updated_parsed", None),
        getattr(entry, "created_parsed", None),
    ]
    for st in dt_fields:
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None

def within_days(dt: Optional[datetime], days: int) -> bool:
    if not dt:
        return True  # keep permissive behavior for feeds with missing dates
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff

# ---------------------------------------------------------------------
# Text processing and scoring
# ---------------------------------------------------------------------
APOS_CLASS = r"[\'\u2019\u02BC]"
BOUNDARY = r"(?:(?<!\w)|\b)"
END_BOUND = r"(?!\w)"

def _normalise_text(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def _name_variants(name: str) -> List[str]:
    base = _normalise_text(name).strip()
    if len(base) < 3:
        return []  # avoid noisy matches
    base = re.escape(base)
    return [
        rf"{BOUNDARY}{base}{END_BOUND}",
        rf"{BOUNDARY}{base}{APOS_CLASS}s{END_BOUND}",
        rf"{BOUNDARY}@{base}{END_BOUND}",
        rf"{BOUNDARY}#{base}{END_BOUND}",
    ]

def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return html.unescape(text).strip()

def _calculate_relevance_score(text: str, client: str, title: str) -> float:
    score = 1.0
    norm_text = _normalise_text(text)
    norm_client = _normalise_text(client)
    norm_title = _normalise_text(title)

    if norm_client in norm_title:
        score += 2.0
    if norm_client in norm_text[:200]:
        score += 0.7

    mentions = norm_text.count(norm_client)
    if mentions > 1:
        score += 0.5 * (mentions - 1)

    context_keywords = ['album', 'single', 'tour', 'concert', 'release', 'new', 'announces', 'performs']
    for keyword in context_keywords:
        if keyword in norm_text:
            score += 0.3

    return min(score, 5.0)

# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------
@dataclass
class Match:
    client: str
    title: str
    description: str
    link: str
    published: str
    source: str
    domain: str
    found_date: str
    relevance_score: float = 1.0

# ---------------------------------------------------------------------
# RSS monitor engine
# ---------------------------------------------------------------------
class RSSClientMonitor:
    def __init__(self, clients: List[str], feeds: List[str], max_workers: int = 10):
        self.clients = [c for c in clients if c]
        self.rss_feeds = [f for f in feeds if f]
        self.max_workers = max_workers
        self.client_patterns: Dict[str, re.Pattern] = {}
        self._compile_client_patterns()

    def _compile_client_patterns(self):
        compiled = {}
        for name in self.clients:
            variants = _name_variants(name)
            if not variants:
                continue
            pat = "|".join(variants)
            compiled[name] = re.compile(pat, re.IGNORECASE)
        self.client_patterns = compiled

    def _match_clients_in_text(self, text: str) -> List[str]:
        norm = _normalise_text(text)
        return [client for client, pat in self.client_patterns.items() if pat.search(norm)]

    def parse_feed_safe(self, feed_url: str) -> List[dict]:
        try:
            raw, enc = robust_get(feed_url)
            head = raw[:200].lower()
            if b"<rss" not in head and b"<feed" not in head and b"<?xml" not in head:
                return []
            text = decode_bytes_best_effort(raw, enc).lstrip("\ufeff \t\r\n")
            feed = feedparser.parse(text)
            return list(feed.entries or [])
        except Exception as e:
            logger.error(f"Error parsing {feed_url}: {e}")
            return []

    def _entry_text(self, entry: dict) -> str:
        parts = [
            entry.get("title", ""),
            entry.get("summary", ""),
            entry.get("description", ""),
            entry.get("content:encoded", ""),
        ]
        contents = entry.get("content") or []
        for c in contents:
            parts.append(c.get("value", ""))
        joined = " ".join(p for p in parts if p)
        return joined[:20000]

    def _format_date(self, entry: dict) -> str:
        try:
            dt = parse_datetime_from_entry(entry)
            if dt:
                return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        return "Unknown Date"

    def _dedupe_key(self, entry: dict) -> str:
        guid = (entry.get("id") or entry.get("guid") or "").strip()
        link = canonicalise_url(entry.get("link") or "")
        title = (entry.get("title") or "").strip().lower()
        key_raw = guid or f"{link}|{title}"
        return md5(key_raw.encode("utf-8", errors="ignore")).hexdigest()

    def _get_domain(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower().replace('www.', '')
            return domain if domain else "unknown"
        except Exception:
            return "unknown"

    def filter_recent_entries(self, entries: List[dict], days: int) -> List[dict]:
        recent = []
        for e in entries:
            dt = parse_datetime_from_entry(e)
            if within_days(dt, days):
                recent.append(e)
        return recent

    def scan_feeds_concurrent(self, days: int = 7, progress_callback=None, fetch=None) -> List[Match]:
        all_matches: List[Match] = []
        seen: set = set()
        fetch = fetch or self.parse_feed_safe

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(fetch, url): url for url in self.rss_feeds}
            completed = 0
            total_feeds = len(future_to_url)

            for future in concurrent.futures.as_completed(future_to_url):
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_feeds)

                feed_url = future_to_url[future]
                try:
                    entries = future.result()
                except Exception as e:
                    logger.error(f"Feed failed: {feed_url} -> {e}")
                    entries = []

                for entry in self.filter_recent_entries(entries, days):
                    key = self._dedupe_key(entry)
                    if key in seen:
                        continue
                    seen.add(key)

                    text = self._entry_text(entry)
                    if not text.strip():
                        continue

                    matched_clients = self._match_clients_in_text(text)
                    if not matched_clients:
                        continue

                    title = entry.get("title") or "No Title"
                    raw_desc = entry.get("description") or entry.get("summary") or ""
                    description = _clean_html(raw_desc)
                    link = entry.get("link") or "No Link"
                    published = self._format_date(entry)
                    domain = self._get_domain(link)

                    for client in matched_clients:
                        relevance = _calculate_relevance_score(text, client, title)
                        all_matches.append(Match(
                            client=client,
                            title=title,
                            description=description[:300] + ("..." if len(description) > 300 else ""),
                            link=link,
                            published=published,
                            source=feed_url,
                            domain=domain,
                            found_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            relevance_score=relevance
                        ))

        all_matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_matches

# ---------------------------------------------------------------------
# Premium UI styling
# ---------------------------------------------------------------------
def apply_premium_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

        .main { padding: 2rem 1rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        .block-container { max-width: 1400px; padding-top: 3rem; padding-bottom: 3rem; }

        h1 { font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent;
             font-size: 3rem !important; margin-bottom: 0.5rem !important; letter-spacing: -0.02em; }
        h2 { font-weight: 600; color: #1a202c; font-size: 1.75rem !important; margin-top: 2rem !important; margin-bottom: 1rem !important; }
        h3 { font-weight: 600; color: #2d3748; font-size: 1.25rem !important; }

        [data-testid="stSidebar"] { background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%); border-right: 1px solid #e2e8f0; box-shadow: 2px 0 10px rgba(0,0,0,0.05); }
        [data-testid="stSidebar"] h2 { color: #2d3748; font-size: 1.25rem !important; font-weight: 700; padding-left: 0.5rem; border-left: 4px solid #667eea; }
        [data-testid="stSidebar"] h3 { color: #4a5568; font-size: 1rem !important; font-weight: 600; margin-top: 1.5rem !important; }

        .stTextArea textarea { border-radius: 12px; border: 2px solid #e2e8f0; font-size: 0.9rem; font-family: 'SF Mono', Monaco, monospace; transition: all 0.3s ease; }
        .stTextArea textarea:focus { border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }

        .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 12px; padding: 0.75rem 2rem; font-weight: 600; font-size: 1.1rem; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); width: 100%; }
        .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6); }

        [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        [data-testid="stMetricLabel"] { font-weight: 600; color: #4a5568; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; }

        .stAlert { border-radius: 12px; border: none; padding: 1rem 1.25rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }

        .article-card { background: white; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; transition: all 0.3s ease; }
        .article-card:hover { transform: translateY(-4px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }
        .article-title { font-size: 1.25rem; font-weight: 700; color: #1a202c; margin-bottom: 0.75rem; line-height: 1.4; }
        .article-meta { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; font-size: 0.875rem; color: #718096; }
        .article-meta-item { display: inline-flex; align-items: center; gap: 0.25rem; }
        .article-description { color: #4a5568; line-height: 1.6; margin-bottom: 1rem; }

        .relevance-badge { display: inline-block; padding: 0.5rem 1rem; border-radius: 20px; font-weight: 600; font-size: 0.875rem; }
        .relevance-high { background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; }
        .relevance-medium { background: linear-gradient(135deg, #ecc94b 0%, #d69e2e 100%); color: white; }
        .relevance-low { background: linear-gradient(135deg, #cbd5e0 0%, #a0aec0 100%); color: white; }

        .link-button { display: inline-block; padding: 0.5rem 1.25rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 0.875rem; transition: all 0.3s ease; }
        .link-button:hover { transform: translateX(4px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }

        .stProgress > div > div { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; }
        .stMultiSelect [data-baseweb="tag"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 6px; }
        .stSlider [data-baseweb="slider"] [role="slider"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }

        .stDownloadButton > button { background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; border: none; border-radius: 10px; padding: 0.75rem 1.5rem; font-weight: 600; transition: all 0.3s ease; }
        .stDownloadButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(72, 187, 120, 0.4); }

        .streamlit-expanderHeader { background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); border-radius: 10px; font-weight: 600; color: #2d3748; }

        .hero-section { text-align: center; padding: 2rem 1rem; background: white; border-radius: 20px; margin-bottom: 2rem; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .subtitle { color: #718096; font-size: 1.25rem; font-weight: 500; margin-top: 0.5rem; }

        .empty-state { text-align: center; padding: 4rem 2rem; background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .empty-state-icon { font-size: 4rem; margin-bottom: 1rem; }

        #MainMenu {visibility: hidden;} footer {visibility: hidden;}

        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%); }
        </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------
st.set_page_config(page_title="Client Mentions Monitor", page_icon="🎧", layout="wide")
apply_premium_styling()

st.markdown("""
<div class="hero-section">
    <h1>🎧 Client Mentions Monitor</h1>
    <p class="subtitle">Track mentions of your clients across leading music news feeds — beautifully and effortlessly.</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("Configuration")
selected_clients = st.sidebar.multiselect(
    "Select clients to monitor",
    options=sorted(DEFAULT_CLIENTS),
    default=sorted(DEFAULT_CLIENTS)[:10],
    help="Pick one or more client names to search for."
)
selected_feeds = st.sidebar.multiselect(
    "Select news feeds",
    options=CURATED_DEFAULT_FEEDS,
    default=CURATED_DEFAULT_FEEDS,
    help="Choose which RSS feeds to scan."
)
days = st.sidebar.slider("Include articles from the last N days", 1, 30, 7)
max_workers = st.sidebar.slider("Parallel feed fetchers", 2, 20, 10)

st.sidebar.markdown("---")
st.sidebar.info("Press **Scan Feeds** below to start monitoring.")

# Cached helpers
@st.cache_data(ttl=600, show_spinner=False)
def cached_fetch_feed(feed_url: str):
    try:
        raw, enc = robust_get(feed_url)
        head = raw[:200].lower()
        if b"<rss" not in head and b"<feed" not in head and b"<?xml" not in head:
            return []
        text = decode_bytes_best_effort(raw, enc).lstrip("\ufeff \t\r\n")
        feed = feedparser.parse(text)
        return list(feed.entries or [])
    except Exception:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def cached_scan(clients, feeds, days, max_workers):
    mon = RSSClientMonitor(clients, feeds, max_workers=max_workers)
    return mon.scan_feeds_concurrent(days=days, fetch=cached_fetch_feed)

def st_progress_callback():
    bar = st.progress(0)
    text = st.empty()
    def cb(done: int, total: int):
        percent = int(done / total * 100) if total else 100
        bar.progress(percent)
        text.write(f"Scanning feeds… {done}/{total}")
        if done == total:
            bar.empty()
            text.empty()
    return cb

monitor = RSSClientMonitor(selected_clients, selected_feeds, max_workers=max_workers)

if st.button("🚀 Scan Feeds Now", use_container_width=True):
    with st.spinner("Checking cached results…"):
        matches = cached_scan(selected_clients, selected_feeds, days, max_workers)

    if not matches:
        progress_cb = st_progress_callback()
        with st.spinner("Fetching RSS feeds…"):
            matches = monitor.scan_feeds_concurrent(
                days=days,
                progress_callback=progress_cb,
                fetch=cached_fetch_feed,
            )

    if not matches:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <h3>No mentions found</h3>
            <p>Try adjusting your date range or adding more clients or feeds.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ Found {len(matches)} relevant mentions!")

        df = pd.DataFrame([m.__dict__ for m in matches])
        col1, col2, col3 = st.columns(3)
        col1.metric("Mentions Found", len(df))
        col2.metric("Feeds Selected", len(selected_feeds))
        col3.metric("Clients Selected", len(selected_clients))

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Results as CSV",
            csv,
            "client_mentions.csv",
            "text/csv",
            use_container_width=True,
        )

        st.subheader("Latest Mentions")
        for match in matches:
            relevance_class = (
                "relevance-high" if match.relevance_score >= 4 else
                "relevance-medium" if match.relevance_score >= 2 else
                "relevance-low"
            )
            st.markdown(f"""
            <div class="article-card">
                <div class="article-title">{match.title}</div>
                <div class="article-meta">
                    <div class="article-meta-item">📰 <strong>{match.domain}</strong></div>
                    <div class="article-meta-item">📅 {match.published}</div>
                    <div class="article-meta-item">👤 {match.client}</div>
                </div>
                <div class="article-description">{match.description}</div>
                <div>
                    <span class="relevance-badge {relevance_class}">
                        Relevance: {match.relevance_score:.1f}
                    </span>
                    <a href="{match.link}" class="link-button" target="_blank" rel="noopener">Read Article →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("👈 Configure your clients and feeds in the sidebar, then click **Scan Feeds Now**.")

st.markdown(
    f"<p style='text-align:center; color:#A0AEC0; font-size:0.8rem;'>© {datetime.now().year} Client Mentions Monitor</p>",
    unsafe_allow_html=True
)
