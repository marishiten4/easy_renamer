import os
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS
import json
import tempfile
import base64

class EasyRenamer:
    def __init__(self):
        # セッション状態の初期化
        if 'settings' not in st.session_state:
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
                st.session_state.settings = json.load(f)
        except FileNotFoundError:
            st.session_state.settings = {
                'template_texts': ['出品画像', 'カードゲーム用', 'コレクション'],
                'big_words': ['キャラクター', '美少女', 'アニメ'],
                'small_words': ['可愛い', '人気', '高品質'],
                'registered_words': []
            }

    def save_settings(self):
        """設定ファイルの保存"""
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(st.session_state.settings, f, ensure_ascii=False, indent=4)

    def manage_word_list(self, list_type):
        """ワードリスト管理"""
        st.header(f"{list_type}管理")
        
        # 現在のリスト
        current_list = st.session_state.settings.get(list_type, [])
        
        # 新しいワード追加
        new_word = st.text_input(f"新しい{list_type}を追加", key=f"new_{list_type}")
        if st.button(f"{list_type}追加", key=f"add_{list_type}"):
            if new_word and new_word not in current_list:
                current_list.append(new_word)
                st.session_state.settings[list_type] = current_list
                self.save_settings()
                st.success(f"{new_word}を追加しました")
        
        # 既存のワード削除
        st.subheader("登録済みワード")
        words_to_remove = []
        for idx, word in enumerate(current_list):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(word)
            with col2:
                if st.button("削除", key=f"remove_{list_type}_{idx}"):
                    words_to_remove.append(word)
        
        # 削除処理
        if words_to_remove:
            for word in words_to_remove:
                current_list.remove(word)
            st.session_state.settings[list_type] = current_list
            self.save_settings()
            st.experimental_rerun()

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
                'temp_path': temp_file_path,
                'file_base64': base64.b64encode(uploaded_file.getvalue()).decode()
            })

        return renamed_files

def main():
    # タイトルとページ設定
    st.set_page_config(page_title="Easy Renamer", layout="wide")
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    # EasyRenamerインスタンス作成
    renamer = EasyRenamer()

    # タブ設定
    tab1, tab2, tab3 = st.tabs(["リネーム", "定型文管理", "検索ワード管理"])

    with tab1:
        # ファイルアップロード（目立つように大きく）
        st.header("📤 画像アップロード")
        st.markdown("""
        <style>
        .uploadarea {
            border: 2px dashed #FF4B4B;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            background-color: #FFF3F3;
        }
        </style>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "画像をアップロード (最大2GB/ファイル)", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="最大2GBまでの画像をアップロードできます",
        )

        # リネーム設定
        st.header("🛠️ リネーム設定")
        
        # 定型文・ワード選択
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_template = st.selectbox(
                "定型文", 
                st.session_state.settings['template_texts']
            )
        with col2:
            big_word = st.selectbox(
                "大ワード", 
                st.session_state.settings['big_words']
            )
        with col3:
            small_word = st.selectbox(
                "小ワード", 
                st.session_state.settings['small_words']
            )

        # リネームテンプレート
        rename_template = f"{selected_template}_{big_word}_{small_word}"
        st.text_input("リネームテンプレート", value=rename_template, disabled=True)

        # リネームオプション
        use_numbering = st.checkbox("連番を付ける", value=True)

        # 画像処理
        if uploaded_files:
            # 画像名称表示エリア
            st.header("📋 画像名称")
            selected_image_name = st.text_input("選択中の画像名", disabled=True)

            # 画像プレビュー (50個まで)
            st.header("🖼️ 画像プレビュー")
            
            # ページネーション
            page_size = 50
            total_pages = (len(uploaded_files) - 1) // page_size + 1
            page_number = st.number_input(
                "ページ", 
                min_value=1, 
                max_value=total_pages, 
                value=1
            )
            
            start_idx = (page_number - 1) * page_size
            end_idx = start_idx + page_size
            page_files = uploaded_files[start_idx:end_idx]
            
            # 画像グリッド
            image_cols = st.columns(5)
            for i, uploaded_file in enumerate(page_files):
                with image_cols[i % 5]:
                    st.image(uploaded_file, use_column_width=True)
                    if st.button(f"選択", key=f"select_{start_idx + i}"):
                        selected_image_name = uploaded_file.name

            # リネーム処理
            if st.button("画像をリネーム", type="primary"):
                renamed_files = renamer.rename_files(uploaded_files, rename_template, use_numbering)

                # 結果表示
                st.header("✅ リネーム結果")
                for file_info in renamed_files:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"元のファイル名: {file_info['original_name']}")
                    with col2:
                        st.write(f"新しいファイル名: {file_info['new_name']}")
                    
                    # メタデータ表示
                    with st.expander(f"{file_info['original_name']}のメタデータ"):
                        st.json(file_info['metadata'])

    with tab2:
        renamer.manage_word_list('template_texts')

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            renamer.manage_word_list('big_words')
        with col2:
            renamer.manage_word_list('small_words')

def main_wrapper():
    main()

if __name__ == "__main__":
    main_wrapper()
