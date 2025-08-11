import streamlit as st
from dotenv import load_dotenv
from utils.llm_analyzer import LLMAnalyzer
import html

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
    page_title="Simulink要約生成ツール",
    page_icon="📝",
    layout="wide"
)

# 全体の背景色とスタイルを白ベースに変更
st.markdown("""
<style>
    .stApp {
        background-color: #FFFFFF;
    }
    .main .block-container {
        background-color: #FFFFFF;
        padding-top: 2rem;
    }
    /* ヘッダとサイドバーを自然な白基調に */
    [data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E6E6E6;
    }
    [data-testid="stSidebar"] {
        background-color: #F7F7F7 !important;
        color: #000000;
    }
    .stTextArea > div > div > textarea {
        background-color: #F5F5F5;
        color: #000000;
        border: 1px solid #CCCCCC;
    }
    .stMarkdown {
        color: #000000;
    }
    h1, h2, h3 {
        color: #000000;
    }
    .stButton > button {
        background-color: #F0F0F0;
        color: #000000;
        border: 1px solid #CCCCCC;
    }
    .stInfo {
        background-color: #F8F9FA;
        color: #000000;
    }
    p, div, span {
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)

# タイトルと説明
st.title("Simulink要約生成ツール")
st.markdown(
    """
SimulinkのMDLテキスト、またはブロック・接続の構造テキストを貼り付けて、
AIが日本語の概要（箇条書き）を生成します。
"""
)

# サイドバーの設定
with st.sidebar:
    st.header("使い方")
    st.info(
        """
        1. SimulinkのMDLや構造テキストを貼り付け
        2. 「要約生成」をクリック
        3. 生成された日本語の概要をコピー
        """
    )

# 2カラムレイアウト
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Simulink MDL形式")
    input_text = st.text_area(
        label="",
        value=st.session_state.get("input_text", ""),
        height=520,
        key="input_text",
        placeholder=(
            "SimulinkのMDLテキスト、またはブロック/接続の構造テキストを貼り付けてください。\n"
            "例) Block/Line定義や、{processes:[...], data_flows:[...]} のような抽出済みJSON/テキストなど"
        ),
        label_visibility="collapsed",
    )
    if st.button("📝 要約生成", type="primary", use_container_width=True, key="run-summary"):
        if not input_text or not input_text.strip():
            st.warning("入力テキストを貼り付けてください。")
        else:
            with st.spinner("要約を生成中..."):
                try:
                    llm_analyzer = LLMAnalyzer()
                    summary_text = llm_analyzer.generate_summary(input_text)
                    st.session_state['summary_text'] = summary_text
                    st.success("✅ 要約を生成しました！")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    st.stop()

with right_col:
    st.subheader("概要文章")
    if 'summary_text' in st.session_state and st.session_state['summary_text']:
        # 枠付きのシンプルな表示（余計なUIなし）
        safe_html = html.escape(st.session_state['summary_text'])
        st.markdown(
            f"""
            <div style="border:1px solid #E0E0E0; border-radius:8px; padding:16px; height:520px; overflow-y:auto; background:#FFFFFF;">
              <pre style="white-space:pre-wrap; word-wrap:break-word; margin:0; font-family:inherit; color:#000;">{safe_html}</pre>
            </div>
            """,
            unsafe_allow_html=True,
        )

        copy_button(
            text=st.session_state['summary_text'],
            label="📋 概要をコピー",
            key="copy-summary"
        )
    else:
        st.info("左のMDL/構造テキストを貼り付けて『要約生成』を押してください。")
