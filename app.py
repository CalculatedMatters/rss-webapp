#!/usr/bin/env python3
"""
Client Mentions Monitor - Premium UI/UX Edition
"""

import streamlit as st
import json
import logging
import re
import time
import unicodedata
import html
import concurrent.futures
import functools
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import md5
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import pandas as pd
import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry  # correct import for Retry

# ---------------------- Configuration ----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rss-monitor")

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

# ---------------------- HTTP Session ----------------------
def build_http_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=15, pool_maxsize=25)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "ClientMentionsBot/2.0"})
    return s

HTTP = build_http_session()

# ---------------------- Utility Functions ----------------------
def canonicalise_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        norm = parsed._replace(netloc=parsed.netloc.lower(), fragment="")
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
def robust_get(url: str, timeout: int = 15) -> Tuple[bytes, Optional[str]]:
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
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff

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

# ---------------------- Text Processing ----------------------
APOS_CLASS = r"[\'\u2019\u02BC]"
BOUNDARY = r"(?:(?<!\w)|\b)"
END_BOUND = r"(?!\w)"

def _normalise_text(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def _name_variants(name: str) -> List[str]:
    base = re.escape(_normalise_text(name))
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

    mentions = norm_text.count(norm_client)
    if mentions > 1:
        score += 0.5 * (mentions - 1)

    context_keywords = ['album', 'single', 'tour', 'concert', 'release', 'new', 'announces', 'performs']
    for keyword in context_keywords:
        if keyword in norm_text:
            score += 0.3

    return min(score, 5.0)

# ---------------------- RSS Monitor Class ----------------------
class RSSClientMonitor:
    def __init__(self, clients: List[str], feeds: List[str], max_workers: int = 10):
        self.clients = clients
        self.rss_feeds = feeds
        self.max_workers = max_workers
        self.client_patterns: Dict[str, re.Pattern] = {}
        self._compile_client_patterns()

    def _compile_client_patterns(self):
        compiled = {}
        for name in self.clients:
            pat = "|".join(_name_variants(name))
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

            text = decode_bytes_best_effort(raw, enc)
            text = text.lstrip("\ufeff \t\r\n")

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
        ]
        contents = entry.get("content") or []
        for c in contents:
            parts.append(c.get("value", ""))
        return " ".join(p for p in parts if p)

    def _format_date(self, entry: dict) -> str:
        try:
            dt = parse_datetime_from_entry(entry)
            if dt:
                return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        return "Unknown Date"

    def _dedupe_key(self, entry: dict) -> str:
        link = canonicalise_url(entry.get("link") or "")
        title = (entry.get("title") or "").strip().lower()
        key_raw = f"{link}|{title}"
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

    def scan_feeds_concurrent(self, days: int = 7, progress_callback=None) -> List[Match]:
        all_matches: List[Match] = []
        seen: set = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.parse_feed_safe, url): url
                for url in self.rss_feeds
            }

            completed = 0
            total_feeds = len(future_to_url)

            for future in concurrent.futures.as_completed(future_to_url):
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_feeds)

                entries = future.result()
                recent_entries = self.filter_recent_entries(entries, days)

                for entry in recent_entries:
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
                            source=f"{domain}",
                            domain=domain,
                            found_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            relevance_score=relevance
                        ))

        all_matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_matches

# ---------------------- Premium UI Styling ----------------------
def apply_premium_styling():
    """Apply modern, professional CSS styling"""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        .main { padding: 2rem 1rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        .block-container { max-width: 1400px; padding-top: 3rem; padding-bottom: 3rem; }
        h1 { font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem !important; margin-bottom: 0.5rem !important; letter-spacing: -0.02em; }
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
        .article-title { font-size: 1.25rem; font-weight: 700; color: #1a202c; margin-bottom: 0.75rem; }
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

# ---------------------- UI Helpers ----------------------
@dataclass
class _Void:  # to satisfy type hints when needed
    pass

def matches_to_dataframe(matches: List[Match]) -> pd.DataFrame:
    return pd.DataFrame([m.__dict__ for m in matches])

def relevance_class(score: float) -> str:
    if score >= 3.5:
        return "relevance-high"
    if score >= 2.0:
        return "relevance-medium"
    return "relevance-low"

def render_match_card(m: Match):
    st.markdown(f"""
        <div class="article-card">
            <div class="article-title">{html.escape(m.title)}</div>
            <div class="article-meta">
                <div class="article-meta-item">🎯 Client: <strong>{html.escape(m.client)}</strong></div>
                <div class="article-meta-item">📰 Source: {html.escape(m.domain)}</div>
                <div class="article-meta-item">📅 Published: {html.escape(m.published)}</div>
                <div class="article-meta-item"><span class="relevance-badge {relevance_class(m.relevance_score)}">Relevance: {m.relevance_score:.1f}</span></div>
            </div>
            <div class="article-description">{html.escape(m.description)}</div>
            <a class="link-button" href="{m.link}" target="_blank" rel="noopener">Read Article →</a>
        </div>
    """, unsafe_allow_html=True)

def parse_list_textarea(text: str) -> List[str]:
    items = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",") if p.strip()]
        items.extend(parts if parts else [line])
    seen = set()
    out = []
    for x in items:
        k = x.lower()
        if k not in seen:
            out.append(x)
            seen.add(k)
    return out

