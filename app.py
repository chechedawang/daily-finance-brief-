"""
每日财经快报 - 后端服务 V2
=========================
Flask 路由胶水层（越薄越好）。
- fetchers/   → 抓取原始数据
- services/   → 去重 + 打分 + 排序
- cache.py    → 缓存
- config.py   → 全局配置
"""

from datetime import datetime

from flask import Flask, jsonify, render_template

from config import VERSION, SOURCES, TZ_BEIJING
from cache import cache
from services import fetch_all_sources, deduplicate, rank_and_select, filter_by_time_window

app = Flask(__name__)


# ============================================================
# Flask 路由
# ============================================================
@app.route("/")
def index():
    """首页"""
    return render_template("index.html")


@app.route("/api/news")
def get_news():
    """聚合新闻 API（经过去重 + 打分 + Top N + 缓存）"""
    try:
        # 先查缓存
        cached = cache.get()
        if cached is not None:
            return jsonify(cached)

        # 抓取所有源
        result = fetch_all_sources()
        all_articles = result["all_articles"]
        sources_status = result["sources_status"]

        # 时间窗口过滤（前一天 12:00 ~ 当天 12:00）
        in_window = filter_by_time_window(all_articles)

        # 去重
        deduped = deduplicate(in_window)

        # 打分 + 选 Top N
        top_articles = rank_and_select(deduped, SOURCES)

        data = {
            "date": datetime.now(TZ_BEIJING).strftime("%Y年%m月%d日 %A"),
            "total": len(top_articles),
            "sources": sources_status,
            "articles": top_articles,
            "cached_at": datetime.now(TZ_BEIJING).strftime("%H:%M:%S"),
        }

        cache.set(data)
        return jsonify(data)

    except Exception as e:
        import traceback
        err_data = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc().split("\n")[-6:],
        }
        return app.response_class(
            response=__import__("json").dumps(err_data, ensure_ascii=False),
            status=500, mimetype="application/json"
        )


@app.route("/api/refresh")
def refresh_news():
    """强制刷新（清除缓存并重新抓取）"""
    cache.clear()
    return get_news()


@app.route("/api/version")
def api_version():
    """版本检查：确认 Render 上跑的是哪个版本"""
    return jsonify({"version": VERSION, "sources": len(SOURCES)})


@app.route("/api/health")
def api_health():
    """健康检查：确认服务正常运行"""
    return jsonify({"status": "ok"})


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rss_count = sum(1 for s in SOURCES if s.get("type", "rss") == "rss")
    api_count = sum(1 for s in SOURCES if s.get("type") == "api")

    print("=" * 55)
    print("[每日财经快报 V2] 服务启动中...")
    print(f"新闻源: {len(SOURCES)} 个 ({rss_count} RSS + {api_count} API)")
    for s in SOURCES:
        tag = "[API]" if s.get("type") == "api" else "[RSS]"
        print(f"  {tag} {s['name']} - {s['category']}")
    print(f"本地访问: http://localhost:5000")
    print(f"手机访问: http://<你的电脑IP>:5000")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)
