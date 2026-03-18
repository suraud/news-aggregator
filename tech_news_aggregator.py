import feedparser
import os
import webbrowser
import re
import urllib.request
from jinja2 import Environment
from datetime import datetime, timedelta, timezone
import time
import json
from urllib.parse import quote

# 取得するニュースソースの設定（V2.7: 1列・縦型・超高密度）
TRUSTED_DOMAINS = "site:bloomberg.co.jp OR site:reuters.com OR site:kabutan.jp OR site:nikkei.com OR site:finance.yahoo.co.jp"
FINANCE_QUERY = quote(
    f"({TRUSTED_DOMAINS}) (株式 OR 市況 OR 決算 OR 米国株 OR 日経平均 OR 経済 OR 半導体 OR テック企業 OR 投資 OR 為替) -NVIDIA -NVDA"
)
BIZ_URL = f"https://news.google.com/rss/search?q={FINANCE_QUERY}&hl=ja&gl=JP&ceid=JP:ja"

NEWS_SOURCES = [
    {"name": "Anthropic News", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "category": "AI/Claude"},
    {"name": "Google Dev Blog", "url": "https://developers.googleblog.com/feeds/posts/default", "category": "AI/Google"},
    {"name": "Zenn AI Topic", "url": "https://zenn.dev/topics/ai/feed", "category": "Tech/AI"},
    {"name": "Publickey", "url": "https://www.publickey1.jp/atom.xml", "category": "Infra"},
    {"name": "Biz & Stocks", "url": BIZ_URL, "category": "Finance"},
    {"name": "JSer.info", "url": "https://jser.info/rss/", "category": "Web/JS"},
    {"name": "ScanNetSecurity", "url": "https://scan.netsecurity.ne.jp/rss/index.rdf", "category": "Security"},
]

HIGHLIGHT_KEYWORDS = [
    r"MCP", r"Claude(?:\s*[\d\.]+)?", r"Gemini(?:\s*[\d\.]+)?", r"RAG", r"Agent", r"LLM", r"OpenAI", r"GPT",
    r"AWS", r"GCP", r"Azure", r"Kubernetes", r"K8s", r"Terraform", r"Docker", r"Serverless",
    r"Rust", r"Go(?:lang)?", r"TypeScript", r"TS", r"React", r"Next\.js", r"Node\.js", r"API",
    r"株価", r"決算", r"日経平均", r"ナスダック", r"NASDAQ", r"S&P500", r"TSMC", r"テスラ", r"TSLA", r"IPO", r"買収", 
    r"上方修正", r"増配", r"目標株価", r"最高益", r"期待", r"半導体", r"FRB", r"金利", r"円安", r"円高", r"SoftBank", r"Microsoft",
    r"Security", r"脆弱性", r"Zero Trust", r"認証", r"不正アクセス", r"DDoS"
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personalized Vertical Feed v2.7</title>
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
        
        /* 1列（縦積み）のレイアウト */
        .column-feed { display: flex; flex-direction: column; gap: 0; }
        
        .source-section { background: var(--card-bg); border-bottom: 1px solid var(--border-color); padding: 0; margin-bottom: 10px; }
        
        .source-title-sticky { 
            position: sticky; top: 40px; /* headerの高さ分ずらす */
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
    </style>
</head>
<body>
    <header>
        <h1>Personalized Elite Feed v2.7 (1-Column)</h1>
        <span style="font-size: 0.7rem; color: var(--secondary-text);">Updated: {{ updated_at }}</span>
    </header>
    <div class="column-feed">
        {% for source in results %}
        <div class="source-section">
            <div class="source-title-sticky">
                {{ source.name }}
                <span class="category-tag">{{ source.category }}</span>
            </div>
            {% if source.entries %}
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
</body>
</html>
"""

def get_relative_time(dt):
    now = datetime.now(timezone(timedelta(hours=9)))
    diff = now - dt
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            return f"{minutes}m"
        return f"{hours}h"
    elif diff.days == 1:
        return "1d"
    elif diff.days < 7:
        return f"{diff.days}d"
    else:
        return dt.strftime("%m/%d")

def parse_date_string(date_str):
    if not date_str: return None
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.astimezone(timezone(timedelta(hours=9)))
    except:
        return None

def fetch_date_from_html(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            m = re.search(r'property="article:published_time" content="([^"]+)"', html)
            if m: return parse_date_string(m.group(1))
            m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
            if m: return parse_date_string(m.group(1))
    except:
        pass
    return None

def format_date_info(dt):
    if not dt:
        return "Unknown", "Recent"
    return dt.strftime("%Y-%m-%d %H:%M"), get_relative_time(dt)

def highlight_text(text):
    if not text: return ""
    for pattern in HIGHLIGHT_KEYWORDS:
        text = re.sub(f"({pattern})", r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)
    return text

def fetch_feed_with_ua(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return feedparser.parse(response.read())
    except:
        return None

def fetch_news():
    results = []
    for source in NEWS_SOURCES:
        print(f"Fetching: {source['name']}...")
        feed = fetch_feed_with_ua(source['url'])
        entries = []
        if feed and feed.entries:
            for entry in feed.entries[:20]:
                date_struct = (entry.get('published_parsed') or 
                               entry.get('updated_parsed') or 
                               entry.get('created_parsed'))
                dt = None
                if date_struct:
                    dt = datetime(*date_struct[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                if not dt and source['name'] == "Google Dev Blog":
                    dt = fetch_date_from_html(entry.link)
                fmt_date, rel_date = format_date_info(dt)
                entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "date_formatted": fmt_date,
                    "date_relative": rel_date
                })
        results.append({
            "name": source['name'],
            "category": source['category'],
            "entries": entries
        })
    return results

def main():
    results = fetch_news()
    updated_at = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    env = Environment()
    env.filters['highlight'] = highlight_text
    template = env.from_string(HTML_TEMPLATE)
    html_content = template.render(results=results, updated_at=updated_at)
    output_file = "tech_news.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nDone! Dashboard updated at {output_file}")
    
    # GitHub Actions等の環境でなければブラウザを開く
    if not os.environ.get('GITHUB_ACTIONS'):
        webbrowser.open('file://' + os.path.realpath(output_file))

if __name__ == "__main__":
    main()
