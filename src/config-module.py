import json
import os

class AppConfig:
    def __init__(self, config_path='configs/config.json'):
        """
        アプリケーション設定クラスの初期化
        
        Args:
            config_path (str): 設定ファイルのパス
        """
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """
        設定をJSONファイルからロード
        
        Returns:
            dict: アプリケーション設定
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._create_default_config()
    
    def _create_default_config(self):
        """
        デフォルト設定を作成
        
        Returns:
            dict: デフォルトの設定
        """
        default_config = {
            'default_folder': '',
            'max_filename_length': 255,
            'allowed_extensions': ['.jpg', '.jpeg', '.png', '.webp'],
            'backup_folder': 'backup'
        }
        self.save_config(default_config)
        return default_config
    
    def get(self, key, default=None):
        """
        設定値を取得
        
        Args:
            key (str): 設定キー
            default (any, optional): デフォルト値
        
        Returns:
            any: 設定値
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        設定値を更新
        
        Args:
            key (str): 設定キー
            value (any): 設定値
        """
        self.config[key] = value
        self.save_config()
    
    def save_config(self, config=None):
        """
        設定をJSONファイルに保存
        
        Args:
            config (dict, optional): 保存する設定. デフォルトは現在の設定.
        """
        if config is None:
            config = self.config
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
