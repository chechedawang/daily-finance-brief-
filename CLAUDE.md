# CLAUDE.md — 每日财经快报 (Daily Finance Brief)

面向 A 股科技投资者的每日财经新闻聚合器，移动端优先。从 9 个新闻源（RSS + API）抓取，经去重+打分后展示 Top 20。每天 12:00 由 GitHub Actions 自动构建并发布。

- 部署：Render Static Site（静态托管，无休眠）| GitHub：`chechedawang/daily-finance-brief-`
- 站点产物在 `gh-pages` 分支，主分支只放源码
- 用户：A 股投资者，关注科技板块，中英文新闻混读

## 工作规则

- **Git 提交**：先向用户汇报改动，确认后再 `git commit` + `git push`。不自行提交。
- **部署**：推送主分支后，还需在 GitHub Actions 页面手动触发一次（或等次日 12:00 定时任务），才会重新生成站点。

## 技术栈

Python 3.12 | feedparser | requests (connect,read 超时元组) | ThreadPoolExecutor | 标题 2-gram 余弦相似度去重 | 多维代理信号打分 | **纯静态输出**（无 Web 框架、无常驻进程）

## 项目结构

```
build.py            — 构建入口：抓取 → 生成 dist/（唯一入口）
config.py           — SOURCES、打分权重、时间窗口
services/
  pipeline.py       — 完整流水线，唯一数据生产入口（无副作用）
  orchestrator.py   — 并发调度
  dedup.py          — 去重
  ranker.py         — 打分排序
  time_filter.py    — 时间窗口过滤
fetchers/
  __init__.py       — 注册表：api_type → 抓取函数
  base.py           — 公共工具（safe_fetch / make_article 等）
  rss.py            — RSS 抓取
  wallstreetcn.py   — 华尔街见闻 API
templates/index.html — 页面模板（含数据占位符）
static/{style.css,app.js} — 前端资源
dist/               — 构建产物（已 gitignore）
```

## 核心架构

**数据流（构建时一次性完成，非请求时）**：

```
GitHub Actions (cron 12:00)
  → python build.py
      → services/pipeline.py  (抓取 → 过滤 → 去重 → 打分 → 组装)
      → 空数据体检（不合格则拒绝发布，保留上一版）
      → 生成 dist/index.html（数据内联）+ dist/data/news.json
  → 推送到 gh-pages 分支
  → Render Static Site 监听该分支，自动发布
```

**关键设计**：

1. **`services/pipeline.py` 是唯一的数据生产入口**。所有驱动方式（构建、将来的 API）都调 `build_news_data()`，业务逻辑不复制。
2. **数据内联进 `index.html`**（`window.__NEWS_DATA__`），首屏零网络请求——这是页面秒开的关键。
3. **搜索/筛选全在前端内存中完成**，静态站点不产生任何后端请求。
4. **空数据保护**：抓取异常时 build.py 以非 0 退出，中断 CI，上一版站点保持不变。

新闻源配置（`config.py` → `SOURCES`）：RSS 源 `{type:"rss", url, weight, ...}`；API 源 `{type:"api", api_type, ...}`，需在 `fetchers/__init__.py` 注册。

打分 5 维：跨源覆盖(3.0×N) | 新鲜度(2.0, 24h线性衰减) | 来源权威(0.5) | 内容充实度(0.5) | 关键词命中(0.3×N)

## 关键踩坑

### 1. 抓取失败必须抛异常 ⚠️
`fetch_rss` / `fetch_wallstreetcn` **失败时要 raise**，不能静默 `return []`。
静默返回会让 `fetch_one_source` 把 `error` 记成 `None`，导致：空数据保护失效、前端显示"9/9 来源正常"却在骗人。
（此坑已修：2026-09-12）

### 2. ThreadPoolExecutor 陷阱
**禁止** `with ThreadPoolExecutor()`，`with` 退出时 `shutdown(wait=True)` 无视 timeout。手动管理：
```python
executor = ThreadPoolExecutor(max_workers=10)
try: ...
finally: executor.shutdown(wait=False)
```

### 3. 内联 JSON 要转义 `</`
标题里若含 `</script>` 会提前闭合脚本标签。`build.py::_inline_script` 已把 `</` 转成 `<\/`。
改模板时**不要删掉 `<!--__NEWS_DATA__-->` 占位符**，否则构建报错。

### 4. 部分新闻源偶发不稳定（正常现象）
动点科技（403）、爱范儿（超时）、CNBC Tech（超时）、量子位（DNS）都会时不时失败。
**这是网络波动，不是源坏了**——重跑一次通常就恢复，不用管。

