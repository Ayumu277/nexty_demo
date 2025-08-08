# Streamlitアプリ デプロイガイド

## 推奨: Streamlit Community Cloud（無料）

### 手順：
1. このプロジェクトをGitHubにプッシュ
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

2. [share.streamlit.io](https://share.streamlit.io) にアクセス

3. "New app"をクリック

4. 設定：
   - Repository: あなたのGitHubリポジトリ
   - Branch: main
   - Main file path: app.py

5. Advanced settings > Secrets に環境変数を追加：
```toml
OPENAI_API_KEY = "your-api-key-here"
```

6. Deployをクリック

## Docker を使用したローカル/サーバーデプロイ

### ビルドと実行：
```bash
# .envファイルにOPENAI_API_KEYを設定
echo "OPENAI_API_KEY=your-key-here" > .env

# Dockerイメージをビルド
docker build -t streamlit-app .

# コンテナを実行
docker run -p 8501:8501 --env-file .env streamlit-app

# または docker-compose を使用
docker-compose up -d
```

## Herokuへのデプロイ

### 前提条件：
- Heroku CLIのインストール
- Herokuアカウント

### 手順：
```bash
# Herokuにログイン
heroku login

# Herokuアプリを作成
heroku create your-app-name

# 環境変数を設定
heroku config:set OPENAI_API_KEY=your-api-key

# デプロイ
git push heroku main

# アプリを開く
heroku open
```

## AWS EC2へのデプロイ

### EC2インスタンスでの手順：
```bash
# 依存関係のインストール
sudo apt update
sudo apt install python3-pip python3-venv git

# リポジトリをクローン
git clone https://github.com/yourusername/your-repo.git
cd your-repo

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
export OPENAI_API_KEY="your-key-here"

# Streamlitを実行（バックグラウンド）
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

### セキュリティグループの設定：
- ポート8501を開放（インバウンドルール）

## Google Cloud Runへのデプロイ

### 手順：
```bash
# Google Cloud CLIの設定
gcloud init

# Dockerイメージをビルド
gcloud builds submit --tag gcr.io/PROJECT-ID/streamlit-app

# Cloud Runにデプロイ
gcloud run deploy --image gcr.io/PROJECT-ID/streamlit-app --platform managed

# 環境変数を設定
gcloud run services update streamlit-app --set-env-vars OPENAI_API_KEY=your-key
```

## セキュリティに関する注意事項

1. **APIキーの管理**
   - 本番環境では必ず環境変数またはシークレット管理サービスを使用
   - .envファイルは絶対にGitにコミットしない

2. **アクセス制御**
   - 必要に応じて認証機能を追加
   - Streamlit-Authenticatorなどのライブラリを検討

3. **HTTPS**
   - 本番環境では必ずHTTPSを使用
   - リバースプロキシ（Nginx等）の設定を検討

## トラブルシューティング

### よくある問題：

1. **"ModuleNotFoundError"**
   - requirements.txtに必要なパッケージが記載されているか確認
   
2. **環境変数が読み込まれない**
   - .envファイルの場所を確認
   - python-dotenvがインストールされているか確認

3. **ポートの競合**
   - 他のアプリケーションが8501ポートを使用していないか確認
   - 必要に応じてポート番号を変更

## サポート

問題が発生した場合は、以下を確認してください：
- Streamlitの公式ドキュメント: https://docs.streamlit.io
- エラーログの確認
- requirements.txtの依存関係バージョン