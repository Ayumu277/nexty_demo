"""
最小限のアップロードテスト
問題の切り分け用
"""

import streamlit as st

st.title("アップロードテスト")

# 最もシンプルなファイルアップロード
uploaded_file = st.file_uploader("ファイルを選択", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    st.success(f"ファイル名: {uploaded_file.name}")
    st.info(f"サイズ: {uploaded_file.size} bytes")
    
    # 画像を表示
    try:
        st.image(uploaded_file)
    except Exception as e:
        st.error(f"エラー: {e}")