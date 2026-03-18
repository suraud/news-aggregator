import feedparser
import os
import webbrowser
import re
import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from markupsafe import Markup, escape
from jinja2 import Environment
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

# 取得するニュースソースの設定
TRUSTED_DOMAINS = "site:bloomberg.co.jp OR site:reuters.com OR site:kabutan.jp OR site:nikkei.com OR site:finance.yahoo.co.jp"
FINANCE_QUERY = quote(
    f"({TRUSTED_DOMAINS}) (株式 OR 市況 OR 決算 OR 米国株 OR 日経平均 OR 経済 OR 半導体 OR テック企業 OR 投資 OR 為替) -NVIDIA -NVDA"
)
BIZ_URL = f"https://news.google.com/rss/search?q={FINANCE_QUERY}&hl=ja&gl=JP&ceid=JP:ja"

NEWS_SOURCES = [
    {"name": "Anthropic News", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "category": "AI/Claude", "limit": 10},
    {"name": "Google Dev Blog", "url": "https://developers.googleblog.com/feeds/posts/default", "category": "AI/Google", "limit": 15},
    {"name": "Zenn AI Topic", "url": "https://zenn.dev/topics/ai/feed", "category": "Tech/AI", "limit": 10},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "category": "Tech/Global", "limit": 15},
    {"name": "Hatena Tech", "url": "https://b.hatena.ne.jp/hotentry/it.rss", "category": "Tech/JP", "limit": 15},
    {"name": "AWS What's New", "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/", "category": "AWS", "limit": 20},
    {"name": "Publickey", "url": "https://www.publickey1.jp/atom.xml", "category": "Infra", "limit": 15},
    {"name": "Biz & Stocks", "url": BIZ_URL, "category": "Finance", "limit": 20},
    {"name": "JSer.info", "url": "https://jser.info/rss/", "category": "Web/JS", "limit": 7},
    {"name": "ScanNetSecurity", "url": "https://scan.netsecurity.ne.jp/rss/index.rdf", "category": "Security", "limit": 15},
    {"name": "JPCERT/CC", "url": "https://www.jpcert.or.jp/rss/jpcert-all.rdf", "category": "Security", "limit": 10},
]

HIGHLIGHT_KEYWORDS = [
    r"MCP", r"Claude(?:\s*[\d\.]+)?", r"Gemini(?:\s*[\d\.]+)?", r"RAG", r"Agent", r"LLM", r"OpenAI", r"GPT",
    r"AWS", r"GCP", r"Azure", r"Kubernetes", r"K8s", r"Terraform", r"Docker", r"Serverless",
    r"Rust", r"Go(?:lang)?", r"TypeScript", r"TS", r"React", r"Next\.js", r"Node\.js", r"API",
    r"株価", r"決算", r"日経平均", r"ナスダック", r"NASDAQ", r"S&P500", r"TSMC", r"テスラ", r"TSLA", r"IPO", r"買収",
    r"上方修正", r"増配", r"目標株価", r"最高益", r"期待", r"半導体", r"FRB", r"金利", r"円安", r"円高", r"SoftBank", r"Microsoft",
    r"Security", r"脆弱性", r"Zero Trust", r"認証", r"不正アクセス", r"DDoS"
]

