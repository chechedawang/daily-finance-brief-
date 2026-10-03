/**
 * 每日财经快报 - 前端逻辑
 *
 * 数据来源：build.py 在构建时把数据内联到 window.__NEWS_DATA__，
 * 页面加载即可渲染，首屏零网络请求（这是"秒开"的关键）。
 * 搜索、筛选全部在前端内存中完成，不产生任何后端请求。
 */

// ========== 全局状态 ==========
let allArticles = [];       // 全部文章
let currentFilter = 'all';  // 当前分类筛选

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', init);

async function init() {
    const data = await loadData();

    if (!data || !Array.isArray(data.articles) || data.articles.length === 0) {
        showEmpty('新闻加载失败', '数据可能尚未生成，请稍后再试', '😵');
        return;
    }

    allArticles = data.articles;

    // 顶部日期 + 底部更新时间
    document.getElementById('headerDate').textContent = data.date || '';
    document.getElementById('updatedAt').textContent =
        data.generated_at ? `数据更新于 ${data.generated_at}` : '';

    updateStats(data.total, data.sources || []);
    buildFilterChips();
    renderNews();
    bindEvents();

    // 数据就绪，显示工具栏
    document.getElementById('toolbar').hidden = false;
    document.getElementById('statsBar').hidden = false;
}

// ========== 取数 ==========
function loadData() {
    // 首选：构建时内联的数据（正常路径，零请求）
    if (window.__NEWS_DATA__) {
        return Promise.resolve(window.__NEWS_DATA__);
    }
    // 兜底：独立 JSON 文件（异常部署或直接用模板预览时）
    return fetch('data/news.json')
        .then(resp => (resp.ok ? resp.json() : null))
        .catch(() => null);
}

// ========== 事件绑定（委托，避免内联 onclick 被特殊字符破坏） ==========
function bindEvents() {
    // 点击卡片 → 打开原文
    document.getElementById('newsList').addEventListener('click', event => {
        const card = event.target.closest('.news-card');
        if (card && card.dataset.link) {
            window.open(card.dataset.link, '_blank', 'noopener');
        }
    });

    // 点击分类标签 → 切换筛选
    document.getElementById('filterChips').addEventListener('click', event => {
        const chip = event.target.closest('.chip');
        if (!chip) return;
        currentFilter = chip.dataset.filter;
        document.querySelectorAll('.chip').forEach(c => {
            c.classList.toggle('active', c === chip);
        });
        renderNews();
    });
}

// ========== 状态栏 ==========
function updateStats(total, sources) {
    document.getElementById('newsCount').textContent = total;

    const errCount = sources.filter(s => s.error).length;
    const totalSources = sources.length;

    const dot = document.getElementById('statsDot');
    dot.className = 'stats-dot';
    if (totalSources > 0 && errCount === totalSources) {
        dot.classList.add('offline');
    } else if (errCount > 0) {
        dot.classList.add('error');
    }

    document.getElementById('statsText').textContent =
        `${totalSources - errCount}/${totalSources} 个来源正常`;
}

// ========== 分类筛选标签 ==========
function buildFilterChips() {
    const catCount = {};
    allArticles.forEach(a => {
        const cat = a.category || '其他';
        catCount[cat] = (catCount[cat] || 0) + 1;
    });

    let html = chipHtml('all', '全部', allArticles.length, true);
    for (const [cat, count] of Object.entries(catCount)) {
        html += chipHtml(cat, cat, count, false);
    }

    document.getElementById('filterChips').innerHTML = html;
}

function chipHtml(value, label, count, active) {
    return `<span class="chip${active ? ' active' : ''}" data-filter="${escapeHtml(value)}">`
         + `${escapeHtml(label)}<span class="count">${count}</span></span>`;
}

// ========== 渲染新闻列表 ==========
function renderNews() {
    const searchTerm = (document.getElementById('searchInput').value || '').trim().toLowerCase();
    const container = document.getElementById('newsList');

    let filtered = allArticles;

    if (currentFilter !== 'all') {
        filtered = filtered.filter(a => a.category === currentFilter);
    }

    if (searchTerm) {
        filtered = filtered.filter(a => {
            const haystack = [a.title, a.source, a.summary]
                .map(v => (v || '').toLowerCase())
                .join(' ');
            return haystack.includes(searchTerm);
        });
    }

    if (filtered.length === 0) {
        showEmpty(
            searchTerm ? '没有匹配的新闻' : '暂无新闻',
            searchTerm ? '试试其他关键词？' : '数据每日 12:00 自动更新',
            '📭'
        );
        return;
    }

    container.innerHTML = filtered.map(renderCard).join('');
}

function renderCard(article) {
    const cat = article.category || '';
    let extraClass = '';

    if (cat.includes('快讯') || cat.includes('财经')) {
        extraClass = 'cat-flash';
    } else if (cat.includes('科技') || cat.includes('Tech') || cat.includes('半导体')
               || cat.includes('AI') || cat.includes('数字')) {
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
    <div class="news-card ${extraClass}" data-link="${escapeHtml(article.link || '')}">
        <div class="card-meta">
            <span class="source-badge" style="background:${escapeHtml(article.color || '#3b82f6')}">
                ${escapeHtml(article.source || '')}
            </span>
            <span class="category-tag">${escapeHtml(article.category || '综合')}</span>
            <span class="card-time">${escapeHtml(article.time || '')}</span>
        </div>
        <div class="card-title">${escapeHtml(article.title || '')}</div>
        ${article.summary ? `<div class="card-summary">${escapeHtml(article.summary)}</div>` : ''}
        <div class="card-link-hint">📎 阅读原文</div>
    </div>`;
}

// ========== 空状态 / 错误提示 ==========
function showEmpty(text, sub, emoji) {
    document.getElementById('newsList').innerHTML = `
        <div class="state-message">
            <div class="emoji">${emoji || '📭'}</div>
            <div class="text">${escapeHtml(text)}</div>
            <div class="sub">${escapeHtml(sub)}</div>
        </div>`;
}

// ========== HTML 转义（防 XSS）
// 同时转义引号，因此文本内容和属性值两种场景都可安全使用 ==========
function escapeHtml(str) {
    return String(str == null ? '' : str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
