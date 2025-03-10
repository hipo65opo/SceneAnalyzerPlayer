#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
メインウィンドウモジュール
"""

import os
import sys
import json
import logging
import cv2
import platform
from datetime import datetime, timedelta
import tempfile
import csv
from typing import List, Dict, Any, Optional, cast, Callable

from PyQt5.QtCore import (
    Qt, QSize, QTimer, QThread, pyqtSignal as Signal, pyqtSlot as Slot, QUrl, QSettings
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QImage, QPalette, QColor, QFont, QKeySequence,
    QDragEnterEvent, QDropEvent, QCursor, QPainter
)
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog, 
    QMessageBox, QAction, QMenu, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, 
    QLineEdit, QTextEdit, QProgressBar, QStyle, QApplication, QProgressDialog,
    QDialog, QLabel, QPushButton, QSlider
)
from PyQt5.QtMultimedia import (
    QMediaPlayer, QMediaContent
)
from PyQt5.QtMultimediaWidgets import (
    QVideoWidget
)

from scene_analyzer.ui.video_player import VideoPlayer
from scene_analyzer.ui.scene_panel import ScenePanel
from scene_analyzer.ui.timeline_widget import TimelineWidget
from scene_analyzer.ui.session_dialog import SessionDialog
from scene_analyzer.ui.settings_dialog import SettingsDialog
from scene_analyzer.database import Database
from scene_analyzer.scene_detection import SceneDetector, SceneDetectorWorker, SceneAnalyzerWorker, KeyframeExtractorWorker

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    # ログメッセージ用のシグナル
    log_signal = Signal(str)
    
    def __init__(self):
        """初期化"""
        super().__init__()
        
        # ロガーの設定
        self.logger = logging.getLogger(__name__)
        
        # 設定の初期化
        self.settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
        
        # データベース接続
        db_path = os.path.join(os.path.expanduser('~'), '.scene_analyzer', 'scene_analyzer.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.database = Database(db_path)
        
        # ダークモードのグローバルスタイルシートを設定
        self.apply_dark_theme()
        
        # メディアプレイヤーの初期化
        self.init_media_player()
        
        # UI初期化
        self.init_ui()
        
        # UIが初期化された後に再度ダークテーマを適用（ログパネルのスタイル適用のため）
        self.apply_dark_theme()
        
        # 現在の動画ID
        self.current_video_id = None
        
        # 現在のセッションID
        self.current_session_id = None
        
        # ループ再生フラグ
        self.loop_playback = True  # デフォルトでループ再生を有効に設定
        
        # シーン検出器
        self.scene_detector = None
        
        # シーン解析器
        self.scene_analyzer = None
        
        # ログシグナル接続
        self.log_signal.connect(self._append_log)  # type: ignore[arg-type]
        
        # ウィンドウ設定
        self.setWindowTitle("Scene Analyzer")
        self.resize(1280, 720)
        
        self.log("アプリケーションを起動しました")
    
    def apply_dark_theme(self):
        """ダークモードのテーマを適用する"""
        # ダークモードのカラーパレット
        dark_palette = {
            "background": "#1e1e1e",
            "foreground": "#e0e0e0",
            "accent": "#3d8ec9",
            "accent_light": "#5a9fd4",
            "accent_dark": "#2d6ea6",
            "secondary": "#2a2a2a",
            "border": "#3a3a3a",
            "highlight": "#323232",
            "error": "#d64242",
            "success": "#4caf50",
            "warning": "#ff9800",
            "disabled": "#656565",
            "text_disabled": "#9e9e9e"
        }
        
        # アプリケーション全体のスタイルシート
        qss = f"""
            QWidget {{
                background-color: {dark_palette["background"]};
                color: {dark_palette["foreground"]};
                font-family: "Segoe UI", Arial, sans-serif;
            }}
            
            QMainWindow, QDialog {{
                background-color: {dark_palette["background"]};
            }}
            
            QLabel {{
                color: {dark_palette["foreground"]};
            }}
            
            QPushButton {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                background-color: {dark_palette["highlight"]};
                border: 1px solid {dark_palette["accent"]};
            }}
            
            QPushButton:pressed {{
                background-color: {dark_palette["accent_dark"]};
            }}
            
            QPushButton:disabled {{
                background-color: {dark_palette["background"]};
                color: {dark_palette["text_disabled"]};
                border: 1px solid {dark_palette["disabled"]};
            }}
            
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
                border-radius: 3px;
                padding: 2px;
                selection-background-color: {dark_palette["accent"]};
            }}
            
            QComboBox {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
                border-radius: 3px;
                padding: 2px 10px 2px 5px;
                min-height: 20px;
            }}
            
            QComboBox:hover {{
                border: 1px solid {dark_palette["accent"]};
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {dark_palette["border"]};
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
                selection-background-color: {dark_palette["accent"]};
            }}
            
            QSlider::groove:horizontal {{
                border: 1px solid {dark_palette["border"]};
                height: 8px;
                background: {dark_palette["secondary"]};
                margin: 2px 0;
                border-radius: 4px;
            }}
            
            QSlider::handle:horizontal {{
                background: {dark_palette["accent"]};
                border: 1px solid {dark_palette["accent_dark"]};
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            
            QSlider::handle:horizontal:hover {{
                background: {dark_palette["accent_light"]};
            }}
            
            QCheckBox {{
                color: {dark_palette["foreground"]};
                spacing: 5px;
            }}
            
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {dark_palette["border"]};
                border-radius: 3px;
                background-color: {dark_palette["secondary"]};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {dark_palette["accent"]};
            }}
            
            QCheckBox::indicator:hover {{
                border: 1px solid {dark_palette["accent"]};
            }}
            
            QMenuBar {{
                background-color: {dark_palette["background"]};
                color: {dark_palette["foreground"]};
                border-bottom: 1px solid {dark_palette["border"]};
            }}
            
            QMenuBar::item {{
                background: transparent;
                padding: 4px 10px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {dark_palette["highlight"]};
                color: {dark_palette["foreground"]};
            }}
            
            QMenu {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
            }}
            
            QMenu::item {{
                padding: 5px 30px 5px 20px;
                border: 1px solid transparent;
            }}
            
            QMenu::item:selected {{
                background-color: {dark_palette["highlight"]};
                color: {dark_palette["foreground"]};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {dark_palette["border"]};
                margin: 5px 0;
            }}
            
            QScrollBar:vertical {{
                background-color: #121212;
                width: 14px;
                margin: 0;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: #555555;
                min-height: 20px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: #777777;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background-color: #121212;
            }}
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background-color: #121212;
            }}
            
            QScrollBar:horizontal {{
                background-color: #121212;
                height: 14px;
                margin: 0;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: #555555;
                min-width: 20px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: #777777;
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                background-color: #121212;
            }}
            
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background-color: #121212;
            }}
            
            QScrollBar::corner {{
                background-color: #121212;
            }}
            
            QTabWidget::pane {{
                border: 1px solid {dark_palette["border"]};
                background-color: {dark_palette["background"]};
            }}
            
            QTabBar::tab {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
                padding: 5px 10px;
                margin-right: 2px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {dark_palette["accent"]};
                color: white;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {dark_palette["highlight"]};
            }}
            
            QHeaderView::section {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                padding: 5px;
                border: 1px solid {dark_palette["border"]};
            }}
            
            QTableView {{
                background-color: {dark_palette["background"]};
                color: {dark_palette["foreground"]};
                gridline-color: {dark_palette["border"]};
                selection-background-color: {dark_palette["accent"]};
                selection-color: white;
                alternate-background-color: {dark_palette["highlight"]};
            }}
            
            QListView {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border: 1px solid {dark_palette["border"]};
                selection-background-color: {dark_palette["accent"]};
                selection-color: white;
                outline: 0;
            }}
            
            QListView::item:hover {{
                background-color: {dark_palette["highlight"]};
            }}
            
            QListView::item:selected {{
                background-color: {dark_palette["accent"]};
                color: white;
            }}
            
            QProgressBar {{
                border: 1px solid {dark_palette["border"]};
                border-radius: 3px;
                background-color: #1e3a4f;
                text-align: center;
                color: {dark_palette["foreground"]};
            }}
            
            QProgressBar::chunk {{
                background-color: {dark_palette["accent"]};
                width: 10px;
                margin: 0.5px;
            }}
            
            QStatusBar {{
                background-color: {dark_palette["secondary"]};
                color: {dark_palette["foreground"]};
                border-top: 1px solid {dark_palette["border"]};
            }}
            
            QVideoWidget {{
                background-color: black;
            }}
        """
        
        # スタイルシートを適用
        self.setStyleSheet(qss)
        
        # ログパネルのスタイルを更新（log_textが存在する場合のみ）
        if hasattr(self, 'log_text'):
            self.log_text.setStyleSheet(f"font-size: 11px; background-color: {dark_palette['secondary']}; border: 1px solid {dark_palette['border']};")
            self.log_text.document().setDefaultStyleSheet(f"span {{ color: {dark_palette['foreground']}; }} div {{ margin-bottom: 5px; }}")
    
    def init_media_player(self):
        """メディアプレイヤーの初期化"""
        self.media_player = QMediaPlayer(self)
        self.media_player.setNotifyInterval(10)
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.error.connect(self.handle_media_error)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)
    
    def init_ui(self):
        """UIの初期化"""
        # メインウィジェットとレイアウト
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # メインスプリッター（動画プレイヤーとシーンパネル）
        main_splitter = QSplitter(Qt.Horizontal)  # type: ignore[attr-defined]
        
        # 左側：動画プレイヤー部分
        player_widget = QWidget()
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)  # 余白を減らして動画表示領域を広げる
        player_layout.setSpacing(2)  # コンポーネント間の間隔を小さくする
        
        # 動画表示ウィジェット
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        player_layout.addWidget(self.video_widget, 1)  # 伸縮比率を1に設定して、動画表示領域を広げる
        
        # シークバー部分（動画の下に配置）
        seek_widget = QWidget()
        seek_layout = QHBoxLayout(seek_widget)
        seek_layout.setContentsMargins(0, 0, 0, 0)
        
        # シークスライダーの作成
        self.seek_slider = QSlider(Qt.Horizontal)  # type: ignore[attr-defined]
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.set_position)
        seek_layout.addWidget(self.seek_slider)
        
        # 時間表示ラベル
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setMinimumWidth(150)
        seek_layout.addWidget(self.time_label)
        
        # シークウィジェットを追加
        player_layout.addWidget(seek_widget)
        
        # 再生コントロールボタン部分（最下部に配置）
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 動画を開くボタンの作成
        self.open_button = QPushButton("Open", self)
        self.open_button.setToolTip("動画を開く")
        self.open_button.clicked.connect(self.open_video)
        control_layout.addWidget(self.open_button)
        
        # シーン検出解析ボタンの作成
        self.scene_detect_button = QPushButton("シーン検出解析", self)
        self.scene_detect_button.clicked.connect(self.start_scene_detection_analysis)
        control_layout.addWidget(self.scene_detect_button)
        
        # 再生/一時停止ボタンの作成
        self.play_button = QPushButton(self)
        # 青色の再生アイコンを作成
        play_icon = self.create_blue_icon(QStyle.SP_MediaPlay)  # type: ignore[attr-defined]
        self.play_button.setIcon(play_icon)
        self.play_button.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.play_button)
        
        # 停止ボタンの作成
        self.stop_button = QPushButton(self)
        # 青色の停止アイコンを作成
        stop_icon = self.create_blue_icon(QStyle.SP_MediaStop)  # type: ignore[attr-defined]
        self.stop_button.setIcon(stop_icon)
        self.stop_button.clicked.connect(self.stop_playback)
        control_layout.addWidget(self.stop_button)
        
        # 再生速度コンボボックス
        self.speed_combo = QComboBox(self)
        self.speed_combo.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentIndex(2)  # デフォルトは1.0x
        self.speed_combo.currentIndexChanged.connect(self.change_playback_speed)
        control_layout.addWidget(QLabel("速度:"))
        control_layout.addWidget(self.speed_combo)
        
        # 音量スライダーの作成
        self.volume_slider = QSlider(Qt.Horizontal)  # type: ignore[attr-defined]
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)  # デフォルト音量を70%に設定
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.set_volume(70)  # 初期音量を設定
        
        control_layout.addWidget(QLabel("音量:"))
        control_layout.addWidget(self.volume_slider)
        
        # ループ再生チェックボックス
        self.loop_checkbox = QCheckBox("ループ再生", self)
        self.loop_checkbox.setChecked(True)  # デフォルトでチェック状態に設定
        self.loop_checkbox.stateChanged.connect(self.toggle_loop)
        control_layout.addWidget(self.loop_checkbox)
        
        # コントロールウィジェットを追加
        player_layout.addWidget(control_widget)
        
        # 左側パネルをスプリッターに追加
        main_splitter.addWidget(player_widget)
        
        # 右側：シーンリストパネル
        self.scene_panel = ScenePanel(self.database)
        self.scene_panel.scene_selected.connect(self.jump_to_scene)
        main_splitter.addWidget(self.scene_panel)
        
        # スプリッターの初期サイズ比率を設定
        main_splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        
        # 垂直スプリッター（メインコンテンツとログパネル）
        vertical_splitter = QSplitter(Qt.Vertical)  # type: ignore[attr-defined]
        vertical_splitter.addWidget(main_splitter)
        
        # メインコンテンツに最小サイズを設定
        main_splitter.setMinimumHeight(300)
        
        # ログ表示用のテキストエディタを作成
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        # ログパネルのタイトル
        log_title = QLabel("ログパネル")
        log_title.setStyleSheet("font-weight: bold; padding: 2px;")
        log_layout.addWidget(log_title)
        
        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        # ダークモードに合わせたスタイル設定
        self.log_text.setStyleSheet("font-size: 11px; background-color: #2a2a2a; border: 1px solid #3a3a3a;")
        self.log_text.document().setDefaultStyleSheet("span { color: #e0e0e0; } div { margin-bottom: 5px; }")
        self.log_text.setAcceptRichText(True)
        log_layout.addWidget(self.log_text)
        
        # ログコンテナに最小サイズを設定
        log_container.setMinimumHeight(80)
        
        vertical_splitter.addWidget(log_container)
        
        # スプリッターハンドルの設定
        vertical_splitter.setHandleWidth(16)
        vertical_splitter.setChildrenCollapsible(False)
        vertical_splitter.setStyleSheet("""
            QSplitter::handle { 
                background-color: #8a8a8a; 
                border: 1px solid #666666;
                border-radius: 2px;
                margin: 2px;
            }
            QSplitter::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #8a8a8a, stop:0.45 #666666,
                                          stop:0.5 #555555, stop:0.55 #666666,
                                          stop:1 #8a8a8a);
            }
            QSplitter::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #8a8a8a, stop:0.45 #666666,
                                          stop:0.5 #555555, stop:0.55 #666666,
                                          stop:1 #8a8a8a);
            }
            QSplitter::handle:hover { 
                background-color: #666666; 
                border: 1px solid #444444;
            }
            QSplitter::handle:pressed { 
                background-color: #555555; 
            }
            QSplitter::handle:horizontal:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #777777, stop:0.45 #555555,
                                          stop:0.5 #444444, stop:0.55 #555555,
                                          stop:1 #777777);
                border: 1px solid #444444;
            }
            QSplitter::handle:vertical:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #777777, stop:0.45 #555555,
                                          stop:0.5 #444444, stop:0.55 #555555,
                                          stop:1 #777777);
                border: 1px solid #444444;
            }
            QSplitter::handle:pressed { 
                background-color: #444444; 
                border: 1px solid #333333;
            }
        """)
        
        # メインスプリッターのハンドル設定も同様に
        main_splitter.setHandleWidth(16)
        main_splitter.setStyleSheet("""
            QSplitter::handle { 
                background-color: #8a8a8a; 
                border: 1px solid #666666;
                border-radius: 2px;
                margin: 2px;
            }
            QSplitter::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #8a8a8a, stop:0.45 #666666,
                                          stop:0.5 #555555, stop:0.55 #666666,
                                          stop:1 #8a8a8a);
            }
            QSplitter::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #8a8a8a, stop:0.45 #666666,
                                          stop:0.5 #555555, stop:0.55 #666666,
                                          stop:1 #8a8a8a);
            }
            QSplitter::handle:hover { 
                background-color: #666666; 
                border: 1px solid #444444;
            }
            QSplitter::handle:pressed { 
                background-color: #555555; 
            }
        """)
        
        # 垂直スプリッターの初期サイズ比率を設定
        vertical_splitter.setSizes([int(self.height() * 0.85), int(self.height() * 0.15)])
        
        main_layout.addWidget(vertical_splitter)
        
        # メニューバーの作成
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """メニューバーの作成"""
        # ファイルメニュー
        file_menu = QMenu("ファイル", self)
        
        open_action = QAction("動画を開く...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_video)
        file_menu.addAction(open_action)
        
        start_session_action = QAction("シーン検出セッションを開始...", self)
        start_session_action.triggered.connect(self.start_session)
        file_menu.addAction(start_session_action)
        
        export_session_action = QAction("セッションをエクスポート...", self)
        export_session_action.triggered.connect(self.export_session)
        file_menu.addAction(export_session_action)
        
        file_menu.addSeparator()
        
        reinit_db_action = QAction("データベースを再初期化...", self)
        reinit_db_action.triggered.connect(self.reinitialize_database)
        file_menu.addAction(reinit_db_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("終了", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)  # type: ignore[arg-type]
        file_menu.addAction(exit_action)
        
        # ヘルプメニュー
        help_menu = QMenu("ヘルプ", self)
        
        settings_action = QAction("設定...", self)
        settings_action.triggered.connect(self.show_settings)
        help_menu.addAction(settings_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("バージョン情報", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # メニューバーにメニューを追加
        menubar = self.menuBar()
        menubar.addMenu(file_menu)
        menubar.addMenu(help_menu)
    
    def show_about(self):
        """バージョン情報ダイアログを表示"""
        QMessageBox.about(
            self,
            "Scene Analyzer について",
            "<h3>Scene Analyzer</h3>"
            "<p>バージョン: 1.0.0</p>"
            "<p>動画からシーンを検出し、解析するためのツールです。</p>"
            "<p>© 2025 Scene Analyzer Team</p>"
        )
    
    def log(self, message):
        """ログメッセージを追加"""
        try:
            # ログメッセージをシグナルで送信
            self.log_signal.emit(message)
            
            # ロガーにも出力
            logger.debug(message)
        except Exception as e:
            logger.error(f"ログ出力エラー: {e}")
    
    @Slot(str)
    def _append_log(self, message):
        """ログメッセージをテキストエディタに追加"""
        try:
            # 現在の時刻を取得
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # ログメッセージを追加
            self.log_text.append(f"[{current_time}] {message}")
            
            # スクロールを最下部に移動
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
            
            # スタイルシートを再適用（ログメッセージのHTMLがスタイルに影響を与える可能性があるため）
            self.log_text.setStyleSheet("font-size: 11px; background-color: #2a2a2a; border: 1px solid #3a3a3a;")
        except Exception as e:
            logger.error(f"ログ表示エラー: {e}")
    
    def open_video(self):
        """動画ファイルを開くダイアログを表示"""
        file_path, _ = QFileDialog.getOpenFileName(self, "動画ファイルを開く", "", "動画ファイル (*.mp4 *.avi *.mkv *.mov *.wmv);;すべてのファイル (*)")
        if file_path:
            self.load_video(file_path)
    
    def load_video(self, file_path=None):
        """動画ファイルを読み込む"""
        if file_path is None:
            return
            
        if not os.path.exists(file_path):
            self.show_error(f"ファイルが見つかりません: {file_path}")
            return
        
        # ファイル拡張子をチェック
        _, ext = os.path.splitext(file_path)
        supported_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
        if ext.lower() not in supported_extensions:
            self.show_error(f"サポートされていないファイル形式です: {ext}\nサポート形式: {', '.join(supported_extensions)}")
            return
        
        try:
            # メディアプレイヤーに動画をセット
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            
            # データベースに動画情報を保存
            video = self.database.get_video_by_path(file_path)
            if video:
                self.current_video_id = video['id']
            else:
                # 新しい動画の場合は追加
                duration = 0  # 実際の長さは後で更新される
                self.current_video_id = self.database.add_video(file_path, duration)
            
            # シーンパネルに現在の動画IDを設定
            self.scene_panel.set_video(self.current_video_id)
            
            self.log(f"動画を読み込みました: {os.path.basename(file_path)}")
            
            # 動画を自動再生
            self.media_player.play()
        except Exception as e:
            self.show_error(f"動画の読み込み中にエラーが発生しました: {str(e)}")
    
    def toggle_play(self):
        """再生/一時停止を切り替え"""
        if self.media_player.state() == QMediaPlayer.PlayingState:  # type: ignore[attr-defined]
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def stop_playback(self):
        """再生を停止"""
        self.media_player.stop()
    
    def update_position(self, position):
        """再生位置の更新"""
        self.seek_slider.setValue(position)
        self.time_label.setText(f"{self._format_time(position)} / {self._format_time(self.media_player.duration())}")
        
        # 現在の再生位置（ミリ秒）を秒に変換
        current_time_sec = position / 1000.0
        
        # シーンリストがある場合、現在の再生位置に対応するシーンをハイライト
        if hasattr(self, 'scene_panel') and self.scene_panel.scene_list.count() > 0:
            # 現在の再生位置に最も近いシーンを選択
            try:
                self.scene_panel.highlight_scene_at_time(current_time_sec)
            except RuntimeError as e:
                # アイテムが削除されている場合のエラーを無視
                self.logger.warning(f"シーンハイライト中にエラーが発生しました: {e}")
    
    def update_duration(self, duration):
        """動画の長さが変更された時の処理"""
        self.seek_slider.setRange(0, duration)
        self.time_label.setText(f"{self._format_time(0)} / {self._format_time(duration)}")
    
    def set_position(self, position):
        """スライダーから再生位置を設定"""
        self.media_player.setPosition(position)
    
    def set_volume(self, volume):
        """音量を設定"""
        self.media_player.setVolume(volume)
    
    def change_playback_speed(self, index):
        """再生速度を変更"""
        speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        self.set_playback_rate(speeds[index])
    
    def set_playback_rate(self, rate):
        """再生速度を設定"""
        self.media_player.setPlaybackRate(rate)
        self.log(f"再生速度を {rate}x に設定しました")
    
    def _format_time(self, milliseconds):
        """ミリ秒を時:分:秒形式に変換"""
        t = timedelta(milliseconds=milliseconds)
        return str(t).split('.')[0]
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグ＆ドロップ - ドラッグ開始時"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """ドラッグ＆ドロップ - ドロップ時"""
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            if os.path.exists(file_path):
                self.load_video(file_path)
    
    def closeEvent(self, event):
        """ウィンドウを閉じる時の処理"""
        # データベース接続を閉じる
        self.database.close()
        self.log("データベース接続を閉じました")
        event.accept()
    
    def handle_media_error(self, error):
        """メディアプレイヤーのエラーハンドリング"""
        error_messages = {
            QMediaPlayer.NoError: "エラーはありません",  # type: ignore[attr-defined]
            QMediaPlayer.ResourceError: "リソースエラー: メディアが見つからないか、アクセスできません",  # type: ignore[attr-defined]
            QMediaPlayer.FormatError: "フォーマットエラー: メディア形式がサポートされていません",  # type: ignore[attr-defined]
            QMediaPlayer.NetworkError: "ネットワークエラー: ネットワーク接続に問題があります",  # type: ignore[attr-defined]
            QMediaPlayer.AccessDeniedError: "アクセス拒否エラー: メディアへのアクセスが拒否されました",  # type: ignore[attr-defined]
            QMediaPlayer.ServiceMissingError: "サービス欠落エラー: メディアサービスが見つかりません"  # type: ignore[attr-defined]
        }
        
        error_message = error_messages.get(error, f"不明なエラー: {error}")
        
        self.log(f"メディアエラー: {error_message}")
        
        if error != QMediaPlayer.NoError:  # type: ignore[attr-defined]
            # エラーメッセージを表示
            QMessageBox.critical(self, "メディアエラー", error_message)
            
            # Windows環境でMediaFoundationに関連するエラーの場合
            if platform.system() == 'Windows' and (error == QMediaPlayer.ResourceError or error == QMediaPlayer.FormatError):  # type: ignore[attr-defined]
                self.log("Windows MediaFoundationでエラーが発生しました。以下を確認してください:")
                self.log("1. Windows Media Feature Packがインストールされていることを確認してください")
                self.log("2. サポートされている動画形式（H.264/MP4）を使用していることを確認してください")
                
                # 詳細なエラー情報とトラブルシューティングのダイアログを表示
                QMessageBox.information(
                    self,
                    "MediaFoundationエラー - トラブルシューティング",
                    "<h3>MediaFoundationエラー</h3>"
                    "<p>動画の読み込み中にエラーが発生しました。以下の点を確認してください：</p>"
                    "<ol>"
                    "<li><b>Windows Media Feature Pack</b>がインストールされていることを確認してください。</li>"
                    "<li>動画ファイルが<b>H.264/MP4形式</b>であることを確認してください。</li>"
                    "<li>動画ファイルが破損していないことを確認してください。</li>"
                    "<li>別の動画ファイルで試してみてください。</li>"
                    "</ol>"
                    "<p>Windows Nエディションをご使用の場合は、Media Feature Packを別途インストールする必要があります。</p>"
                )
    
    def show_error(self, message):
        """エラーメッセージを表示"""
        self.log(f"エラー: {message}")
        QMessageBox.critical(self, "エラー", message)
    
    def show_settings(self):
        """設定ダイアログを表示"""
        dialog = SettingsDialog(self.database, self)
        dialog.settings_updated_signal.connect(self.settings_updated)
        dialog.exec_()
    
    def settings_updated(self):
        """設定が更新された時の処理"""
        self.log("設定が更新されました")
        # 必要に応じて設定の再読み込みなどを行う
    
    def toggle_loop(self, state):
        """ループ再生の切り替え"""
        self.loop_playback = (state == Qt.Checked)  # type: ignore[attr-defined]
        if self.loop_playback:
            self.log("ループ再生を有効にしました")
        else:
            self.log("ループ再生を無効にしました")
    
    def media_state_changed(self, state):
        """メディア再生状態の変更時の処理"""
        if state == QMediaPlayer.PlayingState:  # type: ignore[attr-defined]
            # 再生中は一時停止アイコンを表示
            pause_icon = self.create_blue_icon(QStyle.SP_MediaPause)  # type: ignore[attr-defined]
            self.play_button.setIcon(pause_icon)
        else:
            # 停止中は再生アイコンを表示
            play_icon = self.create_blue_icon(QStyle.SP_MediaPlay)  # type: ignore[attr-defined]
            self.play_button.setIcon(play_icon)
    
    def media_status_changed(self, status):
        """メディアプレイヤーのステータス変更イベント"""
        if status == QMediaPlayer.EndOfMedia:  # type: ignore[attr-defined]
            if self.loop_playback:
                self.log("ループ再生: 動画を最初から再生します")
                self.media_player.setPosition(0)
                self.media_player.play()
    
    def jump_to_scene(self, scene_data):
        """シーンにジャンプ"""
        if scene_data and 'timestamp' in scene_data:
            self.media_player.setPosition(int(scene_data['timestamp'] * 1000))
    
    def load_session(self, session_id):
        """セッションを読み込む"""
        self.current_session_id = session_id
        self.scene_panel.load_session(session_id)
    
    def update_window_title(self):
        """ウィンドウのタイトルを更新"""
        self.setWindowTitle(f"Scene Analyzer - {self.current_session_id}")

    def start_session(self):
        """セッションを開始"""
        # 動画が読み込まれていない場合は処理しない
        if not self.media_player.isAvailable():
            QMessageBox.warning(self, "警告", "動画が読み込まれていません。先に動画を開いてください。")
            return
            
        # 動画ファイルのパスを取得
        video_path = self.get_video_path()
        if not video_path or not os.path.exists(video_path):
            QMessageBox.critical(self, "エラー", f"動画ファイルが見つかりません")
            return
            
        # セッションダイアログを表示
        dialog = SessionDialog(self.database, self, video_path)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # セッションデータを取得
        session_data = dialog.get_session_data()
        if not session_data:
            return
            
        # セッション名を取得
        session_name = session_data['name']
        
        # 検出パラメータを取得
        detection_threshold = session_data['detection_threshold']
        min_scene_duration = session_data['min_scene_duration']
        use_cuda = session_data['use_cuda']
        
        # APIキーを取得
        api_key = dialog.api_key_edit.text()
        if not api_key:
            # APIキーが設定されていない場合は警告
            QMessageBox.warning(self, "警告", "APIキーが設定されていません。シーン解析は実行できません。")
            return
            
        # APIキーはデータベースにのみ保存し、レジストリには保存しない
        self.database.set_setting("analysis.api_key", api_key)
        
        # セッションを作成
        try:
            session_id = self.database.create_session(session_name, self.current_video_id)
            if not session_id:
                QMessageBox.critical(self, "エラー", "セッションの作成に失敗しました")
                return
            
            # 現在のセッションを設定
            self.current_session_id = session_id
            self.update_window_title()
            
            # ステータスバーを更新
            self.statusBar().showMessage(f"セッション '{session_name}' を作成しました")
            
            # プログレスバーを表示
            self.progress_dialog = QProgressDialog("シーン検出中...", "キャンセル", 0, 100, self)
            self.progress_dialog.setWindowTitle("シーン検出")
            self.progress_dialog.setLabelText("シーンを検出しています...")
            self.progress_dialog.setCancelButtonText("キャンセル")
            self.progress_dialog.setRange(0, 100)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            
            # シーン検出ワーカーとスレッドを作成
            self.detector_thread = QThread()
            self.detector_worker = SceneDetectorWorker(
                video_path=video_path,  # 既に検証済みのvideo_pathを使用
                threshold=detection_threshold,
                min_scene_duration=min_scene_duration,
                use_cuda=use_cuda
            )
            
            # ワーカーをスレッドに移動
            self.detector_worker.moveToThread(self.detector_thread)
            
            # シグナル/スロット接続
            # type: ignore コメントを使用して型チェックを無視
            self.detector_thread.started.connect(self.detector_worker.run)  # type: ignore
            self.detector_worker.progress_updated.connect(self.progress_dialog.setValue)
            self.detector_worker.scene_detected.connect(self.on_scene_detected)
            self.detector_worker.detection_completed.connect(self.on_detection_completed)
            self.detector_worker.error_occurred.connect(self.on_worker_error)
            self.detector_worker.log_message.connect(self.log)
            self.detector_worker.progress_label_updated.connect(self.progress_dialog.setLabelText)
            self.progress_dialog.canceled.connect(self.detector_worker.stop)
            
            # スレッド開始
            self.detector_thread.start()
            
            # ログ出力
            self.log(f"シーン検出を開始しました: セッション '{session_name}'")
            self.log(f"パラメータ: 閾値={detection_threshold}, 最小シーン長={min_scene_duration}秒, CUDA={use_cuda}")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"セッション開始中にエラーが発生しました: {str(e)}")
            logger.error(f"セッション開始中にエラーが発生しました: {str(e)}", exc_info=True)

    def on_scene_detected(self, scene_info):
        """シーン検出時のコールバック"""
        try:
            # シーンをデータベースに保存
            if self.current_session_id is not None:
                scene_id = self.database.add_scene(
                    session_id=int(self.current_session_id),
                    timestamp=scene_info["timestamp"],
                    duration=scene_info["duration"]
                )
            else:
                self.log("警告: 現在のセッションIDがNoneです。シーンを保存できません。")
                return
            
            if scene_id:
                # ログ出力
                self.log(f"シーン検出: {scene_info['timestamp']:.2f}秒, 長さ: {scene_info['duration']:.2f}秒")
        except Exception as e:
            logger.error(f"シーン保存中にエラーが発生しました: {str(e)}", exc_info=True)

    def on_detection_completed(self, scenes):
        """シーン検出完了時のコールバック"""
        try:
            # プログレスダイアログを閉じる
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.setValue(100)
                self.progress_dialog.close()
            
            # スレッドをクリーンアップ
            if hasattr(self, 'detector_thread') and self.detector_thread:
                self.detector_thread.quit()
                self.detector_thread.wait()
            
            # 検出されたシーンの数を取得
            scene_count = len(scenes)
            
            # ログ出力
            self.log(f"シーン検出完了: {scene_count}シーンを検出しました")
            
            # キーフレーム抽出を開始
            self.extract_keyframes()
            
        except Exception as e:
            logger.error(f"シーン検出完了処理中にエラーが発生しました: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "エラー", f"シーン検出完了処理中にエラーが発生しました: {str(e)}")

    def extract_keyframes(self):
        """検出されたシーンからキーフレームを抽出"""
        try:
            # 動画ファイルのパスを取得
            video_path = self.get_video_path()
            if not video_path or not os.path.exists(video_path):
                QMessageBox.critical(self, "エラー", f"動画ファイルが見つかりません: {video_path}")
                return
            
            # セッションのシーンを取得
            if self.current_session_id is not None:
                scenes = self.database.get_scenes(int(self.current_session_id))
                if not scenes:
                    self.log("キーフレーム抽出: シーンが見つかりません")
                    return
            else:
                self.log("警告: 現在のセッションIDがNoneです。シーンを取得できません。")
                return
            
            # プログレスダイアログを表示
            self.progress_dialog = QProgressDialog("キーフレーム抽出中...", "キャンセル", 0, 100, self)
            self.progress_dialog.setWindowTitle("キーフレーム抽出")
            self.progress_dialog.setLabelText("キーフレームを抽出しています...")
            self.progress_dialog.setCancelButtonText("キャンセル")
            self.progress_dialog.setRange(0, 100)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            
            # キーフレーム保存ディレクトリを作成
            keyframes_dir = os.path.join(self.database.get_data_dir(), "keyframes", str(self.current_session_id))
            os.makedirs(keyframes_dir, exist_ok=True)
            
            # デバッグ情報を出力
            self.log(f"キーフレーム保存ディレクトリ: {keyframes_dir}")
            self.log(f"ディレクトリ存在確認: {os.path.exists(keyframes_dir)}")
            
            # ワーカースレッドを作成
            self.keyframe_thread = QThread()
            self.keyframe_worker = KeyframeExtractorWorker(video_path, scenes, keyframes_dir)
            self.keyframe_worker.moveToThread(self.keyframe_thread)
            
            # シグナル接続
            self.keyframe_thread.started.connect(self.keyframe_worker.run)  # type: ignore
            self.keyframe_worker.progress_updated.connect(self.progress_dialog.setValue)
            self.keyframe_worker.log_message.connect(self.log)
            self.keyframe_worker.error_occurred.connect(self.on_worker_error)
            self.keyframe_worker.keyframe_extracted.connect(self.on_keyframe_extracted)
            self.keyframe_worker.extraction_completed.connect(self.on_keyframe_extraction_completed)
            
            # キャンセルボタンの接続
            self.progress_dialog.canceled.connect(self.keyframe_worker.stop)
            
            # スレッド終了時の処理
            self.keyframe_worker.extraction_completed.connect(self.keyframe_thread.quit)
            self.keyframe_worker.error_occurred.connect(self.keyframe_thread.quit)
            self.keyframe_thread.finished.connect(self.keyframe_thread.deleteLater)
            
            # スレッド開始
            self.keyframe_thread.start()
            
        except Exception as e:
            logger.error(f"キーフレーム抽出の準備中にエラーが発生しました: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "エラー", f"キーフレーム抽出の準備中にエラーが発生しました: {str(e)}")
    
    def on_keyframe_extracted(self, scene):
        """キーフレーム抽出時のコールバック"""
        try:
            # データベースを更新
            if "id" in scene and "frame_path" in scene:
                update_result = self.database.update_scene(scene["id"], {"frame_path": scene["frame_path"]})
                if not update_result:
                    self.log(f"警告: シーン {scene['id']} のフレームパス更新に失敗しました")
                else:
                    self.log(f"シーン {scene['id']} のフレームパスを更新しました: {scene['frame_path']}")
                    
                # シーンパネルを更新
                if hasattr(self, 'scene_panel'):
                    self.scene_panel.update_scene(scene)
            else:
                self.log(f"警告: シーン情報が不完全です: {scene}")
                
        except Exception as e:
            logger.error(f"キーフレーム抽出コールバック中にエラーが発生しました: {str(e)}", exc_info=True)
            self.log(f"エラー: キーフレーム抽出コールバック中にエラーが発生しました: {str(e)}")
    
    def on_keyframe_extraction_completed(self, scenes):
        """キーフレーム抽出完了時のコールバック"""
        try:
            # プログレスダイアログを閉じる
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.setValue(100)
                self.progress_dialog.close()
            
            # ログ出力
            self.log(f"キーフレーム抽出完了: {len(scenes)}シーンのキーフレームを抽出しました")
            
            # シーン解析を開始
            if scenes:
                self.analyze_scenes(scenes)
            else:
                self.log("警告: 抽出されたシーンがありません。シーン解析をスキップします。")
            
        except Exception as e:
            logger.error(f"キーフレーム抽出完了処理中にエラーが発生しました: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "エラー", f"キーフレーム抽出完了処理中にエラーが発生しました: {str(e)}")

    def analyze_scenes(self, scenes=None):
        """シーンを解析"""
        try:
            # シーンが指定されていない場合は現在のシーンを使用
            if scenes is None:
                if self.current_session_id is None:
                    self.log("現在のセッションが設定されていません。シーン解析をスキップします。")
                    QMessageBox.warning(self, "警告", "現在のセッションが設定されていません。シーン解析をスキップします。")
                    return
                scenes = self.database.get_scenes(self.current_session_id)
                
            if not scenes:
                self.log("シーンが見つかりません。シーン解析をスキップします。")
                QMessageBox.warning(self, "警告", "シーンが見つかりません。シーン解析をスキップします。")
                return
                
            # APIキーの取得
            api_key = self.database.get_setting('analysis.api_key', '')
            
            # APIキーが空の場合はQSettingsから取得
            if not api_key:
                api_key = self.settings.value("api_key", "")
                
            # APIキーが設定されていない場合は処理を中止
            if not api_key:
                error_msg = "APIキーが設定されていません。設定ダイアログでAPIキーを設定してください。"
                self.log(error_msg)
                QMessageBox.warning(
                    self, 
                    "APIキーエラー", 
                    error_msg
                )
                # 設定ダイアログを表示するか確認
                reply = QMessageBox.question(
                    self,
                    "設定",
                    "APIキー設定ダイアログを開きますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.show_settings_dialog()
                return
                
            # モデル名の取得
            model_name = self.database.get_setting('analysis.model', 'gemini-1.5-flash')
            
            # 有効なシーンのみを抽出
            valid_scenes = []
            for scene in scenes:
                frame_path = scene.get('frame_path')
                if frame_path and os.path.exists(frame_path):
                    valid_scenes.append(scene)
                else:
                    self.log(f"警告: フレーム画像が見つかりません: {frame_path}")
            
            if not valid_scenes:
                self.log("警告: 有効なフレーム画像を持つシーンがありません。シーン解析をスキップします。")
                QMessageBox.warning(self, "警告", "有効なフレーム画像を持つシーンがありません。シーン解析をスキップします。")
                return
            
            self.log(f"シーン解析を開始します。APIキーの状態: {'設定済み' if api_key else '未設定'}")
            self.log(f"Gemini APIを設定します。APIキー: {api_key[:3]}...{api_key[-3:]}")
            
            # プログレスダイアログを表示
            self.progress_dialog = QProgressDialog("シーン解析中...", "キャンセル", 0, 100, self)
            self.progress_dialog.setWindowTitle("シーン解析")
            self.progress_dialog.setLabelText("シーンを解析しています...")
            self.progress_dialog.setCancelButtonText("キャンセル")
            self.progress_dialog.setRange(0, 100)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            
            # プロンプトの取得
            prompt = None
            prompt_id = self.settings.value("prompt_id", None)
            if prompt_id:
                prompt_data = self.database.get_prompt_by_id(prompt_id)
                if prompt_data:
                    prompt = prompt_data.get('content')
                    self.log(f"プロンプトを取得しました: {prompt_data.get('name')}")
            
            # 解析ワーカーとスレッドを作成
            self.analyzer_thread = QThread()
            self.analyzer_worker = SceneAnalyzerWorker(
                scenes=valid_scenes,
                api_key=api_key,
                model_name=model_name,
                prompt=prompt
            )
            
            # シグナル接続
            self.analyzer_worker.progress_updated.connect(self.progress_dialog.setValue)
            self.analyzer_worker.scene_analyzed.connect(self.on_scene_analyzed)
            self.analyzer_worker.analysis_completed.connect(self.on_analysis_completed)
            self.analyzer_worker.error_occurred.connect(self.on_worker_error)
            self.analyzer_worker.log_message.connect(self.log)
            self.progress_dialog.canceled.connect(self.analyzer_worker.stop)
            
            # スレッド設定
            self.analyzer_worker.moveToThread(self.analyzer_thread)
            # 型エラーを回避するためにtype: ignoreを追加
            self.analyzer_thread.started.connect(self.analyzer_worker.run)  # type: ignore
            self.analyzer_worker.analysis_completed.connect(self.analyzer_thread.quit)
            self.analyzer_worker.analysis_completed.connect(self.analyzer_worker.deleteLater)
            self.analyzer_thread.finished.connect(self.analyzer_thread.deleteLater)
            
            # スレッド開始
            self.analyzer_thread.start()
            
        except Exception as e:
            logger.error(f"シーン解析の開始中にエラーが発生しました: {str(e)}", exc_info=True)
            self.log(f"エラー: シーン解析の開始中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(self, "エラー", f"シーン解析の開始中にエラーが発生しました:\n{str(e)}")
            
            # プログレスダイアログを閉じる
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()

    def on_scene_analyzed(self, scene):
        """シーン解析時のコールバック"""
        try:
            # データベースを更新
            self.database.update_scene(
                scene_id=scene["id"],
                data={
                    "description": scene.get("description", ""),
                    "confidence": scene.get("confidence", 0)
                }
            )
            
            # ログ出力
            self.log(f"シーン解析: シーン {scene['id']}, 時間: {scene['timestamp']:.2f}秒")
            
        except Exception as e:
            logger.error(f"シーン解析結果の保存中にエラーが発生しました: {str(e)}", exc_info=True)

    def on_analysis_completed(self, scenes):
        """シーン解析完了時のコールバック"""
        try:
            # プログレスダイアログを閉じる
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.setValue(100)
                self.progress_dialog.close()
            
            # スレッドをクリーンアップ
            if hasattr(self, 'analyzer_thread') and self.analyzer_thread:
                self.analyzer_thread.quit()
                self.analyzer_thread.wait()
            
            # ログ出力
            self.log(f"シーン解析完了: {len(scenes)}シーンを解析しました")
            
            # データベースからセッション情報を確認
            if self.current_video_id is not None and self.current_session_id is not None:
                sessions = self.database.get_sessions_for_video(self.current_video_id)
                session_exists = False
                for session in sessions:
                    if session['id'] == self.current_session_id:
                        session_exists = True
                        self.log(f"セッション情報を確認: ID={session['id']}, 名前={session['name']}")
                        break
                
                if not session_exists:
                    self.log(f"警告: セッション ID={self.current_session_id} がデータベースに見つかりません")
            
            # シーンパネルに現在の動画IDを設定してからセッションを読み込む
            if self.current_video_id is not None:
                self.scene_panel.set_video(self.current_video_id)
                # セッション選択ボックスを明示的に更新
                self.scene_panel.update_session_combo()
            
            # セッションを読み込み
            self.load_session(self.current_session_id)
            
        except Exception as e:
            logger.error(f"シーン解析完了処理中にエラーが発生しました: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "エラー", f"シーン解析完了処理中にエラーが発生しました: {str(e)}")

    def on_worker_error(self, error_msg):
        """ワーカーからのエラーを処理"""
        self.log(f"エラー: {error_msg}")
        
        # プログレスダイアログを閉じる
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            
        # エラーメッセージを表示
        QMessageBox.critical(self, "エラー", error_msg)
        
        # スレッドをクリーンアップ
        if hasattr(self, 'analyzer_thread') and self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.quit()
            self.analyzer_thread.wait()

    def show_settings_dialog(self):
        """設定ダイアログを表示"""
        dialog = SettingsDialog(self.database, self)
        dialog.settings_updated_signal.connect(self.settings_updated)
        dialog.exec_()

    def export_session(self):
        """セッションをエクスポート"""
        if not self.current_session_id:
            # セッションが選択されていない場合、利用可能なセッションを確認
            if self.current_video_id:
                sessions = self.database.get_sessions_for_video(self.current_video_id)
                if sessions:
                    # セッションが存在する場合、選択を促す
                    session_id = sessions[0]['id']
                    session_name = sessions[0]['name']
                    reply = QMessageBox.question(
                        self, 
                        "セッション選択", 
                        f"現在セッションが選択されていません。\n最新のセッション '{session_name}' を選択しますか？",
                        QMessageBox.Yes | QMessageBox.No, 
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # セッションを選択
                        self.current_session_id = session_id
                        self.scene_panel.load_session(session_id)
                        self.log(f"セッション '{session_name}' を選択しました")
                    else:
                        return
                else:
                    QMessageBox.warning(self, "警告", "エクスポートするセッションがありません。\n先にシーン検出セッションを作成してください。")
                    return
            else:
                QMessageBox.warning(self, "警告", "動画が読み込まれていません。\n先に動画を読み込み、シーン検出セッションを作成してください。")
                return
        
        # エクスポート形式の選択ダイアログ
        menu = QMenu(self)
        json_action = QAction("JSONとしてエクスポート", self)
        csv_action = QAction("CSVとしてエクスポート", self)
        
        menu.addAction(json_action)
        menu.addAction(csv_action)
        
        # アクションの接続
        json_action.triggered.connect(lambda: self._export_session_format('json'))
        csv_action.triggered.connect(lambda: self._export_session_format('csv'))
        
        # メニューを表示
        menu.exec_(QCursor.pos())
    
    def _export_session_format(self, format_type):
        """
        セッションを指定された形式でエクスポート
        
        Args:
            format_type (str): エクスポート形式 ('json' または 'csv')
        """
        # シーンパネルのエクスポート機能を呼び出す
        # 一度だけ接続する
        try:
            self.scene_panel.export_requested.disconnect(self.handle_export)
        except TypeError:
            # 接続されていない場合は無視
            pass
        
        self.scene_panel.export_requested.connect(self.handle_export)
        self.scene_panel._export_session(format_type)
    
    def handle_export(self, session_id, format_type):
        """
        エクスポートリクエストを処理
        
        Args:
            session_id (int): セッションID
            format_type (str): エクスポート形式
        """
        try:
            # セッション情報を取得
            session = self.database.get_session(session_id)
            if not session:
                self.log(f"エラー: セッションID {session_id} が見つかりません")
                return
            
            # シーン情報を取得
            scenes = self.database.get_scenes(session_id)
            if not scenes:
                self.log(f"エラー: セッションID {session_id} にシーンが見つかりません")
                return
            
            # エクスポート設定の取得
            export_settings = self.database.get_setting('export', {
                'default_path': os.path.join(os.path.expanduser("~"), "Documents"),
                'format': 'json'
            })
            
            # 辞書型でない場合は、デフォルト値を使用
            if not isinstance(export_settings, dict):
                export_settings = {
                    'default_path': os.path.join(os.path.expanduser("~"), "Documents"),
                    'format': 'json'
                }
            
            default_path = export_settings.get('default_path', os.path.join(os.path.expanduser("~"), "Documents"))
            
            # ファイル保存ダイアログ
            if format_type == 'json':
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "JSONファイルの保存",
                    os.path.join(default_path, f"session_{session_id}.json"),
                    "JSONファイル (*.json);;すべてのファイル (*.*)"
                )
            else:
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "CSVファイルの保存",
                    os.path.join(default_path, f"session_{session_id}.csv"),
                    "CSVファイル (*.csv);;すべてのファイル (*.*)"
                )
            
            if not file_path:
                return
            
            # エクスポート処理
            if format_type == 'json':
                self._export_to_json(file_path, session, scenes)
            else:
                self._export_to_csv(file_path, session, scenes)
            
            # 成功メッセージ
            self.log(f"セッションID {session_id} を {format_type.upper()} 形式でエクスポートしました: {file_path}")
            QMessageBox.information(self, "エクスポート完了", f"セッションを {format_type.upper()} 形式でエクスポートしました。\n\n{file_path}")
            
        except Exception as e:
            logger.error(f"エクスポート中にエラーが発生しました: {str(e)}", exc_info=True)
            self.log(f"エラー: エクスポート中にエラーが発生しました: {str(e)}")
            QMessageBox.critical(self, "エラー", f"エクスポート中にエラーが発生しました: {str(e)}")
    
    def _export_to_json(self, file_path, session, scenes):
        """
        JSONとしてエクスポート
        
        Args:
            file_path (str): 保存先ファイルパス
            session (dict): セッション情報
            scenes (list): シーン情報のリスト
        """
        # エクスポートデータの作成
        export_data = {
            'session': session,
            'scenes': scenes,
            'export_date': datetime.now().isoformat(),
            'app_version': '1.0.0'
        }
        
        # JSONとして保存
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    def _export_to_csv(self, file_path, session, scenes):
        """
        CSVとしてエクスポート
        
        Args:
            file_path (str): 保存先ファイルパス
            session (dict): セッション情報
            scenes (list): シーン情報のリスト
        """
        # CSVとして保存
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # ヘッダー行
            writer.writerow(['シーンID', '開始時間(秒)', '長さ(秒)', '説明', 'タグ'])
            
            # データ行
            for scene in scenes:
                writer.writerow([
                    scene.get('id', ''),
                    scene.get('timestamp', 0),
                    scene.get('duration', 0),
                    scene.get('description', ''),
                    ','.join(scene.get('tags', []))
                ])

    def reinitialize_database(self):
        """データベースを再初期化"""
        self.log("データベースを再初期化します")
        
        # 確認ダイアログを表示
        reply = QMessageBox.warning(
            self, "データベースの再初期化",
            "データベースを再初期化すると、すべての動画、セッション、シーン情報が削除されます。\n"
            "この操作は元に戻せません。続行しますか？\n\n"
            "注意: 再初期化後、アプリケーションは自動的に終了します。再起動が必要です。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # データベースファイルのパス
                db_path = os.path.join(os.path.expanduser('~'), '.scene_analyzer', 'scene_analyzer.db')
                
                # バックアップを作成
                backup_path = f"{db_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                if os.path.exists(db_path):
                    import shutil
                    shutil.copy2(db_path, backup_path)
                    self.log(f"データベースのバックアップを作成しました: {backup_path}")
                
                # 現在のデータベース接続を閉じる
                if self.database:
                    self.database.close()
                    self.log("データベース接続を閉じました")
                
                # メモリ解放を促進
                import gc
                gc.collect()
                
                # 一時的な新しいデータベースファイルを作成
                temp_db_path = f"{db_path}.new"
                
                # 新しいデータベースを作成
                temp_database = Database(temp_db_path)
                temp_database.initialize()
                temp_database.close()
                self.log("一時データベースを作成しました")
                
                # 既存のデータベースファイルを削除または置き換え
                try:
                    # 既存のファイルを削除
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        self.log("既存のデータベースファイルを削除しました")
                except PermissionError:
                    self.log("データベースファイルを直接削除できません。アプリケーション終了時に置き換えます")
                
                try:
                    # 一時ファイルを正式な場所に移動
                    import shutil
                    shutil.move(temp_db_path, db_path)
                    self.log("新しいデータベースファイルを設定しました")
                except PermissionError:
                    self.log("データベースファイルを置き換えられません。アプリケーション終了時に置き換えられるよう設定します")
                    # 終了時に置き換えるためのバッチファイルを作成
                    self._create_db_replace_script(temp_db_path, db_path)
                
                # データベースを再接続
                self.database = Database(db_path)
                self.database.initialize()
                self.log("データベースを再初期化しました")
                
                # シーンパネルにデータベースを再設定
                self.scene_panel.set_database(self.database)
                
                # 現在の動画とセッションをクリア
                self.current_video_id = None
                self.current_session_id = None
                
                # シーンパネルをクリア
                self.scene_panel.clear()
                
                # 成功メッセージを表示
                QMessageBox.information(
                    self, 
                    "完了", 
                    "データベースを再初期化しました。\n"
                    "アプリケーションを再起動してください。"
                )
                
                # ウィンドウタイトルを更新
                self.update_window_title()
                
                # アプリケーションを終了
                QApplication.quit()
                
            except Exception as e:
                logger.error(f"データベースの再初期化に失敗しました: {e}", exc_info=True)
                self.log(f"データベースの再初期化に失敗しました: {e}")
                QMessageBox.critical(self, "エラー", f"データベースの再初期化に失敗しました: {e}")
        else:
            self.log("データベースの再初期化をキャンセルしました")
            
    def _create_db_replace_script(self, temp_db_path, db_path):
        """
        アプリケーション終了後にデータベースファイルを置き換えるためのスクリプトを作成
        
        Args:
            temp_db_path (str): 一時データベースファイルのパス
            db_path (str): 本来のデータベースファイルのパス
        """
        try:
            # スクリプトファイルのパス
            script_dir = os.path.dirname(db_path)
            script_path = os.path.join(script_dir, "replace_db.bat")
            
            # スクリプトの内容
            script_content = f"""@echo off
