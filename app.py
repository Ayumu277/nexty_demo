import streamlit as st
from dotenv import load_dotenv
from utils.image_processor import ImageProcessor
from utils.llm_analyzer import LLMAnalyzer
from utils.simulink_generator import SimulinkGenerator

# 追加
import json
import streamlit.components.v1 as components

# ---- クリップボードコピー用の共通ボタン（onclickを使わず安全に実装） ----
def copy_button(text: str, label: str, key: str):
    """
    押したら即クリップボードへコピーするボタン（components.html内でJSのイベントを登録）
    """
    # JSON 文字列としてエスケープ（改行やクォートを安全にJSへ埋め込む）
    payload = json.dumps(text if text is not None else "")
    # 万一 </script> を含む場合の保険
    payload = payload.replace("</script>", "<\\/script>")

    components.html(
        f"""
        <div>
          <button id="btn-{key}" style="
            padding:8px 12px;
            border-radius:8px;
            cursor:pointer;
            border:1px solid #DDD;
            background:white;
          ">{label}</button>

          <script>
            (function(){{
              const btn = document.getElementById('btn-{key}');
              const payload = {payload};  // JSの文字列として安全に埋め込み済み

              btn.addEventListener('click', async () => {{
                try {{
                  await navigator.clipboard.writeText(payload);
                }} catch (e) {{
                  // Fallback（古いブラウザ/権限無いとき）
                  const ta = document.createElement('textarea');
                  ta.value = payload;
                  document.body.appendChild(ta);
                  ta.select();
                  document.execCommand('copy');
                  document.body.removeChild(ta);
                }}
                const old = btn.innerText;
                btn.innerText = '✅ コピーしました';
                setTimeout(() => btn.innerText = old, 1200);
              }});
            }})();
          </script>
        </div>
        """,
        height=60,
    )


# 環境変数の読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="データフローダイアグラム解析ツール",
    page_icon="🔄",
    layout="wide"
)

# タイトルと説明
st.title("データフローダイアグラム解析ツール")
st.markdown("""
このツールは、データフローダイアグラムの画像をアップロードすると、
AIが画像を解析してSimulink形式への変換と概要文章の生成を行います。
""")

# サイドバーの設定
with st.sidebar:
    st.header("設定")
    st.info("""
    ### 使い方
    1. データフローダイアグラムの画像をアップロード
    2. 「解析開始」ボタンをクリック
    3. 解析結果を確認・コピー
    """)

# メインエリア
st.header("画像アップロード")

# ファイルアップローダー
uploaded_file = st.file_uploader(
    "データフローダイアグラムの画像を選択してください",
    type=['png', 'jpg', 'jpeg'],
    help="PNG, JPG, JPEG形式の画像ファイルをアップロードしてください（最大10MB）"
)

if uploaded_file is not None:
    # アップロードされた画像を表示
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("アップロードした画像")
        st.image(uploaded_file, caption="データフローダイアグラム", use_column_width=True)

    # Session Stateに画像を保存
    if 'uploaded_image' not in st.session_state:
        st.session_state['uploaded_image'] = uploaded_file

    # 解析ボタン
    if st.button("🔍 解析開始", type="primary", use_container_width=True):
        with st.spinner("解析中... しばらくお待ちください"):
            try:
                # 各処理クラスのインスタンス化
                image_processor = ImageProcessor()
                llm_analyzer = LLMAnalyzer()
                simulink_generator = SimulinkGenerator()

                # 画像の前処理
                processed_image = image_processor.process_image(uploaded_file)

                # プログレスバー表示
                progress_bar = st.progress(0)
                status_text = st.empty()

                # LLMによる解析
                status_text.text("画像を解析中...")
                progress_bar.progress(33)
                analysis_result = llm_analyzer.analyze_image(processed_image)

                # Simulink形式への変換
                status_text.text("Simulink形式に変換中...")
                progress_bar.progress(66)
                simulink_code = simulink_generator.generate_simulink(analysis_result)

                # 概要文章の生成
                status_text.text("概要文章を生成中...")
                progress_bar.progress(100)
                summary_text = llm_analyzer.generate_summary(analysis_result)

                # 結果をSession Stateに保存
                st.session_state['analysis_result'] = analysis_result
                st.session_state['simulink_code'] = simulink_code
                st.session_state['summary_text'] = summary_text

                # プログレスバーをクリア
                progress_bar.empty()
                status_text.empty()

                st.success("✅ 解析が完了しました！")

            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.stop()

# 解析結果の表示
if 'analysis_result' in st.session_state:
    st.header("解析結果")

    # 2カラムレイアウト
    col1, col2 = st.columns([1, 1])


    with col1:
        st.subheader("Simulink MDL形式")
        if 'simulink_code' in st.session_state:
            # 編集できるテキストエリア
            st.text_area(
                label="",  # ← 空にする
                value=st.session_state['simulink_code'],
                height=400,
                disabled=False,
                key="simulink_text_area",
                label_visibility="collapsed",  # ← ラベル自体を非表示
            )

            # 直近の編集内容をコピー（テキストエリアを優先）
            current_mdl = st.session_state.get('simulink_text_area', st.session_state['simulink_code'])
            copy_button(
                text=current_mdl,
                label="📋 Simulinkコードをコピー",
                key="copy-mdl"
            )

    with col2:
        st.subheader("概要文章")
        if 'summary_text' in st.session_state:
            # 表示（古いStreamlit互換のフォールバックあり）
            try:
                with st.container(height=400):
                    st.markdown(st.session_state['summary_text'])
            except TypeError:
                st.markdown(st.session_state['summary_text'])

            # 押したら即コピー
            copy_button(
                text=st.session_state['summary_text'],
                label="📋 概要をコピー",
                key="copy-summary"
            )
