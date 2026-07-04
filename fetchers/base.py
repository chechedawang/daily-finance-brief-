"""
抓取层 - 基类 & 公共工具
======================
只负责「从外部拿原始数据」，不关心数据怎么处理。
"""

import re
from datetime import datetime, timezone

import requests


def safe_fetch(url: str, timeout=5, **kwargs) -> str | None:
    """HTTP GET，带超时和异常处理，返回文本。
    timeout 使用 (connect, read) 元组，避免 DNS/连接长时间卡住。"""
    from config import HEADERS

    try:
        resp = requests.get(url, headers=HEADERS, timeout=(3, timeout), **kwargs)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        print(f"[请求失败] {url[:60]}: {e}")
        return None


def safe_fetch_json(url: str, timeout: int = 8, **kwargs) -> dict | None:
    """HTTP GET，返回 JSON 对象"""
    text = safe_fetch(url, timeout, **kwargs)
    if text is None:
        return None
    try:
        import json as _json
        return _json.loads(text)
    except Exception:
        return None


def ts_to_bj(ts: int) -> str:
    """Unix 时间戳 → 北京时间字符串"""
    from config import TZ_BEIJING

    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.astimezone(TZ_BEIJING).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def clean_html(raw: str, max_len: int = 100) -> str:
    """去除 HTML 标签，截断"""
    text = re.sub(r"<[^>]+>", "", raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def parse_rss_date(entry) -> str:
    """从 feedparser entry 提取时间"""
    from config import TZ_BEIJING

    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    if ts:
        try:
            dt = datetime(*ts[:6], tzinfo=timezone.utc)
            return dt.astimezone(TZ_BEIJING).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return entry.get("published") or entry.get("updated") or ""


def make_article(title: str, link: str, summary: str, time_str: str,
                 source: str, category: str, lang: str, color: str) -> dict:
    """生成统一格式的文章字典"""
    return {
        "title": title.strip(),
        "link": link.strip(),
        "summary": summary,
        "time": time_str,
        "source": source,
        "category": category,
        "lang": lang,
        "color": color,
    }
