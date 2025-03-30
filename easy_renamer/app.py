import os
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS
import json
import base64
import re
import shutil
import io

class EasyRenamer:
    def __init__(self):
        # Initialize session state
        if 'settings' not in st.session_state:
            self.load_settings()
        
        if 'selected_image_index' not in st.session_state:
            st.session_state.selected_image_index = None
            
        # AI image metadata keywords
        self.ai_image_keywords = [
            'Stable Diffusion', 'Prompt', 'Negative prompt', 
            'Steps', 'CFG scale', 'Seed', 'Model', 
            'Characters', 'Style', 'Emotion'
        ]
        
        # Metadata keyword mapping
        if 'keyword_mapping' not in st.session_state:
            st.session_state.keyword_mapping = {}

    def load_settings(self):
        """Load settings file"""
        default_settings = {
            'template_texts': ['出品画像', 'カードゲーム用', 'コレクション'],
            'big_words': ['キャラクター', '美少女', 'アニメ'],
            'small_words': ['可愛い', '人気', '高品質'],
            'registered_words': [],
            'metadata_keywords': []
        }
        
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                st.session_state.settings = json.load(f)
        except FileNotFoundError:
            st.session_state.settings = default_settings

    def save_settings(self):
        """Save settings file"""
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(st.session_state.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"設定の保存中にエラーが発生: {e}")

    def extract_metadata_keywords(self, image_file):
        """Extract metadata keywords from image"""
        keywords = []
        param_str = ""
        
        try:
            # Convert to PIL Image object
            image = Image.open(image_file)
            
            # Extract keywords from parameter string
            param_str = image.info.get('parameters', '')
            if param_str:
                # Search for AI keywords
                keywords.extend([
                    keyword for keyword in self.ai_image_keywords 
                    if keyword.lower() in param_str.lower()
                ])
                
                # Extract custom keywords
                prompt_keywords = re.findall(r'\b[A-Za-z]+\b', param_str)
                keywords.extend(prompt_keywords[:5])  # Add first 5 keywords
                
                # Check if keywords have mappings
                mapped_keywords = []
                for keyword in keywords:
                    mapped = st.session_state.keyword_mapping.get(keyword.lower())
                    if mapped:
                        mapped_keywords.append(mapped)
                
                # Add mapped keywords
                keywords.extend(mapped_keywords)
        
        except Exception as e:
            st.warning(f"メタデータ解析中にエラーが発生: {e}")
        
        return list(set(keywords)), param_str  # Remove duplicates and return raw metadata

    def create_word_blocks(self, additional_keywords=None):
        """Create word blocks with drag and drop functionality"""
        # Combine all words
        all_words = (
            st.session_state.settings['template_texts'] + 
            st.session_state.settings['big_words'] + 
            st.session_state.settings['small_words'] +
            st.session_state.settings['metadata_keywords']
        )
        
        # Add metadata keywords
        if additional_keywords:
            all_words.extend(additional_keywords)
        
        # Unique words
        all_words = list(set(all_words))
        
        # Display as buttons
        cols = st.columns(4)
        
        for i, word in enumerate(all_words):
            col_idx = i % 4
            if cols[col_idx].button(word, key=f"word_btn_{i}", use_container_width=True):
                # Add the word to the input field
                current_input = st.session_state.get('rename_input', '')
                if current_input:
                    st.session_state['rename_input'] = f"{current_input} {word}"
                else:
                    st.session_state['rename_input'] = word

    def rename_files(self, files, base_name, custom_numbering, number_position):
        """
        Rename files with custom numbering
        
        :param files: List of uploaded files
        :param base_name: Base rename name
        :param custom_numbering: Custom numbering format
        :param number_position: Position of numbering (prefix or suffix)
        :return: Dictionary of rename results
        """
        results = {}
        output_dir = 'renamed_images'
        
        # Create output directory if not exists
        os.makedirs(output_dir, exist_ok=True)
        
        for idx, uploaded_file in enumerate(files, start=1):
            # Generate custom filename with user-defined numbering
            file_ext = os.path.splitext(uploaded_file.name)[1]
            
            # Replace placeholders in custom numbering
            number_str = custom_numbering.format(n=idx)
            
            # Determine filename based on number position
            if number_position == 'prefix':
                new_filename = f"{number_str}_{base_name}{file_ext}"
            else:  # suffix
                new_filename = f"{base_name}_{number_str}{file_ext}"
            
            new_filepath = os.path.join(output_dir, new_filename)
            
            try:
                # Save file
                with open(new_filepath, "wb") as f:
                    f.write(uploaded_file.getvalue())
                results[uploaded_file.name] = new_filename
            except Exception as e:
                results[uploaded_file.name] = f"エラー: {str(e)}"
        
        return results

    def add_word(self, word_type, word):
        """Add a new word to the specified word list"""
        if word and word not in st.session_state.settings[word_type]:
            st.session_state.settings[word_type].append(word)
            self.save_settings()
            st.success(f"ワード '{word}' を{word_type}に追加しました")
        elif word in st.session_state.settings[word_type]:
            st.warning(f"ワード '{word}' は既に存在します")

    def add_keyword_mapping(self, original_keyword, mapped_keyword):
        """Add a new keyword mapping"""
        if original_keyword and mapped_keyword:
            st.session_state.keyword_mapping[original_keyword.lower()] = mapped_keyword
            st.success(f"キーワードマッピング: '{original_keyword}' → '{mapped_keyword}' を追加しました")
        else:
            st.warning("キーワードとマッピングを両方入力してください")

