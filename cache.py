"""
缓存层
=====
当前为内存缓存，后续可替换为 Redis 等外部缓存。
"""

import time
from datetime import datetime

from config import TZ_BEIJING


class Cache:
    """简单的内存缓存，支持按日期标记的过期策略"""

    def __init__(self):
        self._data = None
        self._timestamp = 0
        self._batch_date = None  # 缓存数据所属的批次日期（如 "2026-07-04"）

    def get(self) -> dict | None:
        """获取缓存数据，如果存在则返回"""
        if self._data is not None:
            return self._data
        return None

    def set(self, data: dict, batch_date: str = None):
        """设置缓存数据"""
        self._data = data
        self._timestamp = time.time()
        self._batch_date = batch_date or datetime.now(TZ_BEIJING).strftime("%Y-%m-%d")

    def clear(self):
        """清除缓存"""
        self._data = None
        self._timestamp = 0
        self._batch_date = None

    @property
    def age_seconds(self) -> float:
        """缓存已存在多少秒"""
        if self._timestamp == 0:
            return float("inf")
        return time.time() - self._timestamp

    @property
    def batch_date(self) -> str | None:
        """缓存数据所属的批次日期"""
        return self._batch_date


# 全局缓存实例
cache = Cache()
