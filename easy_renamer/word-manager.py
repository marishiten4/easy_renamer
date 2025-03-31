import os
import json

class WordManager:
    def __init__(self, data_file="word_data.json"):
        self.data_file = data_file
        self.categories = {}
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
            except Exception as e:
                print(f"単語データの読み込みエラー: {str(e)}")
                self.initialize_data()
        else:
            self.initialize_data()
    
    def initialize_data(self):
        self.categories = {
            "キャラクター": [],
            "髪色": ["赤髪", "青髪", "金髪", "黒髪", "白髪", "緑髪", "紫髪", "ピンク髪"],
            "瞳の色": ["赤瞳", "青瞳", "緑瞳", "金瞳", "黒瞳", "紫瞳"],
            "服装": ["制服", "ドレス", "水着", "メイド服", "コスプレ"],
            "その他": []
        }
        self.save_data()
    
    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"単語データの保存エラー: {str(e)}")
    
    def add_word(self, category, word):
        if category not in self.categories:
            self.categories[category] = []
        
        if word not in self.categories[category]:
            self.categories[category].append(word)
            self.save_data()
    
    def remove_word(self, category, word):
        if category in self.categories and word in self.categories[category]:
            self.categories[category].remove(word)
            self.save_data()
    
    def get_categories(self):
        return list(self.categories.keys())
    
    def get_words(self, category):
        if category in self.categories:
            return self.categories[category]
        return []
    
    def get_all_words(self):
        all_words = []
        for category in self.categories:
            all_words.extend(self.categories[category])
        return all_words
