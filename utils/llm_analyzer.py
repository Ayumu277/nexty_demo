import os
import json
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
# Simulink/DFD 図の要約生成（日本語・箇条書きのみ）

あなたはシステムブロック図/DFD/Simulinkの要約ライターです。
与えられた入力だけを根拠に、システムの流れと構造を要約してください。
中間推論は出力せず、内部で行ってください。

出力ガイドライン:
- 日本語の箇条書き 3〜5 行、各行 1 文、50〜120 字目安
- 1行目: 目的と全体像 / 2行目: 入力→初期処理 / 3行目: ストア/中間結果 / 4行目: 統合・終盤処理 / 5行目(任意): 出力・特徴
- ラベル名は原文のまま。不明は「名称不明」。入力にない内容は推測しない。

厳守する出力形式:
- 箇条書きの Markdown のみ（先頭見出しや前置きは付けない）
        """.strip()

        model_input = (
            f"次の{input_descriptor}を要約してください。箇条書きのみで出力:\n\n" + user_payload
        )

        try:
            resp = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=model_input,
            )
            return resp.output_text

        except AttributeError:
            print("responses.create APIが利用できないため、chat.completions.createを使用します")
            return self._generate_summary_fallback(source)
        except Exception as e:
            raise Exception(f"概要文章生成中にエラーが発生しました: {str(e)}")

    def _generate_summary_fallback(self, source: Union[str, Dict[str, Any]]) -> str:
        """Chat Completions でのフォールバック（テキスト/JSON → Markdown箇条書き概要）"""
        instructions = r"""
# Simulink/DFD 図の要約生成（日本語・箇条書きのみ）
- 出力は箇条書き 3〜5 行、各行 1 文、50〜120 字目安。
- 見出しや前置きは付けない。Markdown の箇条書きのみ。
- ラベルは原文どおり。不明は「名称不明」。推測しない。
        """.strip()

        if isinstance(source, dict):
            payload = json.dumps(source, ensure_ascii=False)
            descriptor = "解析JSON"
        else:
            payload = str(source)
            descriptor = "MDL/構造テキスト"

        user = (
            f"次の{descriptor}を要約してください（箇条書きのみ）。\n\n" + payload
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
        return resp.choices[0].message.content

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
