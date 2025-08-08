# データフローダイアグラム解析ツール

データフローダイアグラムの画像をアップロードし、AIによる解析でSimulink形式への変換と概要文章の生成を行うStreamlitアプリケーションです。

## 機能

- 📤 データフローダイアグラム画像のアップロード
- 🤖 OpenAI GPT-4oによる画像解析
- 🔄 Simulink MDL形式への自動変換
- 📝 システム概要文章の自動生成
- 💾 解析結果のダウンロード

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. OpenAI APIキーの設定

`.env`ファイルにAPIキーを設定してください：

```
OPENAI_API_KEY=your_api_key_here
```

### 3. アプリケーションの起動

```bash
streamlit run app.py
```

## 使い方

1. ブラウザでアプリケーションを開く
2. データフローダイアグラムの画像（PNG/JPG/JPEG）をアップロード
3. 「解析開始」ボタンをクリック
4. 解析結果を確認
5. 必要に応じて概要文章やSimulinkファイルをダウンロード

## プロジェクト構成

```
nexty-demo/
├── app.py                  # メインアプリケーション
├── requirements.txt        # 依存パッケージ
├── .env                   # 環境変数（APIキー）
├── .gitignore            # Git除外設定
├── utils/
│   ├── __init__.py
│   ├── image_processor.py    # 画像処理
│   ├── llm_analyzer.py       # LLM解析
│   └── simulink_generator.py # Simulink生成
└── outputs/              # 出力ファイル保存先
```

## 技術スタック

- **フロントエンド**: Streamlit
- **画像処理**: PIL/Pillow
- **AI/LLM**: OpenAI GPT-4o
- **出力形式**: Simulink MDL

## 注意事項

- 画像サイズは最大10MBまで
- OpenAI APIの利用料金が発生します
- APIキーは安全に管理してください# nexty_demo