# 正規表現を事前コンパイル
_HIGHLIGHT_RE = re.compile("|".join(f"({p})" for p in HIGHLIGHT_KEYWORDS), re.IGNORECASE)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personalized Vertical Feed v3.0</title>
    <style>
        :root {
            --bg-color: #f0f2f5;
            --card-bg: #ffffff;
            --text-color: #1c1e21;
            --secondary-text: #606770;
            --border-color: #dddfe2;
            --accent-color: #1877f2;
            --highlight-bg: #fff3cd;
            --highlight-text: #856404;
            --date-badge: #ebedf0;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #18191a;
                --card-bg: #242526;
                --text-color: #e4e6eb;
                --secondary-text: #b0b3b8;
                --border-color: #3e4042;
                --accent-color: #2d88ff;
                --highlight-bg: #ffd33d22;
                --highlight-text: #f2cc60;
                --date-badge: #3a3b3c;
            }
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.2; color: var(--text-color); background-color: var(--bg-color); margin: 0 auto; padding: 0; max-width: 1000px; }
        header { padding: 10px 15px; background: var(--card-bg); border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: baseline; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { margin: 0; font-size: 1.1rem; }
        .column-feed { display: flex; flex-direction: column; gap: 0; }
        .source-section { background: var(--card-bg); border-bottom: 1px solid var(--border-color); padding: 0; margin-bottom: 10px; }
        .source-title-sticky {
            position: sticky; top: 40px;
            background: var(--bg-color);
            padding: 4px 15px;
            font-size: 0.8rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 90;
            border-bottom: 1px solid var(--border-color);
            color: var(--secondary-text);
        }
        .category-tag { font-size: 0.6rem; background: var(--accent-color); color: white; padding: 1px 6px; border-radius: 4px; }
        ul { list-style: none; padding: 0; margin: 0; }
        li { padding: 8px 15px; border-bottom: 1px solid rgba(0,0,0,0.05); transition: background 0.1s; }
        li:hover { background-color: rgba(0,0,0,0.02); }
        li:last-child { border-bottom: none; }
        .entry-meta { display: flex; align-items: center; gap: 8px; font-size: 0.7rem; color: var(--secondary-text); margin-bottom: 2px; }
        .entry-date { background: var(--date-badge); padding: 0 4px; border-radius: 3px; font-weight: 600; }
        .entry-title { text-decoration: none; color: var(--text-color); font-size: 0.9rem; font-weight: 500; display: block; white-space: normal; line-height: 1.3; }
        .entry-title:hover { color: var(--accent-color); }
        .highlight { background-color: var(--highlight-bg); color: var(--highlight-text); padding: 0 1px; border-radius: 2px; font-weight: bold; }
        .empty-msg { padding: 15px; font-size: 0.8rem; color: var(--secondary-text); font-style: italic; }
        .error-msg { padding: 15px; font-size: 0.8rem; color: #e74c3c; font-style: italic; }
        .filter-btn { background: var(--date-badge); border: 1px solid var(--border-color); color: var(--text-color); padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; cursor: pointer; }
        .filter-btn.active { background: var(--accent-color); color: white; border-color: var(--accent-color); }
        .filter-bar { display: flex; align-items: center; gap: 6px; }
        .filter-bar input { background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color); padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; width: 120px; }
        .cat-btn { background: var(--date-badge); border: 1px solid var(--border-color); color: var(--secondary-text); padding: 2px 6px; border-radius: 4px; font-size: 0.6rem; cursor: pointer; }
        .cat-btn.hidden { opacity: 0.4; text-decoration: line-through; }
    </style>
</head>
<body>
    <header>
        <h1>Personalized Elite Feed v3.0 (1-Column)</h1>
        <span style="font-size: 0.7rem; color: var(--secondary-text);">Updated: {{ updated_at }}</span>
        <div class="filter-bar">
            <input type="text" id="keyword" placeholder="Filter..." oninput="applyFilters()">
            <button class="filter-btn" onclick="this.classList.toggle('active');applyFilters()">Today</button>
        </div>
    </header>
    <div style="padding:4px 15px;display:flex;gap:4px;flex-wrap:wrap;background:var(--bg-color);border-bottom:1px solid var(--border-color);" id="catBar">
        {% for source in results %}
        <button class="cat-btn" data-cat="{{ source.name }}" onclick="this.classList.toggle('hidden');applyFilters()">{{ source.category }}</button>
        {% endfor %}
    </div>
    </header>
    <div class="column-feed">
        {% for source in results %}
        <div class="source-section">
            <div class="source-title-sticky" data-source="{{ source.name }}">
                {{ source.name }}
                <span class="category-tag">{{ source.category }}</span>
            </div>
            {% if source.error %}
            <p class="error-msg">⚠ Feed fetch failed</p>
            {% elif source.entries %}
            <ul>
                {% for entry in source.entries %}
                <li>
                    <div class="entry-meta">
                        <span class="entry-date">{{ entry.date_relative }}</span>
                        {% if entry.date_formatted != "Unknown" %}
                        <span style="font-size: 0.65rem; opacity: 0.6;">{{ entry.date_formatted }}</span>
                        {% endif %}
                    </div>
                    <a href="{{ entry.link }}" class="entry-title" target="_blank">{{ entry.title | highlight }}</a>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="empty-msg">No entries found.</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
{% autoescape false %}
<script>
function applyFilters(){
  var kw=document.getElementById('keyword').value.toLowerCase();
  var todayOn=document.querySelector('.filter-btn').classList.contains('active');
  var hiddenCats={};
  document.querySelectorAll('.cat-btn.hidden').forEach(function(b){hiddenCats[b.getAttribute('data-cat')]=true;});
  document.querySelectorAll('.source-section').forEach(function(sec){
    var name=sec.querySelector('.source-title-sticky').getAttribute('data-source')||'';
    if(hiddenCats[name]){sec.style.display='none';return;}
    var items=sec.querySelectorAll('li');
    if(!items.length){sec.style.display='';return;}
    var visible=0;
    items.forEach(function(li){
      var badge=(li.querySelector('.entry-date')||{}).textContent||'';
      badge=badge.trim();
      var isToday=badge.endsWith('m')||badge.endsWith('h');
      var title=(li.querySelector('.entry-title')||{}).textContent||'';
      title=title.toLowerCase();
      var show=(!todayOn||isToday)&&(!kw||title.indexOf(kw)!==-1);
      li.style.display=show?'':'none';
      if(show)visible++;
    });
    sec.style.display=visible?'':'none';
  });
}
</script>
{% endautoescape %}
</body>
</html>
"""

def get_relative_time(dt):
    now = datetime.now(JST)
    diff = now - dt
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            return f"{diff.seconds // 60}m"
        return f"{hours}h"
    elif diff.days == 1:
        return "1d"
    elif diff.days < 7:
        return f"{diff.days}d"
    return dt.strftime("%m/%d")

def parse_date_string(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).astimezone(JST)
    except (ValueError, TypeError):
        return None

def fetch_date_from_html(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            m = re.search(r'property="article:published_time" content="([^"]+)"', html)
            if m:
                return parse_date_string(m.group(1))
            m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
            if m:
                return parse_date_string(m.group(1))
    except (urllib.request.URLError, OSError, UnicodeDecodeError) as e:
        logger.debug(f"Date fetch failed for {url}: {e}")
    return None

def format_date_info(dt):
    if not dt:
        return "Unknown", "Recent"
    return dt.strftime("%Y-%m-%d %H:%M"), get_relative_time(dt)

def highlight_text(text):
    if not text:
        return Markup("")
    escaped = escape(text)
    result = _HIGHLIGHT_RE.sub(r'<span class="highlight">\g<0></span>', str(escaped))
    return Markup(result)

def fetch_feed_with_ua(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return feedparser.parse(response.read())

def fetch_single_source(source):
    """1ソースを取得して結果dictを返す。並列実行用。"""
    logger.info(f"Fetching: {source['name']}...")
    try:
        feed = fetch_feed_with_ua(source['url'])
    except (urllib.request.URLError, OSError) as e:
        logger.warning(f"FAILED: {source['name']} - {e}")
        return {"name": source['name'], "category": source['category'], "entries": [], "error": True}

    entries = []
    if feed and feed.entries:
        limit = source.get('limit', 20)
        for entry in feed.entries[:limit]:
            date_struct = (entry.get('published_parsed') or
                           entry.get('updated_parsed') or
                           entry.get('created_parsed'))
            dt = None
            if date_struct:
                dt = datetime(*date_struct[:6], tzinfo=timezone.utc).astimezone(JST)
            if not dt and source['name'] == "Google Dev Blog":
                dt = fetch_date_from_html(entry.link)
            fmt_date, rel_date = format_date_info(dt)
            entries.append({
                "title": entry.title,
                "link": entry.link,
                "date_formatted": fmt_date,
                "date_relative": rel_date
            })

    logger.info(f"  {source['name']}: {len(entries)} entries")
    return {"name": source['name'], "category": source['category'], "entries": entries, "error": False}

def fetch_news():
    results = [None] * len(NEWS_SOURCES)
    with ThreadPoolExecutor(max_workers=len(NEWS_SOURCES)) as executor:
        future_to_idx = {executor.submit(fetch_single_source, src): i for i, src in enumerate(NEWS_SOURCES)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()

    # サマリーログ
    ok = sum(1 for r in results if not r["error"])
    fail = sum(1 for r in results if r["error"])
    total = sum(len(r["entries"]) for r in results)
    logger.info(f"Summary: {ok}/{ok+fail} sources OK, {total} total entries")
    if fail:
        logger.warning(f"Failed sources: {[r['name'] for r in results if r['error']]}")
    return results

def main():
    results = fetch_news()
    updated_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    env = Environment(autoescape=True)
    env.filters['highlight'] = highlight_text
    template = env.from_string(HTML_TEMPLATE)
    html_content = template.render(results=results, updated_at=updated_at)
    output_file = "tech_news.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"Done! Dashboard updated at {output_file}")

    if not os.environ.get('GITHUB_ACTIONS'):
        webbrowser.open('file://' + os.path.realpath(output_file))

if __name__ == "__main__":
    main()
