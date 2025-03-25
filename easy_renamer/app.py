import os
import streamlit as st
from PIL import Image
import piexif  # メタデータ読み取り用

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
        self.selected_folder = st.text_input('画像フォルダのパスを入力', '')
        if self.selected_folder and os.path.exists(self.selected_folder):
            self.image_files = [f for f in os.listdir(self.selected_folder) 
                                if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            st.success(f'{len(self.image_files)}個の画像が見つかりました')

    def extract_metadata(self, image_path):
        """画像メタデータから情報を抽出"""
        try:
            img = Image.open(image_path)
            exif = img._getexif()
            # ここに具体的なメタデータ解析ロジックを実装
            return exif
        except Exception as e:
            st.error(f'メタデータ読み取りエラー: {e}')
            return None

    def generate_rename_candidates(self):
        """メタデータから候補ワードを生成"""
        if not self.selected_folder:
            st.warning('フォルダを先に選択してください')
            return

        # サンプル実装
        for image_file in self.image_files:
            full_path = os.path.join(self.selected_folder, image_file)
            metadata = self.extract_metadata(full_path)
            # メタデータ解析ロジックを追加
            # 候補ワードの生成

    def rename_files(self, new_names):
        """ファイルリネーム処理"""
        for old_name, new_name in zip(self.image_files, new_names):
            old_path = os.path.join(self.selected_folder, old_name)
            new_path = os.path.join(self.selected_folder, new_name)
            os.rename(old_path, new_path)
        st.success('ファイルリネームが完了しました')

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
            st.image(image_path, caption=selected_image)
    
    # リネーム処理
    st.header('リネーム設定')
    new_names = st.text_area('新しいファイル名', '')
    
    if st.button('リネーム実行'):
        if new_names:
            renamer.rename_files(new_names.split('\n'))
        else:
            st.warning('リネーム名を入力してください')

if __name__ == '__main__':
    main()
