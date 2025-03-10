#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
シーンリスト表示パネルの実装
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QScrollArea, QFrame, QSplitter, QMenu, QAction,
    QFileDialog, QMessageBox, QProgressBar, QApplication, QDialog
)
# 型チェックエラーを無視するコメントを追加
# type: ignore[attr-defined]
from PyQt5.QtCore import Qt, QSize, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtGui import QPixmap, QImage, QIcon, QCursor, QColor, QPalette

logger = logging.getLogger(__name__)

class SceneItem(QWidget):
    """シーンアイテムウィジェット"""
    
    # シグナル定義
    clicked = Signal(dict)  # クリック時のシグナル
    show_details = Signal(dict)  # 詳細表示シグナル
    
    def __init__(self, scene_data, parent=None):
        """
        初期化
        
        Args:
            scene_data (dict): シーン情報
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.scene_data = scene_data
        self.selected = False
        
        # UIの初期化
        self.init_ui()
    
    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # サムネイル
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 68)  # 16:9のアスペクト比
        self.thumbnail_label.setStyleSheet("border: 1px solid #444444; background-color: #1a1a1a;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        
        # サムネイル画像の読み込み
        self.load_thumbnail()
        
        layout.addWidget(self.thumbnail_label)
        
        # 情報レイアウト
        info_layout = QVBoxLayout()
        
        # タイムコード
        timestamp = self.scene_data.get('timestamp', 0)
        duration = self.scene_data.get('duration', 0)
        
        time_str = self._format_time(timestamp)
        duration_str = self._format_time(duration)
        
        self.time_label = QLabel(f"開始: {time_str} (長さ: {duration_str})")
        self.time_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        info_layout.addWidget(self.time_label)
        
        # 説明
        description = self.scene_data.get('description', '')
        
        # 説明を常に1行に制限し、一貫した表示にする
        short_desc = description.split('\n')[0] if description else "説明なし"
        if len(short_desc) > 50:
            short_desc = short_desc[:47] + "..."
        
        self.desc_label = QLabel(short_desc)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #b0b0b0;")
        info_layout.addWidget(self.desc_label)
        
        # 詳細ボタンを常に追加（説明の有無に関わらず）
        details_button = QPushButton("詳細")
        details_button.setStyleSheet("font-size: 9px; padding: 2px 5px; background-color: #3d8ec9; color: white; border: none;")
        details_button.setFixedWidth(40)
        details_button.clicked.connect(self._show_details)
        info_layout.addWidget(details_button)
        
        layout.addLayout(info_layout)
        layout.setStretchFactor(info_layout, 1)
        
        # スタイル設定
        self.setStyleSheet("""
            SceneItem {
                background-color: #2a2a2a;
                border-radius: 4px;
                margin: 2px;
                border: 1px solid #3a3a3a;
            }
            SceneItem:hover {
                background-color: #323232;
                border: 1px solid #444444;
            }
        """)
        
        # 最小高さを設定
        self.setMinimumHeight(80)
    
    def load_thumbnail(self):
        """サムネイル画像を読み込む"""
        # サムネイルパスを取得
        frame_path = self.scene_data.get('frame_path')
        thumbnail_path = self.scene_data.get('thumbnail_path')
        
        # シーンIDを取得
        scene_id = self.scene_data.get('id', 'unknown')
        
        # デバッグログ
        logger.debug(f"シーン {scene_id} のサムネイル読み込み: frame_path={frame_path}, thumbnail_path={thumbnail_path}")
        
        # frame_pathまたはthumbnail_pathのどちらかが存在する場合に表示
        image_path = None
        
        # frame_pathの確認 - 詳細なデバッグ情報を追加
        if frame_path:
            logger.debug(f"シーン {scene_id} のframe_path検証: パス={frame_path}")
            if os.path.isfile(frame_path):
                logger.debug(f"シーン {scene_id} のフレーム画像パスが存在します: {frame_path}")
                image_path = frame_path
            else:
                # ファイルが存在しない場合、詳細なデバッグ情報を出力
                logger.warning(f"シーン {scene_id} のframe_pathが有効なファイルではありません: {frame_path}")
                logger.warning(f"  - exists: {os.path.exists(frame_path)}")
                logger.warning(f"  - isfile: {os.path.isfile(frame_path)}")
                logger.warning(f"  - ディレクトリ存在: {os.path.exists(os.path.dirname(frame_path))}")
                
                # 絶対パスに変換して再確認
                abs_path = os.path.abspath(frame_path)
                logger.warning(f"シーン {scene_id} の絶対パス変換: {abs_path}")
                logger.warning(f"  - 絶対パス exists: {os.path.exists(abs_path)}")
                logger.warning(f"  - 絶対パス isfile: {os.path.isfile(abs_path)}")
                
                if os.path.isfile(abs_path):
                    logger.info(f"シーン {scene_id} の絶対パスが有効なため使用します: {abs_path}")
                    image_path = abs_path
        
        # thumbnail_pathの確認 - frame_pathが使えない場合のフォールバック
        if not image_path and thumbnail_path:
            logger.debug(f"シーン {scene_id} のthumbnail_path検証: パス={thumbnail_path}")
            if os.path.isfile(thumbnail_path):
                logger.debug(f"シーン {scene_id} のサムネイル画像パスが存在します: {thumbnail_path}")
                image_path = thumbnail_path
            else:
                # ファイルが存在しない場合、詳細なデバッグ情報を出力
                logger.warning(f"シーン {scene_id} のthumbnail_pathが有効なファイルではありません: {thumbnail_path}")
                logger.warning(f"  - exists: {os.path.exists(thumbnail_path)}")
                logger.warning(f"  - isfile: {os.path.isfile(thumbnail_path)}")
                
                # 絶対パスに変換して再確認
                abs_path = os.path.abspath(thumbnail_path)
                logger.warning(f"シーン {scene_id} の絶対パス変換: {abs_path}")
                logger.warning(f"  - 絶対パス exists: {os.path.exists(abs_path)}")
                logger.warning(f"  - 絶対パス isfile: {os.path.isfile(abs_path)}")
                
                if os.path.isfile(abs_path):
                    logger.info(f"シーン {scene_id} の絶対パスが有効なため使用します: {abs_path}")
                    image_path = abs_path
        
        if image_path:
            logger.debug(f"シーン {scene_id} の画像パスが存在します: {image_path}")
            try:
                # ファイルサイズを確認
                file_size = os.path.getsize(image_path)
                logger.debug(f"シーン {scene_id} の画像ファイルサイズ: {file_size} バイト")
                
                if file_size == 0:
                    logger.warning(f"シーン {scene_id} の画像ファイルサイズが0バイトです")
                    self.thumbnail_label.setText("No Image")
                    return
                
                # 画像読み込みを試みる
                try:
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(120, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore[attr-defined]
                        self.thumbnail_label.setPixmap(pixmap)
                        logger.debug(f"シーン {scene_id} のサムネイル画像を読み込みました: {image_path}")
                    else:
                        # QPixmapが失敗した場合、PILを使用して試みる
                        logger.warning(f"QPixmapでの読み込みに失敗しました。PILで試みます: {image_path}")
                        try:
                            from PIL import Image
                            from PIL.ImageQt import ImageQt
                            
                            # PILで画像を開く
                            pil_image = Image.open(image_path)
                            # QImageに変換
                            qimage = ImageQt(pil_image)
                            # QPixmapに変換
                            pixmap = QPixmap.fromImage(qimage)
                            
                            if not pixmap.isNull():
                                pixmap = pixmap.scaled(120, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore[attr-defined]
                                self.thumbnail_label.setPixmap(pixmap)
                                logger.debug(f"シーン {scene_id} のサムネイル画像をPILで読み込みました: {image_path}")
                            else:
                                logger.warning(f"PILでも画像の読み込みに失敗しました: {image_path}")
                                self.thumbnail_label.setText("No Image")
                        except ImportError:
                            logger.warning("PILがインストールされていません")
                            self.thumbnail_label.setText("No Image")
                        except Exception as pil_err:
                            logger.error(f"PILでの画像読み込みエラー: {str(pil_err)}")
                            self.thumbnail_label.setText("No Image")
                except Exception as pixmap_err:
                    logger.error(f"QPixmapでの画像読み込みエラー: {str(pixmap_err)}")
                    self.thumbnail_label.setText("No Image")
            except Exception as e:
                logger.error(f"シーン {scene_id} のサムネイル画像の読み込み中にエラーが発生しました: {str(e)}")
                self.thumbnail_label.setText("No Image")
        else:
            logger.warning(f"シーン {scene_id} の有効な画像パスが見つかりません")
            self.thumbnail_label.setText("No Image")
    
    def _format_time(self, seconds):
        """
        秒数を時:分:秒.ミリ秒形式に変換
        
        Args:
            seconds (float): 秒数
            
        Returns:
            str: フォーマットされた時間文字列
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"
        else:
            return f"{minutes:02d}:{seconds:05.2f}"
    
    def mousePressEvent(self, event):
        """マウスクリックイベント"""
        super().mousePressEvent(event)
        self.clicked.emit(self.scene_data)
    
    def set_selected(self, selected, is_playback_highlight=False):
        """
        選択状態を設定
        
        Args:
            selected (bool): 選択状態
            is_playback_highlight (bool): 再生中のハイライトかどうか
        """
        self.selected = selected
        
        if selected:
            # 選択時のスタイル設定
            self.setAutoFillBackground(True)
            palette = self.palette()
            
            if is_playback_highlight:
                # 再生中のハイライトは明るいグレー
                palette.setColor(self.backgroundRole(), QColor("#4a4a4a"))
            else:
                # 通常の選択は青色
                palette.setColor(self.backgroundRole(), QColor("#3d8ec9"))
                
            self.setPalette(palette)
            
            # サムネイル画像の枠線を設定
            if hasattr(self, 'thumbnail_label'):
                if is_playback_highlight:
                    self.thumbnail_label.setStyleSheet("border: 2px solid #5a5a5a; background-color: #1a1a1a;")
                else:
                    self.thumbnail_label.setStyleSheet("border: 2px solid #3d8ec9; background-color: #1a1a1a;")
            
            # 時間ラベルを白色に設定
            if hasattr(self, 'time_label'):
                self.time_label.setStyleSheet("color: white; font-weight: bold;")
            
            # 説明ラベルを白色に設定
            if hasattr(self, 'desc_label'):
                self.desc_label.setStyleSheet("color: white;")
                
            # 詳細ボタンがあれば白色に設定
            if hasattr(self, 'details_button'):
                if is_playback_highlight:
                    self.details_button.setStyleSheet("color: white; background-color: #5a5a5a; border: none; padding: 2px 5px; font-size: 9px;")
                else:
                    self.details_button.setStyleSheet("color: white; background-color: #5a9fd4; border: none; padding: 2px 5px; font-size: 9px;")
        else:
            # 非選択時は元のスタイルに戻す
            self.setAutoFillBackground(True)
            palette = self.palette()
            palette.setColor(self.backgroundRole(), QColor("#2a2a2a"))
            self.setPalette(palette)
            
            # サムネイル画像の枠線を元に戻す
            if hasattr(self, 'thumbnail_label'):
                self.thumbnail_label.setStyleSheet("border: 1px solid #444444; background-color: #1a1a1a;")
            
            # 時間ラベルを元に戻す
            if hasattr(self, 'time_label'):
                self.time_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
            
            # 説明ラベルを元に戻す
            if hasattr(self, 'desc_label'):
                if self.scene_data.get('description', ''):
                    self.desc_label.setStyleSheet("color: #b0b0b0;")
                else:
                    self.desc_label.setStyleSheet("color: #808080; font-style: italic;")
                    
            # 詳細ボタンがあれば元に戻す
            if hasattr(self, 'details_button'):
                self.details_button.setStyleSheet("font-size: 9px; padding: 2px 5px; background-color: #3d8ec9; color: white; border: none;")
    
    def _show_details(self):
        """詳細表示ダイアログを表示"""
        self.show_details.emit(self.scene_data)


