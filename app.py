#!/usr/bin/env python3
"""
Client Mentions Monitor — Single-file Streamlit App (UX-focused)
- All default clients & feeds are always included; users can only ADD more
- Clear CTA, progressive disclosure, friendly empty states, and robust feedback
- Sorting, quick filtering, min relevance, pagination (post-scan only)
"""

import re
import time
import html
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
# Defaults (always included)
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
# HTTP (robust retries, urllib3 v1/v2 compatible)
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
        return Retry(allowed_methods=frozenset(["GET", "HEAD"]), **base_kwargs)  # urllib3 v2
    except TypeError:
        return Retry(method_whitelist=frozenset(["GET", "HEAD"]), **base_kwargs)  # urllib3 v1

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
# Utils
# ---------------------------------------------------------------------
TRACKING_PARAMS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","fbclid","gclid","igshid"}

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
        return True  # permissive for feeds missing dates
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff

# ---------------------------------------------------------------------
# Text handling & scoring
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
        return []
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
    for kw in ['album','single','tour','concert','release','new','announces','performs']:
        if kw in norm_text:
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
# Engine
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
            compiled[name] = re.compile("|".join(variants), re.IGNORECASE)
        self.client_patterns = compiled

    def _match_clients_in_text(self, text: str) -> List[str]:
        n = _normalise_text(text)
        return [client for client, pat in self.client_patterns.items() if pat.search(n)]

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
        return " ".join(p for p in parts if p)[:20000]

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
        raw = guid or f"{link}|{title}"
        return md5(raw.encode("utf-8", errors="ignore")).hexdigest()

    def _get_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower().replace('www.', '') or "unknown"
        except Exception:
            return "unknown"

    def filter_recent_entries(self, entries: List[dict], days: int) -> List[dict]:
        return [e for e in entries if within_days(parse_datetime_from_entry(e), days)]

    def scan_feeds_concurrent(self, days: int = 7, progress_callback=None, fetch=None) -> List[Match]:
        all_matches: List[Match] = []
        seen: set = set()
        fetch = fetch or self.parse_feed_safe

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(fetch, url): url for url in self.rss_feeds}
            completed = 0
            total = len(future_to_url)

            for future in concurrent.futures.as_completed(future_to_url):
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)

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

        all_matches.sort(key=lambda x: (-(x.relevance_score), x.domain, x.title))
        return all_matches

