import streamlit as st
import os
import shutil
import io
import time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from modules.renamer import EasyRenamer
from modules.ui_components import (
    load_css, 
    create_image_list_component, 
    create_word_blocks_component,
    create_format_preview
)

def main():
    # Page configuration
    st.set_page_config(
        page_title="Easy Renamer", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )
    
    # Load custom CSS
    load_css()
    
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    # Initialize the renamer
    renamer = EasyRenamer()

    # Create tabs
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
            # Create a three-column layout for better organization
            col_list, col_rename, col_preview = st.columns([1, 1, 1])
            
            # Pagination for image list
            page_size = 50
            total_pages = (len(st.session_state.uploaded_files) - 1) // page_size + 1
            
            with col_list:
                st.subheader("画像一覧")
                
                col_page, col_info = st.columns([1, 1])
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
                
                # Display clickable image list
                selected_image_name = create_image_list_component(page_files, st.session_state.get('selected_image'))
                
                # Update session state
                st.session_state.selected_image = selected_image_name
            
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
                        index=0 if st.session_state.number_position == 'prefix' else 1,
                        key="number_position_radio"
                    )
                
                with col_format:
                    # Customizable numbering input
                    st.session_state.custom_numbering = st.text_input(
                        "連番形式",
                        value=st.session_state.custom_numbering,
                        help="例: {n:02d} (数字2桁), A{n} (文字と数字の組み合わせ)",
                        key="custom_numbering_input"
                    )
                
                # Show preview of the format
                create_format_preview(st.session_state.custom_numbering, 
                                     st.session_state.number_position, 
                                     "ファイル名")
                
                # Find the selected image file
                selected_image = next((f for f in st.session_state.uploaded_files if f.name == selected_image_name), None)
                
                # Extract and display metadata
                st.subheader("メタデータキーワード")
                
                # Initialize metadata cache if needed
                if 'metadata_cache' not in st.session_state:
                    st.session_state.metadata_cache = {}
                
                # Extract metadata and mapped keywords
                if selected_image:
                    # Extract metadata
                    metadata_result = renamer.extract_metadata_keywords(selected_image)
                    
                    # Store extracted keywords for word blocks
                    if 'extracted_keywords' not in st.session_state:
                        st.session_state.extracted_keywords = []
                    
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
                
                # Create word blocks with improved functionality
                create_word_blocks_component(renamer, st.session_state.extracted_keywords)
                
                # Rename input with improved styling
                st.markdown('<div class="rename-input-container">', unsafe_allow_html=True)
                rename_input = st.text_input(
                    "リネーム名を入力", 
                    key="rename_input_field",
                    help="ワードブロックをクリックまたはドラッグ&ドロップで挿入できます",
                    value=st.session_state.rename_input
                )
                # Update session state for rename input
                st.session_state.rename_input = rename_input
                st.markdown('</div>', unsafe_allow_html=True)

                # Character count validation
                char_count = len(rename_input)
                if char_count > 130:
                    st.markdown(f"<span style='color:red'>文字数: {char_count} (130文字を超えています)</span>", unsafe_allow_html=True)
                else:
                    st.write(f"文字数: {char_count}")

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
                        
                        # Display download button
                        with open("renamed_images.zip", "rb") as file:
                            st.download_button(
                                label="ZIPファイルをダウンロード",
                                data=file,
                                file_name="renamed_images.zip",
                                mime="application/zip"
                            )
                        
                        # Display results
                        st.subheader("リネーム結果")
                        for original, new_name in rename_results.items():
                            st.write(f"{original} → {new_name}")
                    else:
                        st.error("リネーム名を入力してください")
                
            # Find the selected image file
            selected_image = next((f for f in st.session_state.uploaded_files if f.name == selected_image_name), None)
            
            with col_preview:
                st.subheader("画像プレビュー")
                
                if selected_image:
                    # Initialize image cache if needed
                    if 'image_cache' not in st.session_state:
                        st.session_state.image_cache = {}
                        
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

    with tab2:
        st.header("📋 定型文管理")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("登録済み定型文")
            
            # Display existing templates
            for idx, template in enumerate(st.session_state.settings['template_texts']):
                col_text, col_delete = st.columns([3, 1])
                with col_text:
                    st.text(template)
                with col_delete:
                    if st.button("削除", key=f"del_template_{idx}"):
                        st.session_state.settings['template_texts'].pop(idx)
                        renamer.save_settings()
                        st.experimental_rerun()
        
        with col2:
            st.subheader("新規定型文登録")
            new_template = st.text_input("新しい定型文")
            if st.button("追加", key="add_template"):
                renamer.add_word('template_texts', new_template)
                st.experimental_rerun()

    with tab3:
        st.header("🔍 検索ワード管理")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("ビッグワード")
            
            # Existing big words
            for idx, word in enumerate(st.session_state.settings['big_words']):
                col_text, col_delete = st.columns([3, 1])
                with col_text:
                    st.text(word)
                with col_delete:
                    if st.button("削除", key=f"del_big_{idx}"):
                        st.session_state.settings['big_words'].pop(idx)
                        renamer.save_settings()
                        st.experimental_rerun()
            
            # Add new big word
            new_big_word = st.text_input("新しいビッグワード")
            if st.button("追加", key="add_big"):
                renamer.add_word('big_words', new_big_word)
                st.experimental_rerun()
        
        with col2:
            st.subheader("スモールワード")
            
            # Existing small words
            for idx, word in enumerate(st.session_state.settings['small_words']):
                col_text, col_delete = st.columns([3, 1])
                with col_text:
                    st.text(word)
                with col_delete:
                    if st.button("削除", key=f"del_small_{idx}"):
                        st.session_state.settings['small_words'].pop(idx)
                        renamer.save_settings()
                        st.experimental_rerun()
            
            # Add new small word
            new_small_word = st.text_input("新しいスモールワード")
            if st.button("追加", key="add_small"):
                renamer.add_word('small_words', new_small_word)
                st.experimental_rerun()

    with tab4:
        st.header("📝 メタデータキーワード管理")
        
        # Existing metadata keywords
        st.subheader("登録済みキーワード")
        for idx, word in enumerate(st.session_state.settings['metadata_keywords']):
            col_text, col_delete = st.columns([3, 1])
            with col_text:
                st.text(word)
            with col_delete:
                if st.button("削除", key=f"del_meta_{idx}"):
                    st.session_state.settings['metadata_keywords'].pop(idx)
                    renamer.save_settings()
                    st.experimental_rerun()
        
        # Add new metadata keyword
        st.subheader("新規キーワード登録")
        new_metadata = st.text_input("新しいメタデータキーワード")
        if st.button("追加", key="add_meta"):
            renamer.add_word('metadata_keywords', new_metadata)
            st.experimental_rerun()

    with tab5:
        st.header("🔄 キーワードマッピング")
        
        # Display existing mappings
        st.subheader("登録済みマッピング")
        for idx, (keyword, mapped_words) in enumerate(st.session_state.settings['keyword_mappings'].items()):
            col_key, col_mapped, col_delete = st.columns([1, 2, 1])
            with col_key:
                st.text(keyword)
            with col_mapped:
                st.text(", ".join(mapped_words))
            with col_delete:
                if st.button("削除", key=f"del_map_{idx}"):
                    del st.session_state.settings['keyword_mappings'][keyword]
                    renamer.save_settings()
                    st.experimental_rerun()
        
        # Add new mapping
        st.subheader("新規マッピング登録")
        col1, col2 = st.columns(2)
        with col1:
            new_keyword = st.text_input("キーワード（元の値）")
        with col2:
            mapped_values = st.text_input("マッピング先（カンマ区切り）")
            
        if st.button("追加", key="add_mapping"):
            if renamer.add_keyword_mapping(new_keyword, mapped_values):
                st.success(f"キーワードマッピングを追加しました: {new_keyword}")
                st.experimental_rerun()
            else:
                st.error("キーワードを入力してください")

if __name__ == "__main__":
    main()