class SceneListWidget(QListWidget):
    """シーンリストウィジェット"""
    
    # シグナル定義
    scene_selected = Signal(dict)  # シーン選択シグナル
    scene_details = Signal(dict)   # シーン詳細表示シグナル
    
    def __init__(self, parent=None):
        """
        初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        # スタイル設定
        self.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #2a2a2a;
                padding: 2px;
            }
        """)
        
        # 選択モード設定
        self.setSelectionMode(QListWidget.SingleSelection)
        
        # 現在選択されているアイテム
        self.current_item = None
    
    def add_scene(self, scene_data):
        """
        シーンをリストに追加
        
        Args:
            scene_data (dict): シーン情報
            
        Returns:
            SceneItem: 追加されたシーンアイテム
        """
        # リストアイテムの作成
        item = QListWidgetItem(self)
        
        # シーンウィジェットの作成
        scene_widget = SceneItem(scene_data)
        scene_widget.clicked.connect(self._on_scene_clicked)
        scene_widget.show_details.connect(self._on_scene_details)
        
        # アイテムのサイズを設定
        item.setSizeHint(QSize(self.width(), scene_widget.minimumHeight()))
        
        # アイテムをリストに追加
        self.addItem(item)
        self.setItemWidget(item, scene_widget)
        
        return scene_widget
    
    def clear_scenes(self):
        """シーンリストをクリア"""
        self.clear()
        self.current_item = None
    
    def _on_scene_clicked(self, scene_data):
        """
        シーンクリック時の処理
        
        Args:
            scene_data (dict): クリックされたシーン情報
        """
        # 以前の選択を解除
        if self.current_item:
            self.current_item.set_selected(False)
        
        # 新しい選択を設定
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            
            if widget and widget.scene_data.get('timestamp') == scene_data.get('timestamp'):
                widget.set_selected(True, is_playback_highlight=False)  # 通常の選択として設定
                self.current_item = widget
                break
        
        # シグナル発行
        self.scene_selected.emit(scene_data)
    
    def _on_scene_details(self, scene_data):
        """
        シーン詳細表示時の処理
        
        Args:
            scene_data (dict): 詳細表示するシーン情報
        """
        # シグナルを発行するだけ
        self.scene_details.emit(scene_data)
    
    def select_scene_at_time(self, time_position):
        """
        指定時間位置に最も近いシーンを選択
        
        Args:
            time_position (float): 時間位置（秒）
            
        Returns:
            bool: シーンが選択されたかどうか
        """
        if self.count() == 0:
            return False
        
        # 最も近いシーンを探す
        closest_scene = None
        min_diff = float('inf')
        
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget:
                scene_time = widget.scene_data.get('timestamp', 0)
                
                # 現在位置以前の最も近いシーンを選択
                if time_position >= scene_time and (time_position - scene_time) < min_diff:
                    min_diff = time_position - scene_time
                    closest_scene = widget
        
        # 最も近いシーンが見つからなかった場合は最初のシーンを選択
        if not closest_scene and self.count() > 0:
            closest_scene = self.itemWidget(self.item(0))
        
        # シーンを選択
        if closest_scene:
            self._on_scene_clicked(closest_scene.scene_data)
            return True
        
        return False


