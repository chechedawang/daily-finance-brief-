"""
业务层 - 完整流水线
==================
把「并发抓取 → 时间窗口过滤 → 去重 → 打分排序 → 组装」串成一个纯函数。

这是唯一的数据生产入口：所有驱动方式（build.py 静态构建、未来的 API 等）
都调用它，避免业务逻辑被复制成多份。
"""

from datetime import datetime

from config import SOURCES, TZ_BEIJING, VERSION

from .dedup import deduplicate
from .orchestrator import fetch_all_sources
from .ranker import rank_and_select
from .time_filter import filter_by_time_window


def build_news_data() -> dict:
    """
    执行完整流水线，返回前端直接可用的数据字典。

    无副作用（不写文件、不碰全局状态），可安全重复调用。

    返回结构：
        {
            "version":      str,    # 代码版本
            "date":         str,    # 展示用日期，如 "2026年09月12日 Saturday"
            "total":        int,    # 最终条数
            "sources":      list,   # 各源抓取状态 [{name, count, error}]
            "articles":     list,   # Top N 文章
            "generated_at": str,    # 生成时间（北京时间）
        }
    """
    result = fetch_all_sources()

    # 时间窗口过滤（前一天 12:00 ~ 当天 12:00）
    in_window = filter_by_time_window(result["all_articles"])

    # 标题相似度去重
    deduped = deduplicate(in_window)

    # 多维打分 + 取 Top N
    top_articles = rank_and_select(deduped, SOURCES)

    now = datetime.now(TZ_BEIJING)

    return {
        "version": VERSION,
        "date": now.strftime("%Y年%m月%d日 %A"),
        "total": len(top_articles),
        "sources": result["sources_status"],
        "articles": top_articles,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
    }
