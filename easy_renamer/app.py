import os
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS
import json
import tempfile

class EasyRenamer:
    def __init__(self):
        # 設定ファイルの読み込み
        self.load_settings()

        # AI生成画像用の追加メタデータキーワード
        self.ai_image_keywords = [
            'Stable Diffusion', 'Prompt', 'Negative prompt', 
            'Steps', 'CFG scale', 'Seed', 'Model', 
            'Characters', 'Style', 'Emotion'
        ]

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
            st.error(f"メタデータ抽出エラー: {e}")

        return metadata

    def rename_files(self, uploaded_files, rename_template, numbering=True):
        """ファイルリネーム処理"""
        renamed_files = []
        
        for idx, uploaded_file in enumerate(uploaded_files, 1):
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_file_path = temp_file.name

            # リネーム
            if numbering:
                new_filename = f"{rename_template}_{idx:03d}{os.path.splitext(uploaded_file.name)[1]}"
            else:
                new_filename = f"{rename_template}{os.path.splitext(uploaded_file.name)[1]}"

            # メタデータ抽出
            metadata = self.extract_metadata(temp_file_path)

            renamed_files.append({
                'original_name': uploaded_file.name,
                'new_name': new_filename,
                'metadata': metadata,
                'temp_path': temp_file_path
            })

        return renamed_files

def main():
    st.title("Easy Renamer - 画像リネームツール")
    
    # EasyRenamerインスタンス作成
    renamer = EasyRenamer()

    # サイドバー
    st.sidebar.header("設定")
    
    # 定型文管理
    st.sidebar.subheader("定型文")
    selected_template = st.sidebar.selectbox("定型文を選択", renamer.settings['template_texts'])
    
    # 大・小ワード管理
    st.sidebar.subheader("検索ワード")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        big_word = st.selectbox("大ワード", renamer.settings['big_words'])
    with col2:
        small_word = st.selectbox("小ワード", renamer.settings['small_words'])

    # リネーム用テンプレート作成
    rename_template = f"{selected_template}_{big_word}_{small_word}"
    st.sidebar.write(f"現在のテンプレート: {rename_template}")

    # ファイルアップロード
    uploaded_files = st.file_uploader("画像をアップロード", accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'webp'])

    # リネームオプション
    use_numbering = st.checkbox("連番を付ける", value=True)

    if uploaded_files:
        # プレビュー
        st.subheader("画像プレビュー")
        preview_cols = st.columns(min(5, len(uploaded_files)))
        for i, uploaded_file in enumerate(uploaded_files[:5]):
            preview_cols[i].image(uploaded_file, caption=uploaded_file.name, use_column_width=True)

        # リネーム処理
        if st.button("画像をリネーム"):
            renamed_files = renamer.rename_files(uploaded_files, rename_template, use_numbering)

            # 結果表示
            st.subheader("リネーム結果")
            for file_info in renamed_files:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"元のファイル名: {file_info['original_name']}")
                with col2:
                    st.write(f"新しいファイル名: {file_info['new_name']}")
                
                # メタデータ表示
                with st.expander(f"{file_info['original_name']}のメタデータ"):
                    st.json(file_info['metadata'])

def main_wrapper():
    main()

if __name__ == "__main__":
    main_wrapper()
