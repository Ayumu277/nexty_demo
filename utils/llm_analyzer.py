import os
import json
from openai import OpenAI
from typing import Dict, Any


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
    def generate_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        解析JSONをもとに、画像見本のような「箇条書きの概要文章（Markdown）」を生成。
        出力は **以下フォーマットのみ**：
        ### 概要文章
        - ...
        - ...
        - ...
        - ...
        - ...
        """
        # Markdownプロンプト（指示はinstructionsへ、データはinputへ渡す）
        instructions = r"""
# 画像→Simulink/DFD 図の**概要文章** 生成プロンプト

あなたは**システムブロック図/DFD/Simulink 図の要約ライター**です。
与えられた解析JSON（要素と接続）だけを根拠に、図の構造を要約します。
**中間の推論や根拠は出力しない**でください（内部でのみ実施）。

## 出力ガイドライン
- 出力は**日本語の箇条書き（最大5行）**、各行**1文**、**50〜120字**を目安。
- **1行目**: 図の目的と全体像（何を、どの経路で処理するシステムか）。
- **2行目**: 入力から初期処理/分岐（並列の有無）。
- **3行目**: データ保存（データストア）/中間結果の扱い。
- **4行目**: 合流・統合処理や終盤処理の役割。
- **5行目(任意)**: 出力の集約・成果物、構造的特徴（並列/効率/冗長性など）。
- 図中のラベル（例: 処理1、データストア2）は**原文どおり**に用いる。
- 不明は**「名称不明」**と記載。画像に無い内容は**推測しない**。

## 出力フォーマット（厳守）
以下のMarkdownのみを出力すること。前置き/後置き/見出し以外の余計な文章を禁止。

- （1行目：全体像）
- （2行目：入力→初期処理/分岐）
- （3行目：ストア保存/供給）
- （4行目：統合処理/終盤処理）
- （5行目：出力の集約・特徴）
        """.strip()

        input_text = (
            "次の解析JSONを基に、上記ガイドライン/フォーマットに厳密に従って出力してください。\n\n"
            + json.dumps(analysis_result, ensure_ascii=False)
        )

        try:
            resp = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_text,
            )
            return resp.output_text

        except AttributeError:
            print("responses.create APIが利用できないため、chat.completions.createを使用します")
            return self._generate_summary_fallback(analysis_result)
        except Exception as e:
            raise Exception(f"概要文章生成中にエラーが発生しました: {str(e)}")

    def _generate_summary_fallback(self, analysis_result: Dict[str, Any]) -> str:
        """Chat Completions でのフォールバック（JSON→Markdown箇条書き概要）"""
        instructions = r"""
# 画像→Simulink/DFD 図の**概要文章** 生成プロンプト
（システムは日本語で出力。下記フォーマット以外を出さない）

### 出力ガイドライン
- 箇条書き最大5行、各行1文、50〜120字目安。
- 1行目: 全体像 / 2行目: 入力→初期処理 / 3行目: ストア / 4行目: 統合 / 5行目: 出力の特徴（任意）
- ラベルは原文どおり。不明は「名称不明」。推測しない。

### 出力フォーマット（厳守）
### 概要文章
- （1行目：全体像）
- （2行目：入力→初期処理/分岐）
- （3行目：ストア保存/供給）
- （4行目：統合処理/終盤処理）
- （5行目：出力の集約・特徴）
        """.strip()

        user = (
            "次の解析JSONを基に、上記フォーマットでMarkdownのみを出力してください。\n\n"
            + json.dumps(analysis_result, ensure_ascii=False)
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
