"""
抓取层 - 华尔街见闻 API
=====================
端点：apiv1/content/lives（全球频道，覆盖 A 股/科技/宏观）
返回最新的实时快讯
"""

import requests

from config import HEADERS
from .base import ts_to_bj, clean_html, make_article


def fetch_wallstreetcn(source: dict) -> list:
    """
    抓取华尔街见闻快讯。

    失败时抛异常而非静默返回空列表，由 fetch_one_source 捕获并记录。
    """
    articles = []
    url = (
        "https://api-one.wallstcn.com/apiv1/content/lives"
        "?channel=global&limit=20&first_page=true"
    )

    resp = requests.get(url, headers=HEADERS, timeout=(3, 5))
    resp.raise_for_status()
    items = resp.json().get("data", {}).get("items", [])

    for item in items:
        title = item.get("title") or ""
        content = item.get("content_text") or ""
        uri = item.get("uri") or ""
        ts = item.get("display_time")

        try:
            time_str = ts_to_bj(int(ts)) if ts else ""
        except (TypeError, ValueError):
            time_str = ""

        # 快讯可能没有单独标题，用内容前 40 字做标题
        if not title and content:
            title = clean_html(content, max_len=40).replace("…", "")

        if not title or not uri:
            continue

        articles.append(make_article(
            title=title,
            link=uri,
            summary=clean_html(content, max_len=100),
            time_str=time_str,
            source=source["name"],
            category=source["category"],
            lang=source["lang"],
            color=source["color"],
        ))

    return articles
