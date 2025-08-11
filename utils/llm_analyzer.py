import os
import json
import re
from openai import OpenAI
from typing import Dict, Any, Union


class LLMAnalyzer:
    """画像→構造抽出→Markdown箇条書き概要の2段階。Responses API優先、Chat Completionsにフォールバック。"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません")
        self.client = OpenAI(api_key=api_key)
        # GPT-5は未提供のため gpt-4o を利用（画像入力対応）
        self.model = "gpt-4o"

    # ========= 1) 画像→構造抽出（JSON） =========
    def analyze_image(self, image_base64: str) -> Dict[str, Any]:
        """
        画像を解析して DFD/Simulink 図の構造を抽出（Responses API）
        戻り値: {
            processes: [{id,name,description}],
            data_stores: [{id,name,description}],
            external_entities: [{id,name,description}],
            data_flows: [{id,from,to,data}],
            system_overview: str
        }
        """
        instructions = r"""
あなたはデータフローダイアグラム/Simulink/ブロック図の読解専門家です。
与えられた「画像のみ」を根拠に、以下の構造を**純粋なJSON**で返してください。
- 入出力ノード（丸/端点/Source/Sink）
- 処理ブロック（矩形/楕円）とラベル（例: 処理1）
- データストア/メモリ/DB（円筒/二重線/開いた箱）
- 矢印の向きと接続（分岐/並列/合流/循環）

不明な名称は "名称不明" とする。画像に無い内容は推測しない。

JSONスキーマ:
{
  "processes": [{"id":"P1","name":"文字列","description":"文字列"}],
  "data_stores": [{"id":"D1","name":"文字列","description":"文字列"}],
  "external_entities": [{"id":"E1","name":"文字列","description":"文字列"}],
  "data_flows": [{"id":"F1","from":"ID","to":"ID","data":"文字列"}],
  "system_overview": "文字列"
}

出力はこのJSON**のみ**。前置き/後置き/注釈は禁止。
        """.strip()

        try:
            resp = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "画像から図形要素と接続を抽出し、スキーマ通りのJSONだけを返してください。"
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{image_base64}"
                        }
                    ]
                }],
            )
            out = resp.output_text  # JSON想定
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                s, e = out.find("{"), out.rfind("}")
                if s != -1 and e != -1:
                    return json.loads(out[s:e + 1])
                raise ValueError(f"モデル出力がJSONではありません: {out[:200]}")

        except AttributeError:
            # ライブラリが古い/環境差異で Responses 未対応の場合
            print("responses.create APIが利用できないため、chat.completions.createを使用します")
            return self._analyze_image_fallback(image_base64)
        except Exception as e:
            raise Exception(f"画像解析中にエラーが発生しました: {str(e)}")

    def _analyze_image_fallback(self, image_base64: str) -> Dict[str, Any]:
        """Chat Completions でのフォールバック（画像→JSON）"""
        prompt = r"""
あなたはDFD/Simulink図の読解専門家です。画像だけを根拠に、次のJSONスキーマで**純粋なJSONのみ**を返してください。
{
  "processes": [{"id":"P1","name":"文字列","description":"文字列"}],
  "data_stores": [{"id":"D1","name":"文字列","description":"文字列"}],
  "external_entities": [{"id":"E1","name":"文字列","description":"文字列"}],
  "data_flows": [{"id":"F1","from":"ID","to":"ID","data":"文字列"}],
  "system_overview": "文字列"
}
不明な名称は "名称不明"。推測はしない。前置き/後置きは禁止。
        """.strip()

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }],
            max_tokens=2000,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)

    # ========= 2) 構造JSON→Markdown箇条書き概要 =========
    def generate_summary(self, source: Union[str, Dict[str, Any]]) -> str:
        """
        入力（SimulinkのMDLテキスト、構造テキスト、または既存の解析JSON）をもとに、
        日本語の箇条書き概要（Markdownのみ、見出しなし）を生成する。
        """
        # 入力の種別に応じて説明テキストを作る
        if isinstance(source, dict):
            user_payload = json.dumps(source, ensure_ascii=False)
            input_descriptor = "解析JSON（要素・接続の構造）"
        else:
            user_payload = str(source)
            input_descriptor = "SimulinkのMDLテキスト/構造テキスト"

        instructions = r"""
# Simulink/DFD 図の要約生成（指定フォーマット厳守）

あなたはシステム解説書の技術ライターです。以下のテンプレートに“完全一致”させて、
与えられた内容をもとに簡潔な概要を作成してください。句読点・改行・ circled 数字の体裁を厳守します。

テンプレート:
概要
以下に本システムの概要を示す。
① モデル化対象
<1,2行で記述>

② モデル化の範囲・抽象度
<1,2行で記述>

③ モデル化した機能
<機能1を1,2行で>
<機能2を1,2行で>
<機能3（任意）を1,2行で>

