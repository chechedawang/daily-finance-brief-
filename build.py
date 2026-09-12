"""
静态站点构建入口
================
抓取新闻 → 生成静态站点到 dist/，交给 CDN 托管（无休眠、无冷启动）。

用法：
    python build.py              # 抓取 + 生成 dist/
    python build.py --serve      # 生成后启动本地预览 http://localhost:8000
    python build.py --no-fetch   # 复用上次数据重新渲染（调试模板用，不联网）
    python build.py --force      # 跳过空数据保护，强制发布

设计要点：
- 业务逻辑全部复用 services/，本文件只负责「驱动 + 落盘」
- 数据内联进 index.html，首屏零请求（这是秒开的关键）
- 空数据保护：抓取异常时拒绝发布，不覆盖上一版好数据
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "templates" / "index.html"
STATIC_DIR = ROOT / "static"
DIST = ROOT / "dist"

# 模板中的数据注入点，构建时替换为内联 <script>
DATA_PLACEHOLDER = "<!--__NEWS_DATA__-->"

# 有效文章少于此数视为抓取失败，拒绝发布
MIN_ARTICLES = 5


# ============================================================
# 数据获取
# ============================================================
def fetch_data() -> dict:
    """跑完整流水线，抓取并组装前端数据"""
    from services.pipeline import build_news_data
    return build_news_data()


def load_previous_data() -> dict:
    """读取上一版生成的数据（--no-fetch 用）"""
    path = DIST / "data" / "news.json"
    if not path.exists():
        raise SystemExit(f"[错误] 找不到 {path}\n       请先正常跑一次 python build.py")
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================
# 发布前体检
# ============================================================
def check_health(data: dict) -> bool:
    """
    抓取异常时返回 False，拒绝覆盖上一版站点。
    静态化的代价是坏数据会被固化下来，所以必须在这里堵住。
    """
    total = data.get("total", 0)
    sources = data.get("sources", [])
    ok = [s for s in sources if not s.get("error")]
    failed = [s for s in sources if s.get("error")]

    print(f"\n[体检] 有效文章 {total} 条 | 来源 {len(ok)}/{len(sources)} 正常")
    for s in failed:
        print(f"       ✗ {s['name']}: {s['error']}")

    if not ok:
        print("\n[拒绝发布] 所有来源均抓取失败，已保留上一版站点。")
        return False

    if total < MIN_ARTICLES:
        print(f"\n[拒绝发布] 有效文章仅 {total} 条（下限 {MIN_ARTICLES} 条），疑似抓取失败。")
        print("           已保留上一版站点，本次不覆盖。确认无误可加 --force 强制发布。")
        return False

    return True


# ============================================================
# 生成站点
# ============================================================
def _inline_script(data: dict) -> str:
    """
    渲染内联数据 <script>。
    把 '</' 转义为 '<\\/'，防止 JSON 内容里的 </script> 提前闭合脚本标签。
    """
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    return f"<script>window.__NEWS_DATA__={payload};</script>"


def write_site(data: dict):
    """把页面和数据落盘到 dist/"""
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # 1) index.html —— 注入内联数据
    html = TEMPLATE.read_text(encoding="utf-8")
    if DATA_PLACEHOLDER not in html:
        raise SystemExit(f"[错误] 模板 {TEMPLATE} 缺少数据占位符 {DATA_PLACEHOLDER}")
    (DIST / "index.html").write_text(
        html.replace(DATA_PLACEHOLDER, _inline_script(data)), encoding="utf-8"
    )

    # 2) 静态资源
    shutil.copytree(STATIC_DIR, DIST / "static")

    # 3) 独立 JSON —— 便于调试，也供其他程序消费
    (DIST / "data").mkdir()
    (DIST / "data" / "news.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    size_kb = (DIST / "index.html").stat().st_size / 1024
    print(f"\n[生成] dist/index.html  ({size_kb:.0f} KB，数据已内联)")
    print( "[生成] dist/data/news.json")
    print( "[生成] dist/static/")


# ============================================================
# 本地预览
# ============================================================
def serve(port: int):
    """启动本地预览服务器（Python 内置 http.server，零额外依赖）"""
    import functools
    import http.server
    import socketserver

    socketserver.TCPServer.allow_reuse_address = True
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n[预览] http://localhost:{port}   (Ctrl+C 停止)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[预览] 已停止")


# ============================================================
# 入口
# ============================================================
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="每日财经快报 - 静态站点构建")
    parser.add_argument("--serve", action="store_true", help="生成后启动本地预览服务器")
    parser.add_argument("--port", type=int, default=8000, help="预览端口（默认 8000）")
    parser.add_argument("--no-fetch", action="store_true", help="复用上次数据重新渲染，不联网")
    parser.add_argument("--force", action="store_true", help="跳过空数据保护，强制发布")
    args = parser.parse_args()

    if args.no_fetch:
        print("[构建] --no-fetch：复用上次数据")
        data = load_previous_data()
    else:
        print("[构建] 抓取新闻源...")
        data = fetch_data()

    if not args.force and not check_health(data):
        raise SystemExit(1)

    write_site(data)

    if args.serve:
        serve(args.port)


if __name__ == "__main__":
    main()
