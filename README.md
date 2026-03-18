# Tech & Finance News Aggregator

エンジニアと投資家のための、高密度・情報管制塔ダッシュボード。
AI、インフラ、セキュリティ、そして厳選されたマーケット情報を1画面（1列）で俯瞰できます。

## 特徴

- **1カラム・高密度フィード:** 縦スクロールだけで全ジャンルの最新情報を高速スキャン。
- **マルチソース集約:**
  - AI: Anthropic, Google Developers, Zenn
  - Infra: Publickey, JSer.info (Web/JS)
  - Security: ScanNetSecurity
  - Finance: Google News (Bloomberg, Reuters, 株探, 日経, Yahoo!等から高品質な情報を抽出)
- **インテリジェント・ハイライト:** 
  - AIエージェント (MCP, Claude, Gemini, RAG...)
  - クラウドネイティブ (AWS, K8s, Terraform...)
  - 投資判断 (上方修正, 増配, 最高益, 決算...)
- **正確な日付表示:** Google Blog等の日付欠落フィードに対し、個別記事のHTMLメタ解析による自動補完。
- **フルオート運用:** GitHub Actionsにより毎日3回 (7:00, 12:00, 18:00) 自動更新。
- **ダークモード対応:** OS設定に合わせた快適な閲覧環境。

## 技術スタック

- **Language:** Python 3.12
- **Tools:** `feedparser` (RSS解析), `jinja2` (HTMLテンプレート)
- **CI/CD:** GitHub Actions (自動実行 & デプロイ)
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
- `NEWS_SOURCES`: 取得元のRSS URL
- `HIGHLIGHT_KEYWORDS`: ハイライトしたい正規表現パターン
- `PERSONALIZED_BIZ_QUERY`: 金融ニュースの検索条件

## ライセンス
MIT License