# ---------------------- Main App ----------------------
def main():
    st.set_page_config(page_title="Client Mentions Monitor", page_icon="🔎", layout="wide")
    apply_premium_styling()

    st.markdown("""
        <div class="hero-section">
            <h1>Client Mentions Monitor</h1>
            <div class="subtitle">Scanning music news feeds for <strong>all preset clients</strong></div>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar controls
    with st.sidebar:
        st.header("Configuration")

        # Clients (fixed to all presets)
        st.subheader("Clients")
        st.success(f"Using all preset clients: {len(DEFAULT_CLIENTS)} total.")
        with st.expander("Preview client list", expanded=False):
            st.caption(", ".join(DEFAULT_CLIENTS))

        # Feeds
        st.subheader("Feeds")
        use_curated = st.checkbox("Use curated default feeds", True)
        extra_feeds_text = st.text_area(
            "Additional feed URLs (one per line)",
            "",
            height=120,
            placeholder="https://example.com/rss\nhttps://another.com/feed"
        )
        extra_feeds = parse_list_textarea(extra_feeds_text)
        feeds = (CURATED_DEFAULT_FEEDS if use_curated else []) + extra_feeds
        feeds = list(dict.fromkeys(feeds))  # dedupe, preserve order

        # Scan options
        st.subheader("Scan Options")
        days = st.slider("Look back (days)", min_value=1, max_value=60, value=7)
        max_workers = st.slider("Parallel requests", min_value=2, max_value=32, value=10)
        min_relevance = st.slider("Minimum relevance to show", min_value=1.0, max_value=5.0, value=1.0, step=0.1)

        start_scan = st.button("🔍 Scan Feeds")

    # Content area
    if not feeds:
        st.warning("Please add at least one RSS feed in the sidebar.")
        return

    st.write("")

    if start_scan:
        clients = DEFAULT_CLIENTS  # always use the full preset list

        # Progress UI
        progress = st.progress(0.0, text="Starting scan…")
        progress_text = st.empty()

        def progress_cb(done, total):
            pct = done / max(total, 1)
            progress.progress(pct, text=f"Scanning feeds… {done}/{total}")
            progress_text.caption(f"Processed {done} of {total} feeds")

        monitor = RSSClientMonitor(clients=clients, feeds=feeds, max_workers=max_workers)

        t0 = time.time()
        matches = monitor.scan_feeds_concurrent(days=days, progress_callback=progress_cb)
        scan_seconds = time.time() - t0

        # Filter by relevance
        matches = [m for m in matches if m.relevance_score >= min_relevance]

        progress.empty()
        progress_text.empty()

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Feeds scanned", f"{len(feeds)}")
        col2.metric("Matches found", f"{len(matches)}")
        unique_clients = len(set(m.client for m in matches))
        col3.metric("Clients mentioned", f"{unique_clients} / {len(DEFAULT_CLIENTS)}")
        col4.metric("Scan time", f"{scan_seconds:.1f}s")

        if matches:
            st.subheader("Matches")
            # Export
            df = matches_to_dataframe(matches)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, file_name=f"client_mentions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")

            # Optional filter by client (useful with many hits)
            with st.expander("Filter by client (optional)", expanded=False):
                selected_clients = st.multiselect(
                    "Show only these clients",
                    options=sorted(set(m.client for m in matches)),
                    default=[]
                )
                matches_to_show = [m for m in matches if (not selected_clients or m.client in selected_clients)]
            # Render cards
            for i, m in enumerate(matches_to_show, start=1):
                render_match_card(m)
                if i % 10 == 0:
                    st.divider()
            if not matches_to_show:
                st.info("No matches after applying filters.")
        else:
            st.markdown("""
                <div class="empty-state">
                    <div class="empty-state-icon">📰</div>
                    <h3>No mentions found</h3>
                    <p>Try increasing the look-back window, adding more feeds, or lowering the minimum relevance.</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.subheader("How it works")
        st.markdown("""
        1. This app always scans **all preset clients** (no need to pick manually).  
        2. Choose your **feeds** (use curated defaults and/or add your own).  
        3. Click **Scan Feeds** to fetch and analyze recent items.  
        4. Review the **cards**, adjust the **relevance filter**, and **export CSV**.
        """)
        st.info("Tip: Add more RSS/Atom feeds in the sidebar to widen coverage.")

if __name__ == "__main__":
    main()
