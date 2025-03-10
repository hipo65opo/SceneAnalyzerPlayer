#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scene Analyzerアプリケーションのエントリーポイント
"""

import os
import sys
import logging
import platform

from PyQt5.QtWidgets import QApplication
# QtCoreからQtを直接インポート
from PyQt5.QtCore import Qt, QCoreApplication

# HiDPI設定
# type: ignore[attr-defined] - PyQt5の定数アクセスに関する型チェックエラーを無視
# QApplicationではなくQCoreApplicationを使用
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """アプリケーションのメインエントリーポイント"""
    # プラットフォーム情報をログに出力
    logger.info(f"プラットフォーム: {platform.system()} {platform.release()}")
    
    # Windows環境の場合、MediaFoundationバックエンドを使用
    if platform.system() == 'Windows':
        logger.info("Windows環境を検出しました。MediaFoundationバックエンドを使用します。")
        # MediaFoundationバックエンドを明示的に設定
        os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
    
    # アプリケーションの作成
    app = QApplication(sys.argv)
    app.setApplicationName("Scene Analyzer")
    app.setOrganizationName("Scene Analyzer Team")
    app.setOrganizationDomain("sceneanalyzer.example.com")
    
    # メインウィンドウのインポートと作成
    from scene_analyzer.main import run_app
    
    # アプリケーションの実行
    sys.exit(run_app(app))

if __name__ == "__main__":
    main() 