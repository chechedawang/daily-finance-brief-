"""
业务层 - 打分排序
===============
基于多个代理信号对文章打分，降序取 Top N。
信号：跨源覆盖度、时间新鲜度、来源权威度、内容充实度、关键词密度
"""

from datetime import datetime, timedelta

from config import (
    TOP_N, SCORE_WEIGHTS, KEYWORDS, TZ_BEIJING,
    TIME_WINDOW_HOURS, REFRESH_HOUR,
)
from services.dedup import _normalize


def _get_source_weight(source_name: str, sources_config: list) -> float:
    """获取来源权威度权重"""
    for s in sources_config:
        if s["name"] == source_name:
            return s.get("weight", 0.5)
    return 0.5


def _compute_cross_source_bonus(title: str, all_titles: list,
                                similarity_func) -> float:
    """
    计算跨源覆盖度加分：统计有多少其他文章标题与之相似。
    相似度计算用外部传入的函数，避免循环导入。
    """
    from services.dedup import _tokenize

    tokens_a = _tokenize(title)
    coverage = 0
    for other_title in all_titles:
        if other_title == title:
            continue
        sim = similarity_func(tokens_a, _tokenize(other_title))
        if sim > 0.5:  # 较宽松的阈值
            coverage += 1
    return min(coverage, 5) * SCORE_WEIGHTS["cross_source"]


def _compute_freshness(time_str: str, now: datetime) -> float:
    """计算新鲜度分数：越接近 now 得分越高"""
    if not time_str:
        return 0.0
    try:
        # 尝试解析 "2026-07-04 11:30" 格式
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=TZ_BEIJING)
    except (ValueError, TypeError):
        return 0.0

    # 时间窗口内按线性衰减
    window = timedelta(hours=TIME_WINDOW_HOURS)
    age = now - dt
    if age < timedelta(0):
        return SCORE_WEIGHTS["freshness_max"]  # 未来时间按满分算
    if age > window:
        # 超过窗口衰减
        extra = age - window
        decay = max(0, 1.0 - extra.total_seconds() / (window.total_seconds() * 2))
        return SCORE_WEIGHTS["freshness_max"] * decay
    return SCORE_WEIGHTS["freshness_max"] * (1.0 - age.total_seconds() / window.total_seconds())


def _compute_content_richness(article: dict) -> float:
    """计算内容充实度：有摘要、标题较长等加分"""
    score = 0.0
    title = article.get("title", "")
    summary = article.get("summary", "")

    # 标题长度适中（15~60 字最佳）
    title_len = len(title)
    if 15 <= title_len <= 60:
        score += 0.5
    elif title_len > 60:
        score += 0.3
    else:
        score += 0.1

    # 有摘要
    if summary:
        score += 0.5

    return score * SCORE_WEIGHTS["content_richness"]


def _compute_keyword_score(title: str, summary: str) -> float:
    """计算关键词密度加分"""
    text = _normalize(title + " " + (summary or ""))
    hits = 0
    for kw in KEYWORDS:
        kw_norm = _normalize(kw)
        if kw_norm in text:
            hits += 1
    return min(hits, 5) * SCORE_WEIGHTS["keyword"]


def rank_and_select(articles: list, sources_config: list) -> list:
    """
    对文章列表打分、排序，返回 Top N。
    去重应在调用此函数前完成。
    """
    if not articles:
        return []

    from config import TZ_BEIJING
    from services.dedup import _tokenize, _cosine_similarity

    now = datetime.now(TZ_BEIJING)

    # 收集所有标题用于跨源覆盖度计算
    all_titles = [a.get("title", "") for a in articles]

    scored = []
    for article in articles:
        title = article.get("title", "")
        summary = article.get("summary", "")
        time_str = article.get("time", "")

        score = 0.0
        score += _compute_cross_source_bonus(title, all_titles, _cosine_similarity)
        score += _compute_freshness(time_str, now)
        score += SCORE_WEIGHTS["source_weight"] * _get_source_weight(article.get("source", ""), sources_config)
        score += _compute_content_richness(article)
        score += _compute_keyword_score(title, summary)

        scored.append((score, article))

    # 按得分降序，取 Top N
    scored.sort(key=lambda x: x[0], reverse=True)

    return [article for score, article in scored[:TOP_N]]
