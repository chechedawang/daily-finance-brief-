/**
 * 每日财经快报 - 前端逻辑
 */

// ========== 全局状态 ==========
let allArticles = [];        // 所有新闻
let sourcesInfo = [];        // 来源状态信息
let currentFilter = 'all';   // 当前分类筛选
let isLoading = false;

// ========== 页面加载时自动获取新闻 ==========
document.addEventListener('DOMContentLoaded', () => {
    loadNews(false);
});

// ========== 获取新闻数据 ==========
async function loadNews(forceRefresh) {
    if (isLoading) return;
    isLoading = true;

    const refreshBtn = document.getElementById('refreshBtn');
    refreshBtn.classList.add('spinning');

    try {
        const endpoint = forceRefresh ? '/api/refresh' : '/api/news';
        const resp = await fetch(endpoint);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();

        // 更新全局状态
        allArticles = data.articles || [];
        sourcesInfo = data.sources || [];

        // 更新 UI
        updateHeader(data.date);
        updateStats(data.total, data.sources);
        buildFilterChips();
        renderNews();
        document.getElementById('cacheTime').textContent =
            `数据更新于 ${data.cached_at}`;

        // 显示之前隐藏的元素
        document.getElementById('statsBar').style.display = 'flex';
        document.getElementById('toolbar').style.display = 'flex';

    } catch (err) {
        console.error('获取新闻失败:', err);
        document.getElementById('newsList').innerHTML = `
            <div class="state-message">
                <div class="emoji">😵</div>
                <div class="text">新闻加载失败</div>
                <div class="sub">请检查网络连接后点击右上角刷新按钮重试</div>
            </div>`;
    } finally {
        isLoading = false;
        refreshBtn.classList.remove('spinning');
    }
}

// ========== 更新顶部日期 ==========
function updateHeader(dateStr) {
    document.getElementById('headerDate').textContent = dateStr || '';
}

// ========== 更新状态栏 ==========
function updateStats(total, sources) {
    document.getElementById('newsCount').textContent = total;

    const okCount = sources.filter(s => !s.error).length;
    const errCount = sources.filter(s => s.error).length;
    const totalSources = sources.length;

    const dot = document.getElementById('statsDot');
    dot.className = 'stats-dot';
    if (errCount === totalSources) {
        dot.classList.add('offline');
    } else if (errCount > 0) {
        dot.classList.add('error');
    }

    document.getElementById('statsText').textContent =
        `${okCount}/${totalSources} 个来源正常`;
}

// ========== 构建分类筛选按钮 ==========
function buildFilterChips() {
    const catCount = {};
    allArticles.forEach(a => {
        const cat = a.category || '其他';
        catCount[cat] = (catCount[cat] || 0) + 1;
    });

    let html = `<span class="chip active" data-filter="all" onclick="setFilter('all', this)">
        全部<span class="count">${allArticles.length}</span>
    </span>`;

    for (const [cat, count] of Object.entries(catCount)) {
        html += `<span class="chip" data-filter="${cat}" onclick="setFilter('${cat}', this)">
            ${cat}<span class="count">${count}</span>
        </span>`;
    }

    document.getElementById('filterChips').innerHTML = html;
}

// ========== 切换分类筛选 ==========
function setFilter(filter, el) {
    currentFilter = filter;
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    renderNews();
}

// ========== 渲染新闻列表 ==========
function renderNews() {
    const searchTerm = document.getElementById('searchInput').value.trim().toLowerCase();
    const container = document.getElementById('newsList');

    let filtered = allArticles;

    if (currentFilter !== 'all') {
        filtered = filtered.filter(a => a.category === currentFilter);
    }

    if (searchTerm) {
        filtered = filtered.filter(a =>
            a.title.toLowerCase().includes(searchTerm) ||
            a.source.toLowerCase().includes(searchTerm) ||
            a.summary.toLowerCase().includes(searchTerm)
        );
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="state-message">
                <div class="emoji">📭</div>
                <div class="text">${searchTerm ? '没有匹配的新闻' : '暂无新闻'}</div>
                <div class="sub">${searchTerm ? '试试其他关键词？' : '请点击右上角刷新按钮获取最新新闻'}</div>
            </div>`;
        return;
    }

    container.innerHTML = filtered.map(article => {
        let extraClass = '';
        const cat = article.category || '';
        if (cat.includes('快讯') || cat.includes('财经')) {
            extraClass = 'cat-flash';
        } else if (cat.includes('科技') || cat.includes('Tech') || cat.includes('半导体') || cat.includes('AI') || cat.includes('数字')) {
            extraClass = 'cat-tech';
        } else if (cat.includes('市场') || cat.includes('A股') || cat.includes('全球')) {
            extraClass = 'cat-global-market';
        } else if (cat.includes('宏观')) {
            extraClass = 'cat-macro';
        }

        if (article.lang === 'en') {
            extraClass += ' lang-en';
        }

        return `
        <div class="news-card ${extraClass}" onclick="openArticle('${escapeHtml(article.link)}')">
            <div class="card-meta">
                <span class="source-badge" style="background:${article.color || '#3b82f6'}">
                    ${escapeHtml(article.source)}
                </span>
                <span class="category-tag">${escapeHtml(article.category || '综合')}</span>
                <span class="card-time">${escapeHtml(article.time || '')}</span>
            </div>
            <div class="card-title">${escapeHtml(article.title)}</div>
            ${article.summary ? `<div class="card-summary">${escapeHtml(article.summary)}</div>` : ''}
            <div class="card-link-hint">📎 阅读原文</div>
        </div>`;
    }).join('');
}

// ========== 打开原文链接 ==========
function openArticle(url) {
    if (!url) return;
    window.open(url, '_blank');
}

// ========== HTML 转义（防 XSS） ==========
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ========== 下拉刷新（移动端） ==========
let touchStartY = 0;
document.addEventListener('touchstart', e => {
    touchStartY = e.touches[0].clientY;
}, { passive: true });

document.addEventListener('touchmove', e => {
    const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
    const touchY = e.touches[0].clientY;
    if (scrollTop <= 0 && touchY - touchStartY > 60) {
        loadNews(true);
    }
}, { passive: true });
