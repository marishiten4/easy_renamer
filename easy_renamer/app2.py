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

    def create_word_blocks(self):
        """ワードブロックの作成"""
        # 全てのワードを統合
        all_words = (
            st.session_state.settings['template_texts'] + 
            st.session_state.settings['big_words'] + 
            st.session_state.settings['small_words']
        )
        
        # ワードブロックのHTML/CSS
        st.markdown("""
        <style>
        .word-block {
            display: inline-block;
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 5px 10px;
            margin: 5px;
            cursor: move;
        }
        #rename-input {
            width: 100%;
            font-size: 16px;
            padding: 10px;
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
            
            // 現在の入力値
            var currentValue = input.value;
            
            // 新しい値を作成
            var newValue = 
                currentValue.slice(0, startPos) + 
                " " + data + " " + 
                currentValue.slice(endPos);
            
            // 値を設定
            input.value = newValue.replace(/\s+/g, ' ').trim();
            
            // Streamlitにイベントを送信
            const event = new Event('input');
            input.dispatchEvent(event);
        }
        </script>
        """, unsafe_allow_html=True)

        # ワードブロックの表示
        word_block_html = ""
        for word in all_words:
            word_block_html += f'<span class="word-block" draggable="true" ondragstart="drag(event)">{word}</span>'
        
        st.markdown(f'<div ondrop="drop(event)" ondragover="allowDrop(event)">{word_block_html}</div>', unsafe_allow_html=True)

def main():
    # タイトルとページ設定
    st.set_page_config(page_title="Easy Renamer", layout="wide")
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    # EasyRenamerインスタンス作成
    renamer = EasyRenamer()

    # タブ設定
    tab1, tab2, tab3 = st.tabs(["リネーム", "定型文管理", "検索ワード管理"])

    with tab1:
        # ファイルアップロード
        st.header("📤 画像アップロード")
        uploaded_files = st.file_uploader(
            "画像をアップロード (最大2GB/ファイル)", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="最大2GBまでの画像をアップロードできます"
        )

        if uploaded_files:
            # 連番設定
            st.header("🔢 連番設定")
            col1, col2 = st.columns(2)
            with col1:
                start_number = st.number_input("開始番号", min_value=1, value=1)
            with col2:
                number_padding = st.selectbox("桁数", [2, 3, 4, 5], index=1)

            # リネーム名称入力
            st.header("📝 リネーム名称")
            
            # ワードブロック
            renamer.create_word_blocks()
            
            # リネーム入力
            rename_input = st.text_input(
                "リネーム名を入力", 
                key="rename_input",
                help="ワードブロックをドラッグ&ドロップで挿入できます"
            )

            # 画像一覧
            st.header("🖼️ 画像一覧")
            
            # ページネーション付きの50個表示
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
            
            # 画像名称一覧
            st.subheader("画像名称一覧")
            image_names = [f.name for f in page_files]
            st.table(image_names)

            # リネーム処理
            if st.button("画像をリネーム", type="primary"):
                # リネーム処理のロジックを追加（詳細は省略）
                st.success(f"{len(uploaded_files)}枚の画像をリネームする準備ができました")

    # 他のタブの実装は前回と同様

def main_wrapper():
    main()

if __name__ == "__main__":
    main_wrapper()
