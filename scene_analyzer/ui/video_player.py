#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ビデオプレーヤーモジュール
"""

from PyQt5.QtCore import Qt, QUrl, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from typing import cast, Callable, Any

class VideoPlayer(QWidget):
    """ビデオプレーヤークラス"""
    
    # シグナル定義
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(int)
    error_occurred = Signal(str)
    
    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        
        # レイアウト
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ビデオウィジェット
        self.video_widget = QVideoWidget(self)
        layout.addWidget(self.video_widget)
        
        # メディアプレーヤー
        self.media_player = QMediaPlayer(self)
        self.media_player.setVideoOutput(self.video_widget)
        
        # シグナル接続
        self.media_player.positionChanged.connect(self.position_changed.emit)  # type: ignore
        self.media_player.durationChanged.connect(self.duration_changed.emit)  # type: ignore
        self.media_player.stateChanged.connect(self.state_changed.emit)  # type: ignore
        self.media_player.error.connect(self._handle_error)  # type: ignore
    
    def load(self, file_path):
        """動画ファイルを読み込む"""
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
    
    def play(self):
        """再生"""
        self.media_player.play()
    
    def pause(self):
        """一時停止"""
        self.media_player.pause()
    
    def stop(self):
        """停止"""
        self.media_player.stop()
    
    def set_position(self, position):
        """再生位置を設定"""
        self.media_player.setPosition(position)
    
    def set_volume(self, volume):
        """音量を設定"""
        self.media_player.setVolume(volume)
    
    def set_playback_rate(self, rate):
        """再生速度を設定"""
        self.media_player.setPlaybackRate(rate)
    
    def get_position(self):
        """現在の再生位置を取得"""
        return self.media_player.position()
    
    def get_duration(self):
        """動画の長さを取得"""
        return self.media_player.duration()
    
    def get_state(self):
        """現在の再生状態を取得"""
        return self.media_player.state()
    
    @Slot(int)
    def _handle_error(self, error):
        """エラーハンドリング"""
        error_msg = f"メディアプレーヤーエラー: {error}"
        self.error_occurred.emit(error_msg) 