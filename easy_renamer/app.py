import os
import streamlit as st
from PIL import Image
import piexif
import tempfile
import shutil

class FileRenamer:
    def __init__(self):
        # セッション状態の初期化
        if 'selected_folder' not in st.session_state:
            st.session_state.selected_folder = None
        if 'image_files' not in st.session_state:
            st.session_state.image_files = []

        self.preset_words = {
            'big_words': ['キャラクター名', 'ポーズ', '衣装'],
            'small_words': ['可愛い', '綺麗', 'セクシー']
        }

    def upload_folder(self):
        """フォルダアップロード機能"""
        uploaded_files = st.file_uploader(
            "画像ファイルをアップロード", 
            type=['png', 'jpg', 'jpeg'], 
            accept_multiple_files=True
        )

        if uploaded_files:
            # 一時フォルダの作成
            temp_dir = tempfile.mkdtemp()
            st.session_state.selected_folder = temp_dir
            st.session_state.image_files = []

            # ファイルを一時フォルダに保存
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state.image_files.append(uploaded_file.name)

            st.success(f'{len(st.session_state.image_files)}個の画像をアップロードしました')
            return True
        return False

    def display_image_list(self):
        """画像一覧の表示"""
        if st.session_state.image_files:
            # 画像選択
            selected_image = st.selectbox('画像を選択', st.session_state.image_files)
            
            # 選択画像の表示
            if selected_image:
                image_path = os.path.join(st.session_state.selected_folder, selected_image)
                try:
                    st.image(image_path, caption=selected_image)
                except Exception as e:
                    st.error(f'画像表示エラー: {e}')

    def generate_rename_preview(self):
        """リネーム候補の生成と表示"""
        # 定型文セクション
        st.subheader('定型文設定')
        col1, col2 = st.columns(2)
        
        with col1:
            big_word = st.selectbox('大分類ワード', self.preset_words['big_words'])
        
        with col2:
            small_word = st.selectbox('小分類ワード', self.preset_words['small_words'])
        
        # 画像番号入力
        image_number = st.number_input('画像番号', min_value=1, value=1)
        
        # リネーム候補の生成
        rename_template = f"{big_word}_{small_word}_{image_number:03d}"
        
        st.subheader('リネーム プレビュー')
        st.text_input('生成された名前', rename_template)

    def rename_files(self, rename_template):
        """ファイルリネーム処理"""
        if not st.session_state.selected_folder:
            st.error('先に画像をアップロードしてください')
            return

        try:
            for i, filename in enumerate(st.session_state.image_files, 1):
                # ファイル拡張子の取得
                ext = os.path.splitext(filename)[1]
                
                # 新しいファイル名の生成
                new_filename = f"{rename_template}{ext}"
                
                # ファイルリネーム
                old_path = os.path.join(st.session_state.selected_folder, filename)
                new_path = os.path.join(st.session_state.selected_folder, new_filename)
                
                os.rename(old_path, new_path)
                st.session_state.image_files[i-1] = new_filename

            st.success('ファイルリネームが完了しました')
            
            # リネーム後の画像一覧を表示
            st.subheader('リネーム後の画像一覧')
            st.write(st.session_state.image_files)

        except Exception as e:
            st.error(f'リネーム中にエラーが発生: {e}')

def main():
    st.set_page_config(page_title="画像リネームツール", page_icon=":camera:")
    st.title('画像リネームツール - Yahoo オークション出品用')
    
    renamer = FileRenamer()
    
    # サイドバー
    st.sidebar.header('操作')
    
    # フォルダアップロード
    if renamer.upload_folder():
        # 画像一覧表示
        renamer.display_image_list()
        
        # リネーム候補生成
        renamer.generate_rename_preview()
        
        # リネーム実行ボタン
        if st.button('リネーム実行'):
            rename_template = f"{st.session_state.big_word}_{st.session_state.small_word}_{st.session_state.image_number:03d}"
            renamer.rename_files(rename_template)

if __name__ == '__main__':
    main()
