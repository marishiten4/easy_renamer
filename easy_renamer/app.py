import os
import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS
import json
import base64
import re

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
        default_settings = {
            'template_texts': ['出品画像', 'カードゲーム用', 'コレクション'],
            'big_words': ['キャラクター', '美少女', 'アニメ'],
            'small_words': ['可愛い', '人気', '高品質'],
            'registered_words': []
        }
        
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                st.session_state.settings = json.load(f)
        except FileNotFoundError:
            st.session_state.settings = default_settings

    def save_settings(self):
        """設定ファイルの保存"""
        try:
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(st.session_state.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            st.error(f"設定の保存中にエラーが発生: {e}")

    def extract_metadata_keywords(self, image_file):
        """画像からメタデータキーワードを抽出"""
        keywords = []
        try:
            # 画像をPIL Imageオブジェクトに変換
            image = Image.open(image_file)
            
            # パラメータ文字列からのキーワード抽出
            param_str = image.info.get('parameters', '')
            if param_str:
                # AIキーワードを検索
                keywords.extend([
                    keyword for keyword in self.ai_image_keywords 
                    if keyword.lower() in param_str.lower()
                ])
                
                # カスタムキーワード抽出のロジック
                # 例：プロンプトから関連キーワードを抽出
                prompt_match = re.findall(r'\b[A-Za-z]+\b', param_str)
                keywords.extend(prompt_match[:5])  # 最初の5つのキーワードを追加
        
        except Exception as e:
            st.warning(f"メタデータ解析中にエラーが発生: {e}")
        
        return list(set(keywords))  # 重複を削除

    def create_word_blocks(self, additional_keywords=None):
        """ワードブロックの作成"""
        # 全てのワードを統合
        all_words = (
            st.session_state.settings['template_texts'] + 
            st.session_state.settings['big_words'] + 
            st.session_state.settings['small_words']
        )
        
        # メタデータキーワードを追加
        if additional_keywords:
            all_words.extend(additional_keywords)
        
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

        # ワードブロックの表示
        word_block_html = ""
        for word in all_words:
            word_block_html += f'<span class="word-block" draggable="true" ondragstart="drag(event)">{word}</span>'
        
        st.markdown(f'<div ondrop="drop(event)" ondragover="allowDrop(event)">{word_block_html}</div>', unsafe_allow_html=True)

    def rename_files(self, files, base_name, start_number, number_padding):
        """
        ファイルをリネームする
        
        :param files: アップロードされたファイルリスト
        :param base_name: ベースとなるリネーム名
        :param start_number: 開始番号
        :param number_padding: 連番のパディング桁数
        :return: リネーム結果の辞書
        """
        results = {}
        output_dir = 'renamed_images'
        
        # 出力ディレクトリが存在しない場合は作成
        os.makedirs(output_dir, exist_ok=True)
        
        for idx, uploaded_file in enumerate(files, start=start_number):
            # 連番付きのファイル名を生成
            number_str = f"{idx:0{number_padding}d}"
            file_ext = os.path.splitext(uploaded_file.name)[1]
            new_filename = f"{base_name}_{number_str}{file_ext}"
            new_filepath = os.path.join(output_dir, new_filename)
            
            try:
                # ファイルの保存
                with open(new_filepath, "wb") as f:
                    f.write(uploaded_file.getvalue())
                results[uploaded_file.name] = new_filename
            except Exception as e:
                results[uploaded_file.name] = f"エラー: {str(e)}"
        
        return results

def main():
    st.set_page_config(page_title="Easy Renamer", layout="wide")
    st.title("🖼️ Easy Renamer - 画像リネームツール")

    renamer = EasyRenamer()

    tab1, tab2, tab3 = st.tabs(["リネーム", "定型文管理", "検索ワード管理"])

    with tab1:
        st.header("📤 画像アップロード")
        uploaded_files = st.file_uploader(
            "画像をアップロード (最大2GB/ファイル)", 
            accept_multiple_files=True, 
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="最大2GBまでの画像をアップロードできます"
        )

        if uploaded_files:
            # メタデータキーワード抽出のプレビュー
            st.header("🔍 メタデータキーワード")
            metadata_keywords = renamer.extract_metadata_keywords(uploaded_files[0])
            st.write("抽出されたキーワード:", metadata_keywords)

            # 連番設定
            st.header("🔢 連番設定")
            col1, col2 = st.columns(2)
            with col1:
                start_number = st.number_input("開始番号", min_value=1, value=1)
            with col2:
                number_padding = st.selectbox("桁数", [2, 3, 4, 5], index=1)

            # リネーム名称入力
            st.header("📝 リネーム名称")
            
            # メタデータキーワードを含めたワードブロック
            renamer.create_word_blocks(additional_keywords=metadata_keywords)
            
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
                if rename_input:
                    # リネーム処理を実行
                    rename_results = renamer.rename_files(
                        uploaded_files, 
                        rename_input, 
                        start_number, 
                        number_padding
                    )
                    
                    # 結果を表示
                    st.subheader("リネーム結果")
                    for original, new_name in rename_results.items():
                        st.write(f"{original} → {new_name}")
                    
                    # リネームされた画像フォルダをダウンロード可能に
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

def main_wrapper():
    main()

if __name__ == "__main__":
    main_wrapper()
