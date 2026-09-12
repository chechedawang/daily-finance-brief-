"""
抓取层 - RSS 源
=============
feedparser 统一抓取 RSS/Atom 源
"""

import feedparser

from config import RSS_ENTRY_LIMIT
from .base import safe_fetch, clean_html, parse_rss_date, make_article


def fetch_rss(source: dict) -> list:
    """
    抓取单个 RSS 源，返回文章列表。

    失败时抛异常而非静默返回空列表 —— 由 fetch_one_source 捕获并记录，
    这样上层才能区分「这个源挂了」和「这个源今天没新闻」。
    """
    articles = []
    url = source["url"]
    content = safe_fetch(url)

    if content is None:
        raise RuntimeError("抓取失败（网络错误或非 200 响应）")

    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise RuntimeError("RSS 解析失败或订阅源为空")

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
