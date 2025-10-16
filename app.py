#!/usr/bin/env python3
"""
Client Mentions Monitor - Premium UI/UX Edition
Beautiful, modern interface for monitoring client mentions across music news feeds
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
from requests.adapters import HTTPAdapter, Retry

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
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
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
                except Exception as e:
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
                
                feed_url = future_to_url[future]
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
                            source=feed_url,
                            domain=domain,
                            found_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            relevance_score=relevance
                        ))
        
        all_matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_matches

# ---------------------- Streamlit UI ----------------------
def main():
    st.set_page_config(
        page_title="Client Mentions Monitor",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    h1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; padding: 0.75rem 2rem; font-weight: 600; border: none; }
    .match-card { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid; }
    .match-card-high { border-left-color: #48bb78; background: linear-gradient(to right, #f0fff4 0%, white 100%); }
    .match-card-medium { border-left-color: #ecc94b; background: linear-gradient(to right, #fffbeb 0%, white 100%); }
    .match-card-low { border-left-color: #cbd5e0; background: linear-gradient(to right, #f7fafc 0%, white 100%); }
    .relevance-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-weight: 600; font-size: 0.875rem; }
    .relevance-high { background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); color: white; }
    .relevance-medium { background: linear-gradient(135deg, #ecc94b 0%, #d69e2e 100%); color: white; }
    .relevance-low { background: linear-gradient(135deg, #cbd5e0 0%, #a0aec0 100%); color: white; }
    .article-link { display: inline-block; margin-top: 1rem; padding: 0.5rem 1.25rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 0.875rem; transition: all 0.3s ease; }
    .article-link:hover { transform: translateX(4px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'matches' not in st.session_state:
        st.session_state.matches = None
    if 'scan_time' not in st.session_state:
        st.session_state.scan_time = None
    if 'num_feeds' not in st.session_state:
        st.session_state.num_feeds = 0
    
    # Header
    st.title("🎵 Client Mentions Monitor")
    st.markdown("Track mentions of your clients across music news feeds")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("Clients to Monitor")
        st.success(f"Monitoring {len(DEFAULT_CLIENTS)} preset clients")
        with st.expander("View client list"):
            st.write(", ".join(DEFAULT_CLIENTS[:10]) + "...")
        
        st.subheader("Settings")
        days = st.slider("Days to look back", 1, 30, 7)
        max_workers = st.slider("Concurrent workers", 2, 20, 10, 
            help="Number of feeds to process simultaneously")
        min_relevance = st.slider("Minimum relevance", 1.0, 5.0, 1.0, 0.5)
        
        run_button = st.button("🚀 Start Scan", use_container_width=True)
        
        if st.session_state.matches is not None:
            if st.button("🗑️ Clear Results", use_container_width=True):
                st.session_state.matches = None
                st.session_state.scan_time = None
                st.rerun()
    
    # Main content
    if run_button:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(completed, total):
            progress_bar.progress(completed / total)
            status_text.text(f"Processing {completed}/{total} feeds...")
        
        monitor = RSSClientMonitor(DEFAULT_CLIENTS, CURATED_DEFAULT_FEEDS, max_workers)
        
        start_time = time.time()
        matches = monitor.scan_feeds_concurrent(days, update_progress)
        elapsed = time.time() - start_time
        
        st.session_state.matches = matches
        st.session_state.scan_time = elapsed
        st.session_state.num_feeds = len(CURATED_DEFAULT_FEEDS)
        
        progress_bar.empty()
        status_text.empty()
    
    # Display results
    if st.session_state.matches is not None:
        matches = [m for m in st.session_state.matches if m.relevance_score >= min_relevance]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Feeds Scanned", st.session_state.num_feeds)
        col2.metric("Matches Found", len(matches))
        col3.metric("Clients Mentioned", len(set(m.client for m in matches)))
        col4.metric("Scan Time", f"{st.session_state.scan_time:.1f}s")
        
        if matches:
            st.markdown("---")
            
            # Client filter
            with st.expander("🔍 Filter by Client"):
                selected = st.multiselect(
                    "Select clients to show",
                    options=sorted(set(m.client for m in matches)),
                    key="client_filter"
                )
            
            display_matches = matches if not selected else [m for m in matches if m.client in selected]
            
            if selected:
                st.info(f"Showing {len(display_matches)} of {len(matches)} matches")
            
            # Export
            df = pd.DataFrame([vars(m) for m in display_matches])
            csv = df.to_csv(index=False)
            st.download_button("📥 Download CSV", csv, f"mentions_{datetime.now().strftime('%Y%m%d')}.csv")
            
            st.markdown("---")
            
            # Display cards
            for match in display_matches:
                # Determine card styling based on relevance
                if match.relevance_score >= 3.5:
                    card_class = "match-card-high"
                    badge_class = "relevance-high"
                elif match.relevance_score >= 2.0:
                    card_class = "match-card-medium"
                    badge_class = "relevance-medium"
                else:
                    card_class = "match-card-low"
                    badge_class = "relevance-low"
                
                st.markdown(f"""
                <div class="match-card {card_class}">
                    <h3 style="margin-top: 0; margin-bottom: 0.5rem;">
                        {html.escape(match.title)}
                    </h3>
                    <div style="margin-bottom: 0.75rem; color: #718096; font-size: 0.875rem;">
                        <strong>🎯 {html.escape(match.client)}</strong> • 
                        📰 {html.escape(match.domain)} • 
                        📅 {html.escape(match.published)} •
                        <span class="relevance-badge {badge_class}">Relevance: {match.relevance_score:.1f}</span>
                    </div>
                    <p style="color: #4a5568; line-height: 1.6; margin-bottom: 1rem;">
                        {html.escape(match.description)}
                    </p>
                    <a href="{match.link}" target="_blank" rel="noopener noreferrer" class="article-link">
                        Read Article →
                    </a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No matches found. Try adjusting the filters.")
    else:
        st.info("👈 Configure settings in the sidebar and click 'Start Scan'")

if __name__ == "__main__":
    main()
