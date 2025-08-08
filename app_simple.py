"""
シンプル版：データフローダイアグラム解析ツール
アップロード問題を解決するための軽量版
"""

import streamlit as st
import os
import base64
import json
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI

# 環境変数の読み込み
load_dotenv()

# ページ設定（シンプルに）
st.set_page_config(
    page_title="DFD解析ツール",
    layout="wide"
)

st.title("データフローダイアグラム解析ツール（軽量版）")

# OpenAIクライアントの初期化
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("APIキーが設定されていません")
        return None
    return OpenAI(api_key=api_key)

# 画像処理関数（シンプル版）
def process_image_simple(uploaded_file):
    """画像をBase64エンコード（シンプル版）"""
    try:
        # バイトデータを直接Base64エンコード
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode('utf-8')
    except Exception as e:
        st.error(f"画像処理エラー: {e}")
        return None

# LLM解析関数（シンプル版）
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
            model="gpt-4o-mini",  # より軽量なモデルを使用
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

# Simulink生成（シンプル版）
def generate_simulink_simple(analysis_result):
    """簡易Simulink MDL生成"""
    if not analysis_result:
        return ""
    
    mdl = "Model {\n  Name 'DataFlowDiagram'\n  System {\n"
    
    # プロセスをブロックとして追加
    for i, process in enumerate(analysis_result.get('processes', [])):
        mdl += f"    Block {{\n      Name '{process.get('name', f'Process{i}')}'\n      BlockType 'SubSystem'\n    }}\n"
    
    mdl += "  }\n}"
    return mdl

# メイン処理
def main():
    # セッション状態の初期化
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    # サイドバー
    with st.sidebar:
        st.header("オプション")
        use_simple_upload = st.checkbox("シンプルアップロードを使用", value=True)
        max_file_size = st.slider("最大ファイルサイズ(MB)", 1, 10, 5)
    
    # ファイルアップロード部分
    st.header("📤 画像アップロード")
    
    if use_simple_upload:
        # 方法1: HTMLの<input>タグを使った軽量アップロード
        st.markdown("### 軽量アップロード方式")
        uploaded_file = st.file_uploader(
            "画像を選択（軽量版）",
            type=['png', 'jpg', 'jpeg'],
            key="simple_uploader",
            help=f"最大{max_file_size}MBまで",
            accept_multiple_files=False,  # 単一ファイルのみ
            label_visibility="collapsed"   # ラベルを隠してシンプルに
        )
    else:
        # 方法2: 通常のStreamlitアップローダー（フル機能）
        st.markdown("### 標準アップロード方式")
        uploaded_file = st.file_uploader(
            "データフローダイアグラムを選択",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=False
        )
    
    if uploaded_file is not None:
        # ファイルサイズチェック
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > max_file_size:
            st.error(f"ファイルサイズが大きすぎます（{file_size_mb:.1f}MB）。{max_file_size}MB以下にしてください。")
            return
        
        # 画像表示
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("アップロード画像")
            st.image(uploaded_file, use_column_width=True)
        
        # 解析ボタン
        if st.button("🔍 解析開始", type="primary"):
            with st.spinner("解析中..."):
                # OpenAIクライアント取得
                client = get_openai_client()
                
                # 画像処理
                image_base64 = process_image_simple(uploaded_file)
                
                # LLM解析
                if image_base64:
                    analysis_result = analyze_with_llm(client, image_base64)
                    st.session_state.analysis_result = analysis_result
                    
                    if analysis_result:
                        st.success("✅ 解析完了！")
    
    # 結果表示
    if st.session_state.analysis_result:
        st.header("📊 解析結果")
        
        result = st.session_state.analysis_result
        
        # タブで結果を表示
        tab1, tab2, tab3 = st.tabs(["概要", "詳細", "Simulink"])
        
        with tab1:
            st.write("### システム概要")
            st.write(result.get('summary', '概要なし'))
        
        with tab2:
            st.write("### プロセス")
            for p in result.get('processes', []):
                st.write(f"- {p.get('name', '')}: {p.get('description', '')}")
            
            st.write("### データストア")
            for d in result.get('data_stores', []):
                st.write(f"- {d.get('name', '')}: {d.get('description', '')}")
            
            st.write("### 外部エンティティ")
            for e in result.get('external_entities', []):
                st.write(f"- {e.get('name', '')}: {e.get('description', '')}")
        
        with tab3:
            simulink_code = generate_simulink_simple(result)
            st.text_area("Simulink MDL", simulink_code, height=300)
            
            # ダウンロードボタン
            st.download_button(
                "📥 MDLファイルをダウンロード",
                simulink_code,
                "model.mdl",
                "text/plain"
            )

if __name__ == "__main__":
    main()