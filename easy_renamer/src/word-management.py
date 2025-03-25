import json
import os

class WordManager:
    def __init__(self, file_path='configs/word_candidates.json'):
        """
        ワード管理クラスの初期化
        
        Args:
            file_path (str): 候補ワードを保存するJSONファイルのパス
        """
        self.file_path = file_path
        self.candidates = self.load_candidates()
    
    def load_candidates(self):
        """
        候補ワードをJSONファイルからロード
        
        Returns:
            dict: カテゴリごとの候補ワード
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'characters': [],
                'styles': [],
                'templates': []
            }
    
    def add_candidate(self, category, word):
        """
        新しい候補ワードを追加
        
        Args:
            category (str): カテゴリ名
            word (str): 追加するワード
        """
        if category not in self.candidates:
            self.candidates[category] = []
        
        if word not in self.candidates[category]:
            self.candidates[category].append(word)
            self.save_candidates()
    
    def remove_candidate(self, category, word):
        """
        候補ワードを削除
        
        Args:
            category (str): カテゴリ名
            word (str): 削除するワード
        """
        if category in self.candidates and word in self.candidates[category]:
            self.candidates[category].remove(word)
            self.save_candidates()
    
    def get_candidates(self, category=None):
        """
        候補ワードを取得
        
        Args:
            category (str, optional): 特定のカテゴリ名. デフォルトはNone.
        
        Returns:
            list or dict: 候補ワード
        """
        if category:
            return self.candidates.get(category, [])
        return self.candidates
    
    def save_candidates(self):
        """
        候補ワードをJSONファイルに保存
        """
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.candidates, f, ensure_ascii=False, indent=4)
