import json
from typing import Dict, List, Any
import xml.etree.ElementTree as ET
from datetime import datetime

class SimulinkGenerator:
    """Simulink MDL形式生成クラス"""
    
    def __init__(self):
        """初期化"""
        self.block_counter = 0
        self.line_counter = 0
    
    def generate_simulink(self, analysis_result: Dict[str, Any]) -> str:
        """
        解析結果からSimulink MDL形式のコードを生成
        
        Args:
            analysis_result: DFD解析結果の辞書
            
        Returns:
            Simulink MDL形式の文字列
        """
        # MDLファイルのヘッダー
        mdl_content = self._generate_header()
        
        # ブロックダイアグラムの開始
        mdl_content += self._generate_block_diagram_start()
        
        # 各要素をSimulinkブロックに変換
        blocks = []
        connections = []
        
        # プロセスをSubsystemブロックとして追加
        process_blocks = self._generate_process_blocks(analysis_result.get('processes', []))
        blocks.extend(process_blocks)
        
        # データストアをData Store Memoryブロックとして追加
        datastore_blocks = self._generate_datastore_blocks(analysis_result.get('data_stores', []))
        blocks.extend(datastore_blocks)
        
        # 外部エンティティをInport/Outportブロックとして追加
        entity_blocks = self._generate_entity_blocks(analysis_result.get('external_entities', []))
        blocks.extend(entity_blocks)
        
        # データフローを接続線として追加
        data_flows = analysis_result.get('data_flows', [])
        connections = self._generate_connections(data_flows)
        
        # ブロックをMDLに追加
        for block in blocks:
            mdl_content += block + "\n"
        
        # 接続線をMDLに追加
        for connection in connections:
            mdl_content += connection + "\n"
        
        # ブロックダイアグラムの終了
        mdl_content += self._generate_block_diagram_end()
        
        return mdl_content
    
    def _generate_header(self) -> str:
        """MDLファイルのヘッダーを生成"""
        header = f"""Model {{
  Name                    "DataFlowDiagram"
  Version                 10.0
  SaveTime                "{datetime.now().strftime('%a %b %d %H:%M:%S %Y')}"
  SaveFormat              "Structure"
  PreLoadFcn              ""
  PostLoadFcn             ""
  Model{{
    ModelBrowserVisibility  on
    ModelBrowserWidth       200
  }}
  SimulationMode          "normal"
  StartTime               "0.0"
  StopTime                "10.0"
  Solver                  "ode45"
  
"""
        return header
    
    def _generate_block_diagram_start(self) -> str:
        """ブロックダイアグラムセクションの開始"""
        return """  System {
    Name                    "DataFlowDiagram"
    Location                [100, 100, 900, 600]
    Open                    on
    ToolBar                 on
    StatusBar               on
    ScreenColor             "white"
    PaperOrientation        "landscape"
    PaperPositionMode       "auto"
    PaperType               "A4"
    ZoomFactor              "100"
    
"""
    
    def _generate_block_diagram_end(self) -> str:
        """ブロックダイアグラムセクションの終了"""
        return """  }
}
"""
    
    def _generate_process_blocks(self, processes: List[Dict[str, Any]]) -> List[str]:
        """プロセスをSubsystemブロックとして生成"""
        blocks = []
        for i, process in enumerate(processes):
            self.block_counter += 1
            block_name = process.get('name', f"Process_{i+1}")
            block_id = process.get('id', f"P{i+1}")
            description = process.get('description', '')
            
            # 座標を計算（グリッド配置）
            x_pos = 100 + (i % 4) * 150
            y_pos = 100 + (i // 4) * 100
            
            block = f"""    Block {{
      BlockType               "SubSystem"
      Name                    "{block_name}"
      SID                     "{self.block_counter}"
      Tag                     "{block_id}"
      Description             "{description}"
      Position                [{x_pos}, {y_pos}, {x_pos+100}, {y_pos+50}]
      BackgroundColor         "lightBlue"
      ShowName                on
      TreatAsAtomicUnit       off
      MinAlgLoopOccurrences   off
      System {{
        Name                    "{block_name}"
        Location                [200, 200, 600, 400]
        Open                    off
      }}
    }}"""
            blocks.append(block)
        
        return blocks
    
    def _generate_datastore_blocks(self, data_stores: List[Dict[str, Any]]) -> List[str]:
        """データストアをData Store Memoryブロックとして生成"""
        blocks = []
        for i, store in enumerate(data_stores):
            self.block_counter += 1
            block_name = store.get('name', f"DataStore_{i+1}")
            block_id = store.get('id', f"D{i+1}")
            description = store.get('description', '')
            
            # 座標を計算
            x_pos = 500 + (i % 2) * 150
            y_pos = 100 + i * 80
            
            block = f"""    Block {{
      BlockType               "DataStoreMemory"
      Name                    "{block_name}"
      SID                     "{self.block_counter}"
      Tag                     "{block_id}"
      Description             "{description}"
      Position                [{x_pos}, {y_pos}, {x_pos+120}, {y_pos+40}]
      BackgroundColor         "yellow"
      ShowName                on
      DataStoreName           "{block_name}_data"
      InitialValue            "0"
    }}"""
            blocks.append(block)
        
        return blocks
    
    def _generate_entity_blocks(self, entities: List[Dict[str, Any]]) -> List[str]:
        """外部エンティティをInport/Outportブロックとして生成"""
        blocks = []
        for i, entity in enumerate(entities):
            self.block_counter += 1
            block_name = entity.get('name', f"Entity_{i+1}")
            block_id = entity.get('id', f"E{i+1}")
            description = entity.get('description', '')
            
            # エンティティの役割に応じてInportまたはOutportを選択
            # ここでは簡単のため、偶数番目をInport、奇数番目をOutportとする
            block_type = "Inport" if i % 2 == 0 else "Outport"
            
            # 座標を計算
            if block_type == "Inport":
                x_pos = 50
                y_pos = 200 + i * 60
            else:
                x_pos = 750
                y_pos = 200 + (i-1) * 60
            
            block = f"""    Block {{
      BlockType               "{block_type}"
      Name                    "{block_name}"
      SID                     "{self.block_counter}"
      Tag                     "{block_id}"
      Description             "{description}"
      Position                [{x_pos}, {y_pos}, {x_pos+80}, {y_pos+30}]
      BackgroundColor         "green"
      ShowName                on
      Port                    "{i+1}"
    }}"""
            blocks.append(block)
        
        return blocks
    
    def _generate_connections(self, data_flows: List[Dict[str, Any]]) -> List[str]:
        """データフローを接続線として生成"""
        connections = []
        for i, flow in enumerate(data_flows):
            self.line_counter += 1
            from_block = flow.get('from', '')
            to_block = flow.get('to', '')
            data_label = flow.get('data', '')
            
            # 接続線の生成
            connection = f"""    Line {{
      SrcBlock                "{from_block}"
      SrcPort                 1
      DstBlock                "{to_block}"
      DstPort                 1
      Name                    "{data_label}"
    }}"""
            connections.append(connection)
        
        return connections
    
    def validate_mdl(self, mdl_content: str) -> bool:
        """
        生成されたMDLコードの妥当性をチェック
        
        Args:
            mdl_content: MDL形式の文字列
            
        Returns:
            妥当な場合True
        """
        # 基本的な構造チェック
        if "Model {" not in mdl_content:
            return False
        if "System {" not in mdl_content:
            return False
        if not mdl_content.strip().endswith("}"):
            return False
        
        return True