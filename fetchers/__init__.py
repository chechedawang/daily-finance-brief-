"""
抓取层 - 注册表 & 统一入口
=========================
API_FETCHERS：api_type → 抓取函数的映射表
fetch_one_source：自动判断类型，调用对应抓取函数
"""

from .rss import fetch_rss
from .wallstreetcn import fetch_wallstreetcn

# API 类型 → 抓取函数的映射表（新增 API 源时在这里注册）
API_FETCHERS = {
    "wallstreetcn": fetch_wallstreetcn,
}


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
            api_type = source.get("api_type", "")
            fetcher = API_FETCHERS.get(api_type)
            if fetcher is None:
                error = f"未知 api_type: {api_type}"
            else:
                articles = fetcher(source)
        else:
            articles = fetch_rss(source)

    except Exception as e:
        error = str(e)

    return {
        "name": name,
        "count": len(articles),
        "articles": articles,
        "error": error,
    }
