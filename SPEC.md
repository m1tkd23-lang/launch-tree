# Tree Launcher (Windows Desktop) - SPEC (PyQt6)

## 1. Goal
Windows上で、アプリ/ファイル/フォルダ/URL をツリー構造で整理し、
ダブルクリック等で起動できるデスクトップランチャーを作る。
ツリーの並び替え・階層移動はドラッグ&ドロップで自由に行える。
UIデザインは段階的に改善できる設計とする（v1は機能優先）。

## 2. Target
- OS: Windows 10 / 11
- UI: PyQt6

## 3. Non-goals (v1ではやらない)
- クラウド同期
- 複数端末での共有
- アカウント/権限
- 監視（フォルダの自動同期）や自動更新
- タスクトレイ常駐（v2以降）
- アイコン自動抽出の完全対応（v1では任意/簡易）

## 4. Terminology
- Node: ツリーの1要素
- Group: 子を持てるノード
- Item: 起動対象を持つノード（path/url）
- Separator: 区切り表示用ノード

## 5. Functional Requirements

### 5.1 Tree UI
- 1ウィンドウ構成
- 左ペイン：ツリー表示
- 右ペイン：詳細（選択ノードの情報表示）
- ノードは展開/折りたたみできる

推奨実装：
- QTreeView + モデル（QStandardItemModel か custom model）

### 5.2 Node Types
- group: 子を持てる（children）
- path: target = Windowsパス（exe, file, folder いずれも可）
- url: target = URL
- separator: 表示用。targetなし。起動不可。

共通フィールド：
- id: 一意（UUID推奨）
- name: 表示名
- type: group/path/url/separator
- target: path or url のみ
- meta: 追加情報（将来拡張用。v1は空で可）
  - icon_path（任意、v2以降の拡張用）
  - hotkey（任意、v2以降の拡張用）

### 5.3 Launch Action
起動の基本仕様：
- path:
  - folder -> Explorerで開く
  - file/exe -> 既定の関連付け or 実行で開く
- url:
  - 既定ブラウザで開く

v1の実装方針（Windows）：
- path は os.startfile(target) を第一候補
- url は QDesktopServices.openUrl(QUrl(target)) を利用

失敗時：
- エラーダイアログを表示（例外でアプリが落ちない）
- ログに詳細を書き込む

### 5.4 Context Menu (右クリック)
ツリー上で右クリックメニューを提供する：
- Add Group
- Add Path Item（ファイル選択 / フォルダ選択）
- Add URL Item（入力ダイアログ）
- Add Separator
- Rename
- Delete（確認ダイアログあり）
- Launch（起動可能なノードのみ）
- Copy target（path/url のみ）

### 5.5 Drag & Drop Reorder
- 同一階層内の並び替えが可能
- 別グループ配下への移動が可能
- 禁止：
  - 自分の子孫にドロップ（循環）
- ドロップ規則：
  - group にドロップ → 子として入る
  - item/separator にドロップ → 同階層の前後に挿入

モデル更新後は即保存（または一定間隔で保存）する。

### 5.6 Persistence (Save/Load)
v1: JSON ファイルで保存する（単一ファイル）
- path: data/launcher.json
- backup: data/launcher.json.bak（保存時に更新）

読み込みフロー：
1) launcher.json を読む
2) 失敗したら launcher.json.bak を読む
3) それも失敗したら初期データで起動（空ツリー）

保存タイミング（v1）：
- 変更が発生するたびに保存（Add/Rename/Delete/DnD）
- 保存失敗はダイアログ + ログ（アプリは継続）

※ 将来拡張：
- v2で SQLite へ移行可能なように storage 層を分離

### 5.7 Search / Filter (v1.1 以降候補)
- 上部に検索ボックスを設置
- 入力文字列でノードをフィルタ or ハイライト（どちらか）
※ v1ではUI枠だけ用意して未実装でも可

## 6. Non-functional Requirements
- 起動が速い（目標：1秒台）
- 落ちない（例外ハンドリング）
- ログ出力（logs/app.log）
- UIとデータモデル/永続化を分離し、後からデザイン変更しやすい構造

## 7. Data Model (JSON)
Example:
{
  "version": 1,
  "root": {
    "id": "root",
    "name": "Launcher",
    "type": "group",
    "children": [
      {
        "id": "g1",
        "name": "CAM",
        "type": "group",
        "children": [
          {"id": "i1", "name": "hyperMILL", "type": "path", "target": "C:\\Apps\\hyperMILL\\hm.exe"},
          {"id": "u1", "name": "社内Wiki", "type": "url", "target": "https://example.com"}
        ]
      }
    ]
  }
}

Rules:
- group only: has children
- separator: no target
- id unique

## 8. Keyboard Shortcuts (v1)
- Enter: Launch selected (path/url only)
- Del: Delete selected (confirm)
- F2: Rename selected
- Ctrl+N: Add Group (optional)
- Ctrl+L: Focus search (v1.1)

## 9. Acceptance Criteria (Definition of Done)
- PyQt6アプリとして起動し、ツリーが表示される
- group/path/url/separator の追加が右クリックからできる
- path/url はダブルクリックで起動できる
- D&Dで並び替え＆階層移動ができる（循環は禁止）
- 変更がJSONに保存され、再起動しても再現される
- JSON破損時に .bak から復旧を試みる
- 失敗時に落ちず、エラー表示＋ログ出力される

## 10. Suggested Project Structure
/apps
  - launcher_gui.py          # entrypoint
/src/launcher
  - domain.py                # Node dataclass / types
  - model_qt.py              # QAbstractItemModel or QStandardItemModel wrapper
  - storage_json.py          # load/save + backup
  - actions.py               # launch logic (path/url)
  - ui_mainwindow.py         # QMainWindow + widgets
  - ui_menus.py              # context menu builder
  - logging_setup.py         # app.log setup
/data
  - launcher.json
  - launcher.json.bak
/logs
  - app.log

## 11. Run
- python -m venv .venv
- .venv\Scripts\activate
- pip install -r requirements.txt
- python apps/launcher_gui.py

## 12. Packaging (later)
- PyInstaller onedir を想定（v1.1〜）
- internal 依存物の扱いは README に明記