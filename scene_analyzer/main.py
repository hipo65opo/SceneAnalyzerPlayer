#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scene Analyzerアプリケーションのメインモジュール
"""

import os
import sys
import logging
import platform
from typing import Optional, Tuple, cast
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget
from PyQt5.QtCore import QCoreApplication, QSettings

# 内部モジュールのインポート
from scene_analyzer.ui.main_window import MainWindow
from scene_analyzer.database import Database

# ロガーの設定
logger = logging.getLogger(__name__)

def check_system_requirements() -> Tuple[bool, str]:
    """
    システム要件をチェックする
    
    Returns:
        Tuple[bool, str]: 要件を満たしているかどうかとエラーメッセージ
    """
    # Windows環境のチェック
    if platform.system() != 'Windows':
        return False, "このアプリケーションはWindows環境でのみ動作します。"
    
    # Windows Media Feature Packのチェック（簡易的な方法）
    try:
        # MediaFoundationの関連DLLが存在するかチェック
        mf_dll_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'mf.dll')
        if not os.path.exists(mf_dll_path):
            return False, "Windows Media Feature Packがインストールされていない可能性があります。"
    except Exception:
        # チェック中にエラーが発生した場合は無視
        pass
    
    return True, ""

def run_app(app: QApplication) -> int:
    """
    アプリケーションを実行する
    
    Args:
        app: QApplicationインスタンス
        
    Returns:
        int: 終了コード
    """
    # ロギングの設定
    log_dir = os.path.join(os.path.expanduser('~'), '.scene_analyzer', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'scene_analyzer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # ロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # ファイルハンドラ
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # ログ開始メッセージ
    logger.info(f"アプリケーションを起動しています。ログファイル: {log_file}")
    
    # システム要件のチェック
    requirements_ok, error_message = check_system_requirements()
    if not requirements_ok:
        # 型チェックエラーを回避するためにcastを使用
        QMessageBox.critical(cast(QWidget, None), "システム要件エラー", error_message)  # type: ignore[arg-type]
        logger.error(f"システム要件エラー: {error_message}")
        return 1
    
    # Windows環境の場合、MediaFoundationバックエンドを明示的に設定
    if platform.system() == 'Windows':
        os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
    
    # データベースの初期化
    db_path = os.path.join(os.path.expanduser('~'), '.scene_analyzer', 'scene_analyzer.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    try:
        # データベース接続
        logger.info(f"データベースに接続しています: {db_path}")
        database = Database(db_path)
        
        # データベースの初期化
        database.initialize()
        
        # 設定の確認と移行
        # 旧設定キーから新設定キーへの移行を確認
        old_to_new_keys = {
            'detection_threshold': 'scene_detection.threshold',
            'min_scene_duration': 'scene_detection.min_scene_duration',
            'use_cuda': 'scene_detection.cuda_enabled',
            'api_key': 'analysis.api_key',
            'model': 'analysis.model',
            'batch_size': 'analysis.batch_size'
        }
        
        # 設定の移行状況をログに出力
        for old_key, new_key in old_to_new_keys.items():
            old_value = database.get_setting(old_key, "")
            new_value = database.get_setting(new_key, "")
            
            if old_value:
                logger.info(f"旧設定キー '{old_key}' が存在します。値: {old_value}")
                if not new_value:
                    database.set_setting(new_key, old_value)
                    if database.conn:
                        cursor = database.conn.cursor()
                        cursor.execute('DELETE FROM settings WHERE key = ?', (old_key,))
                        database.conn.commit()
                    logger.info(f"設定を移行しました: {old_key} -> {new_key}")
        
        # APIキーの同期処理を削除（セキュリティ対策）
        # レジストリに保存されたAPIキーがある場合は削除
        settings = QSettings("SceneAnalyzer", "SceneAnalyzer")
        if settings.contains("api_key"):
            settings.remove("api_key")
            logger.info("レジストリからAPIキーを削除しました（セキュリティ対策）")
        
        # メインウィンドウの作成と表示
        window = MainWindow()
        window.show()
        
        # アプリケーションの実行
        return app.exec_()
    
    except Exception as e:
        logger.error(f"アプリケーションの起動中にエラーが発生しました: {str(e)}")
        QMessageBox.critical(cast(QWidget, None), "起動エラー", f"アプリケーションの起動中にエラーが発生しました:\n{str(e)}")  # type: ignore[arg-type]
        return 1
    
if __name__ == "__main__":
    # このモジュールが直接実行された場合は__main__.pyを呼び出す
    from scene_analyzer.__main__ import main
    sys.exit(main()) 