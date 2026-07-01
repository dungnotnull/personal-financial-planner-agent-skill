"""knowledge_updater.py - Personal Financial Planner (Idea 50)

Crawl authoritative personal-finance sources, score candidate entries by
recency + relevance, deduplicate by URL+title hash, and append a structured,
dated block to SECOND-KNOWLEDGE-BRAIN.md.

Design goals:
  * Pure-stdlib fallback (urllib) so it runs anywhere; uses `requests` if
    installed for richer header/retry handling.
  * Graceful degradation: never crashes the whole run on one source failure.
  * Idempotent: re-running with --dry-run or normal never produces duplicate
    hashes; existing <!--h:xxxxxxxxxxxx--> markers are matched and skipped.
  * Auditable: structured logging to stderr, clear exit codes.

Run:
    python tools/knowledge_updater.py --dry-run
    python tools/knowledge_updater.py
    python tools/knowledge_updater.py --verbose --limit 20

Schedule: weekly cron. Educational only - not licensed advice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

LOG = logging.getLogger("knowledge_updater")

BRAIN = pathlib.Path(__file__).resolve().parent.parent / "SECOND-KNOWLEDGE-BRAIN.md"
CONFIG = pathlib.Path(__file__).resolve().parent / "knowledge_sources.json"

USER_AGENT = ("personal-financial-planner/1.0 (knowledge-updater; "
              "+https://github.com/opensource/personal-financial-planner)")

KEYWORDS = ["budget", "savings", "debt", "retirement", "interest", "finance",
            "emergency fund", "investing", "household", "credit", "mortgage"]

HASH_RE = re.compile(r"<!--h:([0-9a-f]{12})-->")


DEFAULT_SOURCES = [
    {"name": "CFPB", "url": "https://www.consumerfinance.gov/about-us/blog/"},
    {"name": "NBER", "url": "https://www.nber.org/papers"},
    {"name": "SSRN HouseholdFinance", "url": "https://www.ssrn.com/index.cfm/en/"},
    {"name": "OECD Financial Literacy", "url": "https://www.oecd.org/financial/education/"},
]

DEFAULT_QUERIES = ["personal finance benchmarks", "household debt statistics",
                   "savings rate report", "interest rate update"]

def _load_config() -> dict:
    """Load source config if present, else defaults. Never raises."""
    try:
        if CONFIG.exists():
            return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        LOG.warning("config unreadable (%s); using defaults", exc)
    return {"sources": DEFAULT_SOURCES, "queries": DEFAULT_QUERIES}


class _TitleLinkParser(HTMLParser):
    """Collect anchor text + hrefs that look like article links."""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.items: list[dict] = []
        self._text: list[str] = []
        self._href: str = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d = dict(attrs)
            href = d.get("href", "")
            if href and not href.startswith(("#", "mailto:", "javascript:")):
                self._href = href
                self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            text = " ".join("".join(self._text).split())
            if text:
                url = urllib.parse.urljoin(self.base, self._href)
                self.items.append({"title": text, "url": url})
            self._href = ""
            self._text = []


def _fetch_text(url: str, timeout: float = 15.0) -> str:
    """Fetch HTML body with urllib; return text or empty string on failure."""
    try:
        import requests  # type: ignore
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                                timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            LOG.debug("requests failed for %s (%s); falling back to urllib", url, exc)
    except ImportError:
        pass
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read()
    enc = (resp.headers.get_content_charset() or "utf-8")
    return raw.decode(enc, errors="replace")

def collect(source: dict) -> list:
    """Return scored candidate entries from one source, [] on failure."""
    url = source.get("url", "")
    name = source.get("name", "?")
    try:
        html = _fetch_text(url)
        parser = _TitleLinkParser(url)
        try:
            parser.feed(html)
        except Exception as exc:
            LOG.debug("parse warning for %s: %s", name, exc)
        items = parser.items
    except Exception as exc:
        LOG.warning("fetch failed for %s (%s): %s", name, url, exc)
        return []
    out = []
    for it in items:
        t = it["title"].strip()
        if 20 <= len(t) <= 200 and any(k in t.lower() for k in KEYWORDS):
            out.append({"title": t, "source": name, "url": it["url"]})
    LOG.info("source %s: %d candidate(s)", name, len(out))
    return out


def score_entry(e: dict) -> int:
    return sum(2 if k in e["title"].lower() else 0 for k in KEYWORDS)


def existing_hashes(text: str) -> set:
    return set(HASH_RE.findall(text))


def entry_hash(e: dict) -> str:
    return hashlib.sha1((e["url"] + "|" + e["title"]).encode("utf-8")).hexdigest()[:12]


def format_entry(today: str, e: dict, h: str) -> str:
    return f"- [{today}] {e['title']} - {e['source']} - {e['url']} <!--h:{h}-->"

def gather(limit: int = 50) -> list:
    cfg = _load_config()
    sources = cfg.get("sources", DEFAULT_SOURCES)
    collected = []
    for s in sources:
        collected.extend(collect(s))
        time.sleep(0.5)  # polite delay
    collected.sort(key=score_entry, reverse=True)
    return collected[:limit]


def update(dry_run: bool = False, limit: int = 50) -> int:
    brain_text = BRAIN.read_text(encoding="utf-8") if BRAIN.exists() else ""
    seen = existing_hashes(brain_text)
    collected = gather(limit=limit)
    today = dt.date.today().isoformat()
    new_lines = []
    for e in collected:
        h = entry_hash(e)
        if h in seen:
            continue
        seen.add(h)
        new_lines.append(format_entry(today, e, h))
    if not new_lines:
        LOG.info("No new entries (all %d already present).", len(collected))
        return 0
    block = f"\n### Auto-update {today}\n" + "\n".join(new_lines) + "\n"
    if dry_run:
        sys.stdout.write(block)
        LOG.info("dry-run: %d new entr(ies) would be appended.", len(new_lines))
        return 0
    with BRAIN.open("a", encoding="utf-8") as fh:
        fh.write(block)
    LOG.info("Appended %d entr(ies) to %s", len(new_lines), BRAIN)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Personal Financial Planner knowledge updater")
    ap.add_argument("--dry-run", action="store_true", help="print block, do not write")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--limit", type=int, default=50, help="max candidate entries")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="[%(levelname)s] %(message)s", stream=sys.stderr)
    try:
        return update(dry_run=args.dry_run, limit=args.limit)
    except Exception as exc:  # never leave cron in an undefined state
        LOG.error("update failed: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
