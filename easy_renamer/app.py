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
                'Stable Diffusion': ['AI生成', 'デジタルアート'],
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
            # Get the file bytes
            file_bytes = image_file.getvalue()
            
            # Convert to PIL Image object
            image = Image.open(io.BytesIO(file_bytes))
            
            # Extract keywords from parameter string in the info dictionary
            param_str = image.info.get('parameters', '')
            
            # If parameters not found in standard location, try looking in Exif data
            if not param_str and hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                # Look for comment or user comment fields that might contain metadata
                for tag_id in exif or {}:
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ['UserComment', 'ImageDescription', 'Comment']:
                        exif_value = exif[tag_id]
                        if isinstance(exif_value, str) and len(exif_value) > 10:  # Arbitrary length to filter out non-useful comments
                            param_str = exif_value
                            break
            
            # Also try to extract from PNG text chunks
            if not param_str and image.format == 'PNG' and 'text' in image.info:
                for chunk_key, chunk_value in image.info['text'].items():
                    if 'prompt' in chunk_key.lower() or 'parameters' in chunk_key.lower():
                        param_str = chunk_value
                        break
            
            if param_str:
                # Search for AI keywords
                for keyword in self.ai_image_keywords:
                    if keyword.lower() in param_str.lower():
                        keywords.append(keyword)
                
                # Extract custom keywords - look for words in the prompt
                prompt_match = re.findall(r'\b\w+\b', param_str)
                keywords.extend(prompt_match[:10])  # Add first 10 keywords
                
                # Get mapped keywords from settings
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in st.session_state.settings['keyword_mappings']:
                        mapped_keywords.extend(st.session_state.settings['keyword_mappings'][keyword_lower])
                    
                # Also check for partial matches
                for extracted in keywords:
                    extracted_lower = extracted.lower()
                    for mapping_key in st.session_state.settings['keyword_mappings']:
                        if mapping_key in extracted_lower:
                            mapped_keywords.extend(st.session_state.settings['keyword_mappings'][mapping_key])
            
        except Exception as e:
            st.warning(f"メタデータ抽出中にエラーが発生: {str(e)}")
        
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
            cursor: pointer;
            font-weight: bold;
        }
        .word-block:hover {
            background-color: #1E90FF;
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
        """, unsafe_allow_html=True)

        # Create JavaScript for drag and drop + click functionality
        js_code = """
        <script>
        // Wait for document to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            setupWordBlocks();
        });
        
        // This function will be called when Streamlit reruns
        function setupWordBlocks() {
            // Find the rename input field
            var renameInput = document.querySelector('input[aria-label="リネーム名を入力"]');
            if (!renameInput) {
                // Try again in a moment if not found
                setTimeout(setupWordBlocks, 500);
                return;
            }
            
            // Set up all word blocks
            var wordBlocks = document.querySelectorAll('.word-block');
            wordBlocks.forEach(function(block) {
                // Set up draggable
                block.setAttribute('draggable', 'true');
                
                // Drag events
                block.addEventListener('dragstart', function(e) {
                    e.dataTransfer.setData('text/plain', block.innerText);
                });
                
                // Click event to add word to input
                block.addEventListener('click', function() {
                    var currentVal = renameInput.value;
                    var wordText = block.innerText;
                    
                    // Add space if needed
                    if (currentVal && !currentVal.endsWith(' ')) {
                        currentVal += ' ';
                    }
                    
                    renameInput.value = currentVal + wordText + ' ';
                    
                    // Trigger change event
                    var event = new Event('input', { bubbles: true });
                    renameInput.dispatchEvent(event);
                    
                    // Focus back on input
                    renameInput.focus();
                });
            });
            
            // Set up the input as drop target
            renameInput.addEventListener('dragover', function(e) {
                e.preventDefault();
            });
            
            renameInput.addEventListener('drop', function(e) {
                e.preventDefault();
                var data = e.dataTransfer.getData('text/plain');
                
                // Get cursor position
                var cursorPos = renameInput.selectionStart;
                var currentVal = renameInput.value;
                
                // Insert at cursor position
                var newVal = currentVal.substring(0, cursorPos) + data + ' ' + currentVal.substring(cursorPos);
                renameInput.value = newVal;
                
                // Trigger change event
                var event = new Event('input', { bubbles: true });
                renameInput.dispatchEvent(event);
                
                // Move cursor after inserted text
                renameInput.selectionStart = cursorPos + data.length + 1;
                renameInput.selectionEnd = cursorPos + data.length + 1;
            });
        }
        
        // Call setup after each Streamlit rerun
        if (window.parent) {
            // Watch for Streamlit rerun
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList' && mutation.addedNodes.length) {
                        setupWordBlocks();
                    }
                });
            });
            
            // Start observing
            observer.observe(document.body, { childList: true, subtree: true });
        }
        
        // Initial setup
        setupWordBlocks();
        </script>
        """
        
        # Display word blocks
        word_block_html = '<div class="word-blocks-container">'
        for word in all_words:
            word_block_html += f'<span class="word-block">{word}</span>'
        word_block_html += '</div>'
        
        # Display the HTML and JavaScript
        st.markdown(word_block_html + js_code, unsafe_allow_html=True)

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
                number_str = str(idx)  # Fallback if formatting fails
            
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

def display_image_list(files, current_selected=None):
    """Display images in a clickable list view"""
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
    }
    .image-item:hover {
        background-color: #333;
    }
    .image-item.selected {
        background-color: #4169E1;
        border-left: 3px solid #1890ff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create JavaScript for image selection
    js_code = """
    <script>
    // Function to select an image
    function selectImage(imageName) {
        // Update selected state in local storage
        localStorage.setItem('selectedImage', imageName);
        
        // Update UI to show selection
        const items = document.querySelectorAll('.image-item');
        items.forEach(item => {
            if (item.getAttribute('data-name') === imageName) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
        
        // Update hidden input to trigger form submission
        const hiddenInput = document.getElementById('selected-image-input');
        hiddenInput.value = imageName;
        
        // Submit the form
        const form = document.getElementById('image-selection-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
    
    // Set initial selection on page load
    document.addEventListener('DOMContentLoaded', function() {
        const selectedImage = localStorage.getItem('selectedImage');
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
    """
    
    # Start the list container and add hidden form
    html = f"""
    <form id="image-selection-form" action="">
        <input type="hidden" id="selected-image-input" name="selected_image" value="{current_selected or ''}">
        <div class="image-list">
    """
    
    # Add each image to the list
    for file in files:
        is_selected = file.name == current_selected
        selected_class = "selected" if is_selected else ""
        html += f'<div class="image-item {selected_class}" data-name="{file.name}" onclick="selectImage(\'{file.name}\')">{file.name}</div>'
    
    # Close the list container and form
    html += """
        </div>
    </form>
    """
    
    # Display the list and JavaScript
    st.markdown(html + js_code, unsafe_allow_html=True)

def update_file_numbering_preview(base_name, custom_numbering, number_position):
    """Update the file numbering preview"""
    try:
        sample_number = 1
        # Format the number according to the specified format
        formatted_number = custom_numbering.format(n=sample_number)
        
        # Create sample filename
        if number_position == 'prefix':
            sample_filename = f"{formatted_number}_{base_name}.jpg"
        else:  # suffix
            sample_filename = f"{base_name}_{formatted_number}.jpg"
            
        # Display preview
        return sample_filename
    except Exception as e:
        return f"プレビューエラー: {str(e)}"

def main():
    st.set_page_config(
        page_title="Easy Renamer", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )
    
    # Improved CSS for dark theme
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
    
    /* Preview area */
    .preview-container {
        background-color: #212121;
        border: 1px solid #4169E1;
        border-radius: 5px;
        padding: 10px;
        margin-top: 10px;
    }
    
    /* Drag handle for resize */
    .st-emotion-cache-13ln5th {
        resize: vertical;
        overflow: auto;
    }
    
    /* Make images responsive */
    img {
        max-width: 100%;
        height: auto;
        border-radius: 5px;
    }
    
    /* Image captions */
    .css-1aehpvj {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    renamer = EasyRenamer()

    tab1, tab2, tab3, tab4 = st.tabs(["リネーム", "定型文管理", "検索ワード管理", "キーワードマッピング"])

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

            # Get selection from query params or session state
            query_params = st.experimental_get_query_params()
            selected_from_form = st.query_params.get("selected_image", None)
            
            # Initialize or update selected image
            if selected_from_form:
                st.session_state.selected_image = selected_from_form
            elif 'selected_image' not in st.session_state and page_files:
                st.session_state.selected_image = page_files[0].name
                
            # Layout with side-by-side image list and preview
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("画像一覧")
                # Display clickable image list
                display_image_list(page_files, st.session_state.selected_image)
                
                # Find selected image file
                selected_image = next((f for f in page_files if f.name == st.session_state.selected_image), None)
                
                # Extract metadata from selected image
                metadata_result = {"extracted": [], "mapped": []}
                if selected_image:
                    metadata_result = renamer.extract_metadata_keywords(selected_image)
                    # Store mapped keywords for use in word blocks
                    st.session_state.extracted_keywords = metadata_result.get('mapped', [])
            
            with col2:
                st.subheader("画像プレビュー")
                
                if selected_image:
                    # Cache images for better performance
                    if st.session_state.selected_image not in st.session_state.image_cache:
                        # Load and process image
                        image = Image.open(selected_image)
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format=image.format)
                        st.session_state.image_cache[st.session_state.selected_image] = img_byte_arr.getvalue()
                    
                    # Display image
                    st.image(
                        st.session_state.image_cache[st.session_state.selected_image], 
                        caption=st.session_state.selected_image, 
                        use_column_width=True
                    )
                    
                    # Show extracted metadata
                    with st.expander("メタデータキーワード"):
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
            
            # Rename section - moved below image preview for better workflow
            st.header("🏷️ リネーム設定")
            
            # Word blocks for drag and drop
            st.markdown('<div class="custom-header">ワードブロック</div>', unsafe_allow_html=True)
            renamer.create_word_blocks(additional_keywords=st.session_state.extracted_keywords)
            
            # Two columns for rename UI
            col_rename, col_numbering = st.columns([3, 1])
            
            with col_rename:
                # Rename input with improved styling
                st.markdown('<div class="rename-input-container">', unsafe_allow_html=True)
                rename_input = st.text_input(
                    "リネーム名を入力", 
                    key="rename_input",
                    help="ワードブロックをドラッグ&ドロップまたはクリックして挿入できます"
                )
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Character count validation
                char_count = len(rename_input)
                if char_count > 130:
                    st.markdown(f"<span style='color:red'>文字数: {char_count} (130文字を超えています)</span>", unsafe_allow_html=True)
                else:
                    st.write(f"文字数: {char_count}")
            
            with col_numbering:
                st.subheader("連番設定")
                
                # Numbering position selection
                number_position = st.radio(
                    "連番の位置", 
                    ['prefix', 'suffix'], 
                    format_func=lambda x: '先頭' if x == 'prefix' else '末尾',
                    horizontal=True,
                    key="number_position"
                )
                
                # Customizable numbering input
                custom_numbering = st.text_input(
                    "連番形式",
                    value="{n:02d}",
                    help="例: {n:02d} (数字2桁), A{n} (文字と数字の組み合わせ)",
                    key="custom_numbering"
                )
                
                # Real-time preview
                if rename_input:
                    preview = update_file_numbering_preview(rename_input, custom_numbering, number_position)
                    st.markdown(f"""
                    <div class="preview-container">
                        <strong>ファイル名プレビュー:</strong><br>
                        {preview}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Rename buttons
            col_rename_btn, col_clear = st.columns([3, 1])
            
            with col_rename_btn:
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
                    results_html = '<div class="results-container" style="max-height:200px;overflow-y:auto;padding:10px;">'
                    for original, new_name in rename_results.items():
                        results_html += f"<p>{original} → {new_name}</p>"
                    results_html += '</div>'
                    
                    st.markdown(results_html, unsafe_allow_html=True)
                    
                    # Offer zip download
                    with open('renamed_images.zip', 'rb') as f:
                        st.download_button(
                            label="リネーム済み