制約:
- 箇条書き(ハイフン・番号)やMarkdown見出し(#)は使わない。
- 不明は「名称不明」。入力に無い内容は推測しない。
- 名詞止めを基本とし、冗長な修飾は避ける。
- 各見出し直後に必ず改行を入れる（例: 「① モデル化対象\n<内容>」）。見出しと内容を同じ行に書かない。
        """.strip()

        model_input = (
            f"次の{input_descriptor}の内容に基づき、テンプレートを満たす要約を作成してください。\n\n" + user_payload
        )

        try:
            resp = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=model_input,
            )
            return self._format_to_overview_template(resp.output_text)

        except AttributeError:
            print("responses.create APIが利用できないため、chat.completions.createを使用します")
            return self._generate_summary_fallback(source)
        except Exception as e:
            raise Exception(f"概要文章生成中にエラーが発生しました: {str(e)}")

    def _generate_summary_fallback(self, source: Union[str, Dict[str, Any]]) -> str:
        """Chat Completions でのフォールバック（テキスト/JSON → Markdown箇条書き概要）"""
        instructions = r"""
# Simulink/DFD 図の要約生成（指定フォーマット厳守）
以下のテンプレート通りに出力。余計な文字・記号・見出し・前置きを付けない。

テンプレート:
概要
以下に本システムの概要を示す。
① モデル化対象
<1,2行で記述>

② モデル化の範囲・抽象度
<1,2行で記述>

③ モデル化した機能
<機能1を1,2行で>
<機能2を1,2行で>
<機能3（任意）を1,2行で>

ルール:
- circled 数字 ①/②/③ を必ず使う。見出し語は正確に記載。
- 不明は「名称不明」。入力に無い内容は推測しない。
        """.strip()

        if isinstance(source, dict):
            payload = json.dumps(source, ensure_ascii=False)
            descriptor = "解析JSON"
        else:
            payload = str(source)
            descriptor = "MDL/構造テキスト"

        user = (
            f"次の{descriptor}の内容に基づき、上記テンプレートの形式で要約を作成してください。\n\n" + payload
        )

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": user},
            ],
            max_tokens=800,
            temperature=0.2,
        )
        return self._format_to_overview_template(resp.choices[0].message.content)

    # ========= 4) 出力フォーマットの最終整形 =========
    def _format_to_overview_template(self, text: str) -> str:
        """
        指定された改行パターンに完全一致させて整形:
        概要[改行]
        以下に本システムの概要を示す。[改行]
        [改行]
        ① モデル化対象[改行]
        内容行[改行]
        [改行]
        ② モデル化の範囲・抽象度[改行]
        内容行[改行]
        [改行]
        ③ モデル化した機能[改行]
        内容行[改行]
        """
        if not text:
            return text

        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        # 全体を再構築
        result_lines = []

                # 先頭部分を固定フォーマットで追加
        result_lines.append("概要")
        result_lines.append("以下に本システムの概要を示す。")
        result_lines.append("")  # 空行

        # ①②③セクションを順次処理
        sections = re.split(r"(①\s*モデル化対象|②\s*モデル化の範囲・抽象度|③\s*モデル化した機能)", normalized)

        current_section = None
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # 見出し判定
            if "① モデル化対象" in section:
                current_section = "① モデル化対象"
                # 見出しとその内容を一度に処理
                result_lines.append(current_section)
                # 次のセクション（内容）を取得
                if i + 1 < len(sections):
                    content = sections[i + 1].strip()
                    if content:
                        # 内容を整形
                        content_lines = []
                        for line in content.split('\n'):
                            line = line.strip()
                            if line:
                                line = re.sub(r"^[\-•\d\.\s]+", "", line)
                                if line:
                                    content_lines.append(line)
                        if content_lines:
                            combined_content = ' '.join(content_lines)
                            result_lines.append(combined_content)
                result_lines.append("")  # セクション後の空行

            elif "② モデル化の範囲・抽象度" in section:
                current_section = "② モデル化の範囲・抽象度"
                result_lines.append(current_section)
                # 次のセクション（内容）を取得
                if i + 1 < len(sections):
                    content = sections[i + 1].strip()
                    if content:
                        # 内容を整形
                        content_lines = []
                        for line in content.split('\n'):
                            line = line.strip()
                            if line:
                                line = re.sub(r"^[\-•\d\.\s]+", "", line)
                                if line:
                                    content_lines.append(line)
                        if content_lines:
                            combined_content = ' '.join(content_lines)
                            result_lines.append(combined_content)
                result_lines.append("")  # セクション後の空行

            elif "③ モデル化した機能" in section:
                current_section = "③ モデル化した機能"
                result_lines.append(current_section)
                # 次のセクション（内容）を取得
                if i + 1 < len(sections):
                    content = sections[i + 1].strip()
                    if content:
                        # 内容を整形
                        content_lines = []
                        for line in content.split('\n'):
                            line = line.strip()
                            if line:
                                line = re.sub(r"^[\-•\d\.\s]+", "", line)
                                if line:
                                    content_lines.append(line)
                        if content_lines:
                            combined_content = ' '.join(content_lines)
                            result_lines.append(combined_content)

        final_result = '\n'.join(result_lines)
        return final_result

    # ========= 3) 解析結果の妥当性チェック =========
    def validate_analysis(self, analysis_result: Dict[str, Any]) -> bool:
        """抽出JSONの最低限の妥当性チェック"""
        required = ['processes', 'data_stores', 'external_entities', 'data_flows', 'system_overview']
        if not all(k in analysis_result for k in required):
            return False
        if len(analysis_result.get('processes', [])) == 0:
            return False
        if len(analysis_result.get('data_flows', [])) == 0:
            return False
        return True
