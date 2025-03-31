import os
import sys
import json
import shutil
import piexif
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QLineEdit, QFileDialog, QListWidget, 
                             QGridLayout, QScrollArea, QFrame, QMessageBox, QTextEdit, 
                             QListWidgetItem, QCheckBox, QSpinBox)
from PyQt5.QtGui import QPixmap, QFont, QColor, QIcon
from PyQt5.QtCore import Qt, QSize, pyqtSignal
import re

from word_manager import WordManager
from image_preview import ImagePreviewWidget

class EasyRenamer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = "EasyRenamer - 画像リネームツール"
        self.left = 100
        self.top = 100
        self.width = 1200
        self.height = 800
        self.current_folder = ""
        self.image_list = []
        self.current_image_idx = -1
        self.word_manager = WordManager()
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        # メインウィジェットとレイアウト
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 上部レイアウト（フォルダ選択ボタンとパス表示）
        top_layout = QHBoxLayout()
        
        # フォルダ選択ボタン
        self.folder_btn = QPushButton("フォルダ選択")
        self.folder_btn.clicked.connect(self.selectFolder)
        top_layout.addWidget(self.folder_btn)
        
        # 選択フォルダパス表示
        self.folder_path = QLineEdit()
        self.folder_path.setReadOnly(True)
        top_layout.addWidget(self.folder_path)
        
        main_layout.addLayout(top_layout)
        
        # メインコンテンツ（画像一覧、プレビュー、リネーム部分）
        content_layout = QHBoxLayout()
        
        # 左側：画像一覧
        left_layout = QVBoxLayout()
        self.image_list_widget = QListWidget()
        self.image_list_widget.itemClicked.connect(self.displayImage)
        left_layout.addWidget(QLabel("画像一覧"))
        left_layout.addWidget(self.image_list_widget)
        
        left_frame = QFrame()
        left_frame.setLayout(left_layout)
        left_frame.setFrameShape(QFrame.StyledPanel)
        content_layout.addWidget(left_frame, 1)
        
        # 中央：画像プレビューとリネーム部分
        center_layout = QVBoxLayout()
        
        # 画像プレビュー
        self.image_preview = ImagePreviewWidget()
        center_layout.addWidget(self.image_preview, 3)
        
        # リネーム部分
        rename_layout = QVBoxLayout()
        
        # 現在の画像名
        current_name_layout = QHBoxLayout()
        current_name_layout.addWidget(QLabel("現在の画像名:"))
        self.current_filename = QLineEdit()
        self.current_filename.setReadOnly(True)
        current_name_layout.addWidget(self.current_filename)
        rename_layout.addLayout(current_name_layout)
        
        # 新しい画像名
        new_name_layout = QHBoxLayout()
        new_name_layout.addWidget(QLabel("新しい画像名:"))
        self.new_filename = QLineEdit()
        self.new_filename.textChanged.connect(self.checkFilenameLength)
        new_name_layout.addWidget(self.new_filename)
        rename_layout.addLayout(new_name_layout)
        
        # 文字数チェック
        self.char_count = QLabel("0/65文字")
        rename_layout.addWidget(self.char_count)
        
        # 連番設定
        seq_layout = QHBoxLayout()
        seq_layout.addWidget(QLabel("連番:"))
        
        self.use_sequence = QCheckBox("使用する")
        self.use_sequence.stateChanged.connect(self.updateSequence)
        seq_layout.addWidget(self.use_sequence)
        
        seq_layout.addWidget(QLabel("開始番号:"))
        self.seq_start = QSpinBox()
        self.seq_start.setValue(1)
        self.seq_start.setRange(1, 999)
        self.seq_start.valueChanged.connect(self.updateSequence)
        seq_layout.addWidget(self.seq_start)
        
        seq_layout.addWidget(QLabel("桁数:"))
        self.seq_digits = QSpinBox()
        self.seq_digits.setValue(3)
        self.seq_digits.setRange(1, 5)
        self.seq_digits.valueChanged.connect(self.updateSequence)
        seq_layout.addWidget(self.seq_digits)
        
        seq_layout.addStretch()
        rename_layout.addLayout(seq_layout)
        
        # ボタン類
        button_layout = QHBoxLayout()
        self.rename_btn = QPushButton("この画像をリネーム")
        self.rename_btn.clicked.connect(self.renameSingleImage)
        button_layout.addWidget(self.rename_btn)
        
        self.rename_all_btn = QPushButton("一括リネーム")
        self.rename_all_btn.clicked.connect(self.renameAllImages)
        button_layout.addWidget(self.rename_all_btn)
        
        rename_layout.addLayout(button_layout)
        center_layout.addLayout(rename_layout, 1)
        
        center_frame = QFrame()
        center_frame.setLayout(center_layout)
        center_frame.setFrameShape(QFrame.StyledPanel)
        content_layout.addWidget(center_frame, 2)
        
        # 右側：メタデータ＆ワードブロック
        right_layout = QVBoxLayout()
        
        # メタデータ情報
        right_layout.addWidget(QLabel("メタデータ情報:"))
        self.metadata_area = QTextEdit()
        self.metadata_area.setReadOnly(True)
        right_layout.addWidget(self.metadata_area, 1)
        
        # ワードブロック
        right_layout.addWidget(QLabel("単語ブロック:"))
        self.word_block_area = QScrollArea()
        self.word_block_area.setWidgetResizable(True)
        self.word_block_widget = QWidget()
        self.word_block_layout = QGridLayout(self.word_block_widget)
        self.word_block_area.setWidget(self.word_block_widget)
        right_layout.addWidget(self.word_block_area, 2)
        
        # 定型文設定
        right_layout.addWidget(QLabel("定型文:"))
        template_layout = QHBoxLayout()
        self.template_input = QLineEdit()
        template_layout.addWidget(self.template_input)
        self.apply_template_btn = QPushButton("適用")
        self.apply_template_btn.clicked.connect(self.applyTemplate)
        template_layout.addWidget(self.apply_template_btn)
        right_layout.addLayout(template_layout)
        
        right_frame = QFrame()
        right_frame.setLayout(right_layout)
        right_frame.setFrameShape(QFrame.StyledPanel)
        content_layout.addWidget(right_frame, 2)
        
        main_layout.addLayout(content_layout)
        
        # 状態表示
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("フォルダを選択してください")
        
        # 初期状態の設定
        self.updateUIState(False)
    
    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if folder:
            self.current_folder = folder
            self.folder_path.setText(folder)
            self.loadImages()
            self.updateUIState(True)
    
    def loadImages(self):
        self.image_list = []
        self.image_list_widget.clear()
        
        # 画像ファイルのみ取得
        for file in os.listdir(self.current_folder):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.image_list.append(file)
        
        # リストウィジェットに追加
        for image in self.image_list:
            item = QListWidgetItem(image)
            self.image_list_widget.addItem(item)
        
        if self.image_list:
            self.status_bar.showMessage(f"{len(self.image_list)}枚の画像を読み込みました")
            self.image_list_widget.setCurrentRow(0)
            self.displayImage(self.image_list_widget.currentItem())
        else:
            self.status_bar.showMessage("画像がありません")
    
    def displayImage(self, item):
        if item is None:
            return
        
        self.current_image_idx = self.image_list_widget.row(item)
        image_path = os.path.join(self.current_folder, self.image_list[self.current_image_idx])
        
        # 画像プレビュー表示
        self.image_preview.loadImage(image_path)
        
        # 現在のファイル名表示
        self.current_filename.setText(self.image_list[self.current_image_idx])
        
        # 新しいファイル名の初期化
        base_name = os.path.splitext(self.image_list[self.current_image_idx])[0]
        self.new_filename.setText(base_name)
        
        # メタデータ読み込み
        self.loadMetadata(image_path)
        
        # 連番設定の更新
        self.updateSequence()
    
    def loadMetadata(self, image_path):
        metadata_text = "メタデータが見つかりません"
        word_list = []
        
        try:
            with Image.open(image_path) as img:
                if "exif" in img.info:
                    exif_dict = piexif.load(img.info["exif"])
                    if piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
                        description = exif_dict["0th"][piexif.ImageIFD.ImageDescription].decode("utf-8")
                        metadata_text = description
                        
                        # Stable Diffusionのプロンプトを抽出
                        prompt_match = re.search(r"Prompt: (.*?)(?:Negative prompt:|$)", description, re.DOTALL)
                        if prompt_match:
                            prompt = prompt_match.group(1).strip()
                            word_list = self.extractWords(prompt)
                
                # PNGメタデータのチェック
                if not word_list and img.format == "PNG" and "parameters" in img.info:
                    parameters = img.info["parameters"]
                    metadata_text = parameters
                    word_list = self.extractWords(parameters)
        except Exception as e:
            metadata_text = f"メタデータの読み込みエラー: {str(e)}"
        
        self.metadata_area.setText(metadata_text)
        self.updateWordBlocks(word_list)
    
    def extractWords(self, text):
        # 単語抽出ロジック
        words = []
        # カンマで区切られた単語を抽出
        for word in re.split(r'[,、]', text):
            word = word.strip()
            if word:
                words.append(word)
        return words
    
    def updateWordBlocks(self, words):
        # 既存のワードブロックをクリア
        for i in reversed(range(self.word_block_layout.count())):
            self.word_block_layout.itemAt(i).widget().setParent(None)
        
        # 新しいワードブロックを作成
        row, col = 0, 0
        max_cols = 3
        
        for word in words:
            word_btn = QPushButton(word)
            word_btn.setStyleSheet("text-align: left; padding: 5px;")
            word_btn.clicked.connect(lambda _, w=word: self.insertWord(w))
            self.word_block_layout.addWidget(word_btn, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def insertWord(self, word):
        # 現在のカーソル位置に単語を挿入
        current_text = self.new_filename.text()
        cursor_pos = self.new_filename.cursorPosition()
        new_text = current_text[:cursor_pos] + word + current_text[cursor_pos:]
        self.new_filename.setText(new_text)
        self.new_filename.setCursorPosition(cursor_pos + len(word))
        self.new_filename.setFocus()
    
    def updateSequence(self):
        if not self.use_sequence.isChecked() or self.current_image_idx < 0:
            return
        
        # 連番の設定
        start_num = self.seq_start.value()
        digits = self.seq_digits.value()
        current_num = start_num + self.current_image_idx
        
        # 現在の新しいファイル名から連番部分を削除
        filename = self.new_filename.text()
        # 連番パターンを検索して削除
        filename = re.sub(r'_\d+$', '', filename)
        
        # 連番を追加
        seq_str = f"_{current_num:0{digits}d}"
        self.new_filename.setText(filename + seq_str)
    
    def checkFilenameLength(self):
        text = self.new_filename.text()
        
        # 全角/半角を考慮した文字数カウント
        count = 0
        for char in text:
            if ord(char) <= 255:  # 半角
                count += 0.5
            else:  # 全角
                count += 1
        
        # 文字数表示の更新
        self.char_count.setText(f"{count:.1f}/65文字")
        
        # 文字数制限チェック
        if count > 65:
            self.char_count.setStyleSheet("color: red;")
        else:
            self.char_count.setStyleSheet("color: black;")
    
    def renameSingleImage(self):
        if self.current_image_idx < 0:
            return
        
        old_path = os.path.join(self.current_folder, self.image_list[self.current_image_idx])
        ext = os.path.splitext(old_path)[1]
        new_name = self.new_filename.text() + ext
        new_path = os.path.join(self.current_folder, new_name)
        
        try:
            if os.path.exists(new_path) and old_path != new_path:
                if QMessageBox.question(self, "確認", f"{new_name}は既に存在します。上書きしますか？", 
                                      QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                    return
            
            os.rename(old_path, new_path)
            self.image_list[self.current_image_idx] = new_name
            self.image_list_widget.item(self.current_image_idx).setText(new_name)
            self.current_filename.setText(new_name)
            self.status_bar.showMessage(f"リネーム完了: {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"リネームに失敗しました: {str(e)}")
    
    def renameAllImages(self):
        if not self.image_list:
            return
        
        # 確認ダイアログ
        if QMessageBox.question(self, "確認", "すべての画像をリネームしますか？", 
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        
        base_name = self.new_filename.text()
        # 連番パターンを検索して削除
        base_name = re.sub(r'_\d+$', '', base_name)
        
        start_num = self.seq_start.value()
        digits = self.seq_digits.value()
        
        success_count = 0
        for i, image in enumerate(self.image_list):
            old_path = os.path.join(self.current_folder, image)
            ext = os.path.splitext(old_path)[1]
            
            if self.use_sequence.isChecked():
                new_name = f"{base_name}_{start_num + i:0{digits}d}{ext}"
            else:
                new_name = f"{base_name}{ext}"
                
            new_path = os.path.join(self.current_folder, new_name)
            
            try:
                if os.path.exists(new_path) and old_path != new_path:
                    continue
                
                os.rename(old_path, new_path)
                self.image_list[i] = new_name
                self.image_list_widget.item(i).setText(new_name)
                success_count += 1
            except Exception as e:
                print(f"リネームエラー: {str(e)}")
        
        self.status_bar.showMessage(f"{success_count}枚の画像をリネームしました")
        
        # 現在選択中の画像を更新
        if self.current_image_idx >= 0:
            self.current_filename.setText(self.image_list[self.current_image_idx])
    
    def applyTemplate(self):
        template = self.template_input.text()
        if template:
            self.new_filename.setText(template)
            self.updateSequence()
    
    def updateUIState(self, enabled):
        self.image_preview.setEnabled(enabled)
        self.image_list_widget.setEnabled(enabled)
        self.new_filename.setEnabled(enabled)
        self.rename_btn.setEnabled(enabled)
        self.rename_all_btn.setEnabled(enabled)
        self.template_input.setEnabled(enabled)
        self.apply_template_btn.setEnabled(enabled)
        self.use_sequence.setEnabled(enabled)
        self.seq_start.setEnabled(enabled)
        self.seq_digits.setEnabled(enabled)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EasyRenamer()
    window.show()
    sys.exit(app.exec_())
