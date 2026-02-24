# launch-tree

PyQt6 で動作するランチャーツリー管理アプリ（v1 骨格）です。

## セットアップ（venv 作成〜起動）

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python apps/main.py  # apps/main.py が <repo>/src を sys.path に追加して起動
```

## 動作確認手順

1. アプリを起動し、左ペインのツリーと右ペインの詳細（name/type/target）が表示されることを確認
2. ツリーを右クリックして `Add Group` でグループ追加
3. 右クリック `Rename` で名前変更
4. 右クリック `Delete` で確認ダイアログ後に削除
5. 操作ごとに `data/launcher.json` と `data/launcher.json.bak` の更新を確認
6. ログが `logs/app.log` に出力されることを確認

## 初期データ

`data/launcher.json` に既定の初期データを配置しています（同内容を `data/launcher.json.bak` にも保持）。

- root(group)
  - Development(group)
    - Project Docs(item, target: URL)

## 起動機能（v1-2）

- `type=path` ノード: ダブルクリック、または右クリック `Launch` で OS 既定アプリ起動（Windows では `os.startfile`）
- `type=url` ノード: ダブルクリック、または右クリック `Launch` で既定ブラウザ起動（`QDesktopServices.openUrl`）
- 右クリック `Copy target` で target をクリップボードへコピー
- `group` / `separator` など path/url 以外は `Launch` / `Copy target` が無効
- 存在しない path、不正 URL、起動失敗時はエラーダイアログを表示し、詳細を `logs/app.log` に記録
