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
        if 'metadata_word_map' not in st.session_state:
            st.session_state.metadata_word_map = {}  # {メタデータキーワード: 対応ワード}

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
            image = Image.open(image_file)
            param_str = image.info.get('parameters', '')
            if param_str:
                # AIキーワードを検索
                keywords.extend([
                    keyword for keyword in self.ai_image_keywords 
                    if keyword.lower() in param_str.lower()
                ])
                # プロンプトから関連キーワードを抽出（先頭5語）\n                prompt_match = re.findall(r'\\b[A-Za-z]+\\b', param_str)\n                keywords.extend(prompt_match[:5])\n        except Exception as e:\n            st.warning(f\"メタデータ解析中にエラーが発生: {e}\")\n        return list(set(keywords))\n\n    def create_word_blocks(self, additional_keywords=None):\n        \"\"\"ワードブロックの作成（背景: ロイヤルブルー、文字: 白）\"\"\"\n        all_words = (\n            st.session_state.settings['template_texts'] + \n            st.session_state.settings['big_words'] + \n            st.session_state.settings['small_words']\n        )\n        if additional_keywords:\n            all_words.extend(additional_keywords)\n        # ユーザー登録のメタデータワードも追加\n        for key, val in st.session_state.metadata_word_map.items():\n            all_words.append(val)\n        st.markdown(\"\"\"\n        <style>\n        .word-block {\n            display: inline-block;\n            background-color: #4169E1;\n            color: white;\n            padding: 5px 10px;\n            margin: 5px;\n            border-radius: 5px;\n            cursor: move;\n        }\n        #rename-input {\n            width: 100%;\n            font-size: 16px;\n            padding: 10px;\n        }\n        </style>\n        <script>\n        function allowDrop(ev) { ev.preventDefault(); }\n        function drag(ev) { ev.dataTransfer.setData('text', ev.target.innerText); }\n        function drop(ev) {\n            ev.preventDefault();\n            var data = ev.dataTransfer.getData('text');\n            var input = document.getElementById('rename-input');\n            var startPos = input.selectionStart;\n            var endPos = input.selectionEnd;\n            var currentValue = input.value;\n            var newValue = currentValue.slice(0, startPos) + ' ' + data + ' ' + currentValue.slice(endPos);\n            input.value = newValue.replace(/\\s+/g, ' ').trim();\n            const event = new Event('input');\n            input.dispatchEvent(event);\n        }\n        </script>\n        \"\"\", unsafe_allow_html=True)\n        word_block_html = \"\"\n        for word in all_words:\n            word_block_html += f'<span class=\"word-block\" draggable=\"true\" ondragstart=\"drag(event)\">{word}</span>'\n        st.markdown(f'<div ondrop=\"drop(event)\" ondragover=\"allowDrop(event)\">{word_block_html}</div>', unsafe_allow_html=True)\n\n    def rename_files(self, files, base_name, serial_text):\n        \"\"\"\n        ファイルをリネームする\n        :param files: アップロードされたファイルリスト\n        :param base_name: ベースとなるリネーム名\n        :param serial_text: ユーザーが入力する連番（アルファベット＋数字）\n        :return: リネーム結果の辞書\n        \"\"\"\n        results = {}\n        output_dir = 'renamed_images'\n        os.makedirs(output_dir, exist_ok=True)\n        for idx, uploaded_file in enumerate(files):\n            file_ext = os.path.splitext(uploaded_file.name)[1]\n            new_filename = f\"{base_name}_{serial_text}{idx}{file_ext}\"\n            new_filepath = os.path.join(output_dir, new_filename)\n            try:\n                with open(new_filepath, \"wb\") as f:\n                    f.write(uploaded_file.getvalue())\n                results[uploaded_file.name] = new_filename\n            except Exception as e:\n                results[uploaded_file.name] = f\"エラー: {str(e)}\"\n        return results\n\n\ndef main():\n    st.set_page_config(page_title=\"Easy Renamer\", layout=\"wide\")\n    st.title(\"🖼️ Easy Renamer - 画像リネームツール\")\n\n    renamer = EasyRenamer()\n    tab1, tab2, tab3 = st.tabs([\"リネーム\", \"定型文管理\", \"検索ワード管理\"])\n\n    with tab1:\n        st.header(\"📤 画像アップロード＆選択\")\n        uploaded_files = st.file_uploader(\n            \"画像をアップロード (最大2GB/ファイル)\", \n            accept_multiple_files=True, \n            type=['png', 'jpg', 'jpeg', 'webp'],\n            help=\"最大2GBまでの画像をアップロードできます\"\n        )\n\n        if uploaded_files:\n            # 画像一覧：サムネイルグリッド\n            st.subheader(\"🖼️ アップロード画像一覧\")\n            cols = st.columns(4)\n            file_selection = []\n            for i, file in enumerate(uploaded_files):\n                try:\n                    img = Image.open(file)\n                    img.thumbnail((150, 150))\n                    with cols[i % 4]:\n                        st.image(img, caption=file.name)\n                        if st.checkbox(f\"選択\", key=file.name):\n                            file_selection.append(file)\n                except Exception as e:\n                    st.error(f\"画像表示エラー: {e}\")\n            \n            # 選択画像の詳細表示\n            if file_selection:\n                st.subheader(\"📸 選択画像プレビュー & 画像名変更\")\n                selected = st.radio(\"プレビューする画像を選択\", file_selection, format_func=lambda f: f.name)\n                if selected:\n                    preview_img = Image.open(selected)\n                    st.image(preview_img, caption=f\"プレビュー: {selected.name}\", use_column_width=True)\n                    \n                    # 画像名変更入力\n                    new_name_input = st.text_input(\n                        \"新しいファイル名（拡張子除く）\", \n                        value=os.path.splitext(selected.name)[0], \n                        key=\"rename-input\"\n                    )\n                    \n                    # 連番設定（アルファベット＋数字の混合）\n                    serial_text = st.text_input(\"連番文字列 (例: IMG_A001)\", value=\"IMG_A001\")\n                    \n                    # メタデータキーワード抽出\n                    st.subheader(\"🔍 メタデータキーワード\")\n                    metadata_keywords = renamer.extract_metadata_keywords(selected)\n                    st.write(\"抽出されたキーワード:\", metadata_keywords)\n                    \n                    # ワードブロック作成\n                    renamer.create_word_blocks(additional_keywords=metadata_keywords)\n                    \n                    # リネーム名称のプレビュー\n                    new_full_name = f\"{new_name_input}_{serial_text}0{os.path.splitext(selected.name)[1]}\"\n                    st.write(f\"リネーム後のファイル名例: {new_full_name}\")\n                    \n                    if st.button(\"リネーム実行\"):\n                        # リネーム対象は選択された画像すべて\n                        rename_results = renamer.rename_files(file_selection, new_name_input, serial_text)\n                        st.subheader(\"リネーム結果\")\n                        for original, new_name in rename_results.items():\n                            st.write(f\"{original} → {new_name}\")\n                        \n                        # ZIPアーカイブ作成\n                        try:\n                            import shutil\n                            shutil.make_archive('renamed_images', 'zip', 'renamed_images')\n                            with open('renamed_images.zip', 'rb') as f:\n                                st.download_button(\n                                    label=\"リネーム済み画像をダウンロード\",\n                                    data=f.read(),\n                                    file_name='renamed_images.zip',\n                                    mime='application/zip'\n                                )\n                        except Exception as e:\n                            st.error(f\"ZIP作成中にエラー: {e}\")\n                else:\n                    st.info(\"プレビューする画像を選択してください\")\n        else:\n            st.info(\"画像をアップロードしてください\")\n\n    with tab2:\n        st.header(\"定型文管理\")\n        st.write(\"ここでは定型文の管理ができます。\")\n        st.text_area(\"定型文を編集\", value=json.dumps(st.session_state.settings['template_texts'], ensure_ascii=False, indent=4))\n\n    with tab3:\n        st.header(\"検索ワード管理\")\n        st.write(\"ここでは検索ワードの管理ができます。\")\n        key_input = st.text_input(\"メタデータキーワード\", key=\"meta_key\")\n        value_input = st.text_input(\"対応するワード\", key=\"meta_value\")\n        if st.button(\"ワード登録\"):\n            if key_input and value_input:\n                st.session_state.metadata_word_map[key_input] = value_input\n                st.success(f\"{key_input} → {value_input} を登録しました\")\n            else:\n                st.warning(\"両方のフィールドを入力してください\")\n\n\ndef main_wrapper():\n    main()\n\nif __name__ == \"__main__\":\n    main_wrapper()\n```
