#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
タイムラインウィジェットモジュール
"""

from PyQt5.QtCore import Qt, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPaintEvent
from typing import List, Dict, Any, Optional, cast

class TimelineWidget(QWidget):
    """タイムラインウィジェットクラス"""
    
    # シグナル定義
    position_changed = Signal(int)
    scene_selected = Signal(dict)
    
    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        
        # 変数初期化
        self.scenes = []
        self.duration = 0
        self.position = 0
        self.selected_scene = None
        
        # 最小サイズ設定
        self.setMinimumHeight(50)
        
        # マウスイベント追跡
        self.setMouseTracking(True)
    
    def set_scenes(self, scenes):
        """シーンリストを設定"""
        self.scenes = scenes
        self.update()
    
    def set_duration(self, duration):
        """動画の長さを設定"""
        self.duration = duration
        self.update()
    
    def set_position(self, position):
        """現在の再生位置を設定"""
        self.position = position
        self.update()
    
    def paintEvent(self, event: QPaintEvent):
        """描画イベント"""
        if not self.duration:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景
        painter.fillRect(event.rect(), QColor(40, 40, 40))
        
        # シーンの描画
        if self.scenes:
            width = self.width()
            for scene in self.scenes:
                start_time = scene.get('timestamp', 0)
                duration = scene.get('duration', 0)
                
                # 位置計算
                start_pos = int(start_time * width / self.duration)
                scene_width = max(1, int(duration * width / self.duration))
                
                # シーン描画
                if scene == self.selected_scene:
                    painter.fillRect(start_pos, 0, scene_width, self.height(), QColor(100, 150, 200))
                else:
                    painter.fillRect(start_pos, 0, scene_width, self.height(), QColor(80, 120, 160))
        
        # 現在位置の描画
        if self.duration > 0:
            pos_x = int(self.position * self.width() / self.duration)
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(pos_x, 0, pos_x, self.height())
    
    def mousePressEvent(self, event):
        """マウスクリックイベント"""
        if event.button() == Qt.MouseButton.LeftButton and self.duration > 0:  # type: ignore
            # クリック位置から再生位置を計算
            pos = int(event.x() * self.duration / self.width())
            self.position_changed.emit(pos)
            
            # クリックしたシーンを選択
            for scene in self.scenes:
                start_time = scene.get('timestamp', 0)
                duration = scene.get('duration', 0)
                end_time = start_time + duration
                
                if start_time <= pos <= end_time:
                    self.selected_scene = scene
                    self.scene_selected.emit(scene)
                    break
            
            self.update() 