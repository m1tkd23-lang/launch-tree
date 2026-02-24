# launch-tree

仕様は `SPEC.md` を参照してください。

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

## Drag & Drop（v1-3）

- ツリー上でドラッグ&ドロップにより、同一階層の並び替えと別グループ配下への移動が可能
- drop先が `group` の場合は子要素として挿入、`item/separator` の場合は同階層に挿入
- root 直下へのドロップにも対応
- 自分自身・子孫配下へのドロップは禁止（循環防止）
- `group` 以外は子を持てないため、移動先 parent は常に `group` に制限
- DnD後は `data/launcher.json` と `data/launcher.json.bak` に保存され、再起動後も反映


## ターゲット登録（v1-4）

- 右クリックから次を追加可能:
  - `Add Path Item (File)...`
  - `Add Path Item (Folder)...`
  - `Add URL Item...`
  - `Add Separator`
- 挿入ルール:
  - 選択が `group` の場合は子として追加
  - 選択が `item/separator` の場合は同階層の直後に追加
  - 未選択の場合は root 直下に追加
- 追加後は `data/launcher.json` と `data/launcher.json.bak` に保存され、再起動後も保持

## UIテーマ

- テーマ（ダークモード）は `src/launch_tree/ui_style.py` の QSS で管理


## 検索（v1-7: フィルター方式）

- 画面上部の検索ボックスでツリーを**フィルター**表示（非一致ノードは非表示）
- マッチ条件: `name` / `target` / `type` の部分一致（大文字小文字を無視）
- `group` は子孫にマッチがあれば表示（親の文脈を維持）。さらに **group 自身がマッチした場合は配下の子孫を全表示**
- `separator` は同階層に表示対象（separator以外）がある場合のみ表示
- 入力は `textChanged` で即時反映、`Esc` でクリア
- 検索中は結果が見えるように必要な枝を自動展開
- 検索クリア時はツリーを折りたたみ状態へ戻す
