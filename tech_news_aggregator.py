import feedparser
import os
import webbrowser
import re
import urllib.request
from jinja2 import Environment
from datetime import datetime, timedelta, timezone
import time
import json

# 取得するニュースソースの設定
NEWS_SOURCES = [
    {"name": "Anthropic News", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "category": "AI/Claude"},
    {"name": "Anthropic Engineering", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml", "category": "AI/Tech"},
    {"name": "Google Developers Blog", "url": "https://developers.googleblog.com/feeds/posts/default", "category": "AI/Google"},
    {"name": "Zenn (AI Topic)", "url": "https://zenn.dev/topics/ai/feed", "category": "AI/Tech"},
    {"name": "Publickey", "url": "https://www.publickey1.jp/atom.xml", "category": "Infrastructure"},
    {"name": "JSer.info", "url": "https://jser.info/rss/", "category": "Frontend/JS"},
    {"name": "ScanNetSecurity", "url": "https://scan.netsecurity.ne.jp/rss/index.rdf", "category": "Security"},
]

# ハイライトするキーワード
HIGHLIGHT_KEYWORDS = [
    r"MCP", r"Claude(?:\s*[\d\.]+)?", r"Gemini(?:\s*[\d\.]+)?", 
    r"Security", r"脆弱性", r"API", r"Infrastructure", r"Kiro"
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech News Aggregator v2.2</title>
    <style>
        :root {
            --bg-color: #f5f7f9;
            --card-bg: #ffffff;
            --text-color: #333333;
            --secondary-text: #666666;
            --border-color: #e1e4e8;
            --accent-color: #007bff;
            --highlight-bg: #fff3cd;
            --highlight-text: #856404;
            --date-badge: #e2e8f0;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #0d1117;
                --card-bg: #161b22;
                --text-color: #c9d1d9;
                --secondary-text: #8b949e;
                --border-color: #30363d;
                --accent-color: #58a6ff;
                --highlight-bg: #ffd33d33;
                --highlight-text: #f2cc60;
                --date-badge: #30363d;
            }
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: var(--text-color); background-color: var(--bg-color); max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { border-bottom: 2px solid var(--border-color); padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: baseline; }
        h1 { margin: 0; font-size: 1.5rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 20px; }
        .source-section { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .source-title { margin-top: 0; font-size: 1.1rem; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 15px; }
        .category-tag { font-size: 0.7rem; background: var(--accent-color); color: white; padding: 2px 8px; border-radius: 12px; }
        ul { list-style: none; padding: 0; margin: 0; }
        li { margin-bottom: 15px; }
        li:last-child { margin-bottom: 0; }
        .entry-meta { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: var(--secondary-text); margin-bottom: 4px; }
        .entry-date { background: var(--date-badge); padding: 1px 6px; border-radius: 4px; font-weight: 500; }
        .entry-title { font-weight: 500; text-decoration: none; color: var(--text-color); transition: color 0.2s; display: block; }
        .entry-title:hover { color: var(--accent-color); }
        .highlight { background-color: var(--highlight-bg); color: var(--highlight-text); padding: 0 2px; border-radius: 3px; font-weight: bold; }
        .empty-msg { font-size: 0.9rem; color: var(--secondary-text); font-style: italic; }
    </style>
</head>
<body>
    <header>
        <h1>Tech News Dashboard v2.2</h1>
        <span style="font-size: 0.8rem; color: var(--secondary-text);">Last Updated: {{ updated_at }}</span>
    </header>
    <div class="grid">
        {% for source in results %}
        <div class="source-section">
            <h2 class="source-title">
                {{ source.name }}
                <span class="category-tag">{{ source.category }}</span>
            </h2>
            {% if source.entries %}
            <ul>
                {% for entry in source.entries %}
                <li>
                    <div class="entry-meta">
                        <span class="entry-date">{{ entry.date_relative }}</span>
                        {% if entry.date_formatted != "Unknown" %}
                        <span style="font-size: 0.7rem; opacity: 0.7;">({{ entry.date_formatted }})</span>
                        {% endif %}
                    </div>
                    <a href="{{ entry.link }}" class="entry-title" target="_blank">{{ entry.title | highlight }}</a>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="empty-msg">No articles found or failed to fetch.</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def get_relative_time(dt):
    """JST基準で相対時間を計算する"""
    now = datetime.now(timezone(timedelta(hours=9)))
    diff = now - dt
    
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            return f"{minutes}分前"
        return f"{hours}時間前"
    elif diff.days == 1:
        return "昨日"
    elif diff.days < 7:
        return f"{diff.days}日前"
    else:
        return dt.strftime("%m/%d")

def parse_date_string(date_str):
    """様々な形式の日付文字列をパースしてJSTのdatetimeを返す"""
    if not date_str: return None
    try:
        # ISO 8601 (2026-03-17T...)
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.astimezone(timezone(timedelta(hours=9)))
    except:
        return None

def fetch_date_from_html(url):
    """記事ページから日付メタデータを抽出する"""
    print(f"  Fetching article date: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            
            # 1. article:published_time を探す
            m = re.search(r'property="article:published_time" content="([^"]+)"', html)
            if m: return parse_date_string(m.group(1))
            
            # 2. JSON-LD datePublished を探す
            m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
            if m: return parse_date_string(m.group(1))
            
            # 3. 最終手段: title内の日付など（今回は省略）
    except Exception as e:
        print(f"    Failed to fetch HTML date: {e}")
    return None

def format_date_info(dt):
    """ datetime から相対表示と書式化文字列を返す """
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
    except Exception as e:
        print(f"  Request failed for {url}: {e}")
        return None

def fetch_news():
    results = []
    for source in NEWS_SOURCES:
        print(f"Fetching: {source['name']}...")
        feed = fetch_feed_with_ua(source['url'])
        
        entries = []
        if feed and feed.entries:
            for entry in feed.entries[:10]:
                # 1. フィードから日付を取得
                date_struct = (entry.get('published_parsed') or 
                               entry.get('updated_parsed') or 
                               entry.get('created_parsed'))
                
                dt = None
                if date_struct:
                    dt = datetime(*date_struct[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                
                # 2. Google Developers Blog で日付が取れない場合のスクレイピング
                if not dt and source['name'] == "Google Developers Blog":
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
    
    print(f"\nDone! Opening {output_file} in your browser...")
    webbrowser.open('file://' + os.path.realpath(output_file))

if __name__ == "__main__":
    main()
