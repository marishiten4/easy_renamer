import os
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS
import json
import base64
import re
import shutil
import io
import time
from concurrent.futures import ThreadPoolExecutor
import threading

class EasyRenamer:
    def __init__(self):
        # Initialize session state
        if 'settings' not in st.session_state:
            self.load_settings()
        
        if 'image_cache' not in st.session_state:
            st.session_state.image_cache = {}
            
        if 'metadata_cache' not in st.session_state:
            st.session_state.metadata_cache = {}
        
        # AI image metadata keywords
        self.ai_image_keywords = [
            'Stable Diffusion', 'Prompt', 'Negative prompt', 
            'Steps', 'CFG scale', 'Seed', 'Model', 
            'Characters', 'Style', 'Emotion'
        ]

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
        """Extract metadata keywords from image with caching support"""
        # Check if metadata is already cached
        if image_file.name in st.session_state.metadata_cache:
            return st.session_state.metadata_cache[image_file.name]
        
        keywords = []
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
                prompt_match = re.findall(r'\b[A-Za-z]+\b', param_str)
                keywords.extend(prompt_match[:5])  # Add first 5 keywords
        
        except Exception as e:
            pass  # Silently handle errors to improve performance
        
        # Cache the results
        unique_keywords = list(set(keywords))  # Remove duplicates
        st.session_state.metadata_cache[image_file.name] = unique_keywords
        
        return unique_keywords

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
            
        # Remove duplicates while preserving order
        all_words = list(dict.fromkeys(all_words))
        
        # Word block HTML/CSS with drag and drop
        st.markdown("""
        <style>
        .word-block {
            display: inline-block;
            background-color: #4169E1;  /* Royal Blue */
            color: white;
            border: 1px solid #1E90FF;
            border-radius: 5px;
            padding: 5px 10px;
            margin: 5px;
            cursor: move;
            font-weight: bold;
        }
        #rename-input {
            width: 100%;
            font-size: 16px;
            padding: 10px;
        }
        .word-blocks-container {
            max-height: 200px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        </style>
        <script>
        function allowDrop(ev) {
            ev.preventDefault();
        }

        function drag(ev) {
            ev.dataTransfer.setData("text", ev.target.innerText);
        }

        function drop(ev) {
            ev.preventDefault();
            var data = ev.dataTransfer.getData("text");
            var input = document.getElementById("rename-input");
            var startPos = input.selectionStart;
            var endPos = input.selectionEnd;
            
            var currentValue = input.value;
            var newValue = 
                currentValue.slice(0, startPos) + 
                " " + data + " " + 
                currentValue.slice(endPos);
            
            input.value = newValue.replace(/\s+/g, ' ').trim();
            
            const event = new Event('input');
            input.dispatchEvent(event);
        }
        </script>
        """, unsafe_allow_html=True)

        # Display word blocks
        word_block_html = ""
        for word in all_words:
            word_block_html += f'<span class="word-block" draggable="true" ondragstart="drag(event)">{word}</span>'
        
        st.markdown(f'<div class="word-blocks-container" ondrop="drop(event)" ondragover="allowDrop(event)">{word_block_html}</div>', unsafe_allow_html=True)

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
        
        # Process files with a thread pool for better performance
        def process_file(idx_file):
            idx, uploaded_file = idx_file
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
                return (uploaded_file.name, new_filename)
            except Exception as e:
                return (uploaded_file.name, f"エラー: {str(e)}")
        
        # Use ThreadPoolExecutor to process files in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            file_results = executor.map(process_file, enumerate(files, start=1))
            
        # Convert results to dictionary
        for original, new_name in file_results:
            results[original] = new_name
            
        return results

    def add_word(self, word_type, word):
        """Add a new word to the specified word list"""
        if word and word not in st.session_state.settings[word_type]:
            st.session_state.settings[word_type].append(word)
            self.save_settings()
            st.success(f"ワード '{word}' を{word_type}に追加しました")
        elif word in st.session_state.settings[word_type]:
            st.warning(f"ワード '{word}' は既に存在します")

