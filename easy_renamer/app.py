import os
import sys
from PIL import Image
from PIL.ExifTags import TAGS
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

class WordManagementDialog:
    def __init__(self, parent, title, word_list):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("400x500")
        
        self.word_list = word_list
        
        # リストボックス
        self.listbox = tk.Listbox(self.top, width=50)
        self.listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 既存のワードを表示
        for word in self.word_list:
            self.listbox.insert(tk.END, word)
        
        # ボタンフレーム
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="追加", command=self.add_word).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="削除", command=self.remove_word).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="閉じる", command=self.top.destroy).pack(side=tk.LEFT, padx=5)
        
        self.result = None
    
    def add_word(self):
        new_word = simpledialog.askstring("追加", "新しいワードを入力:")
        if new_word and new_word not in self.word_list:
            self.word_list.append(new_word)
            self.listbox.insert(tk.END, new_word)
    
    def remove_word(self):
        selected = self.listbox.curselection()
        if selected:
            index = selected[0]
            del self.word_list[index]
            self.listbox.delete(index)

class EasyRenamer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Easy Renamer")
        self.root.geometry("1400x900")

        # 設定ファイルの読み込み
        self.load_settings()

        # AI生成画像用の追加メタデータキーワード
        self.ai_image_keywords = [
            'Stable Diffusion', 'Prompt', 'Negative prompt', 
            'Steps', 'CFG scale', 'Seed', 'Model', 
            'Characters', 'Style', 'Emotion'
        ]

        # UI要素の初期化
        self.setup_ui()

    def load_settings(self):
        """設定ファイルの読み込み"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'template_texts': ['出品画像', 'カードゲーム用', 'コレクション'],
                'big_words': ['キャラクター', '美少女', 'アニメ'],
                'small_words': ['可愛い', '人気', '高品質'],
                'registered_words': []
            }

    def save_settings(self):
        """設定ファイルの保存"""
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def setup_ui(self):
        """UIの構築"""
        # フレーム分割
        left_frame = tk.Frame(self.root, width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        middle_frame = tk.Frame(self.root, width=600)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        right_frame = tk.Frame(self.root, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # 左フレーム: フォルダ選択と画像一覧
        tk.Button(left_frame, text="フォルダ選択", command=self.select_folder).pack(pady=10)
        
        self.image_listbox = tk.Listbox(left_frame, width=40, height=30)
        self.image_listbox.pack(fill=tk.BOTH, expand=True)
        self.image_listbox.bind('<<ListboxSelect>>', self.show_selected_image)

        # 中央フレーム: 画像表示とリネーム
        self.image_label = tk.Label(middle_frame)
        self.image_label.pack(pady=10)

        tk.Label(middle_frame, text="新しいファイル名:", font=('', 12)).pack()
        self.rename_entry = tk.Entry(middle_frame, width=100, font=('', 12))
        self.rename_entry.pack(pady=10)

        # 右フレーム: メタデータ候補とワード管理
        # メタデータ候補
        tk.Label(right_frame, text="メタデータ候補:", font=('', 12)).pack()
        self.metadata_listbox = tk.Listbox(right_frame, width=50, height=15, selectmode=tk.MULTIPLE)
        self.metadata_listbox.pack(fill=tk.BOTH, expand=True)
        self.metadata_listbox.bind('<Double-1>', self.insert_metadata_word)

        # ワード管理セクション
        word_manage_frame = tk.Frame(right_frame)
        word_manage_frame.pack(pady=10)

        manage_buttons = [
            ("定型文管理", self.manage_template_texts),
            ("大ワード管理", self.manage_big_words),
            ("小ワード管理", self.manage_small_words)
        ]

        for text, command in manage_buttons:
            tk.Button(word_manage_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

        # リネームボタン
        tk.Button(middle_frame, text="選択画像リネーム", command=self.rename_selected_image, font=('', 12)).pack(pady=10)
        tk.Button(middle_frame, text="一括リネーム", command=self.batch_rename, font=('', 12)).pack(pady=10)

    def manage_template_texts(self):
        """定型文管理"""
        dialog = WordManagementDialog(self.root, "定型文管理", self.settings['template_texts'])
        self.root.wait_window(dialog.top)
        self.save_settings()

    def manage_big_words(self):
        """大ワード管理"""
        dialog = WordManagementDialog(self.root, "大ワード管理", self.settings['big_words'])
        self.root.wait_window(dialog.top)
        self.save_settings()

    def manage_small_words(self):
        """小ワード管理"""
        dialog = WordManagementDialog(self.root, "小ワード管理", self.settings['small_words'])
        self.root.wait_window(dialog.top)
        self.save_settings()

    def extract_metadata(self, image_path):
        """画像メタデータの拡張解析"""
        metadata = {}
        try:
            # Exifメタデータ
            img = Image.open(image_path)
            exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    metadata[tag_name] = str(value)

            # AI生成画像用の追加メタデータ解析（コメント部分から）
            with open(image_path, 'rb') as f:
                img_data = f.read()
                comment_start = img_data.find(b'parameters:')
                if comment_start != -1:
                    comment_end = img_data.find(b'\n', comment_start)
                    if comment_end != -1:
                        comment = img_data[comment_start:comment_end].decode('utf-8', errors='ignore')
                        for keyword in self.ai_image_keywords:
                            if keyword.lower() in comment.lower():
                                metadata[keyword] = comment

        except Exception as e:
            print(f"メタデータ抽出エラー: {e}")

        return metadata

    def run(self):
        """アプリケーションの実行"""
        self.root.mainloop()

def main():
    app = EasyRenamer()
    app.run()

if __name__ == "__main__":
    main()
