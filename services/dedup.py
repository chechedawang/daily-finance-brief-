"""
业务层 - 去重
============
基于标题相似度聚类，同一聚类只保留得分最高的那条。
"""

import re
from math import sqrt
from collections import defaultdict

from config import TITLE_SIMILARITY_THRESHOLD


def _normalize(text: str) -> str:
    """归一化文本：去标点、去空格、小写"""
    text = re.sub(r"[^\w一-鿿]", "", text)
    return text.lower()


def _tokenize(text: str) -> set:
    """中文按 2-gram，英文/数字保持原样"""
    text = _normalize(text)
    tokens = set()
    # 2-gram for Chinese
    for i in range(len(text) - 1):
        tokens.add(text[i:i + 2])
    return tokens


def _cosine_similarity(set_a: set, set_b: set) -> float:
    """两个 token 集合的余弦相似度"""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / (sqrt(len(set_a)) * sqrt(len(set_b)))


def deduplicate(articles: list, threshold: float = None) -> list:
    """
    对文章列表去重：标题相似度 > threshold 视为重复，
    通过贪心聚类合并，每个聚类只保留一条。
    """
    if threshold is None:
        threshold = TITLE_SIMILARITY_THRESHOLD

    if not articles:
        return []

    # 预计算每条文章的 token 集合
    token_sets = [None] * len(articles)

    # 贪心聚类：为每条文章找最相似的已有聚类
    clusters = []  # list of list of indices
    cluster_tokens = []  # 每个聚类的代表 token

    for i, article in enumerate(articles):
        if token_sets[i] is None:
            token_sets[i] = _tokenize(article.get("title", ""))
            # 同时生成一个含摘要的增强版 token，用于更准确的匹配
            summary = article.get("summary", "")
            if summary:
                token_sets[i] = token_sets[i] | _tokenize(summary[:60])

        best_cluster = -1
        best_sim = 0.0

        for j, ct in enumerate(cluster_tokens):
            sim = _cosine_similarity(token_sets[i], ct)
            if sim > best_sim:
                best_sim = sim
                best_cluster = j

        if best_sim > threshold:
            clusters[best_cluster].append(i)
        else:
            clusters.append([i])
            cluster_tokens.append(token_sets[i])

    # 每个聚类取第一条（按原始顺序，即按时间倒序）
    result = []
    for cluster in clusters:
        result.append(articles[cluster[0]])

    return result
