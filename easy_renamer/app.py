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
            
        if 'extracted_keywords' not in st.session_state:
            st.session_state.extracted_keywords = []
        
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
            'metadata_keywords': [],
            'keyword_mappings': {
                'Stable Diffusion': ['AI生成', 'デジタル'],
                'anime': ['アニメ', '漫画風'],
                'character': ['キャラクター', '人物'],
                'portrait': ['ポートレート', '肖像画'],
                'landscape': ['風景', '自然']
            }
        }
        
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                st.session_state.settings = json.load(f)
                # Ensure keyword_mappings exists in loaded settings
                if 'keyword_mappings' not in st.session_state.settings:
                    st.session_state.settings['keyword_mappings'] = default_settings['keyword_mappings']
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
        mapped_keywords = []
        try:
            # Convert to PIL Image object
            image = Image.open(image_file)
            
            # Try to extract parameters from image info
            param_str = ""
            if 'parameters' in image.info:
                param_str = image.info['parameters']
            elif 'comment' in image.info:
                param_str = image.info['comment']
            elif hasattr(image, '_getexif') and image._getexif():
                exif = {TAGS.get(k, k): v for k, v in image._getexif().items()}
                if 'UserComment' in exif:
                    param_str = str(exif['UserComment'])
                elif 'ImageDescription' in exif:
                    param_str = str(exif['ImageDescription'])
            
            # Convert bytes to string if needed
            if isinstance(param_str, bytes):
                try:
                    param_str = param_str.decode('utf-8', errors='ignore')
                except:
                    param_str = str(param_str)
            
            if param_str:
                # Search for AI keywords
                for keyword in self.ai_image_keywords:
                    if keyword.lower() in param_str.lower():
                        keywords.append(keyword)
                
                # Extract custom keywords - look for words and phrases
                prompt_match = re.findall(r'\b[A-Za-z0-9]+\b', param_str.lower())
                keywords.extend(prompt_match[:10])  # Add first 10 keywords
                
                # Look for Japanese words (hiragana, katakana, kanji)
                ja_words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', param_str)
                keywords.extend(ja_words[:5])  # Add first 5 Japanese keywords
                
                # Get mapped keywords from settings
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in st.session_state.settings['keyword_mappings']:
                        mapped_keywords.extend(st.session_state.settings['keyword_mappings'][keyword_lower])
                    
                    # Also check for partial matches
                    for mapping_key in st.session_state.settings['keyword_mappings']:
                        if mapping_key.lower() in keyword_lower or keyword_lower in mapping_key.lower():
                            mapped_keywords.extend(st.session_state.settings['keyword_mappings'][mapping_key])
        
        except Exception as e:
            st.warning(f"メタデータの抽出中にエラーが発生: {str(e)}")
        
        # Cache the results
        unique_keywords = list(set(keywords))  # Remove duplicates
        unique_mapped = list(set(mapped_keywords))  # Remove duplicates
        
        result = {
            'extracted': unique_keywords,
            'mapped': unique_mapped
        }
        
        st.session_state.metadata_cache[image_file.name] = result
        return result

    def create_word_blocks(self, additional_keywords=None):
        """Create clickable word blocks"""
        # Combine all words
        all_words = (
            st.session_state.settings['template_texts'] + 
            st.session_state.settings['big_words'] + 
            st.session_state.settings['small_words'] +
            st.session_state.settings['metadata_keywords']
        )
        
        # Add metadata keywords if provided
        if additional_keywords:
            all_words.extend(additional_keywords)
            
        # Remove duplicates while preserving order
        all_words = list(dict.fromkeys(all_words))
        
        # Word block HTML/CSS with click and drag events
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
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.1s ease-in-out;
        }
        .word-block:hover {
            transform: scale(1.05);
            background-color: #1E90FF;
        }
        .word-block:active {
            transform: scale(0.95);
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
            border: 1px solid #4169E1;
            border-radius: 5px;
            background-color: #121212;
        }
        </style>
        <script>
        // Wait for the page to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            // Add click handler to word blocks
            attachWordBlockHandlers();
        });

        function attachWordBlockHandlers() {
            const wordBlocks = document.querySelectorAll('.word-block');
            const renameInput = document.getElementById('rename-input');
            
            if (!renameInput) {
                // If the input element doesn't exist yet, try again in a moment
                setTimeout(attachWordBlockHandlers, 300);
                return;
            }
            
            wordBlocks.forEach(block => {
                // Add click event
                block.addEventListener('click', function() {
                    const wordText = this.innerText;
                    insertTextAtCursor(renameInput, " " + wordText + " ");
                });
                
                // Add drag events
                block.setAttribute('draggable', 'true');
                block.addEventListener('dragstart', function(event) {
                    event.dataTransfer.setData("text", this.innerText);
                });
            });
            
            // Add drop event to the rename input
            renameInput.addEventListener('dragover', function(event) {
                event.preventDefault();
            });
            
            renameInput.addEventListener('drop', function(event) {
                event.preventDefault();
                const data = event.dataTransfer.getData("text");
                insertTextAtCursor(this, " " + data + " ");
            });
        }

        function insertTextAtCursor(input, text) {
            const startPos = input.selectionStart;
            const endPos = input.selectionEnd;
            
            const currentValue = input.value;
            const newValue = 
                currentValue.slice(0, startPos) + 
                text + 
                currentValue.slice(endPos);
            
            input.value = newValue.replace(/\\s+/g, ' ').trim();
            
            // Update Streamlit's state
            const event = new Event('input');
            input.dispatchEvent(event);
            
            // Set cursor position after inserted text
            input.selectionStart = startPos + text.length;
            input.selectionEnd = startPos + text.length;
            input.focus();
        }
        
        // Run the attachment function whenever Streamlit reloads
        // This ensures the handlers work after each page refresh
        const observer = new MutationObserver(function(mutations) {
            attachWordBlockHandlers();
        });
        
        // Start observing the document for changes
        observer.observe(document, { childList: true, subtree: true });
        </script>
        """, unsafe_allow_html=True)
        
        # Display word blocks
        word_block_html = '<div class="word-blocks-container">'
        for word in all_words:
            word_block_html += f'<span class="word-block">{word}</span>'
        word_block_html += '</div>'
        
        st.markdown(word_block_html, unsafe_allow_html=True)

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
            try:
                number_str = custom_numbering.format(n=idx)
            except Exception as e:
                number_str = str(idx)  # Fallback to simple numbering
            
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
            
    def add_keyword_mapping(self, keyword, mapped_words):
        """Add a new keyword mapping"""
        if not keyword:
            return False
            
        # Split the mapped words by comma
        mapped_list = [word.strip() for word in mapped_words.split(',') if word.strip()]
        
        # Add or update the mapping
        if keyword.lower() not in st.session_state.settings['keyword_mappings']:
            st.session_state.settings['keyword_mappings'][keyword.lower()] = mapped_list
        else:
            # Update existing mapping
            st.session_state.settings['keyword_mappings'][keyword.lower()] = mapped_list
            
        self.save_settings()
        return True

def display_image_list(page_files, current_selected=None):
    """Display images in a traditional list view with improved interactivity"""
    st.markdown("""
    <style>
    .image-list {
        border: 1px solid #4169E1;
        border-radius: 5px;
        max-height: 400px;
        overflow-y: auto;
        background-color: #212121;
        color: white;
    }
    .image-item {
        padding: 8px;
        margin: 2px;
        cursor: pointer;
        border-bottom: 1px solid #333;
        transition: background-color 0.2s ease;
    }
    .image-item:hover {
        background-color: #333;
    }
    .image-item.selected {
        background-color: #4169E1;
        border-left: 3px solid #1890ff;
    }
    </style>
    <script>
    function selectImage(imageName) {
        // Set the selected image name in sessionStorage
        sessionStorage.setItem('selectedImage', imageName);
        
        // Update the UI to show the image as selected
        const items = document.querySelectorAll('.image-item');
        items.forEach(item => {
            if (item.getAttribute('data-name') === imageName) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
        
        // Create a new form submission to update the page
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = window.location.href;
        
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selectedImage';
        input.value = imageName;
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }
    
    // Run this when the page loads to restore any selection
    document.addEventListener('DOMContentLoaded', function() {
        const selectedImage = sessionStorage.getItem('selectedImage');
        if (selectedImage) {
            const items = document.querySelectorAll('.image-item');
            items.forEach(item => {
                if (item.getAttribute('data-name') === selectedImage) {
                    item.classList.add('selected');
                }
            });
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Start the list container
    list_html = '<div class="image-list">'
    
    # Add each image to the list
    for file in page_files:
        is_selected = file.name == current_selected
        selected_class = "selected" if is_selected else ""
        list_html += f'<div class="image-item {selected_class}" data-name="{file.name}" onclick="selectImage(\'{file.name}\')">{file.name}</div>'
    
    # Close the list container
    list_html += '</div>'
    
    # Display the list
    st.markdown(list_html, unsafe_allow_html=True)

def format_preview(numbering_format, position, base_name):
    """Format a preview of the file naming based on current settings"""
    try:
        number_str = numbering_format.format(n=1)
        if position == 'prefix':
            return f"{number_str}_{base_name}.jpg"
        else:
            return f"{base_name}_{number_str}.jpg"
    except Exception:
        return "フォーマットエラー"

def main():
    st.set_page_config(
        page_title="Easy Renamer", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )
    
    # Improved CSS for dark theme and interactivity
    st.markdown("""
    <style>
    /* Dark theme for performance */
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }
    
    /* Improve input field */
    .rename-input-container {
        margin: 15px 0;
        padding: 10px;
        background-color: #212121;
        border-radius: 5px;
        border: 1px solid #4169E1;
    }
    
    /* Custom header styles */
    .custom-header {
        font-size: 1.5rem;
        color: #FFFFFF;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    
    /* Style for inputs */
    input, select, textarea {
        background-color: #333 !important;
        color: white !important;
        border: 1px solid #4169E1 !important;
    }
    
    /* Style for buttons */
    button {
        background-color: #4169E1 !important;
        color: white !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #212121;
        border-radius: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #FFFFFF;
    }
    
    /* Results area */
    .results-container {
        background-color: #212121 !important;
        color: white !important;
        border: 1px solid #4169E1 !important;
    }
    
    /* Image captions */
    .css-1aehpvj {
        color: #FFFFFF !important;
    }
    
    /* Add style for image selection */
    img.selected {
        border: 3px solid #4169E1;
    }
    
    /* Format preview */
    .format-preview {
        padding: 5px 10px;
        background-color: #333;
        border-radius: 5px;
        margin-top: 5px;
        font-family: monospace;
    }
    
    /* Improve tooltip styling */
    [data-tooltip]:hover::before {
        background-color: #4169E1;
        color: white;
        border-radius: 4px;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    renamer = EasyRenamer()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["リネーム", "定型文管理", "検索ワード管理", "メタデータキーワード管理", "キーワードマッピング"])

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

            # Initialize or get selected image
            if 'selected_image' not in st.session_state and page_files:
                st.session_state.selected_image = page_files[0].name
            
            # Get image name from query params or form data if available
            params = st.experimental_get_query_params()
            if 'selectedImage' in params:
                st.session_state.selected_image = params['selectedImage'][0]
            
            # Check for POST data with selected image
            try:
                for key in st.request_form:
                    if key == 'selectedImage':
                        st.session_state.selected_image = st.request_form[key]
            except:
                pass

            # Create a two-column layout - left for image list/preview, right for rename options
            col_images, col_rename = st.columns([1, 1])
            
            with col_images:
                st.subheader("画像一覧")
                
                # Get image names
                image_names = [f.name for f in page_files]
                
                # Get selected image from session state
                selected_image_name = st.session_state.selected_image if st.session_state.selected_image in image_names else image_names[0]
                
                # Display clickable image list
                display_image_list(page_files, selected_image_name)
                
                # Update session state
                st.session_state.selected_image = selected_image_name
                
                # Find the selected image file
                selected_image = next((f for f in page_files if f.name == selected_image_name), None)
                
                st.subheader("画像プレビュー")
                if selected_image:
                    # Cache images for better performance
                    if selected_image_name not in st.session_state.image_cache:
                        # Load and process image
                        image = Image.open(selected_image)
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format=image.format if image.format else 'JPEG')
                        st.session_state.image_cache[selected_image_name] = img_byte_arr.getvalue()
                    
                    # Display image
                    st.image(
                        st.session_state.image_cache[selected_image_name], 
                        caption=selected_image_name, 
                        use_column_width=True
                    )
            
            with col_rename:
                # Rename settings
                st.header("🔢 リネーム設定")
                
                # Initialize rename_input in session state if not present
                if 'rename_input' not in st.session_state:
                    st.session_state.rename_input = ""
                
                # Initialize format settings
                if 'number_position' not in st.session_state:
                    st.session_state.number_position = 'suffix'
                    
                if 'custom_numbering' not in st.session_state:
                    st.session_state.custom_numbering = "{n:02d}"
                
                # Two columns for settings
                col_num, col_format = st.columns(2)
                
                with col_num:
                    # Numbering position selection
                    st.session_state.number_position = st.radio(
                        "連番の位置", 
                        ['prefix', 'suffix'], 
                        format_func=lambda x: '先頭' if x == 'prefix' else '末尾',
                        horizontal=True,
                        index=0 if st.session_state.number_position == 'prefix' else 1
                    )
                
                with col_format:
                    # Customizable numbering input
                    st.session_state.custom_numbering = st.text_input(
                        "連番形式",
                        value=st.session_state.custom_numbering,
                        help="例: {n:02d} (数字2桁), A{n} (文字と数字の組み合わせ)"
                    )
                
                # Show preview of the format
                st.markdown('<div class="format-preview">' + 
                           format_preview(st.session_state.custom_numbering, 
                                         st.session_state.number_position, 
                                         "ファイル名") + '</div>', 
                           unsafe_allow_html=True)
                
                # Metadata extraction if an image is selected
                if selected_image:
                    st.subheader("メタデータキーワード")
                    
                    # Extract metadata
                    metadata_result = renamer.extract_metadata_keywords(selected_image)
                    
                    # Store the result for use in word blocks
                    st.session_state.extracted_keywords = metadata_result.get('mapped', [])
                    
                    if metadata_result:
                        col_ex, col_map = st.columns(2)
                        
                        with col_ex:
                            st.write("抽出されたキーワード:")
                            if metadata_result.get('extracted'):
                                st.write(", ".join(metadata_result['extracted']))
                            else:
                                st.write("なし")
                                
                        with col_map:
                            st.write("マッピングされたキーワード:")
                            if metadata_result.get('mapped'):
                                st.write(", ".join(metadata_result['mapped']))
                            else:
                                st.write("なし")
                    else:
                        st.warning("メタデータが見つかりませんでした")
                
                # Rename blocks
                st.markdown('<div class="custom-header">📝 リネーム用ワードブロック</div>', unsafe_allow_html=True)
                renamer.create_word_blocks(additional_keywords=st.session_state.extracted_keywords)
                
                # Rename input with improved styling
                st.markdown('<div class="rename-input-container">', unsafe_allow_html=True)
                rename_input = st.text_input(
                    "リネーム名を入力", 
                    key="rename_input",
                    help="ワードブロックをクリックまたはドラッグ&ドロップで挿入できます",
                    value=st.session_state.rename_input
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
                            st.session_state.custom_numbering,
                            st.session_state.number_position
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
                        results_html = '<div class="results-container" style="max