timeout /t 2 /nobreak > nul
if exist "{db_path}" del "{db_path}"
if exist "{temp_db_path}" move "{temp_db_path}" "{db_path}"
del "%~f0"
"""
            
            # スクリプトファイルを作成
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # スクリプトを実行
            import subprocess
            subprocess.Popen(["start", "cmd", "/c", script_path], shell=True)
            
            self.log(f"データベース置換スクリプトを作成しました: {script_path}")
        except Exception as e:
            logger.error(f"データベース置換スクリプトの作成に失敗しました: {e}", exc_info=True)
            self.log(f"データベース置換スクリプトの作成に失敗しました: {e}")

    def get_video_path(self):
        """現在の動画ファイルのパスを取得"""
        try:
            if not self.current_video_id:
                return None
            
            # データベースから動画情報を取得
            video_info = self.database.get_video(self.current_video_id)
            if not video_info:
                return None
            
            # パスを取得
            video_path = video_info.get("file_path")  # "path"から"file_path"に修正
            if not video_path:
                return None
            
            return video_path
        
        except Exception as e:
            logger.error(f"動画パスの取得に失敗しました: {str(e)}")
        
        return None

    def start_scene_detection_analysis(self):
        """シーン検出と解析を開始"""
        # 動画が読み込まれていない場合は処理しない
        if not self.media_player.isAvailable():
            QMessageBox.warning(self, "警告", "動画が読み込まれていません。先に動画を開いてください。")
            return
            
        # 動画ファイルのパスを取得
        video_path = self.get_video_path()
        if not video_path or not os.path.exists(video_path):
            QMessageBox.critical(self, "エラー", f"動画ファイルが見つかりません")
            return
            
        # セッションダイアログを表示
        dialog = SessionDialog(self.database, self, video_path)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # セッションデータを取得
        session_data = dialog.get_session_data()
        if not session_data:
            return
            
        # セッション名を取得
        session_name = session_data['name']
        
        # 検出パラメータを取得
        detection_threshold = session_data['detection_threshold']
        min_scene_duration = session_data['min_scene_duration']
        use_cuda = dialog.get_use_cuda()
        
        # APIキーを取得
        api_key = dialog.api_key_edit.text()
        if not api_key:
            # APIキーが設定されていない場合は警告
            QMessageBox.warning(self, "警告", "APIキーが設定されていません。シーン解析は実行できません。")
            return
            
        # APIキーはデータベースにのみ保存し、レジストリには保存しない
        self.database.set_setting("analysis.api_key", api_key)
        
        # セッションを作成
        try:
            session_id = self.database.create_session(session_name, self.current_video_id)
            if not session_id:
                QMessageBox.critical(self, "エラー", "セッションの作成に失敗しました")
                return
            
            # 現在のセッションを設定
            self.current_session_id = session_id
            self.update_window_title()
            
            # ステータスバーを更新
            self.statusBar().showMessage(f"セッション '{session_name}' を作成しました")
            
            # プログレスバーを表示
            self.progress_dialog = QProgressDialog("シーン検出中...", "キャンセル", 0, 100, self)
            self.progress_dialog.setWindowTitle("シーン検出")
            self.progress_dialog.setLabelText("シーンを検出しています...")
            self.progress_dialog.setCancelButtonText("キャンセル")
            self.progress_dialog.setRange(0, 100)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            
            # シーン検出ワーカーとスレッドを作成
            self.detector_thread = QThread()
            self.detector_worker = SceneDetectorWorker(
                video_path=video_path,  # 既に検証済みのvideo_pathを使用
                threshold=detection_threshold,
                min_scene_duration=min_scene_duration,
                use_cuda=use_cuda
            )
            
            # ワーカーをスレッドに移動
            self.detector_worker.moveToThread(self.detector_thread)
            
            # シグナル/スロット接続
            # type: ignore コメントを使用して型チェックを無視
            self.detector_thread.started.connect(self.detector_worker.run)  # type: ignore
            self.detector_worker.progress_updated.connect(self.progress_dialog.setValue)
            self.detector_worker.scene_detected.connect(self.on_scene_detected)
            self.detector_worker.detection_completed.connect(self.on_detection_completed)
            self.detector_worker.error_occurred.connect(self.on_worker_error)
            self.detector_worker.log_message.connect(self.log)
            self.detector_worker.progress_label_updated.connect(self.progress_dialog.setLabelText)
            self.progress_dialog.canceled.connect(self.detector_worker.stop)
            
            # スレッド開始
            self.detector_thread.start()
            
            # ログ出力
            self.log(f"シーン検出を開始しました: セッション '{session_name}'")
            self.log(f"パラメータ: 閾値={detection_threshold}, 最小シーン長={min_scene_duration}秒, CUDA={use_cuda}")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"セッション開始中にエラーが発生しました: {str(e)}")
            logger.error(f"セッション開始中にエラーが発生しました: {str(e)}", exc_info=True)

    def create_blue_icon(self, standard_icon):
        """標準アイコンを青色に変更したアイコンを作成する"""
        # 標準アイコンを取得
        icon = self.style().standardIcon(standard_icon)  # type: ignore[attr-defined]
        pixmap = icon.pixmap(32, 32)
        
        # 新しいピクスマップを作成
        new_pixmap = QPixmap(pixmap.size())
        new_pixmap.fill(Qt.transparent)  # type: ignore[attr-defined]
        
        # ペインターを作成
        painter = QPainter(new_pixmap)
        
        # 元のピクスマップを描画
        painter.drawPixmap(0, 0, pixmap)
        
        # 青色のフィルターを適用
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(new_pixmap.rect(), QColor(0, 120, 215))  # 青色
        
        # ペインターを終了
        painter.end()
        
        # 新しいアイコンを作成して返す
        return QIcon(new_pixmap)

    def on_analysis_error(self, error_message):
        """解析エラー発生時の処理"""
        logger.error(f"解析エラー: {error_message}")
        self.log_message(f"エラー: {error_message}")
        
        # エラーダイアログを表示
        QMessageBox.critical(
            self,
            "解析エラー",
            f"シーン解析中にエラーが発生しました:\n{error_message}",
            QMessageBox.Ok
        )
        
        # UIの更新
        self.analyze_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # スレッドのクリーンアップ
        if hasattr(self, 'analyzer_thread') and self.analyzer_thread.isRunning():
            self.analyzer_thread.quit()
            self.analyzer_thread.wait()

           