def display_image_list(page_files, current_selected=None):
    """Display images in a traditional list view"""
    st.markdown("""
    <style>
    .image-list {
        border: 1px solid #ddd;
        border-radius: 5px;
        max-height: 400px;
        overflow-y: auto;
    }
    .image-item {
        padding: 8px;
        margin: 2px;
        cursor: pointer;
        border-bottom: 1px solid #eee;
    }
    .image-item:hover {
        background-color: #f1f1f1;
    }
    .image-item.selected {
        background-color: #e6f7ff;
        border-left: 3px solid #1890ff;
    }
    </style>
    <script>
    function selectImage(imageName) {
        const selectBox = document.querySelector('[data-testid="stSelectbox"]');
        if (selectBox) {
            // Set value and trigger change event
            selectBox.value = imageName;
            selectBox.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Start the list container
    list_html = '<div class="image-list">'
    
    # Add each image to the list
    for file in page_files:
        is_selected = file.name == current_selected
        selected_class = "selected" if is_selected else ""
        list_html += f'<div class="image-item {selected_class}" onclick="selectImage(\'{file.name}\')">{file.name}</div>'
    
    # Close the list container
    list_html += '</div>'
    
    # Display the list
    st.markdown(list_html, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Easy Renamer", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )
    
    # Improved CSS for performance
    st.markdown("""
    <style>
    /* Optimize for performance */
    .stApp {
        background-color: #F8F9FA;
    }
    
    /* Improve input field */
    .rename-input-container {
        margin: 15px 0;
        padding: 10px;
        background-color: #f0f7ff;
        border-radius: 5px;
        border: 1px solid #d0e3ff;
    }
    
    /* Custom header styles */
    .custom-header {
        font-size: 1.5rem;
        color: #1E3A8A;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    renamer = EasyRenamer()

    tab1, tab2, tab3, tab4 = st.tabs(["リネーム", "定型文管理", "検索ワード管理", "メタデータキーワード管理"])

    with tab1:
        st.header("📤 画像アップロード")
        
        # Cache uploaded files to prevent reloading
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = None
            
        uploaded_files = st.file_uploader(
            "画像をアップロード (最大2GB/ファイル)", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="最大2GBまでの画像をアップロードできます",
            key="file_uploader"
        )
        
        if uploaded_files:
            st.session_state.uploaded_files = uploaded_files

        if st.session_state.uploaded_files:
            # Pagination for image list
            page_size = 50
            total_pages = (len(st.session_state.uploaded_files) - 1) // page_size + 1
            
            col_page, col_info = st.columns([1, 3])
            with col_page:
                page_number = st.number_input(
                    "ページ", 
                    min_value=1, 
                    max_value=total_pages, 
                    value=1
                )
            
            with col_info:
                st.info(f"全 {len(st.session_state.uploaded_files)} 枚中 {page_size} 枚を表示中 (全 {total_pages} ページ)")
            
            start_idx = (page_number - 1) * page_size
            end_idx = min(start_idx + page_size, len(st.session_state.uploaded_files))
            page_files = st.session_state.uploaded_files[start_idx:end_idx]

            # Image selection and preview
            col1, col2 = st.columns([4, 6])
            
            with col1:
                st.subheader("画像一覧")
                
                # Use traditional list view for images
                image_names = [f.name for f in page_files]
                
                # Hidden selectbox to store current selection (controlled by JS)
                selected_image_name = st.selectbox(
                    "画像を選択", 
                    image_names,
                    key="image_selector",
                    label_visibility="collapsed"
                )
                
                # Display traditional list view
                display_image_list(page_files, selected_image_name)
                
                # Find the selected image file
                selected_image = next(f for f in page_files if f.name == selected_image_name)
                
                # Metadata keywords extraction (with performance optimization)
                metadata_keywords = renamer.extract_metadata_keywords(selected_image)
                
                if metadata_keywords:
                    st.write("抽出されたキーワード:", ", ".join(metadata_keywords))
                else:
                    st.write("キーワードが見つかりませんでした")

            with col2:
                st.subheader("画像プレビュー")
                
                # Cache images for better performance
                if selected_image_name not in st.session_state.image_cache:
                    # Load and process image
                    image = Image.open(selected_image)
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format)
                    st.session_state.image_cache[selected_image_name] = img_byte_arr.getvalue()
                
                # Display image with expansion option
                st.image(
                    st.session_state.image_cache[selected_image_name], 
                    caption=selected_image_name, 
                    use_column_width=True
                )

            # Rename settings
            st.header("🔢 リネーム設定")
            
            # Two columns for settings
            col_num, col_format = st.columns(2)
            
            with col_num:
                # Numbering position selection
                number_position = st.radio(
                    "連番の位置", 
                    ['prefix', 'suffix'], 
                    format_func=lambda x: '先頭' if x == 'prefix' else '末尾',
                    horizontal=True
                )
            
            with col_format:
                # Customizable numbering input
                custom_numbering = st.text_input(
                    "連番形式",
                    value="{n:02d}",
                    help="例: {n:02d} (数字2桁), A{n} (文字と数字の組み合わせ)"
                )
            
            # Rename blocks
            st.markdown('<div class="custom-header">📝 リネーム名称</div>', unsafe_allow_html=True)
            renamer.create_word_blocks(additional_keywords=metadata_keywords)
            
            # Rename input with improved styling
            st.markdown('<div class="rename-input-container">', unsafe_allow_html=True)
            rename_input = st.text_input(
                "リネーム名を入力", 
                key="rename_input",
                help="ワードブロックをドラッグ&ドロップで挿入できます"
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # Character count validation
            char_count = len(rename_input)
            if char_count > 130:
                st.markdown(f"<span style='color:red'>文字数: {char_count} (130文字を超えています)</span>", unsafe_allow_html=True)
            else:
                st.write(f"文字数: {char_count}")

            # Rename buttons in two columns for better UI
            col_rename, col_clear = st.columns([3, 1])
            
            with col_rename:
                rename_button = st.button("画像をリネーム", type="primary", use_container_width=True)
            
            with col_clear:
                if st.button("クリア", use_container_width=True):
                    st.session_state.rename_input = ""
                    st.experimental_rerun()

            # Rename processing
            if rename_button:
                if rename_input:
                    # Show progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("リネーム処理を開始します...")
                    time.sleep(0.5)  # Small delay for UI feedback
                    
                    # Execute rename process
                    rename_results = renamer.rename_files(
                        st.session_state.uploaded_files, 
                        rename_input, 
                        custom_numbering,
                        number_position
                    )
                    
                    # Update progress
                    progress_bar.progress(50)
                    status_text.text("リネーム処理完了、ZIPファイルを作成中...")
                    
                    # Create ZIP file
                    with open('renamed_images.zip', 'wb') as zipf:
                        shutil.make_archive('renamed_images', 'zip', 'renamed_images')
                    
                    # Complete progress
                    progress_bar.progress(100)
                    status_text.text("処理完了！")
                    
                    # Display results in scrollable area
                    st.subheader("リネーム結果")
                    
                    # Create scrollable results area
                    st.markdown("""
                    <style>
                    .results-container {
                        max-height: 200px;
                        overflow-y: auto;
                        padding: 10px;
                        background-color: #f8f9fa;
                        border-radius: 5px;
                        border: 1px solid #eaeaea;
                        margin-bottom: 15px;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    results_html = '<div class="results-container">'
                    for original, new_name in rename_results.items():
                        results_html += f"<p>{original} → {new_name}</p>"
                    results_html += '</div>'
                    
                    st.markdown(results_html, unsafe_allow_html=True)
                    
                    # Offer zip download
                    with open('renamed_images.zip', 'rb') as f:
                        st.download_button(
                            label="リネーム済み画像をダウンロード",
                            data=f.read(),
                            file_name='renamed_images.zip',
                            mime='application/zip',
                            use_container_width=True
                        )
                else:
                    st.warning("リネーム名を入力してください")

    # Word management tabs
    with tab2:
        st.header("📋 定型文管理")
        template_words = st.text_input("定型文を追加")
        if st.button("定型文を追加"):
            renamer.add_word('template_texts', template_words)
        
        # Display current template words with delete option
        st.subheader("現在の定型文:")
        
        # Use columns to display words in a grid
        cols = st.columns(3)
        for i, word in enumerate(st.session_state.settings['template_texts']):
            with cols[i % 3]:
                st.write(f"・{word}")

    with tab3:
        st.header("🔍 検索ワード管理")
        
        # Two columns for word management
        col1, col2 = st.columns(2)
        
        with col1:
            # Big words management
            st.subheader("大きめワード")
            big_word = st.text_input("大きめワードを追加")
            if st.button("大きめワードを追加"):
                renamer.add_word('big_words', big_word)
            
            # Display big words
            for word in st.session_state.settings['big_words']:
                st.write(f"・{word}")
        
        with col2:
            # Small words management
            st.subheader("小さめワード")
            small_word = st.text_input("小さめワードを追加")
            if st.button("小さめワードを追加"):
                renamer.add_word('small_words', small_word)
            
            # Display small words
            for word in st.session_state.settings['small_words']:
                st.write(f"・{word}")

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
        
        # Display metadata keywords in a more compact form
        st.subheader("現在のメタデータキーワード:")
        
        # Use columns to display words in a grid
        cols = st.columns(3)
        for i, word in enumerate(st.session_state.settings['metadata_keywords']):
            with cols[i % 3]:
                st.write(f"・{word}")

def main_wrapper():
    main()

if __name__ == "__main__":
    main_wrapper()
