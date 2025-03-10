#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
設定ダイアログの実装
"""

import os
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QTabWidget, QTextEdit, QFileDialog, QMessageBox,
    QCheckBox, QDialogButtonBox, QWidget, QListWidget, QInputDialog
)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot as Slot, pyqtSignal as Signal
from scene_analyzer.database import Database
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """設定ダイアログクラス"""
    
    # 設定更新シグナル
    settings_updated_signal = Signal()  # 設定が更新されたことを通知するシグナル
    
    def __init__(self, database, parent=None):
        """
        初期化
        
        Args:
            database: データベースインスタンス
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.database = database
        
        # データベースパス変更フラグ
        self.db_path_changed = False
        
        # ウィンドウの設定
        self.setWindowTitle("設定")
        self.resize(600, 500)
        
        # UIの初期化
        self.init_ui()
        
        # 設定の読み込み
        self.load_settings()
    
    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout(self)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 各タブの作成
        self.create_general_tab()
        self.create_scene_detection_tab()
        self.create_analysis_tab()
        self.create_prompt_tab()
        self.create_export_tab()
        
        # ボタンボックス
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply | QDialogButtonBox.Reset)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_settings)
        main_layout.addWidget(button_box)
        
        # OKボタンが押されたときの処理
        self.accepted.connect(self.apply_settings)
    
    def create_general_tab(self):
        """一般設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # アプリケーション設定グループ
        group_box = QGroupBox("アプリケーション設定")
        form_layout = QFormLayout(group_box)
        
        # データベースパス
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setReadOnly(True)
        browse_button = QPushButton("参照...")
        browse_button.clicked.connect(self.browse_db_path)
        
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(self.db_path_edit)
        db_path_layout.addWidget(browse_button)
        form_layout.addRow("データベースパス:", db_path_layout)
        
        # データベースクリアボタン
        clear_db_button = QPushButton("データベースをクリア")
        clear_db_button.clicked.connect(self.clear_database)
        form_layout.addRow("", clear_db_button)
        
        layout.addWidget(group_box)
        
        # HiDPI設定グループ
        group_box = QGroupBox("表示設定")
        form_layout = QFormLayout(group_box)
        
        # HiDPI対応
        self.hidpi_checkbox = QCheckBox("HiDPI対応を有効にする")
        form_layout.addRow("", self.hidpi_checkbox)
        
        layout.addWidget(group_box)
        
        # スペーサーを追加
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "一般")
    
    def create_scene_detection_tab(self):
        """シーン検出設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # シーン検出設定グループ
        group_box = QGroupBox("シーン検出設定")
        form_layout = QFormLayout(group_box)
        
        # 検出感度
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.01, 1.0)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.3)
        form_layout.addRow("検出感度:", self.threshold_spin)
        
        # 最小シーン長
        self.min_scene_duration_spin = QDoubleSpinBox()
        self.min_scene_duration_spin.setRange(0.5, 30.0)
        self.min_scene_duration_spin.setSingleStep(0.5)
        self.min_scene_duration_spin.setDecimals(1)
        self.min_scene_duration_spin.setValue(10.0)
        form_layout.addRow("最小シーン長（秒）:", self.min_scene_duration_spin)
        
        layout.addWidget(group_box)
        
        # CUDA設定グループ
        group_box = QGroupBox("CUDA設定")
        form_layout = QFormLayout(group_box)
        
        # CUDA有効化
        self.cuda_checkbox = QCheckBox("CUDAを使用する")
        form_layout.addRow("", self.cuda_checkbox)
        
        # CUDAデバイスID
        self.cuda_device_spin = QSpinBox()
        self.cuda_device_spin.setRange(0, 3)
        self.cuda_device_spin.setValue(0)
        form_layout.addRow("CUDAデバイスID:", self.cuda_device_spin)
        
        layout.addWidget(group_box)
        
        # スペーサーを追加
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "シーン検出")
    
    def create_analysis_tab(self):
        """解析設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Gemini API設定グループ
        group_box = QGroupBox("Gemini API設定")
        form_layout = QFormLayout(group_box)
        
        # APIキー
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("APIキー:", self.api_key_edit)
        
        # モデル選択
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ])
        form_layout.addRow("モデル:", self.model_combo)
        
        layout.addWidget(group_box)
        
        # 解析設定グループ
        group_box = QGroupBox("解析設定")
        form_layout = QFormLayout(group_box)
        
        # バッチサイズ
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 20)
        self.batch_size_spin.setValue(5)
        form_layout.addRow("バッチサイズ:", self.batch_size_spin)
        
        # 信頼度閾値
        self.confidence_threshold_spin = QDoubleSpinBox()
        self.confidence_threshold_spin.setRange(0.0, 1.0)
        self.confidence_threshold_spin.setSingleStep(0.05)
        self.confidence_threshold_spin.setDecimals(2)
        self.confidence_threshold_spin.setValue(0.7)
        form_layout.addRow("信頼度閾値:", self.confidence_threshold_spin)
        
        layout.addWidget(group_box)
        
        # スペーサーを追加
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "解析")
    
    def create_prompt_tab(self):
        """プロンプト設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # プロンプトリスト
        self.prompt_list = QListWidget()
        self.prompt_list.setSelectionMode(QListWidget.SingleSelection)
        self.prompt_list.currentRowChanged.connect(self.on_prompt_selected)  # type: ignore[arg-type]
        
        # プロンプト編集
        self.prompt_name_edit = QLineEdit()
        self.prompt_content_edit = QTextEdit()
        
        # ボタン
        button_layout = QHBoxLayout()
        self.add_prompt_button = QPushButton("追加")
        self.add_prompt_button.clicked.connect(self.add_prompt)
        self.update_prompt_button = QPushButton("更新")
        self.update_prompt_button.clicked.connect(self.update_prompt)
        self.delete_prompt_button = QPushButton("削除")
        self.delete_prompt_button.clicked.connect(self.delete_prompt)
        
        button_layout.addWidget(self.add_prompt_button)
        button_layout.addWidget(self.update_prompt_button)
        button_layout.addWidget(self.delete_prompt_button)
        
        # フォームレイアウト
        form_layout = QFormLayout()
        form_layout.addRow("名前:", self.prompt_name_edit)
        form_layout.addRow("内容:", self.prompt_content_edit)
        
        # レイアウトに追加
        layout.addWidget(QLabel("プロンプト一覧:"))
        layout.addWidget(self.prompt_list)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        
        self.tab_widget.addTab(tab, "プロンプト")
        
        # プロンプトの読み込み
        try:
            self.load_prompts()
        except Exception as e:
            logger.error(f"プロンプトの読み込みエラー: {e}")
    
    def create_export_tab(self):
        """エクスポート設定タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # エクスポート設定グループ
        group_box = QGroupBox("エクスポート設定")
        form_layout = QFormLayout(group_box)
        
        # デフォルトエクスポートパス
        self.export_path_edit = QLineEdit()
        browse_button = QPushButton("参照...")
        browse_button.clicked.connect(self.browse_export_path)
        
        export_path_layout = QHBoxLayout()
        export_path_layout.addWidget(self.export_path_edit)
        export_path_layout.addWidget(browse_button)
        form_layout.addRow("デフォルトエクスポートパス:", export_path_layout)
        
        # エクスポート形式
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["JSON", "CSV"])
        form_layout.addRow("デフォルトエクスポート形式:", self.export_format_combo)
        
        layout.addWidget(group_box)
        
        # スペーサーを追加
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "エクスポート")
    
    def load_settings(self):
        """設定の読み込み"""
        try:
            # データベースパスを設定
            self.db_path_edit.setText(self.database.db_path)
            
            # シーン検出設定
            self.threshold_spin.setValue(float(self.database.get_setting('scene_detection.threshold', '0.3')))
            self.min_scene_duration_spin.setValue(float(self.database.get_setting('scene_detection.min_scene_duration', '10.0')))
            self.cuda_checkbox.setChecked(self.database.get_setting('scene_detection.cuda_enabled', 'false') == 'true')
            self.cuda_device_spin.setValue(int(self.database.get_setting('scene_detection.cuda_device_id', '0')))
            
            # 解析設定
            api_key = self.database.get_setting('analysis.api_key', '')
            
            # APIキーが空の場合はQSettingsから取得
            if not api_key:
                settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
                api_key = settings.value("api_key", "")
                logger.info(f"QSettingsからAPIキーを読み込みました: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
                if api_key:
                    logger.info("QSettingsの値を使用します")
            else:
                logger.info(f"APIキーを読み込みました: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
            
            self.api_key_edit.setText(api_key)
            
            # モデル選択
            model = self.database.get_setting('analysis.model', 'gemini-pro-vision')
            index = self.model_combo.findText(model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            
            # バッチサイズ
            self.batch_size_spin.setValue(int(self.database.get_setting('analysis.batch_size', '5')))
            
            # 信頼度閾値
            self.confidence_threshold_spin.setValue(float(self.database.get_setting('analysis.confidence_threshold', '0.7')))
            
            # エクスポート設定
            self.export_path_edit.setText(self.database.get_setting('export.default_path', os.path.join(os.path.expanduser("~"), "Documents")))
            self.export_format_combo.setCurrentText(self.database.get_setting('export.format', 'JSON').upper())
            
            # 表示設定
            hidpi_enabled = self.database.get_setting('display.hidpi_enabled', 'true') == 'true'
            self.hidpi_checkbox.setChecked(hidpi_enabled)
            
        except Exception as e:
            logger.error(f"設定の読み込みエラー: {e}")
            QMessageBox.warning(self, "設定エラー", f"設定の読み込み中にエラーが発生しました: {e}")
    
    def load_prompts(self):
        """プロンプトの読み込み"""
        try:
            # プロンプトリストをクリア
            self.prompt_list.clear()
            
            # データベースからプロンプトを取得
            prompts = self.database.get_all_prompts()
            
            # プロンプトをリストに追加
            for prompt in prompts:
                self.prompt_list.addItem(prompt['name'])
                
        except Exception as e:
            logger.error(f"プロンプトの読み込みエラー: {e}")
    
    def apply_settings(self):
        """設定の適用"""
        try:
            # データベースパスの保存
            self.database.set_setting('database.path', self.db_path_edit.text())
            
            # シーン検出設定
            self.database.set_setting('scene_detection.threshold', str(self.threshold_spin.value()))
            self.database.set_setting('scene_detection.min_scene_duration', str(self.min_scene_duration_spin.value()))
            self.database.set_setting('scene_detection.cuda_enabled', str(self.cuda_checkbox.isChecked()).lower())
            self.database.set_setting('scene_detection.cuda_device_id', str(self.cuda_device_spin.value()))
            
            # 解析設定
            api_key = self.api_key_edit.text()
            logger.info(f"APIキーを保存します: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
            self.database.set_setting('analysis.api_key', api_key)
            
            # APIキーはレジストリに保存しない（セキュリティ対策）
            # QSettingsの既存のAPIキーを削除
            from PyQt5.QtCore import QSettings
            settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
            if settings.contains("api_key"):
                settings.remove("api_key")
                logger.info("レジストリからAPIキーを削除しました（セキュリティ対策）")
            
            self.database.set_setting('analysis.model', self.model_combo.currentText())
            self.database.set_setting('analysis.batch_size', str(self.batch_size_spin.value()))
            self.database.set_setting('analysis.confidence_threshold', str(self.confidence_threshold_spin.value()))
            
            # エクスポート設定
            self.database.set_setting('export.default_path', self.export_path_edit.text())
            self.database.set_setting('export.format', self.export_format_combo.currentText().lower())
            
            # 表示設定
            self.database.set_setting('display.hidpi_enabled', str(self.hidpi_checkbox.isChecked()).lower())
            
            logger.info("設定を保存しました")
            
            # 親ウィンドウに設定変更を通知
            if self.parent() and hasattr(self.parent(), 'settings_updated'):
                self.parent().settings_updated()  # type: ignore[attr-defined]
            
            # シグナルを発行
            self.settings_updated_signal.emit()
            
        except Exception as e:
            logger.error(f"設定の保存エラー: {e}")
            QMessageBox.warning(self, "設定エラー", f"設定の保存中にエラーが発生しました: {e}")
    
    def reset_settings(self):
        """設定のリセット"""
        reply = QMessageBox.question(
            self, "設定のリセット",
            "すべての設定をデフォルト値にリセットしますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # シーン検出設定
            self.threshold_spin.setValue(0.3)
            self.min_scene_duration_spin.setValue(10.0)
            self.cuda_checkbox.setChecked(False)
            self.cuda_device_spin.setValue(0)
            
            # 解析設定
            self.api_key_edit.clear()
            self.model_combo.setCurrentIndex(0)
            self.batch_size_spin.setValue(5)
            self.confidence_threshold_spin.setValue(0.7)
            
            # エクスポート設定
            self.export_path_edit.setText(os.path.join(os.path.expanduser("~"), "Documents"))
            self.export_format_combo.setCurrentIndex(0)
            
            # 表示設定
            self.hidpi_checkbox.setChecked(True)
            
            logger.info("設定をリセットしました")
    
    def browse_db_path(self):
        """データベースパスの参照"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "データベースファイルの選択", 
            self.db_path_edit.text(),
            "SQLiteデータベース (*.db);;すべてのファイル (*.*)"
        )
        
        if file_path:
            # 現在のパスと異なる場合は警告を表示
            if file_path != self.database.db_path:
                reply = QMessageBox.warning(
                    self,
                    "データベースパスの変更",
                    "データベースパスを変更すると、アプリケーションの再起動が必要です。\n"
                    "また、新しいパスにデータベースが存在しない場合は、新しいデータベースが作成されます。\n\n"
                    "データベースパスを変更しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.db_path_edit.setText(file_path)
                    # 変更フラグを設定
                    self.db_path_changed = True
            else:
                self.db_path_edit.setText(file_path)
    
    def browse_export_path(self):
        """エクスポートパスの参照"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "エクスポートディレクトリの選択",
            self.export_path_edit.text()
        )
        
        if dir_path:
            self.export_path_edit.setText(dir_path)
    
    def clear_database(self):
        """データベースのクリア"""
        reply = QMessageBox.warning(
            self, "データベースのクリア",
            "データベースをクリアすると、すべての動画、セッション、シーン情報が削除されます。\n"
            "この操作は元に戻せません。続行しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # データベース接続状態を確認
                if not self.database.is_connected():
                    # 接続が切れている場合は再接続を試みる
                    db_path = os.path.join(os.path.expanduser('~'), '.scene_analyzer', 'scene_analyzer.db')
                    self.database = Database(db_path)
                    logger.info("データベースに再接続しました")
                
                # 処理中ダイアログを表示
                self.progress_dialog = QMessageBox(self)
                self.progress_dialog.setWindowTitle("処理中")
                self.progress_dialog.setText("データベースをクリアしています...\nこの処理には数秒かかる場合があります。")
                self.progress_dialog.setStandardButtons(QMessageBox.NoButton)
                self.progress_dialog.show()
                
                # UIの更新を強制
                QApplication.processEvents()
                
                # データベースをクリア
                success = self.database.clear_database()
                
                # 処理中ダイアログを閉じる
                self.progress_dialog.accept()
                self.progress_dialog = None
                
                if success:
                    QMessageBox.information(self, "完了", "データベースをクリアしました。")
                    
                    # プロンプトを再読み込み
                    self.load_prompts()
                    
                    # 設定を再読み込み
                    self.load_settings()
                    
                    # 親ウィンドウに通知
                    if self.parent() and hasattr(self.parent(), 'settings_updated'):
                        self.parent().settings_updated()  # type: ignore[attr-defined]
                else:
                    QMessageBox.critical(self, "エラー", "データベースのクリアに失敗しました。")
                
            except Exception as e:
                logger.error(f"データベースクリアエラー: {e}", exc_info=True)
                QMessageBox.critical(self, "エラー", f"データベースのクリア中にエラーが発生しました: {e}")
    
    @Slot(int)
    def on_prompt_selected(self, index):  # type: ignore[misc]
        """
        プロンプト選択時の処理
        
        Args:
            index (int): 選択されたインデックス
        """
        if index < 0:
            return
            
        try:
            # データベース接続状態を確認
            if not self.database.is_connected():
                self.prompt_content_edit.setText("データベース接続が確立されていません。")
                return
                
            # データベース接続オブジェクトがNoneでないことを確認
            if self.database.conn is None:
                self.prompt_content_edit.setText("データベース接続オブジェクトがNoneです。")
                return
                
            prompt_name = self.prompt_list.item(index).text()
            cursor = self.database.conn.cursor()
            cursor.execute('SELECT content FROM prompts WHERE name = ?', (prompt_name,))
            row = cursor.fetchone()
            
            if row:
                self.prompt_content_edit.setText(row['content'])
            else:
                self.prompt_content_edit.setText("")
                
        except Exception as e:
            logger.error(f"プロンプト取得エラー: {e}")
            self.prompt_content_edit.setText(f"エラー: {e}")
    
    def add_prompt(self):
        """新規プロンプトを追加"""
        # プロンプト名の入力ダイアログを表示
        prompt_name, ok = QInputDialog.getText(
            self, "新規プロンプト", "プロンプト名を入力してください:"
        )
        
        if not ok or not prompt_name:
            return
            
        # 既存のプロンプト名と重複していないか確認
        for i in range(self.prompt_list.count()):
            if self.prompt_list.item(i).text() == prompt_name:
                QMessageBox.warning(self, "警告", f"プロンプト名「{prompt_name}」は既に存在します。")
                return
        
        # デフォルトの内容を設定
        default_content = "この画像に写っているものを詳細に説明してください。必ず日本語で回答してください。"
        
        try:
            # データベース接続状態を確認
            if not self.database.is_connected():
                QMessageBox.critical(self, "エラー", "データベース接続が確立されていません。")
                return
                
            # データベース接続オブジェクトがNoneでないことを確認
            if self.database.conn is None:
                QMessageBox.critical(self, "エラー", "データベース接続オブジェクトがNoneです。")
                return
                
            # 新規プロンプトを保存
            cursor = self.database.conn.cursor()
            cursor.execute('''
            INSERT INTO prompts (name, content) VALUES (?, ?)
            ''', (prompt_name, default_content))
            self.database.conn.commit()
            
            # リストに追加
            self.prompt_list.addItem(prompt_name)
            
            # 新しいプロンプトを選択
            for i in range(self.prompt_list.count()):
                if self.prompt_list.item(i).text() == prompt_name:
                    self.prompt_list.setCurrentRow(i)
                    break
            
            QMessageBox.information(self, "追加完了", f"プロンプト「{prompt_name}」を追加しました。")
            
        except Exception as e:
            logger.error(f"プロンプト追加エラー: {e}")
            QMessageBox.critical(self, "エラー", f"プロンプトの追加中にエラーが発生しました: {e}")
    
    def update_prompt(self):
        """プロンプトを更新"""
        # 選択されたプロンプトを取得
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "更新するプロンプトを選択してください。")
            return
            
        # 現在の名前と内容を取得
        current_name = selected_items[0].text()
        current_content = self.prompt_content_edit.toPlainText()
        
        if not current_content:
            QMessageBox.warning(self, "警告", "プロンプトの内容を入力してください。")
            return
            
        try:
            # データベース接続状態を確認
            if not self.database.is_connected():
                QMessageBox.critical(self, "エラー", "データベース接続が確立されていません。")
                return
                
            # データベース接続オブジェクトがNoneでないことを確認
            if self.database.conn is None:
                QMessageBox.critical(self, "エラー", "データベース接続オブジェクトがNoneです。")
                return
                
            # 既存プロンプトの更新
            cursor = self.database.conn.cursor()
            cursor.execute('''
            UPDATE prompts SET name = ?, content = ? WHERE name = ?
            ''', (current_name, current_content, current_name))
            self.database.conn.commit()
            
            # プロンプトリストの更新
            selected_items = self.prompt_list.selectedItems()
            if selected_items:
                selected_items[0].setText(current_name)
                
            QMessageBox.information(self, "保存完了", "プロンプトを更新しました。")
            
        except Exception as e:
            logger.error(f"プロンプト更新エラー: {e}")
            QMessageBox.critical(self, "エラー", f"プロンプトの更新中にエラーが発生しました: {e}")
    
    def delete_prompt(self):
        """プロンプトを削除"""
        # 選択されたプロンプトを取得
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "削除するプロンプトを選択してください。")
            return
            
        # 確認ダイアログを表示
        prompt_name = selected_items[0].text()
        reply = QMessageBox.question(
            self, "プロンプトの削除",
            f"プロンプト「{prompt_name}」を削除しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # データベース接続状態を確認
                if not self.database.is_connected():
                    QMessageBox.critical(self, "エラー", "データベース接続が確立されていません。")
                    return
                    
                # データベース接続オブジェクトがNoneでないことを確認
                if self.database.conn is None:
                    QMessageBox.critical(self, "エラー", "データベース接続オブジェクトがNoneです。")
                    return
                    
                # プロンプトの削除
                cursor = self.database.conn.cursor()
                cursor.execute('DELETE FROM prompts WHERE name = ?', (prompt_name,))
                self.database.conn.commit()
                
                # リストから削除
                row = self.prompt_list.row(selected_items[0])
                self.prompt_list.takeItem(row)
                
                # 内容をクリア
                self.prompt_content_edit.clear()
                
                QMessageBox.information(self, "削除完了", f"プロンプト「{prompt_name}」を削除しました。")
                
            except Exception as e:
                logger.error(f"プロンプト削除エラー: {e}")
                QMessageBox.critical(self, "エラー", f"プロンプトの削除中にエラーが発生しました: {e}")

    def accept(self):
        """OKボタンが押されたときの処理"""
        # 設定を適用
        self.apply_settings()
        
        # データベースパスが変更された場合は再起動を促す
        if self.db_path_changed:
            QMessageBox.information(
                self,
                "再起動が必要",
                "データベースパスが変更されました。\n"
                "変更を適用するには、アプリケーションを再起動してください。"
            )
        
        # ダイアログを閉じる
        super().accept() 