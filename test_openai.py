"""
OpenAI API接続テスト
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# 環境変数を読み込み
load_dotenv()

# APIキーを取得
api_key = os.getenv("OPENAI_API_KEY")
print(f"APIキーの長さ: {len(api_key) if api_key else 0} 文字")

try:
    # OpenAIクライアントを初期化
    client = OpenAI(api_key=api_key)
    
    # 簡単なテスト
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Hello, this is a test. Reply with 'OK' if you receive this."}
        ],
        max_tokens=10
    )
    
    print("✅ 接続成功！")
    print(f"レスポンス: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ エラー: {e}")
    print(f"エラーの詳細: {type(e).__name__}")