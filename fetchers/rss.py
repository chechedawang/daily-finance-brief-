"""
抓取层 - RSS 源
=============
feedparser 统一抓取 RSS/Atom 源
"""

import feedparser

from config import RSS_ENTRY_LIMIT
from .base import safe_fetch, clean_html, parse_rss_date, make_article


def fetch_rss(source: dict) -> list:
    """抓取单个 RSS 源，返回文章列表"""
    articles = []
    url = source["url"]
    content = safe_fetch(url)

    if content is None:
        return articles

    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        return articles

    for entry in feed.entries[:RSS_ENTRY_LIMIT]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        articles.append(make_article(
            title=title,
            link=link,
            summary=clean_html(entry.get("summary", "")),
            time_str=parse_rss_date(entry),
            source=source["name"],
            category=source["category"],
            lang=source["lang"],
            color=source["color"],
        ))

    return articles