# ---------------------------------------------------------------------
# Premium styling
# ---------------------------------------------------------------------
def apply_premium_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        .main { padding: 2rem 1rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        .block-container { max-width: 1280px; padding-top: 2rem; padding-bottom: 2rem; }
        h1 { font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.6rem !important; margin-bottom: 0.25rem !important; letter-spacing: -0.02em; }
        h2 { font-weight: 600; color: #1a202c; font-size: 1.4rem !important; margin-top: 1.5rem !important; margin-bottom: 0.75rem !important; }
        .hero-section { text-align: center; padding: 1.5rem 1rem; background: white; border-radius: 16px; margin-bottom: 1rem; box-shadow: 0 6px 24px rgba(0,0,0,0.06); }
        .subtitle { color: #718096; font-size: 1rem; font-weight: 500; margin-top: 0.25rem; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%); border-right: 1px solid #e2e8f0; }
        .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 12px; padding: 0.65rem 1rem; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.35); }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(102, 126, 234, 0.45); }
        [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .article-card { background: white; border-radius: 14px; padding: 1.1rem; margin-bottom: 1rem; box-shadow: 0 4px 18px rgba(0,0,0,0.06); border: 1px solid #edf2f7; }
        .article-title { font-size: 1.05rem; font-weight: 700; color: #1a202c; margin-bottom: 0.5rem; line-height: 1.35; }
        .article-meta { display: flex; gap: 0.8rem; flex-wrap: wrap; margin-bottom: 0.5rem; font-size: 0.86rem; color: #718096; }
        .article-description { color: #4a5568; line-height: 1.55; margin-bottom: 0.6rem; }
        .relevance-badge { display: inline-block; padding: 0.35rem 0.75rem; border-radius: 999px; font-weight: 700; font-size: 0.75rem; }
        .relevance-high { background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; }
        .relevance-medium { background: linear-gradient(135deg, #ecc94b 0%, #d69e2e 100%); color: white; }
        .relevance-low { background: linear-gradient(135deg, #cbd5e0 0%, #a0aec0 100%); color: white; }
        .link-button { display: inline-block; padding: 0.45rem 0.9rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
        .empty-state { text-align: center; padding: 2.5rem 1.5rem; background: white; border-radius: 16px; box-shadow: 0 6px 24px rgba(0,0,0,0.06); }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------
st.set_page_config(page_title="Client Mentions Monitor", page_icon="🎧", layout="wide")
apply_premium_styling()

st.markdown("""
<div class="hero-section" role="banner" aria-label="Client Mentions Monitor">
    <h1>🎧 Client Mentions Monitor</h1>
    <p class="subtitle">All clients and all feeds are scanned by default. Add more in the sidebar.</p>
</div>
""", unsafe_allow_html=True)

# --- session state for additions (persist per session) ---
if "extra_clients" not in st.session_state:
    st.session_state.extra_clients = []
if "extra_feeds" not in st.session_state:
    st.session_state.extra_feeds = []
if "last_df" not in st.session_state:
    st.session_state.last_df = None
if "pagination" not in st.session_state:
    st.session_state.pagination = {"page": 1, "page_size": 10}

def _unique_trimmed(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        s2 = (s or "").strip()
        if not s2:
            continue
        key = s2.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s2)
    return out

# --- sidebar: add-only forms (progressive, clear labels, validation) ---
st.sidebar.header("Add clients & feeds")

with st.sidebar.form("add_clients_form", clear_on_submit=True):
    st.markdown("**Add Clients** (one per line)")
    new_clients = st.text_area(
        "Add client names",
        placeholder="e.g.\nArtist One\nCool Duo\nAnother Client",
        height=110,
        label_visibility="collapsed",
    )
    add_clients = st.form_submit_button("➕ Add Clients")
    if add_clients:
        items = [line.strip() for line in (new_clients or "").splitlines() if line.strip()]
        if items:
            st.session_state.extra_clients = _unique_trimmed(st.session_state.extra_clients + items)
            st.toast(f"Added {len(items)} client(s).", icon="✅")
        else:
            st.toast("No clients to add.", icon="⚠️")

with st.sidebar.form("add_feeds_form", clear_on_submit=True):
    st.markdown("**Add Feed URLs** (one per line)")
    new_feeds = st.text_area(
        "Add feed URLs",
        placeholder="https://example.com/feed\nhttps://site.com/rss",
        height=110,
        label_visibility="collapsed",
    )
    add_feeds = st.form_submit_button("➕ Add Feeds")
    if add_feeds:
        def _valid_url(u: str) -> bool:
            try:
                p = urlparse(u.strip())
                return bool(p.scheme in ("http", "https") and p.netloc)
            except Exception:
                return False
        raw_items = [line.strip() for line in (new_feeds or "").splitlines() if line.strip()]
        items = [u for u in raw_items if _valid_url(u)]
        bad = [u for u in raw_items if u not in items]
        if items:
            st.session_state.extra_feeds = _unique_trimmed(st.session_state.extra_feeds + items)
            st.toast(f"Added {len(items)} feed(s).", icon="✅")
        if bad:
            st.warning(f"Skipped {len(bad)} invalid URL(s).")

st.sidebar.markdown("---")
c1, c2 = st.sidebar.columns(2)
if c1.button("🧹 Clear Clients", use_container_width=True):
    st.session_state.extra_clients = []
    st.toast("Cleared added clients.", icon="🗑️")
if c2.button("🧹 Clear Feeds", use_container_width=True):
    st.session_state.extra_feeds = []
    st.toast("Cleared added feeds.", icon="🗑️")

# --- computed master lists (defaults + additions) ---
SELECTED_CLIENTS = _unique_trimmed(DEFAULT_CLIENTS + st.session_state.extra_clients)
SELECTED_FEEDS = _unique_trimmed(CURATED_DEFAULT_FEEDS + st.session_state.extra_feeds)

# --- quick context line (helps orientation) ---
st.caption(f"Scanning **{len(SELECTED_CLIENTS)} clients** across **{len(SELECTED_FEEDS)} feeds**.")

# ---------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------
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
def cached_scan(clients: List[str], feeds: List[str], days: int, max_workers: int):
    mon = RSSClientMonitor(clients, feeds, max_workers=max_workers)
    return mon.scan_feeds_concurrent(days=days, fetch=cached_fetch_feed)

# ---------------------------------------------------------------------
# Minimal controls (progressive): days & performance
# ---------------------------------------------------------------------
top_a, top_b, top_c = st.columns([1,1,2])
with top_a:
    days = st.slider("Last N days", 1, 30, 7, help="Only include articles published within this window.")
with top_b:
    max_workers = st.slider("Parallel fetchers", 2, 20, 10, help="Higher = faster, but heavier on networks.")
with top_c:
    run_now = st.button("🚀 Scan All Feeds Now", use_container_width=True)

def st_progress_callback():
    bar = st.progress(0, text="Starting…")
    def cb(done: int, total: int):
        percent = int(done / total * 100) if total else 100
        bar.progress(percent, text=f"Scanning feeds… {done}/{total}")
        if done == total:
            time.sleep(0.15)
            bar.empty()
    return cb

# ---------------------------------------------------------------------
# Run scan
# ---------------------------------------------------------------------
monitor = RSSClientMonitor(SELECTED_CLIENTS, SELECTED_FEEDS, max_workers=max_workers)

if run_now:
    with st.spinner("Checking cached results…"):
        matches = cached_scan(SELECTED_CLIENTS, SELECTED_FEEDS, days, max_workers)

    if not matches:
        progress_cb = st_progress_callback()
        with st.spinner("Fetching RSS feeds…"):
            matches = monitor.scan_feeds_concurrent(days=days, progress_callback=progress_cb, fetch=cached_fetch_feed)

    # Store raw results for post-filters (don’t mutate originals)
    df = pd.DataFrame([m.__dict__ for m in matches])
    st.session_state.last_df = df.copy()

# ---------------------------------------------------------------------
# Results area (progressive controls after a scan)
# ---------------------------------------------------------------------
df = st.session_state.last_df
if df is None or df.empty:
    st.markdown("""
    <div class="empty-state" role="status">
        <div style="font-size:2.2rem; margin-bottom:0.3rem;">🔍</div>
        <h3 style="margin:0;">No results yet</h3>
        <p style="color:#4a5568; margin:0.25rem 0 0;">Press <strong>Scan All Feeds Now</strong> to start.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mentions Found", len(df))
    col2.metric("Unique Clients", df["client"].nunique())
    col3.metric("Sources", df["domain"].nunique())
    col4.metric("Avg. Relevance", f"{df['relevance_score'].mean():.1f}")

    # Post-scan controls (progressive disclosure)
    st.divider()
    st.write("### Refine results")

    f1, f2, f3, f4 = st.columns([2,1,1,1])
    with f1:
        query = st.text_input("Quick filter (title/description/client/domain)", placeholder="e.g. tour, album, ‘Matt Corby’, stereogum")
    with f2:
        min_rel = st.slider("Min relevance", 1.0, 5.0, 2.0, 0.1)
    with f3:
        sort_by = st.selectbox("Sort by", ["Relevance (desc)", "Date (newest)"])
    with f4:
        page_size = st.selectbox("Page size", [10, 20, 50], index=0)

    # Apply filters
    view = df.copy()
    if query:
        q = query.strip().lower()
        view = view[
            view["title"].str.lower().str.contains(q, na=False) |
            view["description"].str.lower().str.contains(q, na=False) |
            view["client"].str.lower().str.contains(q, na=False) |
            view["domain"].str.lower().str.contains(q, na=False)
        ]
    view = view[view["relevance_score"] >= min_rel]

    # Sort
    if sort_by == "Date (newest)":
        # Attempt to parse published; Unknown Date at end
        def _to_dt(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d %H:%M")
            except Exception:
                return datetime.min
        view = view.copy()
        view["_dt"] = view["published"].apply(_to_dt)
        view = view.sort_values(by=["_dt", "relevance_score"], ascending=[False, False]).drop(columns=["_dt"])
    else:
        view = view.sort_values(by=["relevance_score","published"], ascending=[False, False])

    # Pagination (keeps cognitive load low)
    total_items = len(view)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    current_page = min(st.session_state.pagination.get("page", 1), total_pages)

    nav_left, nav_mid, nav_right = st.columns([1,2,1])
    with nav_left:
        if st.button("◀ Prev", use_container_width=True, disabled=current_page <= 1):
            current_page -= 1
    with nav_mid:
        st.write(f"Page **{current_page} / {total_pages}**")
    with nav_right:
        if st.button("Next ▶", use_container_width=True, disabled=current_page >= total_pages):
            current_page += 1
    st.session_state.pagination["page"] = current_page

    start = (current_page - 1) * page_size
    end = start + page_size
    page_df = view.iloc[start:end]

    # Download current view
    st.download_button(
        "⬇️ Download filtered CSV",
        page_df.to_csv(index=False).encode("utf-8"),
        file_name="client_mentions_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Render cards (scannable, consistent)
    st.write("### Mentions")
    for _, row in page_df.iterrows():
        rel_class = "relevance-high" if row["relevance_score"] >= 4 else ("relevance-medium" if row["relevance_score"] >= 2 else "relevance-low")
        st.markdown(f"""
        <div class="article-card" role="article" aria-label="{row['title']}">
            <div class="article-title">{row['title']}</div>
            <div class="article-meta">
                <div>📰 <strong>{row['domain']}</strong></div>
                <div>📅 {row['published']}</div>
                <div>👤 {row['client']}</div>
            </div>
            <div class="article-description">{row['description']}</div>
            <div style="display:flex; gap:.5rem; align-items:center;">
                <span class="relevance-badge {rel_class}">Relevance: {row['relevance_score']:.1f}</span>
                <a href="{row['link']}" class="link-button" target="_blank" rel="noopener">Read Article →</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