def main():
    st.set_page_config(page_title="Easy Renamer", layout="wide")
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    # Apply custom CSS
    st.markdown("""
    <style>
    .selected-image {
        border: 3px solid #4169E1 !important;
        background-color: #F0F8FF;
    }
    .image-list {
        height: 400px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 5px;
    }
    .stButton>button {
        width: 100%;
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    renamer = EasyRenamer()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["リネーム", "定型文管理", "検索ワード管理", "メタデータキーワード管理", "キーワードマッピング"]
    )

    with tab1:
        st.header("📤 画像アップロード")
        uploaded_files = st.file_uploader(
            "画像をアップロード (最大2GB/ファイル)", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="最大2GBまでの画像をアップロードできます"
        )

        if uploaded_files:
            # Pagination for image list
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

            # Image selection, preview, and renaming in columns
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("画像一覧")
                
                # Display file list with clickable items
                st.markdown('<div class="image-list">', unsafe_allow_html=True)
                
                for i, file in enumerate(page_files):
                    if st.button(file.name, key=f"file_{i}", use_container_width=True):
                        st.session_state.selected_image_index = i
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                if st.session_state.selected_image_index is not None and st.session_state.selected_image_index < len(page_files):
                    selected_image = page_files[st.session_state.selected_image_index]
                    
                    # Create columns for metadata and preview
                    meta_col, preview_col = st.columns([1, 1])
                    
                    with meta_col:
                        st.subheader("メタデータ")
                        # Extract metadata
                        metadata_keywords, raw_metadata = renamer.extract_metadata_keywords(selected_image)
                        
                        # Display extracted keywords
                        st.write("抽出されたキーワード:")
                        for keyword in metadata_keywords:
                            st.markdown(f"- {keyword}")
                        
                        # Display raw metadata
                        with st.expander("詳細メタデータ"):
                            st.text(raw_metadata)
                    
                    with preview_col:
                        st.subheader("画像プレビュー")
                        # Load and display selected image
                        image = Image.open(selected_image)
                        
                        # Create a BytesIO object to display the image
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format=image.format)
                        img_byte_arr = img_byte_arr.getvalue()
                        
                        # Display image with expansion option
                        st.image(img_byte_arr, caption=selected_image.name, use_column_width=True)
                else:
                    st.info("左側の一覧から画像を選択してください")

            # Rename settings
            st.header("🔢 リネーム設定")
            
            # Numbering position selection
            number_position = st.radio(
                "連番の位置", 
                ['prefix', 'suffix'], 
                format_func=lambda x: '先頭' if x == 'prefix' else '末尾',
                horizontal=True
            )
            
            # Customizable numbering input
            custom_numbering = st.text_input(
                "連番形式",
                value="{n:02d}",
                help="例: {n:02d} (数字2桁), A{n} (文字と数字の組み合わせ)"
            )
            
            # Rename blocks
            st.header("📝 リネーム名称")
            metadata_kw = metadata_keywords if 'metadata_keywords' in locals() else None
            renamer.create_word_blocks(additional_keywords=metadata_kw)
            
            # Rename input
            rename_input = st.text_input(
                "リネーム名を入力", 
                key="rename_input",
                help="上のボタンをクリックして単語を挿入できます"
            )

            # Character count validation
            char_count = len(rename_input)
            if char_count > 130:
                st.markdown(f"<span style='color:red'>文字数: {char_count} (130文字を超えています)</span>", unsafe_allow_html=True)
            else:
                st.write(f"文字数: {char_count}")

            # Rename processing - Add two buttons for options
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("選択画像をリネーム", type="primary"):
                    if rename_input:
                        if st.session_state.selected_image_index is not None:
                            # Rename only selected image
                            selected_file = [page_files[st.session_state.selected_image_index]]
                            rename_results = renamer.rename_files(
                                selected_file,
                                rename_input,
                                custom_numbering,
                                number_position
                            )
                            
                            # Display results
                            st.subheader("リネーム結果")
                            for original, new_name in rename_results.items():
                                st.write(f"{original} → {new_name}")
                                
                            # Create and offer zip download
                            with open('renamed_images.zip', 'wb') as zipf:
                                shutil.make_archive('renamed_images', 'zip', 'renamed_images')
                            
                            with open('renamed_images.zip', 'rb') as f:
                                st.download_button(
                                    label="リネーム済み画像をダウンロード",
                                    data=f.read(),
                                    file_name='renamed_images.zip',
                                    mime='application/zip'
                                )
                        else:
                            st.warning("画像を選択してください")
                    else:
                        st.warning("リネーム名を入力してください")
            
            with col2:
                if st.button("すべての画像をリネーム", type="secondary"):
                    if rename_input:
                        # Confirm with the user
                        if st.checkbox("一括リネームを確認 (チェックを入れて確定)", key="bulk_confirm"):
                            # Execute rename process for all files
                            rename_results = renamer.rename_files(
                                uploaded_files,
                                rename_input,
                                custom_numbering,
                                number_position
                            )
                            
                            # Display results
                            st.subheader("リネーム結果")
                            for original, new_name in rename_results.items():
                                st.write(f"{original} → {new_name}")
                            
                            # Create and offer zip download
                            with open('renamed_images.zip', 'wb') as zipf:
                                shutil.make_archive('renamed_images', 'zip', 'renamed_images')
                            
                            with open('renamed_images.zip', 'rb') as f:
                                st.download_button(
                                    label="リネーム済み画像をダウンロード",
                                    data=f.read(),
                                    file_name='renamed_images.zip',
                                    mime='application/zip'
                                )
                    else:
                        st.warning("リネーム名を入力してください")

    with tab2:
        st.header("📋 定型文管理")
        template_words = st.text_input("定型文を追加")
        if st.button("定型文を追加"):
            renamer.add_word('template_texts', template_words)
        
        st.write("現在の定型文:", st.session_state.settings['template_texts'])

    with tab3:
        st.header("🔍 検索ワード管理")
        
        # Big words management
        st.subheader("大きめワード")
        big_word = st.text_input("大きめワードを追加")
        if st.button("大きめワードを追加"):
            renamer.add_word('big_words', big_word)
        
        st.write("現在の大きめワード:", st.session_state.settings['big_words'])
        
        # Small words management
        st.subheader("小さめワード")
        small_word = st.text_input("小さめワードを追加")
        if st.button("小さめワードを追加"):
            renamer.add_word('small_words', small_word)
        
        st.write("現在の小さめワード:", st.session_state.settings['small_words'])

    with tab4:
        st.header("🏷️ メタデータキーワード管理")
        
        # Metadata keywords management
        metadata_keyword = st.text_input("メタデータキーワードを追加")
        if st.button("メタデータキーワードを追加"):
            # Add to metadata keywords list
            if metadata_keyword and metadata_keyword not in st.session_state.settings['metadata_keywords']:
                st.session_state.settings['metadata_keywords'].append(metadata_keyword)
                renamer.save_settings()
                st.success(f"メタデータキーワード '{metadata_keyword}' を追加しました")
            elif metadata_keyword in st.session_state.settings['metadata_keywords']:
                st.warning(f"メタデータキーワード '{metadata_keyword}' は既に存在します")
        
        st.write("現在のメタデータキーワード:", st.session_state.settings['metadata_keywords'])

    with tab5:
        st.header("🔗 キーワードマッピング")
        
        # Keyword mapping management
        col1, col2 = st.columns(2)
        
        with col1:
            original_keyword = st.text_input("元のキーワード (英語)")
        
        with col2:
            mapped_keyword = st.text_input("マッピングするキーワード (日本語)")
        
        if st.button("キーワードマッピングを追加"):
            renamer.add_keyword_mapping(original_keyword, mapped_keyword)
        
        # Display current mappings
        st.subheader("現在のキーワードマッピング")
        if st.session_state.keyword_mapping:
            mapping_df = [{"元のキーワード": k, "マッピングされたキーワード": v} 
                         for k, v in st.session_state.keyword_mapping.items()]
            st.table(mapping_df)
        else:
            st.write("マッピングはまだ追加されていません")

def main_wrapper():
    main()

if __name__ == "__main__":
    main_wrapper()
