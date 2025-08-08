"""
代替アップロード方式を提供するバージョン
ドラッグ＆ドロップまたはBase64入力に対応
"""

import streamlit as st
import os
import base64
import json
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI

# 環境変数の読み込み
load_dotenv()

st.set_page_config(page_title="DFD解析（代替版）", layout="wide")
st.title("データフローダイアグラム解析ツール（代替アップロード版）")

# OpenAIクライアントの初期化
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("APIキーが設定されていません")
        return None
    return OpenAI(api_key=api_key)

# LLM解析関数
def analyze_with_llm(client, image_base64):
    """GPT-4oで画像解析"""
    if not client or not image_base64:
        return None
    
    prompt = """
    このデータフローダイアグラムを解析して、以下のJSON形式で返してください：
    {
        "processes": [{"name": "プロセス名", "description": "説明"}],
        "data_stores": [{"name": "データストア名", "description": "説明"}],
        "external_entities": [{"name": "エンティティ名", "description": "説明"}],
        "data_flows": [{"from": "送信元", "to": "送信先", "data": "データ"}],
        "summary": "システムの概要説明"
    }
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }],
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"解析エラー: {e}")
        return None

# メイン処理
def main():
    # タブでアップロード方式を選択
    tab1, tab2, tab3 = st.tabs(["📤 通常アップロード", "📋 Base64入力", "💡 トラブルシューティング"])
    
    uploaded_image_base64 = None
    
    with tab1:
        st.markdown("### 通常のファイルアップロード")
        st.info("もしアップロードが重い場合は、他のタブの方法をお試しください")
        
        uploaded_file = st.file_uploader(
            "画像ファイルを選択",
            type=['png', 'jpg', 'jpeg'],
            key="normal_upload"
        )
        
        if uploaded_file is not None:
            # 画像を表示
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded_file, caption="アップロード画像", use_column_width=True)
            
            # Base64に変換
            bytes_data = uploaded_file.getvalue()
            uploaded_image_base64 = base64.b64encode(bytes_data).decode('utf-8')
            
            with col2:
                if st.button("🔍 解析開始", key="analyze_normal"):
                    with st.spinner("解析中..."):
                        client = get_openai_client()
                        result = analyze_with_llm(client, uploaded_image_base64)
                        if result:
                            st.session_state['analysis_result'] = result
                            st.success("✅ 解析完了！")
    
    with tab2:
        st.markdown("### Base64エンコードされた画像を直接入力")
        st.markdown("""
        **使い方:**
        1. ターミナルで画像をBase64に変換:
        ```bash
        base64 -i your_image.png -o image_base64.txt
        # または
        cat your_image.png | base64 > image_base64.txt
        ```
        2. 生成されたBase64文字列を下のテキストエリアに貼り付け
        """)
        
        base64_input = st.text_area(
            "Base64エンコードされた画像データを貼り付け",
            height=200,
            key="base64_input",
            help="Base64文字列を直接貼り付けてください"
        )
        
        if base64_input:
            try:
                # Base64をデコードして画像として表示
                image_bytes = base64.b64decode(base64_input)
                image = Image.open(BytesIO(image_bytes))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(image, caption="入力画像", use_column_width=True)
                
                with col2:
                    if st.button("🔍 解析開始", key="analyze_base64"):
                        with st.spinner("解析中..."):
                            client = get_openai_client()
                            result = analyze_with_llm(client, base64_input)
                            if result:
                                st.session_state['analysis_result'] = result
                                st.success("✅ 解析完了！")
            except Exception as e:
                st.error(f"Base64デコードエラー: {e}")
    
    with tab3:
        st.markdown("### 🔧 アップロード問題の解決方法")
        
        st.markdown("""
        **もしファイルアップロードが重い・固まる場合:**
        
        1. **ブラウザを変更**
           - Google Chromeを推奨
           - ブラウザのキャッシュをクリア
           - シークレット/プライベートモードで試す
        
        2. **画像サイズを縮小**
           ```bash
           # ImageMagickを使用した画像縮小
           convert input.png -resize 1024x1024 output.png
           ```
        
        3. **Base64方式を使用**
           - 「Base64入力」タブから直接入力
        
        4. **別のポートで起動**
           ```bash
           streamlit run app_alternative.py --server.port 8502
           ```
        
        5. **Streamlitキャッシュをクリア**
           ```bash
           rm -rf ~/.streamlit/cache/
           ```
        """)
    
    # 解析結果の表示
    if 'analysis_result' in st.session_state and st.session_state['analysis_result']:
        st.markdown("---")
        st.header("📊 解析結果")
        
        result = st.session_state['analysis_result']
        
        # 結果を3カラムで表示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("プロセス")
            for p in result.get('processes', []):
                st.write(f"• {p.get('name', '')}")
                if p.get('description'):
                    st.caption(p.get('description'))
        
        with col2:
            st.subheader("データストア")
            for d in result.get('data_stores', []):
                st.write(f"• {d.get('name', '')}")
                if d.get('description'):
                    st.caption(d.get('description'))
        
        with col3:
            st.subheader("外部エンティティ")
            for e in result.get('external_entities', []):
                st.write(f"• {e.get('name', '')}")
                if e.get('description'):
                    st.caption(e.get('description'))
        
        # 概要
        st.markdown("### 📝 システム概要")
        st.info(result.get('summary', '概要なし'))
        
        # JSONダウンロード
        st.download_button(
            "📥 解析結果をダウンロード (JSON)",
            json.dumps(result, ensure_ascii=False, indent=2),
            "analysis_result.json",
            "application/json"
        )

if __name__ == "__main__":
    main()