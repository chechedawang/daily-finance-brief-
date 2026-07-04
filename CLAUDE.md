# CLAUDE.md — 每日财经快报 (Daily Finance Brief)

## 项目概述

面向 A 股科技投资者的每日财经新闻聚合器，移动端优先的 Web 应用。从 9 个新闻源（RSS + API）抓取内容，统一展示。

- **部署地址**：https://daily-finance-brief.onrender.com
- **GitHub**：`chechedawang/daily-finance-brief-`（SSH: `git@github.com:chechedawang/daily-finance-brief-.git`）
- **用户**：A 股投资者，关注科技板块，中英文新闻混读

## 工作规则

- **Git 提交**：修改代码后，需要先向用户汇报改动内容，等用户确认后再执行 `git commit` 和 `git push`。不要自行提交。
- **部署**：推送后由用户在 Render 面板手动部署。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, Flask, gunicorn |
| 前端 | 纯 HTML/CSS/JS（无框架），移动端响应式 |
| RSS 解析 | feedparser |
| HTTP 请求 | requests（`(connect, read)` 超时元组） |
| 并发 | `concurrent.futures.ThreadPoolExecutor` |
| 部署 | Render.com 免费层（新加坡节点），Cloudflare CDN |
| 版本管理 | Git + SSH Key 认证 |

## 项目结构

```
├── app.py              # Flask 后端，新闻源配置 + 抓取逻辑 + API 路由
├── templates/
│   └── index.html      # 单页前端（CSS/JS 内嵌）
├── render.yaml         # Render 部署配置
├── requirements.txt    # Python 依赖
└── .gitignore
```

## 核心架构

### 新闻源配置（`SOURCES` 列表）

每个源是一个字典，两类：

- **RSS 源**：`type: "rss"`，需 `url` 字段，用 feedparser 解析
- **API 源**：`type: "api"`，需 `api_type` 字段，需在 `API_FETCHERS` 中注册抓取函数

```python
# 新增 RSS 源示例
{"name": "来源名", "type": "rss", "url": "https://...",
 "category": "分类", "lang": "zh", "color": "#10b981"}

# 新增 API 源示例
{"name": "来源名", "type": "api", "api_type": "my_api",
 "category": "分类", "lang": "zh", "color": "#dc2626"}
```

### 缓存策略

10 分钟内存缓存（`_cache` 字典），`/api/refresh` 可强制刷新。

### API 端点

| 路由 | 说明 |
|---|---|
| `/` | 首页 |
| `/api/news` | 聚合新闻 JSON |
| `/api/refresh` | 清除缓存并重新抓取 |
| `/api/version` | 版本检查 |
| `/api/health` | 健康检查 |

## 关键踩坑记录

### 1. ThreadPoolExecutor + with 语句陷阱 ⚠️

**绝对不能** 在 Render 上用 `with ThreadPoolExecutor() as executor:` 写完就结束。`with` 退出时自动调用 `executor.shutdown(wait=True)`，会阻塞等待所有 future 完成，**无视** `wait(timeout=...)`。

正确做法：手动管理 executor，用 `shutdown(wait=False)`：

```python
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
try:
    # ... submit futures, wait with timeout ...
finally:
    executor.shutdown(wait=False)  # 关键：不等待未完成线程
```

### 2. Render 反代层 30 秒超时

Render 的负载均衡器有约 30 秒的硬超时。请求必须在 20 秒内返回（留 10 秒余量）。当前方案：
- 单源 HTTP 超时：`(connect=3s, read=5s)` + `(connect=3s, read=5s)` for API
- 整体抓取硬上限：`wait(timeout=20)` 秒
- gunicorn timeout：90 秒

### 3. 国内 RSS 源从新加坡访问可能失败

Render 免费层只有新加坡节点。36氪、动点科技等国内站点可能很慢或阻断境外请求。这是正常现象——部分源超时不影响整体服务。

### 4. gunicorn 配置

```yaml
startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 90 --preload
```

- 1 worker：免费层 512MB 内存，多 worker 容易 OOM
- `--preload`：预加载模块，worker fork 时共享内存
- `timeout 90`：给 worker 充足时间（实际请求在 20s 内结束）

### 5. 华尔街见闻 API

端点：`api-one.wallstcn.com/apiv1/content/lives?channel=global`
返回实时快讯，覆盖 A 股/宏观。字段：`title`, `content_text`, `display_time`, `uri`。

### 6. 中文源 RSS 选型

之前尝试过但失败的源（被反爬或 RSS 不可用）：
- 虎嗅、极客公园、品玩 → 反爬拦截
- 华尔街见闻 RSS、东方财富、证券时报 → RSS 不可用

目前使用的中文 RSS：36氪、量子位、爱范儿、动点科技、少数派

## 本地开发

```bash
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5000
```

Windows 下注意：如果控制台报 GBK 编码错误，启动入口已有 `sys.stdout.reconfigure(encoding="utf-8")` 处理。

## 部署流程

1. 改代码 → `git commit` → `git push origin master`
2. 打开 Render 面板 → Manual Deploy → Deploy latest commit
3. 等 1-2 分钟构建完成
4. 访问 https://daily-finance-brief.onrender.com 验证

> 免费层 15 分钟无请求后休眠，首次访问可能慢（冷启动 50s+），刷新即可。

## Git 认证

SSH Key 认证（`~/.ssh/id_ed25519`），公钥已添加到 GitHub。`git push` 无需输入密码。
