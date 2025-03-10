#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
セッション作成ダイアログモジュール
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QDoubleSpinBox, QCheckBox, QComboBox, QDialogButtonBox,
    QFormLayout, QGroupBox, QSpinBox, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal as Signal

# ロガーの設定
logger = logging.getLogger(__name__)

class SessionDialog(QDialog):
    """セッション作成ダイアログ"""
    
    def __init__(self, database, parent=None, video_path=None):
        """
        初期化
        
        Args:
            database: データベースインスタンス
            parent: 親ウィジェット
            video_path: 動画ファイルパス
        """
        super().__init__(parent)
        
        self.database = database
        self.video_path = video_path
        self.setWindowTitle("シーン検出セッションの作成")
        self.setMinimumWidth(500)
        
        self.init_ui()
        self.load_settings()
        self.load_prompts()
    
    def init_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout(self)
        
        # 動画ファイル名表示
        if self.video_path:
            video_name_label = QLabel(f"対象動画: {os.path.basename(self.video_path)}")
            video_name_label.setStyleSheet("font-weight: bold; color: #0066cc;")
            layout.addWidget(video_name_label)
        
        # 現在の日時を取得してセッション名のデフォルト値として設定
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H%M")
        default_session_name = f"セッション_{current_datetime}"
        
        # セッション名
        self.name_edit = QLineEdit()
        self.name_edit.setText(default_session_name)
        self.name_edit.setPlaceholderText("セッション名を入力（例: セッション_2025-03-06_1530）")
        
        # 検出感度
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(0.3)
        self.threshold_spin.setToolTip("シーン変化を検出する感度（値が小さいほど感度が高い）")
        
        # 最小シーン長
        self.min_duration_spin = QDoubleSpinBox()
        self.min_duration_spin.setRange(0.5, 30.0)
        self.min_duration_spin.setSingleStep(0.5)
        self.min_duration_spin.setValue(10.0)
        self.min_duration_spin.setSuffix(" 秒")
        self.min_duration_spin.setToolTip("検出するシーンの最小長（秒）")
        
        # CUDA使用
        self.use_cuda_check = QCheckBox("GPUを使用（CUDA）")
        self.use_cuda_check.setToolTip("GPUを使用して処理を高速化（CUDAが利用可能な場合）")
        
        # APIキー
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Google Gemini APIキーを入力")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        
        # モデル選択
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ])
        
        # プロンプト選択
        self.prompt_combo = QComboBox()
        
        # バッチサイズ
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 20)
        self.batch_size_spin.setValue(5)
        self.batch_size_spin.setToolTip("一度に処理するシーンの数（大きいほど速いが、APIの制限に注意）")
        
        # フォームレイアウト
        form_layout = QFormLayout()
        form_layout.addRow("セッション名:", self.name_edit)
        form_layout.addRow("検出感度:", self.threshold_spin)
        form_layout.addRow("最小シーン長:", self.min_duration_spin)
        form_layout.addRow("", self.use_cuda_check)
        
        # 解析設定グループ
        analysis_group = QGroupBox("シーン解析設定")
        analysis_layout = QFormLayout(analysis_group)
        analysis_layout.addRow("APIキー:", self.api_key_edit)
        analysis_layout.addRow("モデル:", self.model_combo)
        analysis_layout.addRow("プロンプト:", self.prompt_combo)
        analysis_layout.addRow("バッチサイズ:", self.batch_size_spin)
        
        # ボタン
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # レイアウトに追加
        layout.addLayout(form_layout)
        layout.addWidget(analysis_group)
        layout.addWidget(button_box)
    
    def load_settings(self):
        """設定を読み込む"""
        try:
            # データベースから設定を読み込む
            detection_threshold = self.database.get_setting("scene_detection.threshold", "0.3")
            min_scene_duration = self.database.get_setting("scene_detection.min_scene_duration", "2.0")
            use_cuda = self.database.get_setting("scene_detection.cuda_enabled", "false")
            api_key = self.database.get_setting("analysis.api_key", "")
            model = self.database.get_setting("analysis.model", "gemini-pro-vision")
            batch_size = self.database.get_setting("analysis.batch_size", "5")
            
            # 設定を反映
            self.threshold_spin.setValue(float(detection_threshold))
            self.min_duration_spin.setValue(float(min_scene_duration))
            
            # use_cudaの処理を修正
            if isinstance(use_cuda, bool):
                self.use_cuda_check.setChecked(use_cuda)
            else:
                self.use_cuda_check.setChecked(use_cuda.lower() == "true")
                
            # APIキーの設定
            if not api_key:
                # QSettingsからAPIキーを取得
                from PyQt5.QtCore import QSettings
                settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
                api_key = settings.value("api_key", "")
                
            self.api_key_edit.setText(api_key)
            
            index = self.model_combo.findText(model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            
            self.batch_size_spin.setValue(int(batch_size))
                
        except Exception as e:
            logger.error(f"設定の読み込みエラー: {e}")
    
    def load_prompts(self):
        """プロンプトを読み込む"""
        try:
            # データベースからプロンプトを読み込む
            prompts = self.database.get_all_prompts()
            
            # プロンプトをコンボボックスに追加
            self.prompt_combo.clear()
            for prompt in prompts:
                self.prompt_combo.addItem(prompt['name'], prompt['id'])
                
        except Exception as e:
            logger.error(f"プロンプトの読み込みエラー: {e}")
    
    def get_session_data(self) -> Dict[str, Any]:
        """
        セッションデータを取得
        
        Returns:
            Dict[str, Any]: セッションデータ
        """
        return {
            "name": self.name_edit.text(),
            "detection_threshold": self.threshold_spin.value(),
            "min_scene_duration": self.min_duration_spin.value(),
            "use_cuda": self.use_cuda_check.isChecked(),
            "api_key": self.api_key_edit.text(),
            "model": self.model_combo.currentText(),
            "prompt": self.prompt_combo.currentData(),
            "batch_size": self.batch_size_spin.value()
        }
    
    def accept(self):
        """ダイアログが受け入れられたときの処理"""
        # 入力検証
        if not self.validate_input():
            return
            
        # APIキーが入力されていれば保存
        api_key = self.api_key_edit.text().strip()
        if api_key:
            self.database.set_setting('analysis.api_key', api_key)
        
        # 選択されたモデルを取得
        selected_model = self.model_combo.currentText()
        
        # 選択されたプロンプトIDを取得
        prompt_id = self.get_selected_prompt_id()
        
        # QSettingsにプロンプトIDとモデル名を保存
        from PyQt5.QtCore import QSettings
        settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
        settings.setValue("prompt_id", prompt_id)
        settings.setValue("model_name", selected_model)  # モデル名を保存
        
        # セッションデータを設定
        self.session_data = {
            'name': self.name_edit.text(),
            'detection_threshold': self.threshold_spin.value(),
            'min_scene_duration': self.min_duration_spin.value(),
            'use_cuda': self.use_cuda_check.isChecked(),
            'api_key': api_key,
            'model': selected_model,
            'prompt_id': prompt_id,
            'batch_size': self.batch_size_spin.value()
        }
        
        super().accept()
    
    def validate_input(self) -> bool:
        """
        入力を検証
        
        Returns:
            bool: 検証結果
        """
        # セッション名が空でないか確認
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "入力エラー", "セッション名を入力してください。")
            return False
        
        # APIキーが入力されているか確認（解析を行う場合）
        if not self.api_key_edit.text().strip():
            result = QMessageBox.question(
                self,
                "APIキーが未入力",
                "APIキーが入力されていません。シーン検出のみを行いますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result == QMessageBox.No:
                return False
        
        return True
    
    def save_settings(self):
        """設定を保存"""
        try:
            # 設定をデータベースに保存
            self.database.set_setting("scene_detection.threshold", str(self.threshold_spin.value()))
            self.database.set_setting("scene_detection.min_scene_duration", str(self.min_duration_spin.value()))
            self.database.set_setting("scene_detection.cuda_enabled", str(self.use_cuda_check.isChecked()).lower())
            
            # APIキーの保存
            api_key = self.api_key_edit.text()
            if api_key:
                self.database.set_setting("analysis.api_key", api_key)
                
                # APIキーはレジストリに保存しない（セキュリティ対策）
                # QSettingsの既存のAPIキーを削除
                from PyQt5.QtCore import QSettings
                settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
                if settings.contains("api_key"):
                    settings.remove("api_key")
                    logger.info("レジストリからAPIキーを削除しました（セキュリティ対策）")
            else:
                # APIキーが空の場合、QSettingsからも削除
                from PyQt5.QtCore import QSettings
                settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
                if settings.contains("api_key"):
                    settings.remove("api_key")
                    logger.info("レジストリからAPIキーを削除しました")
            
            self.database.set_setting("analysis.model", self.model_combo.currentText())
            self.database.set_setting("analysis.batch_size", str(self.batch_size_spin.value()))
            
        except Exception as e:
            logger.error(f"設定の保存エラー: {e}")
            QMessageBox.warning(self, "エラー", f"設定の保存中にエラーが発生しました: {e}")
    
    def get_selected_prompt_id(self) -> Optional[int]:
        """
        選択されたプロンプトのIDを取得
        
        Returns:
            Optional[int]: プロンプトID（選択されていない場合はNone）
        """
        current_index = self.prompt_combo.currentIndex()
        if current_index >= 0:
            # コンボボックスに設定されたIDを直接取得
            return self.prompt_combo.currentData()
        return None

    def get_session_name(self) -> str:
        """
        セッション名を取得
        
        Returns:
            str: セッション名
        """
        return self.name_edit.text()

    def get_threshold(self) -> float:
        """
        検出閾値を取得
        
        Returns:
            float: 検出閾値
        """
        return self.threshold_spin.value()

    def get_min_scene_duration(self) -> float:
        """
        最小シーン長を取得
        
        Returns:
            float: 最小シーン長（秒）
        """
        return self.min_duration_spin.value()

    def get_use_cuda(self) -> bool:
        """
        CUDA使用フラグを取得
        
        Returns:
            bool: CUDA使用フラグ
        """
        return self.use_cuda_check.isChecked() 