正常产出 20 条，`7/9` 或 `8/9` 来源可用。前端状态栏会如实显示失败源。
只要有效文章 ≥ 5 条，空数据保护就会放行。

### 5. Render 静态站点：Build Command 必须留空 ⚠️
Render 会按**主分支**的语言自动猜构建命令（Python 项目 → `pip install -r requirements.txt`），
但实际部署的是 `gh-pages` 分支，里面只有 `index.html` / `static/` / `data/`，**没有 requirements.txt**，
于是报 `ERROR: Could not open requirements file`，部署失败。

**修复**：Settings → Build Command **清空**（若不允许留空，填 `echo "prebuilt by CI"`）。

成功的日志应该很短，没有 `Installing Python` / `Poetry` 之类的步骤：
```
==> Checking out commit xxx in branch gh-pages
==> Empty build command; skipping build
```
约 6 秒完成。**新建同类站点时第一件事就是检查这个字段有没有被自动填上。**

### 6. 新闻源选型（2026-09-12 实测）

**当前 9 个源**：钛媒体、量子位、爱范儿、动点科技、少数派、TechCrunch、CNBC Tech、The Verge、华尔街见闻。
**已移除**：36氪（RSS 返回反爬 HTML 页，2026-09 由钛媒体顶替）。

**备选源实测结果**——判定标准是「能通过时间窗口的条数」，不是 HTTP 200：

| 源 | 窗口内条数 | 点评 |
|---|---|---|
| Solidot | 15 | 时间分布最好，但偏科普，不适合财经 |
| **钛媒体** | **9** | **✅ 已采用**，科技+财经，最贴近 36氪 的定位 |
| InfoQ中文 | 9 | 偏开发技术 |
| 开源中国 | 7 | 偏开发技术 |
| IT之家 | 0 | ⚠️ 见下方陷阱 |
| 界面新闻 | 0 | ⚠️ 同 IT之家 |
| 极客公园 | 0 | **源本身不新鲜**，最新一条滞后一整天 |
| 新浪科技 | 0 | 源停留在 **2018 年**，早已死亡 |
| 机器之心 / cnBeta / 虎嗅 | — | 返回反爬 HTML 页 |
| 雷峰网 | — | 请求失败 |

**两条关键教训**：

1. **HTTP 200 ≠ 可用**。36氪 返回 200 但内容是反爬 HTML 页；新浪科技返回 200 但内容是 2018 年的。
   验证一个新源，必须实际解析出条目、**且能通过时间窗口**，两个条件都满足才算数。

2. **`RSS_ENTRY_LIMIT=15` 对高产源偏小**。IT之家 的 feed 有 60 条，只取最新 15 条 →
   仅覆盖约 1 小时，全部落在「[昨天12:00, 今天12:00]」窗口之外，一条都用不上。
   若将来要引入高产源（IT之家、界面新闻这类），需先调大 `config.py` 里的这个值。

### 6. Windows 控制台编码
`build.py` 已用 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` 处理。
自己写临时脚本打印中文/符号时也要加，否则 GBK 报 `UnicodeEncodeError`。

## 本地开发 & 部署

```bash
pip install -r requirements.txt
python build.py --serve        # 抓取 → 生成 dist/ → http://localhost:8000
```

`build.py` 参数：

| 参数 | 作用 |
|---|---|
| `--serve` | 生成后启动本地预览（内置 http.server，零依赖） |
| `--port N` | 预览端口，默认 8000 |
| `--no-fetch` | 复用上次数据重新渲染，不联网（调模板时用，很快） |
| `--force` | 跳过空数据保护，强制发布 |

调试模板改动的快速循环：`python build.py --no-fetch --serve`（秒级，不抓取）。

### 首次部署到 Render（一次性配置）

1. 先在 GitHub Actions 页面手动跑一次工作流，生成 `gh-pages` 分支
2. Render 面板 → **New → Static Site** → 连接仓库
3. **Branch** 选 `gh-pages`
4. **Build Command** 留空（产物已由 CI 构建好）
5. **Publish Directory** 填 `.`
6. 确认自动部署（Auto-Deploy）已开启

之后每天 12:00 自动更新。Git 部署走 SSH Key 认证，push 无需密码。

### 与 V2（Render 动态服务）的区别

V2 是常驻 Flask 服务，免费层 15 分钟无请求就休眠、冷启动约 60 秒，首访很慢。
V3 改为构建静态产物 + CDN 托管，**无休眠、无冷启动**；代价是失去「网页上点按钮实时刷新」的能力，手动兜底改为在 GitHub Actions 页面点 *Run workflow*。
