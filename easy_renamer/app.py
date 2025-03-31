import streamlit as st
import os
import json
import base64
import piexif
import re
from PIL import Image
from io import BytesIO
import pandas as pd

# セッション状態の初期化
if 'current_folder' not in st.session_state:
    st.session_state.current_folder = ""
if 'image_list' not in st.session_state:
    st.session_state.image_list = []
if 'current_image_idx' not in st.session_state:
    st.session_state.current_image_idx = -1
if 'use_sequence' not in st.session_state:
    st.session_state.use_sequence = False
if 'seq_start' not in st.session_state:
    st.session_state.seq_start = 1
if 'seq_digits' not in st.session_state:
    st.session_state.seq_digits = 3
if 'template_text' not in st.session_state:
    st.session_state.template_text = ""
if 'new_filename' not in st.session_state:
    st.session_state.new_filename = ""
if 'current_metadata' not in st.session_state:
    st.session_state.current_metadata = ""
if 'word_blocks' not in st.session_state:
    st.session_state.word_blocks = []

# 設定ファイルの読み込み
def load_word_data():
    try:
        if os.path.exists("word_data.json"):
            with open("word_data.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルトの単語データ
            default_data = {
                "キャラクター": [],
                "髪色": ["赤髪", "青髪", "金髪", "黒髪", "白髪", "緑髪", "紫髪", "ピンク髪"],
                "瞳の色": ["赤瞳", "青瞳", "緑瞳", "金瞳", "黒瞳", "紫瞳"],
                "服装": ["制服", "ドレス", "水着", "メイド服", "コスプレ"],
                "その他": []
            }
            with open("word_data.json", 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data
    except Exception as e:
        st.error(f"単語データの読み込みエラー: {str(e)}")
        return {}

# 画像のメタデータを抽出
def extract_metadata(image_path):
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
                        word_list = extract_words(prompt)
            
            # PNGメタデータのチェック
            if not word_list and img.format == "PNG" and "parameters" in img.info:
                parameters = img.info["parameters"]
                metadata_text = parameters
                word_list = extract_words(parameters)
    except Exception as e:
        metadata_text = f"メタデータの読み込みエラー: {str(e)}"
    
    return metadata_text, word_list

# テキストから単語を抽出
def extract_words(text):
    words = []
    # カンマで区切られた単語を抽出
    for word in re.split(r'[,、]', text):
        word = word.strip()
        if word:
            words.append(word)
    return words

# 画像のパスを取得
def get_image_path(index):
    if 0 <= index < len(st.session_state.image_list):
        return os.path.join(st.session_state.current_folder, st.session_state.image_list[index])
    return None

# 画像を読み込む
def load_image(image_path):
    try:
        with open(image_path, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"画像の読み込みエラー: {str(e)}")
        return None

# 画像をリネーム
def rename_image(old_path, new_name):
    try:
        ext = os.path.splitext(old_path)[1]
        new_path = os.path.join(os.path.dirname(old_path), new_name + ext)
        
        # 同じ名前なら何もしない
        if old_path == new_path:
            return True, "ファイル名は変更されていません"
        
        # 既に存在する場合は確認
        if os.path.exists(new_path):
            return False, f"{new_name + ext}は既に存在します"
        
        os.rename(old_path, new_path)
        return True, f"リネーム完了: {new_name + ext}"
    except Exception as e:
        return False, f"リネームエラー: {str(e)}"

# 連番設定を適用
def apply_sequence():
    if not st.session_state.use_sequence or st.session_state.current_image_idx < 0:
        return
    
    # 既存の連番を削除
    filename = st.session_state.new_filename
    filename = re.sub(r'_\d+$', '', filename)
    
    # 連番を追加
    current_num = st.session_state.seq_start + st.session_state.current_image_idx
    seq_str = f"_{current_num:0{st.session_state.seq_digits}d}"
    st.session_state.new_filename = filename + seq_str

# 文字数をカウント
def count_chars(text):
    count = 0
    for char in text:
        if ord(char) <= 255:  # 半角
            count += 0.5
        else:  # 全角
            count += 1
    return count

# 画像を表示
def display_image(index):
    if 0 <= index < len(st.session_state.image_list):
        st.session_state.current_image_idx = index
        image_path = get_image_path(index)
        
        if image_path:
            # 画像の表示
            image_data = load_image(image_path)
            if image_data:
                # 画像のファイル名を設定
                filename = st.session_state.image_list[index]
                st.session_state.new_filename = os.path.splitext(filename)[0]
                
                # メタデータを抽出
                metadata_text, word_list = extract_metadata(image_path)
                st.session_state.current_metadata = metadata_text
                st.session_state.word_blocks = word_list
                
                # 連番設定の適用
                apply_sequence()
                
                return image_data
    return None

# 一括リネーム
def rename_all_images():
    if not st.session_state.image_list:
        return "画像がありません"
    
    base_name = st.session_state.new_filename
    # 連番パターンを削除
    base_name = re.sub(r'_\d+$', '', base_name)
    
    success_count = 0
    failed_count = 0
    
    for i, image in enumerate(st.session_state.image_list):
        old_path = os.path.join(st.session_state.current_folder, image)
        ext = os.path.splitext(old_path)[1]
        
        if st.session_state.use_sequence:
            new_name = f"{base_name}_{st.session_state.seq_start + i:0{st.session_state.seq_digits}d}"
        else:
            new_name = base_name
            
        new_path = os.path.join(st.session_state.current_folder, new_name + ext)
        
        try:
            if os.path.exists(new_path) and old_path != new_path:
                failed_count += 1
                continue
            
            os.rename(old_path, new_path)
            st.session_state.image_list[i] = new_name + ext
            success_count += 1
        except Exception as e:
            failed_count += 1
    
    return f"{success_count}枚のリネームに成功、{failed_count}枚は失敗しました"

# メインアプリ
def main():
    st.set_page_config(page_title="EasyRenamer - 画像リネームツール", layout="wide")
    
    st.title("EasyRenamer - 画像リネームツール")
    
    # サイドバー：フォルダ選択
    with st.sidebar:
        st.header("フォルダ選択")
        folder_path = st.text_input("フォルダパス", value=st.session_state.current_folder)
        
        if st.button("フォルダ読み込み"):
            if os.path.isdir(folder_path):
                st.session_state.current_folder = folder_path
                # 画像ファイルのみを読み込む
                image_files = [f for f in os.listdir(folder_path) 
                            if os.path.isfile(os.path.join(folder_path, f)) and 
                            f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
                st.session_state.image_list = image_files
                st.session_state.current_image_idx = 0 if image_files else -1
                st.success(f"{len(image_files)}枚の画像を読み込みました")
                st.rerun()
            else:
                st.error("有効なフォルダパスを入力してください")
        
        # 連番設定
        st.header("連番設定")
        use_seq = st.checkbox("連番を使用する", value=st.session_state.use_sequence)
        if use_seq != st.session_state.use_sequence:
            st.session_state.use_sequence = use_seq
            apply_sequence()
            st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            seq_start = st.number_input("開始番号", min_value=1, value=st.session_state.seq_start)
            if seq_start != st.session_state.seq_start:
                st.session_state.seq_start = seq_start
                apply_sequence()
                st.rerun()
        
        with col2:
            seq_digits = st.number_input("桁数", min_value=1, max_value=5, value=st.session_state.seq_digits)
            if seq_digits != st.session_state.seq_digits:
                st.session_state.seq_digits = seq_digits
                apply_sequence()
                st.rerun()
        
        # 定型文設定
        st.header("定型文設定")
        template = st.text_input("定型文", value=st.session_state.template_text)
        if st.button("定型文を適用"):
            st.session_state.template_text = template
            st.session_state.new_filename = template
            apply_sequence()
            st.rerun()
    
    # メインコンテンツ
    if not st.session_state.image_list:
        st.info("フォルダを選択して画像を読み込んでください")
    else:
        # 画像一覧と画像表示を2カラムレイアウトで表示
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("画像一覧")
            # 画像一覧の表示（データフレームを使用）
            image_df = pd.DataFrame(st.session_state.image_list, columns=["ファイル名"])
            selected_index = st.selectbox("画像を選択", range(len(image_df)), 
                                       format_func=lambda i: image_df.loc[i, "ファイル名"],
                                       index=st.session_state.current_image_idx if st.session_state.current_image_idx >= 0 else 0)
            
            if selected_index != st.session_state.current_image_idx:
                image_data = display_image(selected_index)
                if image_data:
                    st.rerun()
        
        with col2:
            st.subheader("画像プレビュー")
            if st.session_state.current_image_idx >= 0:
                image_path = get_image_path(st.session_state.current_image_idx)
                if image_path:
                    image_data = load_image(image_path)
                    if image_data:
                        st.image(image_data, width=400)
                        
                        # 現在のファイル名と新しいファイル名
                        current_filename = st.session_state.image_list[st.session_state.current_image_idx]
                        st.text(f"現在のファイル名: {current_filename}")
                        
                        # 新しいファイル名の入力
                        new_filename = st.text_input("新しいファイル名", value=st.session_state.new_filename)
                        if new_filename != st.session_state.new_filename:
                            st.session_state.new_filename = new_filename
                            apply_sequence()
                        
                        # 文字数カウント
                        char_count = count_chars(st.session_state.new_filename)
                        if char_count > 65:
                            st.error(f"文字数: {char_count:.1f}/65文字（制限超過）")
                        else:
                            st.info(f"文字数: {char_count:.1f}/65文字")
                        
                        # リネームボタン
                        if st.button("この画像をリネーム"):
                            success, message = rename_image(
                                image_path, 
                                st.session_state.new_filename
                            )
                            if success:
                                st.success(message)
                                # 画像リストを更新
                                ext = os.path.splitext(image_path)[1]
                                st.session_state.image_list[st.session_state.current_image_idx] = st.session_state.new_filename + ext
                                st.rerun()
                            else:
                                st.error(message)
                        
                        # 一括リネームボタン
                        if st.button("一括リネーム"):
                            result = rename_all_images()
                            st.success(result)
                            st.rerun()
        
        # メタデータとワードブロックのエリア
        st.subheader("メタデータ情報")
        st.text_area("メタデータ", value=st.session_state.current_metadata, height=150)
        
        st.subheader("単語ブロック")
        if st.session_state.word_blocks:
            # 単語ブロックを表示（ボタンとして）
            cols = st.columns(4)
            for i, word in enumerate(st.session_state.word_blocks):
                col_idx = i % 4
                if cols[col_idx].button(word, key=f"word_{i}"):
                    # 単語をクリックすると、新しいファイル名に追加
                    st.session_state.new_filename += word
                    apply_sequence()
                    st.rerun()

if __name__ == "__main__":
    main()
