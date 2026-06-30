"""
每日财经快报 - 后端服务
========================
功能：抓取 RSS + JSON API 多个新闻源，聚合后提供给前端展示。
技术：Flask + feedparser + requests + 内存缓存
运行：python app.py

新闻源配置说明：
  - 每个源包含 name/type/category/lang/color
  - type="rss"  → 需要 url 字段（RSS 地址）
  - type="api"  → 需要 api_type 字段（指定抓取函数）
  - 增删改源只需编辑下面的 SOURCES 列表
"""

import re
import time
import concurrent.futures
from datetime import datetime, timezone, timedelta

import requests
import feedparser
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# ============================================================
# 新闻源配置
# ============================================================
# type 字段说明：
#   "rss" → 标准 RSS 源，用 feedparser 解析
#   "api" → JSON API 源，用 api_type 指定的函数抓取
#
# 扩充方法：照猫画虎加一个字典即可，格式对齐

SOURCES = [
    # ========== RSS 源（科技产业） ==========
    {
        "name": "36氪",
        "type": "rss",
        "url": "https://36kr.com/feed",
        "category": "科技产业",
        "lang": "zh",
        "color": "#10b981",
    },
    {
        "name": "量子位",
        "type": "rss",
        "url": "https://www.qbitai.com/feed",
        "category": "AI科技",
        "lang": "zh",
        "color": "#f59e0b",
    },
    {
        "name": "爱范儿",
        "type": "rss",
        "url": "https://www.ifanr.com/feed",
        "category": "科技产业",
        "lang": "zh",
        "color": "#ef4444",
    },
    {
        "name": "动点科技",
        "type": "rss",
        "url": "https://technode.com/feed/",
        "category": "科技出海",
        "lang": "zh",
        "color": "#8b5cf6",
    },
    {
        "name": "少数派",
        "type": "rss",
        "url": "https://sspai.com/feed",
        "category": "数字生活",
        "lang": "zh",
        "color": "#06b6d4",
    },
    # ========== RSS 源（全球科技） ==========
    {
        "name": "TechCrunch",
        "type": "rss",
        "url": "https://techcrunch.com/feed/",
        "category": "全球科技",
        "lang": "en",
        "color": "#3b82f6",
    },
    {
        "name": "CNBC Tech",
        "type": "rss",
        "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
        "category": "全球市场",
        "lang": "en",
        "color": "#6366f1",
    },
    {
        "name": "The Verge",
        "type": "rss",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "科技产业",
        "lang": "en",
        "color": "#ec4899",
    },
    # ========== API 源（A股财经快讯） ==========
    {
        "name": "华尔街见闻",
        "type": "api",
        "api_type": "wallstreetcn",
        "category": "财经快讯",
        "lang": "zh",
        "color": "#dc2626",
    },
]

# ============================================================
# 缓存 & 全局配置
# ============================================================
_cache = {"data": None, "timestamp": 0}
CACHE_SECONDS = 600  # 缓存 10 分钟

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

TZ_BEIJING = timezone(timedelta(hours=8))


