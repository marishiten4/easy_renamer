import streamlit as st
import os
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
import json

class StreamlitRenameTool:
    def __init__(self):
        st.set_page_config(
            page_title="Easy Renamer",
            page_icon="🖼️",
            layout="wide"
        )
        
        # セッション状態の初期化
        if 'image_folder' not in st.session_state:
            st.session_state.image_folder = None
        if 'images' not in st.session_state:
            st.session_state.images = []
        
        # 設定ファイルの読み込み
        self.load_config()
        
    def load_config(self):
        try:
            with open('configs/word_candidates.json', 'r', encoding='utf-8') as f:
                self.word_candidates = json.load(f)
        except FileNotFoundError:
            self.word_candidates = {
                'characters': [],
                'styles': [],
                'templates': []
            }
    
    def select_folder(self):
        """フォルダ選択機能"""
        st.sidebar.header("フォルダ選択")
        folder_path = st.sidebar.text_input("フォルダパスを入力", 
                                            value=st.session_state.image_folder or '')
        
        if st.sidebar.button("フォルダを選択"):
            if os.path.isdir(folder_path):
                st.session_state.image_folder = folder_path
                # 画像ファイルのみをフィルタリング
                self.scan_images()
            else:
                st.error("有効なフォルダを選択してください")
    
    def scan_images(self):
        """画像をスキャンし、セッションに保存"""
        supported_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        st.session_state.images = [
            f for f in os.listdir(st.session_state.image_folder) 
            if os.path.splitext(f)[1].lower() in supported_extensions
        ]
    
    def extract_metadata(self, file_path):
        """画像からメタデータを抽出"""
        try:
            metadata_info = []
            image = Image.open(file_path)
            exif_data = image.getexif()
            
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    str_value = str(value)
                    metadata_info.append(str_value)
            
            return metadata_info
        except Exception as e:
            st.warning(f"メタデータ抽出エラー: {e}")
            return []
    
    def create_rename_interface(self):
        """リネームインターフェース"""
        st.header("Easy Renamer")
        
        # フォルダが選択されていない場合
        if not st.session_state.image_folder:
            self.select_folder()
            return
        
        # サイドバーに候補ワード
        st.sidebar.header("候補ワード")
        for category, words in self.word_candidates.items():
            st.sidebar.subheader(category.capitalize())
            for word in words:
                if st.sidebar.button(word, key=f"{category}_{word}"):
                    st.session_state.current_word = word
        
        # メイン画面レイアウト
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 画像選択
            selected_image = st.selectbox(
                "リネームする画像を選択", 
                st.session_state.images
            )
            
            # 画像プレビュー
            if selected_image:
                full_path = os.path.join(st.session_state.image_folder, selected_image)
                st.image(full_path, caption=selected_image, use_column_width=True)
                
                # メタデータ表示
                metadata = self.extract_metadata(full_path)
                if metadata:
                    st.subheader("メタデータ")
                    st.write(metadata)
        
        with col2:
            # リネーム入力
            new_filename = st.text_input(
                "新しいファイル名", 
                value=selected_image
            )
            
            # リネームボタン
            if st.button("リネーム"):
                try:
                    old_path = os.path.join(st.session_state.image_folder, selected_image)
                    new_path = os.path.join(st.session_state.image_folder, new_filename)
                    
                    # バックアップフォルダ作成
                    backup_folder = os.path.join(st.session_state.image_folder, 'backup')
                    os.makedirs(backup_folder, exist_ok=True)
                    
                    # バックアップ
                    shutil.copy2(old_path, os.path.join(backup_folder, selected_image))
                    
                    # リネーム
                    os.rename(old_path, new_path)
                    st.success(f"{selected_image} を {new_filename} にリネームしました")
                    
                    # 画像リストを更新
                    self.scan_images()
                except Exception as e:
                    st.error(f"リネーム中にエラーが発生: {e}")
    
    def run(self):
        """アプリケーションの実行"""
        st.title("🖼️ Easy Renamer")
        self.create_rename_interface()

def main():
    app = StreamlitRenameTool()
    app.run()

if __name__ == "__main__":
    main()
