"""Centralized application QSS theme."""

APP_QSS = """
QWidget {
    background-color: #141414;
    color: #e6e6e6;
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #141414;
}

QSplitter::handle {
    background-color: #232323;
    width: 2px;
}

QTreeView {
    background-color: #1b1b1b;
    border: 1px solid #2b2b2b;
    border-radius: 14px;
    padding: 10px;
    outline: 0;
    show-decoration-selected: 1;
}

QTreeView::item {
    background: transparent;
    border-radius: 10px;
    padding: 10px 12px;
    margin: 2px 2px;
}

QTreeView::item:hover {
    background-color: #2a2a2a;
}

QTreeView::item:selected {
    background-color: #2f3e53;
    color: #f2f2f2;
}

QHeaderView::section {
    background-color: #222222;
    color: #d8d8d8;
    border: none;
    border-bottom: 1px solid #2f2f2f;
    padding: 8px;
}

QWidget#detailPanel {
    background-color: #151515;
    border-radius: 16px;
    padding: 8px;
}

QFrame#detailCard {
    background-color: #1e1e1e;
    border: 1px solid #2f2f2f;
    border-radius: 16px;
    padding: 16px;
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: 600;
    color: #f0f0f0;
}

QLabel#detailValue {
    color: #d7d7d7;
    padding: 4px 0;
}

QPushButton {
    background-color: #2a3444;
    color: #f4f4f4;
    border: 1px solid #3f4f66;
    border-radius: 14px;
    padding: 12px 20px;
    min-height: 22px;
    font-size: 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #33445d;
}

QPushButton:pressed {
    background-color: #2a3a50;
}

QPushButton:disabled {
    background-color: #232323;
    color: #8b8b8b;
    border: 1px solid #313131;
}

QMenu {
    background-color: #202020;
    color: #e8e8e8;
    border: 1px solid #323232;
    border-radius: 12px;
    padding: 8px;
}

QMenu::item {
    padding: 10px 18px;
    border-radius: 8px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background-color: #33445d;
}

QMenu::separator {
    height: 1px;
    background: #3a3a3a;
    margin: 8px 10px;
}
"""