# ============================================================
# 工具函数
# ============================================================
def safe_fetch(url: str, timeout: int = 6, **kwargs) -> str | None:
    """HTTP GET，带超时和异常处理，返回文本"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, **kwargs)
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
        return requests.json() if hasattr(requests, 'json') else __import__('json').loads(text)
    except Exception:
        import json as _json
        return _json.loads(text)


def ts_to_bj(ts: int) -> str:
    """Unix 时间戳 → 北京时间字符串"""
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
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    if ts:
        try:
            dt = datetime(*ts[:6], tzinfo=timezone.utc)
            return dt.astimezone(TZ_BEIJING).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
    return entry.get("published") or entry.get("updated") or ""


def make_article(title, link, summary, time_str, source, category, lang, color):
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


# ============================================================
# 各 API 源的抓取函数
# ============================================================

def fetch_wallstreetcn(source: dict) -> list:
    """
    华尔街见闻 - 快讯 API
    端点：apiv1/content/lives（全球频道，覆盖 A 股/科技/宏观）
    返回最新的实时快讯，非常适合 A 股投资者
    """
    articles = []
    url = (
        "https://api-one.wallstcn.com/apiv1/content/lives"
        "?channel=global&limit=20&first_page=true"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
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
                title = title.replace("…", "")  # 标题不去掉省略号不美观

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


# API 类型 → 抓取函数的映射表（新增 API 源时在这里注册）
API_FETCHERS = {
    "wallstreetcn": fetch_wallstreetcn,
}


# ============================================================
# 统一抓取入口（RSS + API 都走这里）
# ============================================================
def fetch_one_source(source: dict) -> dict:
    """
    抓取单个新闻源，自动判断类型并调用对应逻辑。
    返回 {name, count, articles, error}
    """
    name = source["name"]
    articles = []
    error = None

    try:
        src_type = source.get("type", "rss")

        if src_type == "api":
            # ---- API 源 ----
            api_type = source.get("api_type", "")
            fetcher = API_FETCHERS.get(api_type)
            if fetcher is None:
                error = f"未知 api_type: {api_type}"
            else:
                articles = fetcher(source)

        else:
            # ---- RSS 源 ----
            url = source["url"]
            content = safe_fetch(url)
            if content is None:
                error = "无法获取内容"
            else:
                feed = feedparser.parse(content)
                if feed.bozo and not feed.entries:
                    error = f"解析异常: {feed.bozo_exception}"
                else:
                    for entry in feed.entries[:15]:
                        title = (entry.get("title") or "").strip()
                        link = (entry.get("link") or "").strip()
                        if not title or not link:
                            continue
                        articles.append(make_article(
                            title=title,
                            link=link,
                            summary=clean_html(entry.get("summary", "")),
                            time_str=parse_rss_date(entry),
                            source=name,
                            category=source["category"],
                            lang=source["lang"],
                            color=source["color"],
                        ))
    except Exception as e:
        error = str(e)

    return {
        "name": name,
        "count": len(articles),
        "articles": articles,
        "error": error,
    }


# ============================================================
# Flask 路由
# ============================================================
@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/api/news")
def get_news():
    """聚合新闻 API（带缓存）"""
    global _cache
    now = time.time()

    if _cache["data"] is not None and (now - _cache["timestamp"]) < CACHE_SECONDS:
        return jsonify(_cache["data"])

    all_articles = []
    sources_status = []

    # 并发抓取所有源
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_one_source, src): src for src in SOURCES}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            sources_status.append({
                "name": result["name"],
                "count": result["count"],
                "error": result["error"],
            })
            all_articles.extend(result["articles"])

    # 按时间排序
    all_articles.sort(key=lambda a: a.get("time", ""), reverse=True)

    data = {
        "date": datetime.now(TZ_BEIJING).strftime("%Y年%m月%d日 %A"),
        "total": len(all_articles),
        "sources": sources_status,
        "articles": all_articles,
        "cached_at": datetime.now(TZ_BEIJING).strftime("%H:%M:%S"),
    }

    _cache["data"] = data
    _cache["timestamp"] = now
    return jsonify(data)


@app.route("/api/refresh")
def refresh_news():
    """强制刷新（清除缓存）"""
    global _cache
    _cache["data"] = None
    _cache["timestamp"] = 0
    return get_news()


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rss_count = sum(1 for s in SOURCES if s.get("type", "rss") == "rss")
    api_count = sum(1 for s in SOURCES if s.get("type") == "api")

    print("=" * 55)
    print("[每日财经快报] 服务启动中...")
    print(f"新闻源: {len(SOURCES)} 个 ({rss_count} RSS + {api_count} API)")
    for s in SOURCES:
        tag = "[API]" if s.get("type") == "api" else "[RSS]"
        print(f"  {tag} {s['name']} - {s['category']}")
    print(f"本地访问: http://localhost:5000")
    print(f"手机访问: http://<你的电脑IP>:5000")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)
