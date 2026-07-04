"""
全局配置
=======
所有可调参数集中在这里，改配置不碰逻辑代码。
"""

from datetime import timezone, timedelta

VERSION = "2.0.0"

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
        "weight": 0.8,          # 来源权威度权重（0~1）
    },
    {
        "name": "量子位",
        "type": "rss",
        "url": "https://www.qbitai.com/feed",
        "category": "AI科技",
        "lang": "zh",
        "color": "#f59e0b",
        "weight": 0.7,
    },
    {
        "name": "爱范儿",
        "type": "rss",
        "url": "https://www.ifanr.com/feed",
        "category": "科技产业",
        "lang": "zh",
        "color": "#ef4444",
        "weight": 0.7,
    },
    {
        "name": "动点科技",
        "type": "rss",
        "url": "https://technode.com/feed/",
        "category": "科技出海",
        "lang": "zh",
        "color": "#8b5cf6",
        "weight": 0.6,
    },
    {
        "name": "少数派",
        "type": "rss",
        "url": "https://sspai.com/feed",
        "category": "数字生活",
        "lang": "zh",
        "color": "#06b6d4",
        "weight": 0.5,
    },
    # ========== RSS 源（全球科技） ==========
    {
        "name": "TechCrunch",
        "type": "rss",
        "url": "https://techcrunch.com/feed/",
        "category": "全球科技",
        "lang": "en",
        "color": "#3b82f6",
        "weight": 0.9,
    },
    {
        "name": "CNBC Tech",
        "type": "rss",
        "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
        "category": "全球市场",
        "lang": "en",
        "color": "#6366f1",
        "weight": 0.9,
    },
    {
        "name": "The Verge",
        "type": "rss",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "科技产业",
        "lang": "en",
        "color": "#ec4899",
        "weight": 0.85,
    },
    # ========== API 源（A股财经快讯） ==========
    {
        "name": "华尔街见闻",
        "type": "api",
        "api_type": "wallstreetcn",
        "category": "财经快讯",
        "lang": "zh",
        "color": "#dc2626",
        "weight": 0.9,
    },
]

# ============================================================
# 缓存配置
# ============================================================
CACHE_SECONDS = 600  # 常规缓存 10 分钟

# ============================================================
# 抓取配置
# ============================================================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}
FETCH_TIMEOUT = 20          # 整体抓取超时（秒）
MAX_WORKERS = 10            # 并发抓取线程数
RSS_ENTRY_LIMIT = 15        # RSS 源每源取几条

# ============================================================
# 排重 + 排名配置
# ============================================================
TOP_N = 20                       # 最终取 Top N 条
TITLE_SIMILARITY_THRESHOLD = 0.6 # 标题相似度阈值（>此值视为重复）

# 打分权重（总和不必为 1，是加分项，各维度独立计算）
SCORE_WEIGHTS = {
    "cross_source":   3.0,   # 跨源覆盖度加分（每多一个源报道 +N 分）
    "freshness_max":  2.0,   # 新鲜度满分（越接近当前时间越高）
    "source_weight":  0.5,   # 来源权威度系数（乘以 source.weight）
    "content_richness": 0.5, # 内容充实度（有摘要加分）
    "keyword":        0.3,   # 关键词密度加分（每命中一个关键词 +N 分）
}

# 热度关键词（含公司名/股票代码/政策词）
KEYWORDS = [
    # 中国科技公司
    "华为", "腾讯", "阿里", "百度", "字节", "美团", "拼多多", "京东", "网易",
    "小米", "比亚迪", "宁德时代", "中芯国际", "商汤", "科大讯飞",
    # 国际科技公司
    "Apple", "苹果", "Google", "谷歌", "Microsoft", "微软", "NVIDIA", "英伟达",
    "Tesla", "特斯拉", "Meta", "OpenAI", "Amazon", "亚马逊",
    # 热点赛道
    "AI", "人工智能", "大模型", "GPT", "ChatGPT", "芯片", "半导体",
    "自动驾驶", "机器人", "新能源", "光伏", "锂电",
    # 政策/宏观
    "央行", "降息", "加息", "IPO", "上市", "融资", "收购", "合并",
    "A股", "港股", "美股", "上证", "深证", "纳斯达克",
]

# ============================================================
# 时间窗口配置（每天 12:00 刷新，取前一天 12:00 ~ 当天 12:00）
# ============================================================
REFRESH_HOUR = 12  # 每天刷新时间（北京时间）
TIME_WINDOW_HOURS = 24  # 时间窗口跨度（小时）

TZ_BEIJING = timezone(timedelta(hours=8))
