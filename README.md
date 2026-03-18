# Tech & Finance News Aggregator

エンジニアと投資家のための、高密度・情報管制塔ダッシュボード。
AI、インフラ、セキュリティ、グローバルテック、そして厳選されたマーケット情報を1画面（1列）で俯瞰できます。

## 特徴

- **1カラム・高密度フィード:** 縦スクロールだけで全ジャンルの最新情報を高速スキャン。
- **マルチソース集約（11ソース）:**
  - AI: Anthropic, Google Developers, Zenn
  - Global: Hacker News (フロントページのトレンド記事)
  - Tech/JP: はてなブックマーク テクノロジー
  - AWS: AWS What's New
  - Infra: Publickey
  - Web/JS: JSer.info
  - Security: ScanNetSecurity, JPCERT/CC
  - Finance: Google News (Bloomberg, Reuters, 株探, 日経, Yahoo!等から高品質な情報を抽出)
- **インテリジェント・ハイライト:** 
  - AIエージェント (MCP, Claude, Gemini, RAG...)
  - クラウドネイティブ (AWS, K8s, Terraform...)
  - 投資判断 (上方修正, 増配, 最高益, 決算...)
  - セキュリティ (脆弱性, Zero Trust, DDoS...)
- **正確な日付表示:** Google Blog等の日付欠落フィードに対し、個別記事のHTMLメタ解析による自動補完。
- **並列フィード取得:** 全ソースを同時取得し、高速に更新。
- **フルオート運用:** GitHub Actionsにより毎日3回 (7:00, 12:00, 18:00 JST) 自動更新。ビルド失敗時はGitHub Issueを自動作成。
- **クライアントサイドフィルタ:** キーワード検索、今日の記事のみ表示、カテゴリ別トグルをブラウザ上で即座に切り替え。
- **ダークモード対応:** OS設定に合わせた快適な閲覧環境。

## 技術スタック

- **Language:** Python 3.12
- **Tools:** `feedparser` (RSS解析), `jinja2` (HTMLテンプレート), `markupsafe` (XSS対策)
- **CI/CD:** GitHub Actions (自動実行 & デプロイ, pip キャッシュ対応)
- **Hosting:** GitHub Pages

## セットアップ

### ローカル実行
```bash
pip install -r requirements.txt
python tech_news_aggregator.py
```

### GitHub での自動更新
1. リポジトリを GitHub にプッシュ。
2. **Settings > Pages** で `Build and deployment > Source` を **GitHub Actions** に設定。
3. `Actions` タブから手動実行、またはスケジュール実行を待つ。

## カスタマイズ

`tech_news_aggregator.py` 内の以下の変数を変更することで、自分専用に調整可能です。
- `NEWS_SOURCES`: 取得元のRSS URL（`limit` でソースごとの表示件数を制御）
- `HIGHLIGHT_KEYWORDS`: ハイライトしたい正規表現パターン
- `FINANCE_QUERY`: 金融ニュースの検索条件

## ライセンス
MIT License
