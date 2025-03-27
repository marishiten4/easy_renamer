import os
import sys
import json
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QTextEdit, QMessageBox, QGridLayout, QScrollArea)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

class EasyRenamer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_images = []
        self.current_page = 0
        self.images_per_page = 50
        self.metadata_keywords = self.load_keywords()

    def initUI(self):
        self.setWindowTitle('Easy Renamer')
        self.setGeometry(100, 100, 1200, 800)

        # メインウィジェットとレイアウト
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # 左側レイアウト（画像リスト）
        left_layout = QVBoxLayout()
        
        # 画像リストウィジェット
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.display_selected_image)
        left_layout.addWidget(self.image_list)
        
        # ページ送りボタン
        page_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton('前のページ')
        self.next_page_btn = QPushButton('次のページ')
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.next_page_btn.clicked.connect(self.next_page)
        page_layout.addWidget(self.prev_page_btn)
        page_layout.addWidget(self.next_page_btn)
        left_layout.addLayout(page_layout)

        # 中央レイアウト（画像表示とリネーム）
        center_layout = QVBoxLayout()
        
        # 選択画像表示
        self.image_display = QLabel()
        self.image_display.setFixedSize(400, 400)
        self.image_display.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.image_display)
        
        # リネーム入力エリア
        self.rename_input = QLineEdit()
        center_layout.addWidget(self.rename_input)
        
        # 右側レイアウト（メタデータと設定）
        right_layout = QVBoxLayout()
        
        # メタデータ候補エリア
        self.metadata_list = QListWidget()
        self.metadata_list.itemDoubleClicked.connect(self.insert_metadata_keyword)
        right_layout.addWidget(QLabel('メタデータ候補:'))
        right_layout.addWidget(self.metadata_list)
        
        # 定型文・検索ワード入力
        self.template_input = QLineEdit()
        right_layout.addWidget(QLabel('定型文:'))
        right_layout.addWidget(self.template_input)
        
        # フォルダ選択ボタン
        select_folder_btn = QPushButton('フォルダ選択')
        select_folder_btn.clicked.connect(self.select_folder)
        right_layout.addWidget(select_folder_btn)
        
        # リネームボタン
        rename_btn = QPushButton('リネーム')
        rename_btn.clicked.connect(self.rename_files)
        right_layout.addWidget(rename_btn)

        # レイアウト組み立て
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(center_layout, 1)
        main_layout.addLayout(right_layout, 1)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def load_keywords(self):
        # キーワード読み込み（JSONファイルから）
        try:
            with open('keywords.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'フォルダ選択')
        if folder_path:
            self.load_images(folder_path)

    def load_images(self, folder_path):
        # 画像読み込み
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        self.current_images = [
            os.path.join(folder_path, f) 
            for f in os.listdir(folder_path) 
            if os.path.splitext(f)[1].lower() in image_extensions
        ]
        self.current_page = 0
        self.update_image_list()

    def update_image_list(self):
        # 画像リスト更新
        self.image_list.clear()
        start = self.current_page * self.images_per_page
        end = start + self.images_per_page
        page_images = self.current_images[start:end]
        
        for img_path in page_images:
            self.image_list.addItem(os.path.basename(img_path))
        
        # ページ送りボタン制御
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(end < len(self.current_images))

    def display_selected_image(self, item):
        # 選択画像表示
        index = self.image_list.row(item)
        full_path = self.current_images[self.current_page * self.images_per_page + index]
        
        pixmap = QPixmap(full_path)
        scaled_pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_display.setPixmap(scaled_pixmap)
        
        # メタデータ解析
        self.analyze_metadata(full_path)

    def analyze_metadata(self, image_path):
        # メタデータ解析
        self.metadata_list.clear()
        try:
            with Image.open(image_path) as img:
                # メタデータ取得（Exifやその他の方法）
                metadata = img.info.get('parameters', '')
                if metadata:
                    # メタデータからキーワード候補を抽出
                    keywords = self.extract_keywords(metadata)
                    self.metadata_list.addItems(keywords)
        except Exception as e:
            print(f"メタデータ解析エラー: {e}")

    def extract_keywords(self, metadata):
        # キーワード抽出ロジック
        # 実際の実装ではより高度な自然言語処理が必要
        keywords = []
        for category, words in self.metadata_keywords.items():
            for word in words:
                if word.lower() in metadata.lower():
                    keywords.append(word)
        return keywords

    def insert_metadata_keyword(self, item):
        # メタデータキーワード挿入
        keyword = item.text()
        current_text = self.rename_input.text()
        self.rename_input.setText(f"{current_text} {keyword}")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_image_list()

    def next_page(self):
        if (self.current_page + 1) * self.images_per_page < len(self.current_images):
            self.current_page += 1
            self.update_image_list()

    def rename_files(self):
        # リネーム処理
        new_name = self.rename_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, '警告', '新しい名前を入力してください')
            return

        # 文字数チェック
        if len(new_name) > 65:  # 全角65文字相当
            QMessageBox.warning(self, '警告', '文字数が制限を超えています')
            return

        # 確認ダイアログ
        reply = QMessageBox.question(
            self, 'リネーム確認', 
            f'選択した画像を\n{new_name}\nでリネームしますか？', 
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            selected_items = self.image_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, '警告', '画像を選択してください')
                return

            for item in selected_items:
                index = self.image_list.row(item)
                full_path = self.current_images[self.current_page * self.images_per_page + index]
                directory = os.path.dirname(full_path)
                file_ext = os.path.splitext(full_path)[1]
                
                # 連番付与
                base_name = f"{new_name}"
                counter = 1
                new_path = os.path.join(directory, f"{base_name}{file_ext}")
                while os.path.exists(new_path):
                    new_path = os.path.join(directory, f"{base_name}_{counter}{file_ext}")
                    counter += 1
                
                os.rename(full_path, new_path)
            
            # リスト再読み込み
            self.load_images(directory)

def main():
    app = QApplication(sys.argv)
    renamer = EasyRenamer()
    renamer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
