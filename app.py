import streamlit as st
from dotenv import load_dotenv
from utils.llm_analyzer import LLMAnalyzer

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

st.header("入力テキスト")

input_text = st.text_area(
    label="",
    value=st.session_state.get("input_text", ""),
    height=300,
    key="input_text",
    placeholder=(
        "SimulinkのMDLテキスト、またはブロック/接続の構造テキストを貼り付けてください。\n"
        "例) Block/Line定義や、{processes:[...], data_flows:[...]} のような抽出済みJSON/テキストなど"
    ),
    label_visibility="collapsed",
)

if st.button("📝 要約生成", type="primary", use_container_width=True):
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

# 出力: 日本語の要約（Markdownのみ）
st.header("概要文章")
if 'summary_text' in st.session_state and st.session_state['summary_text']:
    try:
        st.markdown(st.session_state['summary_text'])
    except TypeError:
        st.markdown(st.session_state['summary_text'])

    copy_button(
        text=st.session_state['summary_text'],
        label="📋 概要をコピー",
        key="copy-summary"
    )
