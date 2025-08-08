import base64
from PIL import Image
import io
from typing import Union, BinaryIO

class ImageProcessor:
    """画像処理ユーティリティクラス"""
    
    def __init__(self, max_size: int = 10 * 1024 * 1024):
        """
        初期化
        
        Args:
            max_size: 最大ファイルサイズ（バイト）、デフォルト10MB
        """
        self.max_size = max_size
    
    def process_image(self, uploaded_file) -> str:
        """
        アップロードされた画像を処理してBase64エンコード
        
        Args:
            uploaded_file: Streamlitのアップロードファイルオブジェクト
            
        Returns:
            Base64エンコードされた画像文字列
        """
        # ファイルサイズチェック
        file_size = uploaded_file.size
        if file_size > self.max_size:
            raise ValueError(f"ファイルサイズが大きすぎます。最大{self.max_size // (1024*1024)}MBまでです。")
        
        # 画像を読み込み
        image = Image.open(uploaded_file)
        
        # RGB形式に変換（必要に応じて）
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        
        # 画像サイズを最適化（必要に応じてリサイズ）
        image = self._optimize_image_size(image)
        
        # Base64エンコード
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return img_base64
    
    def _optimize_image_size(self, image: Image.Image, max_width: int = 2048, max_height: int = 2048) -> Image.Image:
        """
        画像サイズを最適化
        
        Args:
            image: PIL Imageオブジェクト
            max_width: 最大幅
            max_height: 最大高さ
            
        Returns:
            最適化されたPIL Imageオブジェクト
        """
        width, height = image.size
        
        # 最大サイズを超える場合はリサイズ
        if width > max_width or height > max_height:
            # アスペクト比を保持してリサイズ
            aspect_ratio = width / height
            if width > height:
                new_width = min(width, max_width)
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = min(height, max_height)
                new_width = int(new_height * aspect_ratio)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def save_image(self, image_data: Union[str, bytes], output_path: str):
        """
        画像データをファイルに保存
        
        Args:
            image_data: Base64エンコードされた画像データまたはバイトデータ
            output_path: 保存先パス
        """
        if isinstance(image_data, str):
            # Base64デコード
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # ファイルに保存
        with open(output_path, 'wb') as f:
            f.write(image_bytes)