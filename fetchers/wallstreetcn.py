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
    """抓取华尔街见闻快讯"""
    articles = []
    url = (
        "https://api-one.wallstcn.com/apiv1/content/lives"
        "?channel=global&limit=20&first_page=true"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=(3, 5))
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("items", [])
        for item in items:
            title = item.get("title") or ""
            content = item.get("content_text") or ""
            uri = item.get("uri") or ""
            ts = item.get("display_time")
            time_str = ts_to_bj(int(ts)) if ts else ""

            # 快讯可能没有单独标题，用内容前 40 字做标题
            if not title and content:
                title = clean_html(content, max_len=40)
                title = title.replace("…", "")

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
    except Exception as e:
        print(f"[华尔街见闻] 抓取失败: {e}")

    return articles