class ScenePanel(QWidget):
    """シーンパネルウィジェット"""
    
    # シグナル定義
    scene_selected = Signal(dict)  # シーン選択シグナル
    session_selected = Signal(int)  # セッション選択シグナル
    export_requested = Signal(int, str)  # エクスポートリクエストシグナル
    
    def __init__(self, database, parent=None):
        """
        初期化
        
        Args:
            database: データベースインスタンス
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.database = database
        
        # 現在の動画ID
        self.current_video_id = None
        
        # 現在のセッションID
        self.current_session_id = None
        
        # UIの初期化
        self.init_ui()
    
    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ヘッダーレイアウト
        header_layout = QHBoxLayout()
        
        # セッション選択コンボボックス
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(150)
        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        header_layout.addWidget(QLabel("セッション:"))
        header_layout.addWidget(self.session_combo)
        
        # エクスポートボタンは非表示にするため削除
        
        layout.addLayout(header_layout)
        
        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # シーンリスト
        self.scene_list = SceneListWidget()
        self.scene_list.scene_selected.connect(self._on_scene_selected)
        self.scene_list.scene_details.connect(self._on_scene_details)
        layout.addWidget(self.scene_list)
        
        # スタイル設定
        self.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #e0e0e0;
            }
            QPushButton {
                padding: 4px 8px;
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #323232;
                border: 1px solid #444444;
            }
            QPushButton:disabled {
                background-color: #1e1e1e;
                color: #656565;
                border: 1px solid #2a2a2a;
            }
            QComboBox {
                padding: 4px;
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QComboBox:hover {
                border: 1px solid #444444;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                selection-background-color: #3d8ec9;
            }
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                background-color: #1e3a4f;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #3d8ec9;
                width: 10px;
                margin: 0.5px;
            }
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #121212;
                width: 14px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                min-height: 20px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background-color: #121212;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #121212;
            }
            QScrollBar::corner {
                background-color: #121212;
            }
            QScrollBar:horizontal {
                background-color: #121212;
                height: 14px;
                margin: 0;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background-color: #121212;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: #121212;
            }
        """)
    
    def set_video(self, video_id):
        """
        表示する動画を設定
        
        Args:
            video_id (int): 動画ID
        """
        if video_id == self.current_video_id:
            return
        
        self.current_video_id = video_id
        self.current_session_id = None
        
        # セッションコンボボックスをクリア
        self.session_combo.clear()
        
        # シーンリストをクリア
        self.scene_list.clear_scenes()
        
        if video_id is None:
            return
        
        # 動画に関連するセッションを取得
        sessions = self.database.get_sessions_for_video(video_id)
        
        if not sessions:
            return
        
        # セッションコンボボックスに追加
        for session in sessions:
            self.session_combo.addItem(session['name'], session['id'])
        
        # 最新のセッションを選択
        self.session_combo.setCurrentIndex(0)
    
    def load_session(self, session_id):
        """
        セッションを読み込む
        
        Args:
            session_id (int): セッションID
        """
        if session_id is None:
            return
        
        self.current_session_id = session_id
        
        # シーンリストをクリア
        self.scene_list.clear_scenes()
        
        # セッションに関連するシーンを取得
        scenes = self.database.get_scenes_for_session(session_id)
        
        if not scenes:
            return
        
        # シーンリストに追加
        for scene in scenes:
            self.scene_list.add_scene(scene)
    
    def select_scene_at_time(self, time_position):
        """
        指定時間位置に最も近いシーンを選択
        
        Args:
            time_position (float): 時間位置（秒）
            
        Returns:
            bool: シーンが選択されたかどうか
        """
        return self.scene_list.select_scene_at_time(time_position)
    
    def show_progress(self, value, progress_type=None):
        """
        進捗バーを表示
        
        Args:
            value (int): 進捗値 (0-100)
            progress_type (str, optional): 進捗タイプ
        """
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
        
        self.progress_bar.setValue(value)
        
        if progress_type == 'detection':
            self.progress_bar.setFormat("シーン検出: %p%")
        elif progress_type == 'analysis':
            self.progress_bar.setFormat("シーン解析: %p%")
        else:
            self.progress_bar.setFormat("%p%")
        
        if value >= 100:
            # 完了したら少し待ってから非表示に
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
    
    def _on_session_changed(self, index):
        """
        セッション変更時の処理
        
        Args:
            index (int): 選択されたインデックス
        """
        if index < 0:
            return
        
        session_id = self.session_combo.itemData(index)
        self.load_session(session_id)
        self.session_selected.emit(session_id)
    
    def _on_scene_selected(self, scene_data):
        """
        シーン選択時の処理
        
        Args:
            scene_data (dict): 選択されたシーン情報
        """
        self.scene_selected.emit(scene_data)
    
    def _on_scene_details(self, scene_data):
        """
        シーン詳細表示時の処理
        
        Args:
            scene_data (dict): 詳細表示するシーン情報
        """
        # 詳細ダイアログを表示
        dialog = QDialog(self)
        dialog.setWindowTitle("シーン詳細")
        dialog.setMinimumSize(550, 350)
        
        # ダークモードのスタイル設定
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #323232;
                border: 1px solid #444444;
            }
            QPushButton:pressed {
                background-color: #3d8ec9;
            }
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #121212;
                width: 14px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                min-height: 20px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background-color: #121212;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #121212;
            }
            QScrollBar::corner {
                background-color: #121212;
            }
            QScrollBar:horizontal {
                background-color: #121212;
                height: 14px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                min-width: 20px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #777777;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background-color: #121212;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: #121212;
            }
        """)
        
        # ダイアログレイアウト
        layout = QVBoxLayout(dialog)
        
        # ヘッダーレイアウト（サムネイルとタイムコード情報）
        header_layout = QHBoxLayout()
        
        # サムネイル画像
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(180, 101)  # 16:9のアスペクト比
        thumbnail_label.setStyleSheet("border: 1px solid #444444; background-color: #1a1a1a;")
        thumbnail_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        
        # サムネイル画像の読み込み
        frame_path = scene_data.get('frame_path')
        thumbnail_path = scene_data.get('thumbnail_path')
        
        if frame_path and os.path.isfile(frame_path):
            pixmap = QPixmap(frame_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(180, 101, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore[attr-defined]
                thumbnail_label.setPixmap(pixmap)
        elif thumbnail_path and os.path.isfile(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(180, 101, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore[attr-defined]
                thumbnail_label.setPixmap(pixmap)
        else:
            thumbnail_label.setText("サムネイルなし")
        
        header_layout.addWidget(thumbnail_label)
        
        # 情報レイアウト
        info_layout = QVBoxLayout()
        
        # タイムコード情報
        timestamp = scene_data.get('timestamp', 0)
        duration = scene_data.get('duration', 0)
        time_str = f"開始時間: {self._format_time(timestamp)}"
        duration_str = f"シーン長: {self._format_time(duration)}"
        
        time_label = QLabel(time_str)
        time_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        info_layout.addWidget(time_label)
        
        duration_label = QLabel(duration_str)
        duration_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        info_layout.addWidget(duration_label)
        
        # シーンID
        scene_id = scene_data.get('id', 'N/A')
        id_label = QLabel(f"シーンID: {scene_id}")
        id_label.setStyleSheet("color: #a0a0a0;")
        info_layout.addWidget(id_label)
        
        # 信頼度
        confidence = scene_data.get('confidence', 0)
        if confidence > 0:
            confidence_label = QLabel(f"信頼度: {confidence:.2f}")
            confidence_label.setStyleSheet("color: #a0a0a0;")
            info_layout.addWidget(confidence_label)
        
        header_layout.addLayout(info_layout)
        header_layout.setStretchFactor(info_layout, 1)
        
        layout.addLayout(header_layout)
        
        # 区切り線
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #3a3a3a;")
        layout.addWidget(separator)
        
        # 説明ヘッダー
        desc_header = QLabel("シーン説明:")
        desc_header.setStyleSheet("font-weight: bold; color: #e0e0e0; margin-top: 10px;")
        layout.addWidget(desc_header)
        
        # 説明テキスト
        description = scene_data.get('description', '')
        
        # スクロール可能なテキストエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        if description:
            text_widget = QLabel(description)
            text_widget.setWordWrap(True)
            text_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)  # type: ignore[attr-defined]
            text_widget.setStyleSheet("background-color: #2a2a2a; color: #e0e0e0; padding: 10px; border-radius: 4px;")
        else:
            text_widget = QLabel("このシーンには説明がありません。")
            text_widget.setStyleSheet("background-color: #2a2a2a; color: #808080; font-style: italic; padding: 10px; border-radius: 4px;")
        
        scroll_area.setWidget(text_widget)
        layout.addWidget(scroll_area, 1)  # 1は伸縮係数
        
        # 閉じるボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(dialog.accept)
        close_button.setMinimumWidth(100)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # ダイアログを表示
        dialog.exec_()
    
    def _format_time(self, seconds):
        """
        秒数を時:分:秒.ミリ秒形式に変換
        
        Args:
            seconds (float): 秒数
            
        Returns:
            str: フォーマットされた時間文字列
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"
        else:
            return f"{minutes:02d}:{seconds:05.2f}"
    
    def clear_scenes(self):
        """シーンリストをクリア"""
        self.scene_list.clear_scenes()
    
    def _on_export_clicked(self):
        """エクスポートボタンクリック時の処理"""
        if not self.current_session_id:
            # セッションが選択されていない場合、利用可能なセッションを確認
            if self.current_video_id:
                sessions = self.database.get_sessions_for_video(self.current_video_id)
                if sessions:
                    # セッションが存在する場合、最初のセッションを自動選択
                    session_id = sessions[0]['id']
                    self.current_session_id = session_id
                    self.load_session(session_id)
                    logger.debug(f"セッションを自動選択しました: ID={session_id}")
                else:
                    logger.error("エクスポート: セッションが見つかりません")
                    return
            else:
                logger.error("エクスポート: 動画IDが設定されていません")
                return
        
        # エクスポート形式の選択ダイアログ
        menu = QMenu(self)
        json_action = QAction("JSONとしてエクスポート", self)
        csv_action = QAction("CSVとしてエクスポート", self)
        
        menu.addAction(json_action)
        menu.addAction(csv_action)
        
        # アクションの接続
        json_action.triggered.connect(lambda: self._export_session('json'))
        csv_action.triggered.connect(lambda: self._export_session('csv'))
        
        # メニューを表示
        menu.exec_(QCursor.pos())
    
    def _export_session(self, format_type):
        """
        セッションをエクスポート
        
        Args:
            format_type (str): エクスポート形式 ('json' または 'csv')
        """
        if not self.current_session_id:
            logger.error("エクスポート: セッションIDが設定されていません")
            return
        
        # エクスポート設定の取得
        export_settings = self.database.get_setting('export', {
            'default_path': os.path.join(os.path.expanduser("~"), "Documents"),
            'format': 'json'
        })
        
        default_path = export_settings.get('default_path', os.path.join(os.path.expanduser("~"), "Documents"))
        
        # ファイル保存ダイアログ
        if format_type == 'json':
            file_path, _ = QFileDialog.getSaveFileName(
                self, "JSONファイルの保存",
                os.path.join(default_path, f"session_{self.current_session_id}.json"),
                "JSONファイル (*.json);;すべてのファイル (*.*)"
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "CSVファイルの保存",
                os.path.join(default_path, f"session_{self.current_session_id}.csv"),
                "CSVファイル (*.csv);;すべてのファイル (*.*)"
            )
        
        if not file_path:
            return
        
        # エクスポートシグナル発行
        self.export_requested.emit(self.current_session_id, format_type)
    
    def set_database(self, database):
        """
        データベースを設定
        
        Args:
            database: データベースインスタンス
        """
        self.database = database
        
        # セッションコンボボックスを更新
        self.update_session_combo()
    
    def clear(self):
        """
        シーンリストをクリア
        """
        # シーンリストをクリア
        self.scene_list.clear()
        
        # セッションコンボボックスをクリア
        self.session_combo.clear()
        
        # プログレスバーを非表示
        self.progress_bar.setVisible(False)
    
    def update_session_combo(self):
        """
        セッションコンボボックスを更新
        """
        # セッションコンボボックスをクリア
        self.session_combo.clear()
        
        # 現在の動画IDがない場合は何もしない
        if self.current_video_id is None:
            logger.debug("セッションコンボボックス更新: 動画IDがありません")
            return
        
        try:
            # 動画に関連するセッションを取得
            sessions = self.database.get_sessions_for_video(self.current_video_id)
            
            logger.debug(f"セッションコンボボックス更新: 動画ID={self.current_video_id}, 取得セッション数={len(sessions)}")
            
            if not sessions:
                logger.debug("セッションコンボボックス更新: セッションが見つかりません")
                return
            
            # セッションコンボボックスに追加
            for session in sessions:
                logger.debug(f"セッションコンボボックスに追加: ID={session['id']}, 名前={session['name']}")
                self.session_combo.addItem(session['name'], session['id'])
            
            # 最新のセッションを選択
            self.session_combo.setCurrentIndex(0)
        except Exception as e:
            logger.error(f"セッションコンボボックスの更新中にエラーが発生しました: {e}")
            # エラーが発生した場合は何もしない 
    
    def highlight_scene_at_time(self, time_position):
        """
        指定時間位置に最も近いシーンをハイライトし、表示する
        
        Args:
            time_position (float): 時間位置（秒）
            
        Returns:
            bool: シーンがハイライトされたかどうか
        """
        if not self.scene_list or self.scene_list.count() == 0:
            return False
        
        # 最も近いシーンを探す
        closest_scene = None
        closest_item = None
        min_diff = float('inf')
        
        for i in range(self.scene_list.count()):
            item = self.scene_list.item(i)
            widget = self.scene_list.itemWidget(item)
            if widget:
                scene_time = widget.scene_data.get('timestamp', 0)
                scene_duration = widget.scene_data.get('duration', 0)
                scene_end_time = scene_time + scene_duration
                
                # 現在のシーン内にいる場合
                if time_position >= scene_time and time_position < scene_end_time:
                    closest_scene = widget
                    closest_item = item
                    break
                
                # 現在位置以前の最も近いシーンを選択
                if time_position >= scene_time and (time_position - scene_time) < min_diff:
                    min_diff = time_position - scene_time
                    closest_scene = widget
                    closest_item = item
        
        # 最も近いシーンが見つからなかった場合は最初のシーンを選択
        if not closest_scene and self.scene_list.count() > 0:
            closest_item = self.scene_list.item(0)
            closest_scene = self.scene_list.itemWidget(closest_item)
        
        # シーンをハイライト
        if closest_scene:
            # 以前の選択を解除
            if hasattr(self, 'current_highlighted_item') and self.current_highlighted_item:
                try:
                    widget = self.scene_list.itemWidget(self.current_highlighted_item)
                    if widget:
                        widget.set_selected(False)
                except RuntimeError:
                    # アイテムが削除されている場合は無視
                    self.current_highlighted_item = None
            
            # 新しい選択を設定（再生中のハイライトとして設定）
            closest_scene.set_selected(True, is_playback_highlight=True)
            self.current_highlighted_item = closest_item
            
            # シーンが表示されるようにスクロール
            if closest_item:
                self.scene_list.scrollToItem(closest_item)
            
            return True
        
        return False 