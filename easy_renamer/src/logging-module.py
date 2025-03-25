import logging
import os
from datetime import datetime

class RenameToolError(Exception):
    """カスタム例外クラス"""
    pass

class AppLogger:
    def __init__(self, log_dir='logs'):
        """
        アプリケーションロガーの初期化
        
        Args:
            log_dir (str): ログディレクトリのパス
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # ログファイル名に日付を付与
        log_filename = f'rename_tool_{datetime.now().strftime("%Y%m%d")}.log'
        log_path = os.path.join(log_dir, log_filename)
        
        # ロガーの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, message):
        """
        情報レベルのログを記録
        
        Args:
            message (str): ログメッセージ
        """
        self.logger.info(message)
    
    def warning(self, message):
        """
        警告レベルのログを記録
        
        Args:
            message (str): ログメッセージ
        """
        self.logger.warning(message)
    
    def error(self, message):
        """
        エラーレベルのログを記録
        
        Args:
            message (str): ログメッセージ
        """
        self.logger.error(message)
