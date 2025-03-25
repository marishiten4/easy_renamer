import os
import streamlit as st
from PIL import Image
import piexif  # メタデータ読み取り用

# Streamlitの設定
st.set_page_config(page_title="画像リネームツール", page_icon=":camera:")

class FileRenamer:
    def __init__(self):
        # 初期設定
        self.selected_folder = None
        self.image_files = []
        self.preset_words = {
            'big_words': ['キャラクター名', 'ポーズ', '衣装'],
            'small_words': ['可愛い', '綺麗', 'セクシー']
        }
        self.candidate_words = []

    def select_folder(self):
        """フォルダ選択機能"""
        # Renderの制限により、一時的にハードコードされたパスを使用
        self.selected_folder = '/tmp'  # 一時フォルダを使用
        try:
            self.image_files = [f for f in os.listdir(self.selected_folder) 
                                if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            st.success(f'{len(self.image_files)}個の画像が見つかりました')
        except Exception as e:
            st.error(f'フォルダ読み取りエラー: {e}')

    def extract_metadata(self, image_path):
        """画像メタデータから情報を抽出"""
        try:
            img = Image.open(image_path)
            exif = img._getexif()
            return exif
        except Exception as e:
            st.error(f'メタデータ読み取りエラー: {e}')
            return None

    def rename_files(self, new_names):
        """ファイルリネーム処理"""
        st.warning('実際のファイルリネームは無効化されています。')

def main():
    st.title('画像リネームツール - Yahoo オークション出品用')
    
    renamer = FileRenamer()
    
    # サイドバー
    st.sidebar.header('設定')
    
    # フォルダ選択
    renamer.select_folder()
    
    # 画像一覧表示
    if renamer.image_files:
        selected_image = st.selectbox('画像を選択', renamer.image_files)
        
        # 選択画像の表示
        if selected_image:
            image_path = os.path.join(renamer.selected_folder, selected_image)
            try:
                st.image(image_path, caption=selected_image)
            except Exception as e:
                st.error(f'画像表示エラー: {e}')
    
    # リネーム処理
    st.header('リネーム設定')
    new_names = st.text_area('新しいファイル名', '')
    
    if st.button('リネーム実行'):
        if new_names:
            st.warning('本番環境での実際のファイルリネームは無効化されています。')
        else:
            st.warning('リネーム名を入力してください')

if __name__ == '__main__':
    main()
