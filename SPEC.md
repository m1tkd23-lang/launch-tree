# SPEC.md

## 1. 対象環境
- OS: Windows 10 / 11
- 言語: Python 3.x
- GUI: PyQt6

## 2. アーキテクチャ方針
- リポジトリ構成は `apps/`, `src/`, `tests/` を維持する。
- src レイアウトを採用し、起動時は `apps/main.py` が `<repo>/src` を `sys.path` に追加してから `launch_tree` パッケージを import する。
- エントリポイントは `apps/main.py` とし、起動処理の実体は `launch_tree.core` 側に置く。

## 3. 画面仕様（v1系）
- メインウィンドウは `QMainWindow`。
- 左ペイン: ツリー (`QTreeView`)。
- 右ペイン: 詳細ペイン（選択ノードの `name` / `type` / `target` を表示）。

## 4. データモデル
- ノードは以下の属性を持つ:
  - `id`
  - `name`
  - `type`
  - `target`
  - `children`
- ルートは `group` タイプのノードとして扱う。

## 5. 編集方針（右クリック操作）
- 編集操作は右クリックメニュー + ダイアログベースで行う。
- 最低限の編集機能:
  - `Add Group`
    - 選択ノードが `group` の場合は子として追加
    - 選択ノードが `item/path/url` の場合は同階層に追加
  - `Rename`（入力ダイアログ）
  - `Delete`（確認ダイアログ）

## 6. 永続化仕様
- 保存形式: JSON
- メイン保存先: `data/launcher.json`
- バックアップ: `data/launcher.json.bak`
- 読み込み時のフォールバック順:
  1. `data/launcher.json`
  2. `data/launcher.json.bak`
  3. どちらも失敗時は空ルートで起動
- ノード変更が発生するたびに `launcher.json` と `.bak` の両方を更新する。

## 7. 起動機能（v1-2）
- 起動対象は `type=path` と `type=url`。
- 実行トリガー:
  - ツリーのダブルクリック
  - 右クリックメニュー `Launch`
- 補助操作:
  - 右クリックメニュー `Copy target`
- ノード種別制御:
  - `group` / `separator` 等、`path/url` 以外では `Launch` / `Copy target` は無効

### 7.1 type=path
- Windows 既定の方法として `os.startfile(target)` を使う。
- `target` が存在しない、または起動に失敗した場合:
  - エラーダイアログを表示
  - 例外詳細を `logs/app.log` に記録

### 7.2 type=url
- `QDesktopServices.openUrl(QUrl(target))` で既定ブラウザ起動。
- `QUrl.isValid()` 等で最低限の妥当性確認を行う。
- 不正 URL / 起動失敗時:
  - エラーダイアログを表示
  - 例外詳細を `logs/app.log` に記録

## 8. 検索仕様
- 検索は「フィルタ」ではなく「ハイライト」を採用する。
- 該当ノードを見えたまま色付けする方式とし、非該当ノードを非表示にはしない。

## 9. Drag & Drop（将来対応）
- 現時点では未実装。
- 将来仕様として以下を想定する:
  - 同階層内での並び替え
  - 別グループへの移動
  - 循環参照（自分自身/子孫配下への移動）の禁止

## 10. 例外/ログ方針
- 例外でアプリを落とさない。
- 主要イベント（起動、保存、例外）を `logs/app.log` に記録する。
- ユーザーに必要な失敗はダイアログ表示する。
