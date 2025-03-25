import os
import json
import streamlit as st
from PIL import Image, ExifTags
import piexif

class WordManager:
    def __init__(self):
        # ワードデータの永続化のためjsonファイルを使用
        self.config_file = 'word_config.json'
        self.load_words()

    def load_words(self):
        """設定ファイルからワードをロード"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.word_config = json.load(f)
        except FileNotFoundError:
            self.word_config = {
                'big_words': ['キャラクター名', 'ポーズ', '衣装'],
                'small_words': ['可愛い', '綺麗', 'セクシー'],
                'matching_words': ['少女', '美少女', 'アニメ']
            }
            self.save_words()

    def save_words(self):
        """ワード設定をjsonファイルに保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.word_config, f, ensure_ascii=False, indent=2)

    def add_word(self, category, word):
        """新しいワードを追加"""
        if word not in self.word_config[category]:
            self.word_config[category].append(word)
            self.save_words()

class MetadataExtractor:
    @staticmethod
    def extract_stable_diffusion_prompt(image_path):
        """Stable Diffusionのメタデータからプロンプトを抽出"""
        try:
            img = Image.open(image_path)
            
            # Pillowでメタデータ取得
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'UserComment':
                        return value.decode('utf-8')
            
            # PILで取得できない場合はpiexifを使用
            exif_dict = piexif.load(image_path)
            user_comment = exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment)
            
            if user_comment:
                return user_comment.decode('utf-8')
        
        except Exception as e:
            st.warning(f"メタデータ抽出エラー: {e}")
        
        return ""

class ImageRenamer:
    def __init__(self):
        self.word_manager = WordManager()
        self.metadata_extractor = MetadataExtractor()
        
        # セッション状態の初期化
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = []
        if 'selected_image_index' not in st.session_state:
            st.session_state.selected_image_index = 0

    def upload_images(self):
        """画像アップロード"""
        uploaded_files = st.file_uploader(
            "画像ファイルをアップロード", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )

        if uploaded_files:
            st.session_state.uploaded_files = uploaded_files
            st.session_state.selected_image_index = 0

    def display_image_grid(self):
        """画像グリッド表示とクリック選択"""
        if st.session_state.uploaded_files:
            cols = st.columns(4)
            for i, uploaded_file in enumerate(st.session_state.uploaded_files):
                col = cols[i % 4]
                with col:
                    if st.button(f"画像{i+1}", key=f"img_select_{i}"):
                        st.session_state.selected_image_index = i

            # 選択された画像の詳細表示
            selected_file = st.session_state.uploaded_files[st.session_state.selected_image_index]
            st.subheader(f"選択画像: {selected_file.name}")
            st.image(selected_file, caption=selected_file.name, use_column_width=True)

            # メタデータ抽出
            self.analyze_image_metadata(selected_file)

    def analyze_image_metadata(self, uploaded_file):
        """画像メタデータ分析と候補ワード抽出"""
        # 一時的に画像を保存
        with open(uploaded_file.name, 'wb') as f:
            f.write(uploaded_file.getvalue())

        prompt = self.metadata_extractor.extract_stable_diffusion_prompt(uploaded_file.name)
        
        if prompt:
            st.subheader("抽出されたプロンプト")
            st.text(prompt)

            # マッチングワードの検索
            matching_words = [
                word for word in self.word_manager.word_config['matching_words'] 
                if word in prompt
            ]

            if matching_words:
                st.subheader("検出されたキーワード")
                for word in matching_words:
                    st.success(f"マッチ: {word}")

    def word_selection_area(self):
        """ワード選択・登録エリア"""
        st.sidebar.header("ワード管理")
        
        # ワード追加機能
        with st.sidebar.expander("新規ワード追加"):
            new_word = st.text_input("追加するワード")
            word_category = st.selectbox("カテゴリ", 
                ['big_words', 'small_words', 'matching_words'])
            
            if st.button("ワード追加"):
                if new_word:
                    self.word_manager.add_word(word_category, new_word)
                    st.success(f"{new_word}を{word_category}に追加しました")

        # 既存ワードの表示
        st.sidebar.subheader("登録ワード")
        for category, words in self.word_manager.word_config.items():
            st.sidebar.write(f"{category}:")
            st.sidebar.write(", ".join(words))

def main():
    st.set_page_config(page_title="画像リネームツール", page_icon=":camera:")
    st.title('画像リネームツール - メタデータ解析版')
    
    renamer = ImageRenamer()
    
    # ワード選択エリア
    renamer.word_selection_area()
    
    # 画像アップロード
    renamer.upload_images()
    
    # 画像グリッド表示
    if st.session_state.uploaded_files:
        renamer.display_image_grid()

if __name__ == '__main__':
    main()
