# EasyRenamer

Stable Diffusionで作成した画像を効率的にリネームするためのツールです。

## 機能

- 画像フォルダの選択と一覧表示
- 画像メタデータからの単語抽出
- ワードブロックによる簡単な単語挿入
- 連番設定（開始番号・桁数の指定）
- 定型文の適用
- 一括リネーム機能

## 使用方法

1. サイドバーでフォルダのパスを入力し、「フォルダ読み込み」ボタンを押します
2. 画像一覧から処理したい画像を選択します
3. 新しいファイル名を入力するか、抽出された単語ブロックをクリックして挿入します
4. 連番を使用する場合は、サイドバーで設定を有効にします
5. 「この画像をリネーム」または「一括リネーム」ボタンを押してリネームを実行します

## 必要なライブラリ

- streamlit
- Pillow
- piexif
- pandas

## インストール方法

```
pip install -r requirements.txt
```

## 実行方法

```
streamlit run app.py
```

## 注意事項

- メタデータの抽出はEXIFデータまたはPNGパラメータから行われます
- ファイル名の文字数は全角65文字（半角130文字）以内に収めてください
- 既存のファイル名と同じ名前にリネームすることはできません
