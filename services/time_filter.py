"""
业务层 - 时间窗口过滤
====================
只保留时间落在 [前一天 12:00, 当天 12:00] 窗口内的文章。
"""

from datetime import datetime, timedelta

from config import TZ_BEIJING, REFRESH_HOUR


def get_time_window() -> tuple[datetime, datetime]:
    """
    计算当前时间窗口：[前一天 REFRESH_HOUR:00, 当天 REFRESH_HOUR:00]
    返回 (window_start, window_end) — 均为带时区的 datetime
    """
    now = datetime.now(TZ_BEIJING)
    today_noon = now.replace(hour=REFRESH_HOUR, minute=0, second=0, microsecond=0)
    yesterday_noon = today_noon - timedelta(days=1)

    # 如果当前时间还没到今天的 12:00，窗口仍以前一天 12:00 为终点
    if now < today_noon:
        return yesterday_noon - timedelta(days=1), yesterday_noon

    return yesterday_noon, today_noon


def parse_article_time(time_str: str) -> datetime | None:
    """解析文章时间字符串为带时区的 datetime"""
    if not time_str:
        return None
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=TZ_BEIJING)
    except (ValueError, TypeError):
        pass

    # 尝试其他格式
    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%a, %d %b %Y %H:%M:%S %z"]:
        try:
            dt = datetime.strptime(time_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ_BEIJING)
            return dt
        except (ValueError, TypeError):
            continue

    return None


def filter_by_time_window(articles: list) -> list:
    """
    只保留时间落在当前窗口内的文章。
    对于无法解析时间的文章，保留（不误杀）。
    """
    if not articles:
        return []

    window_start, window_end = get_time_window()
    filtered = []

    for article in articles:
        time_str = article.get("time", "")
        dt = parse_article_time(time_str)
        if dt is None:
            # 无法解析时间的保留
            filtered.append(article)
        elif window_start <= dt < window_end:
            filtered.append(article)

    return filtered
