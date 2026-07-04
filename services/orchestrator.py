"""
业务层 - 并发调度
===============
将所有源并发抓取，统一收集结果
"""

import concurrent.futures

from config import SOURCES, FETCH_TIMEOUT, MAX_WORKERS
from fetchers import fetch_one_source


def fetch_all_sources() -> dict:
    """
    并发抓取所有新闻源，超时控制 + 优雅降级。
    返回 {all_articles, sources_status}
    """
    all_articles = []
    sources_status = []

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)
    future_to_src = {}
    try:
        for src in SOURCES:
            future_to_src[executor.submit(fetch_one_source, src)] = src

        done, not_done = concurrent.futures.wait(
            future_to_src, timeout=FETCH_TIMEOUT,
            return_when=concurrent.futures.ALL_COMPLETED,
        )

        for future in done:
            result = future.result()
            sources_status.append({
                "name": result["name"],
                "count": result["count"],
                "error": result["error"],
            })
            all_articles.extend(result["articles"])

        # 超时未完成的源，取消并标记
        for future in not_done:
            future.cancel()
            src_name = future_to_src[future]["name"]
            sources_status.append({
                "name": src_name,
                "count": 0,
                "error": "请求超时",
            })

    finally:
        executor.shutdown(wait=False)

    return {
        "all_articles": all_articles,
        "sources_status": sources_status,
    }
