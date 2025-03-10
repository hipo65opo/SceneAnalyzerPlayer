#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベース操作モジュール
"""

import os
import sqlite3
import json
import csv
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

# ロガーの設定
logger = logging.getLogger(__name__)

class Database:
    """データベース操作クラス"""
    
    def __init__(self, db_path: str):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self.conn = None
        
        try:
            # データベースディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # データベース接続
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            
            # テーブル作成
            self._create_tables()
            
            logger.info(f"データベース接続を確立しました: {db_path}")
        except sqlite3.Error as e:
            logger.error(f"データベース接続エラー: {e}")
            if self.conn is not None:
                self.conn.close()
                self.conn = None
    
    def initialize(self) -> None:
        """
        データベースを初期化する
        
        テーブルが存在しない場合は作成し、必要な初期データを挿入します。
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return
            
        try:
            # テーブルの作成
            self._create_tables()
            
            # 初期データの挿入
            self._insert_initial_data()
            
            # データベースパスを設定に保存
            self.set_setting('database.path', self.db_path)
            
            logger.info("データベースの初期化が完了しました")
        except sqlite3.Error as e:
            logger.error(f"データベース初期化エラー: {e}")
    
    def _create_tables(self):
        """テーブルを作成"""
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return
            
        try:
            cursor = self.conn.cursor()
            
            # 動画テーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                duration REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # セッションテーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                detection_threshold REAL NOT NULL,
                min_scene_duration REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
            ''')
            
            # シーンテーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                duration REAL NOT NULL,
                thumbnail_path TEXT,
                frame_path TEXT,
                description TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
            ''')
            
            # 設定テーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # プロンプトテーブル
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            self.conn.commit()
            logger.debug("テーブルの作成が完了しました")
        except sqlite3.Error as e:
            logger.error(f"テーブル作成エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
    
    def _insert_initial_data(self):
        """初期データを挿入"""
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return
            
        try:
            cursor = self.conn.cursor()
            
            # デフォルト設定
            default_settings = [
                ('scene_detection.threshold', '0.3'),
                ('scene_detection.min_scene_duration', '10.0'),
                ('scene_detection.cuda_enabled', 'false'),
                ('scene_detection.cuda_device_id', '0'),
                ('analysis.api_key', ''),
                ('analysis.model', 'gemini-pro-vision'),
                ('analysis.batch_size', '5'),
                ('analysis.confidence_threshold', '0.7'),
                ('export.default_path', os.path.join(os.path.expanduser("~"), "Documents")),
                ('export.format', 'json'),
                ('display.hidpi_enabled', 'true')
            ]
            
            # 設定が存在しない場合のみ挿入
            for key, value in default_settings:
                cursor.execute('SELECT COUNT(*) FROM settings WHERE key = ?', (key,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        'INSERT INTO settings (key, value) VALUES (?, ?)',
                        (key, value)
                    )
            
            # 旧設定キーから新設定キーへの移行
            old_to_new_keys = {
                'detection_threshold': 'scene_detection.threshold',
                'min_scene_duration': 'scene_detection.min_scene_duration',
                'use_cuda': 'scene_detection.cuda_enabled',
                'api_key': 'analysis.api_key',
                'model': 'analysis.model',
                'batch_size': 'analysis.batch_size'
            }
            
            # 旧設定キーが存在する場合は新設定キーに移行
            for old_key, new_key in old_to_new_keys.items():
                cursor.execute('SELECT value FROM settings WHERE key = ?', (old_key,))
                row = cursor.fetchone()
                if row:
                    # 旧設定の値を取得
                    old_value = row['value']
                    
                    # 新設定キーに値を設定
                    cursor.execute('SELECT COUNT(*) FROM settings WHERE key = ?', (new_key,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute(
                            'INSERT INTO settings (key, value) VALUES (?, ?)',
                            (new_key, old_value)
                        )
                    else:
                        cursor.execute(
                            'UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?',
                            (old_value, new_key)
                        )
                    
                    # 旧設定キーを削除
                    cursor.execute('DELETE FROM settings WHERE key = ?', (old_key,))
                    logger.info(f"設定キーを移行しました: {old_key} -> {new_key}")
            
            # デフォルトプロンプト
            default_prompts = [
                ('シーン説明', 'この動画シーンについて詳細に説明してください。何が起きているか、誰が映っているか、どのような環境かなどを含めてください。必ず日本語で回答してください。'),
                ('シーンタグ', 'この動画シーンに適したタグを5つから10つ生成してください。カンマ区切りのリスト形式で返してください。必ず日本語で回答してください。'),
                ('感情分析', 'この動画シーンから感じられる感情や雰囲気を分析してください。必ず日本語で回答してください。'),
                ('オブジェクト検出', 'この動画シーンに映っているオブジェクトや人物をリストアップしてください。必ず日本語で回答してください。'),
                ('アクション認識', 'この動画シーンで行われているアクションや動きを特定してください。必ず日本語で回答してください。'),
                ('ワンワード', 'この画像に写っているものを一言で説明してください。必ず日本語で回答してください。')
            ]
            
            # プロンプトが存在しない場合のみ挿入
            for name, content in default_prompts:
                cursor.execute('SELECT COUNT(*) FROM prompts WHERE name = ?', (name,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        'INSERT INTO prompts (name, content) VALUES (?, ?)',
                        (name, content)
                    )
            
            self.conn.commit()
            logger.debug("初期データの挿入が完了しました")
        except sqlite3.Error as e:
            logger.error(f"初期データ挿入エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
    
    def close(self):
        """データベース接続を閉じる"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            logger.info("データベース接続を閉じました")
    
    def get_video_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        ファイルパスから動画情報を取得
        
        Args:
            file_path: 動画ファイルのパス
            
        Returns:
            Dict[str, Any] or None: 動画情報
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM videos WHERE file_path = ?', (file_path,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"動画情報取得エラー: {e}")
            return None
    
    def add_video(self, file_path: str, duration: float) -> Optional[int]:
        """
        動画情報を追加
        
        Args:
            file_path: 動画ファイルのパス
            duration: 動画の長さ（秒）
            
        Returns:
            int or None: 追加された動画のID
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO videos (file_path, duration) VALUES (?, ?)',
                (file_path, duration)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"動画追加エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return None
    
    def update_video_duration(self, video_id: int, duration: float) -> bool:
        """
        動画の長さを更新
        
        Args:
            video_id: 動画ID
            duration: 動画の長さ（秒）
            
        Returns:
            bool: 更新が成功したかどうか
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE videos SET duration = ? WHERE id = ?',
                (duration, video_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"動画長さ更新エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return False
    
    def create_session(self, name: str, video_id: Optional[int] = None) -> Optional[int]:
        """
        セッションを作成
        
        Args:
            name: セッション名
            video_id: 動画ID（指定されない場合は最新の動画IDを使用）
            
        Returns:
            int or None: 作成されたセッションのID
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
        
        try:
            # 動画IDが指定されていない場合は最新の動画IDを取得
            if video_id is None:
                cursor = self.conn.cursor()
                cursor.execute('SELECT id FROM videos ORDER BY id DESC LIMIT 1')
                row = cursor.fetchone()
                
                if not row:
                    logger.error("動画が見つかりません")
                    return None
                
                video_id = row['id']
            
            # 指定された動画IDが存在するか確認
            cursor = self.conn.cursor()
            cursor.execute('SELECT id FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.error(f"指定された動画ID {video_id} が見つかりません")
                return None
            
            # 設定を取得
            detection_threshold = self.get_setting('detection_threshold')
            min_scene_duration = self.get_setting('min_scene_duration')
            
            if not detection_threshold:
                detection_threshold = '0.3'
            
            if not min_scene_duration:
                min_scene_duration = '10.0'
            
            # セッションを作成
            cursor.execute(
                'INSERT INTO sessions (video_id, name, detection_threshold, min_scene_duration) VALUES (?, ?, ?, ?)',
                (video_id, name, float(detection_threshold), float(min_scene_duration))
            )
            
            self.conn.commit()
            logger.info(f"セッションを作成しました: 名前={name}, 動画ID={video_id}")
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"セッション作成エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return None
    
    def add_scene(self, session_id: int, timestamp: float, duration: float, thumbnail_path: Optional[str] = None) -> Optional[int]:
        """
        シーンを追加
        
        Args:
            session_id: セッションID
            timestamp: タイムスタンプ（秒）
            duration: シーンの長さ（秒）
            thumbnail_path: サムネイル画像のパス
            
        Returns:
            int or None: 追加されたシーンのID
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO scenes (session_id, timestamp, duration, thumbnail_path) VALUES (?, ?, ?, ?)',
                (session_id, timestamp, duration, thumbnail_path)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"シーン追加エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return None
    
    def update_scene(self, scene_id: int, data: Dict[str, Any]) -> bool:
        """
        シーン情報を更新
        
        Args:
            scene_id: シーンID
            data: 更新データ
            
        Returns:
            bool: 更新成功フラグ
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return False
            
        try:
            cursor = self.conn.cursor()
            update_fields = []
            values = []
            
            # テーブルのカラム情報を取得
            cursor.execute("PRAGMA table_info(scenes)")
            columns = [row['name'] for row in cursor.fetchall()]
            
            # 更新前のデータを取得して詳細なログを出力
            cursor.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
            before_update = cursor.fetchone()
            if before_update:
                logger.debug(f"シーン更新前のデータ: ID={scene_id}, データ={dict(before_update)}")
            
            for key, value in data.items():
                # カラムが存在する場合のみ更新対象に含める
                if key in columns and key in ['timestamp', 'duration', 'thumbnail_path', 'frame_path', 'description', 'tags', 'confidence']:
                    # パスフィールドの場合、特別な検証を行う
                    if key in ['frame_path', 'thumbnail_path']:
                        if not value:
                            logger.debug(f"空の{key}のため更新をスキップします")
                            continue
                        
                        # パスの存在確認
                        if not os.path.exists(value):
                            logger.warning(f"{key}が存在しません: {value}")
                            
                            # 絶対パスに変換して再確認
                            abs_path = os.path.abspath(value)
                            logger.debug(f"絶対パスに変換: {abs_path}")
                            
                            if not os.path.exists(abs_path):
                                logger.warning(f"絶対パスも存在しません: {abs_path}")
                                
                                # 既存のパスを保持するか確認
                                if before_update and before_update[key]:
                                    existing_path = before_update[key]
                                    if os.path.exists(existing_path):
                                        logger.info(f"既存の{key}が有効なため更新をスキップします: {existing_path}")
                                        continue
                                
                                # ファイルが存在しない場合でも、パスが有効な形式であれば更新する
                                # これは将来的にファイルが作成される可能性があるため
                                logger.info(f"ファイルは存在しませんが、{key}を更新します: {value}")
                            else:
                                # 絶対パスが存在する場合は絶対パスを使用
                                logger.info(f"絶対パスが存在するため使用します: {abs_path}")
                                value = abs_path
                        
                        # ファイルが存在する場合、ファイルサイズを確認
                        if os.path.exists(value) and os.path.isfile(value):
                            file_size = os.path.getsize(value)
                            if file_size == 0:
                                logger.warning(f"{key}のファイルサイズが0バイトです: {value}")
                                # 0バイトのファイルでも一応パスは更新する
                    
                    update_fields.append(f"{key} = ?")
                    values.append(value)
            
            if not update_fields:
                logger.debug(f"シーン {scene_id} の更新するフィールドがありません")
                return False
            
            # UPDATE文を構築
            query = f"UPDATE scenes SET {', '.join(update_fields)} WHERE id = ?"
            values.append(scene_id)
            
            # クエリを実行
            cursor.execute(query, values)
            self.conn.commit()
            
            # 更新後のデータを確認
            cursor.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
            updated_row = cursor.fetchone()
            if updated_row:
                logger.debug(f"シーン更新成功: ID={scene_id}, 更新後データ={dict(updated_row)}")
                
                # 更新されたパスが実際に存在するか確認
                for path_field in ['frame_path', 'thumbnail_path']:
                    if path_field in data and updated_row[path_field]:
                        path_exists = os.path.exists(updated_row[path_field])
                        path_is_file = os.path.isfile(updated_row[path_field])
                        logger.debug(f"更新後の{path_field}検証: {updated_row[path_field]}, exists={path_exists}, isfile={path_is_file}")
            
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"シーン更新エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return False
    
    def get_scenes_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        """
        セッションに属するシーンのリストを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            List[Dict[str, Any]]: シーンのリスト
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return []
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM scenes WHERE session_id = ? ORDER BY timestamp', (session_id,))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"シーンリスト取得エラー: {e}")
            return []
    
    def get_sessions_for_video(self, video_id: int) -> List[Dict[str, Any]]:
        """
        動画に関連するセッションを取得
        
        Args:
            video_id: 動画ID
        
        Returns:
            セッション情報のリスト
        """
        try:
            if self.conn is None:
                logger.error("データベース接続がありません")
                return []
            
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE video_id = ? ORDER BY created_at DESC",
                (video_id,)
            )
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append(dict(row))
            
            return sessions
        except sqlite3.Error as e:
            logger.error(f"セッション取得エラー: {e}")
            return []
    
    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        セッション情報を取得
        
        Args:
            session_id: セッションID
        
        Returns:
            セッション情報の辞書、存在しない場合はNone
        """
        try:
            if self.conn is None:
                logger.error("データベース接続がありません")
                return None
            
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            return None
        except sqlite3.Error as e:
            logger.error(f"セッション取得エラー: {e}")
            return None
    
    def get_setting(self, key: str, default: Any = '') -> Any:
        """
        設定値を取得
        
        Args:
            key: 設定キー
            default: デフォルト値
            
        Returns:
            設定値
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return default
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                # JSON文字列として保存されている可能性があるため、デコードを試みる
                value = row['value']
                try:
                    # JSON形式の場合はデコード
                    return json.loads(value)
                except json.JSONDecodeError:
                    # 通常の文字列の場合はそのまま返す
                    return value
            return default
        except sqlite3.Error as e:
            logger.error(f"設定取得エラー: {e}")
            return default
    
    def set_setting(self, key: str, value: str) -> bool:
        """
        設定値を設定
        
        Args:
            key: 設定キー
            value: 設定値
            
        Returns:
            bool: 設定が成功したかどうか
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM settings WHERE key = ?', (key,))
            
            if cursor.fetchone()[0] > 0:
                # 既存の設定を更新
                cursor.execute(
                    'UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?',
                    (value, key)
                )
            else:
                # 新しい設定を挿入
                cursor.execute(
                    'INSERT INTO settings (key, value) VALUES (?, ?)',
                    (key, value)
                )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"設定更新エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return False
    
    def get_all_settings(self) -> Dict[str, str]:
        """
        すべての設定値を取得
        
        Returns:
            Dict[str, str]: キーと値のペア
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return {}
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT key, value FROM settings')
            rows = cursor.fetchall()
            
            return {row['key']: row['value'] for row in rows}
        except sqlite3.Error as e:
            logger.error(f"設定一覧取得エラー: {e}")
            return {}
    
    def get_all_prompts(self) -> List[Dict[str, Any]]:
        """
        すべてのプロンプトを取得
        
        Returns:
            List[Dict[str, Any]]: プロンプトのリスト
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return []
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM prompts ORDER BY name')
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"プロンプト一覧取得エラー: {e}")
            return []
    
    def add_prompt(self, name: str, content: str) -> Optional[int]:
        """
        プロンプトを追加
        
        Args:
            name: プロンプト名
            content: プロンプト内容
            
        Returns:
            int or None: 追加されたプロンプトのID
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO prompts (name, content) VALUES (?, ?)',
                (name, content)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"プロンプト追加エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return None
    
    def update_prompt(self, prompt_id: int, name: str, content: str) -> bool:
        """
        プロンプトを更新
        
        Args:
            prompt_id: プロンプトID
            name: プロンプト名
            content: プロンプト内容
            
        Returns:
            bool: 更新が成功したかどうか
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE prompts SET name = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (name, content, prompt_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"プロンプト更新エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return False
    
    def delete_prompt(self, prompt_id: int) -> bool:
        """
        プロンプトを削除
        
        Args:
            prompt_id: プロンプトID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM prompts WHERE id = ?', (prompt_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"プロンプト削除エラー: {e}")
            if self.conn is not None:
                self.conn.rollback()
            return False
    
    def export_session_data(self, session_id: int, format_type: str) -> Union[Dict[str, Any], str, None]:
        """
        セッションデータをエクスポート
        
        Args:
            session_id: セッションID
            format_type: エクスポート形式（'json'または'csv'）
            
        Returns:
            Union[Dict[str, Any], str, None]: エクスポートデータ
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            
            # セッション情報を取得
            cursor.execute('''
            SELECT s.*, v.file_path, v.duration as video_duration
            FROM sessions s
            JOIN videos v ON s.video_id = v.id
            WHERE s.id = ?
            ''', (session_id,))
            
            session = cursor.fetchone()
            if not session:
                logger.error(f"セッションが見つかりません: {session_id}")
                return None
            
            # シーン情報を取得
            cursor.execute('SELECT * FROM scenes WHERE session_id = ? ORDER BY timestamp', (session_id,))
            scenes = cursor.fetchall()
            
            # JSON形式でエクスポート
            if format_type == 'json':
                session_dict = dict(session)
                scenes_list = [dict(scene) for scene in scenes]
                
                export_data = {
                    'session': session_dict,
                    'scenes': scenes_list
                }
                
                return export_data
            
            # CSV形式でエクスポート
            elif format_type == 'csv':
                csv_lines = ['timestamp,duration,description,tags']
                
                for scene in scenes:
                    timestamp = scene['timestamp']
                    duration = scene['duration']
                    description = scene['description'] or ''
                    tags = scene['tags'] or ''
                    
                    # CSVエスケープ処理
                    description = description.replace('"', '""')
                    tags = tags.replace('"', '""')
                    
                    csv_lines.append(f'{timestamp},{duration},"{description}","{tags}"')
                
                return '\n'.join(csv_lines)
            
            else:
                logger.error(f"サポートされていないエクスポート形式: {format_type}")
                return None
                
        except sqlite3.Error as e:
            logger.error(f"データエクスポートエラー: {e}")
            return None
    
    def get_video_path(self) -> Optional[str]:
        """
        現在の動画ファイルパスを取得
        
        Returns:
            str or None: 動画ファイルのパス
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT file_path FROM videos ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            
            if row:
                return row['file_path']
            return None
        except sqlite3.Error as e:
            logger.error(f"動画パス取得エラー: {e}")
            return None
    
    def get_scenes(self, session_id: int) -> List[Dict[str, Any]]:
        """
        セッションのシーンを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            List[Dict[str, Any]]: シーンのリスト
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM scenes 
                WHERE session_id = ? 
                ORDER BY timestamp
            ''', (session_id,))
            
            scenes = []
            for row in cursor.fetchall():
                scenes.append(dict(row))
            
            return scenes
        except sqlite3.Error as e:
            logger.error(f"シーン取得エラー: {e}")
            return []
    
    def get_data_dir(self) -> str:
        """
        データディレクトリのパスを取得
        
        Returns:
            str: データディレクトリのパス
        """
        return os.path.dirname(self.db_path)
    
    def reinitialize(self) -> bool:
        """
        データベースを再初期化する
        
        既存のデータベースファイルを削除し、新しいデータベースを作成します。
        注意: すべてのデータが失われます。
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            
        try:
            # データベースファイルが存在する場合は削除
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"既存のデータベースファイルを削除しました: {self.db_path}")
            
            # データベース接続を再確立
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            
            # データベースを初期化
            self.initialize()
            
            logger.info("データベースの再初期化が完了しました")
            return True
        except (sqlite3.Error, OSError) as e:
            logger.error(f"データベース再初期化エラー: {e}")
            return False
    
    def clear_database(self) -> bool:
        """
        データベースの内容をクリアする（テーブル構造は維持）
        
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            try:
                # 再接続を試みる
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
                logger.info("データベースに再接続しました")
            except sqlite3.Error as e:
                logger.error(f"データベース再接続エラー: {e}")
                return False
            
        try:
            cursor = self.conn.cursor()
            
            # 外部キー制約を一時的に無効化
            cursor.execute('PRAGMA foreign_keys = OFF')
            
            # トランザクション開始
            self.conn.execute('BEGIN TRANSACTION')
            
            # 各テーブルのデータを削除
            tables = ['scenes', 'sessions', 'videos', 'settings', 'prompts']
            for table in tables:
                try:
                    cursor.execute(f'DELETE FROM {table}')
                    logger.info(f"テーブル {table} のデータをクリアしました")
                except sqlite3.Error as e:
                    logger.error(f"テーブル {table} のクリア中にエラーが発生しました: {e}")
                    # エラーが発生しても続行
            
            # 外部キー制約を再度有効化
            cursor.execute('PRAGMA foreign_keys = ON')
            
            # 変更をコミット
            self.conn.commit()
            
            # 初期データを再挿入
            self._insert_initial_data()
            
            logger.info("データベースのクリアが完了しました")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"データベースクリアエラー: {e}")
            if self.conn is not None:
                try:
                    self.conn.rollback()
                except sqlite3.Error:
                    pass
            return False
        except Exception as e:
            logger.error(f"予期しないエラーが発生しました: {e}")
            if self.conn is not None:
                try:
                    self.conn.rollback()
                except sqlite3.Error:
                    pass
            return False
    
    def is_connected(self) -> bool:
        """
        データベース接続が確立されているかどうかを確認
        
        Returns:
            bool: 接続が確立されている場合はTrue、そうでない場合はFalse
        """
        if self.conn is None:
            return False
            
        try:
            # 簡単なクエリを実行して接続状態を確認
            cursor = self.conn.cursor()
            cursor.execute('SELECT 1')
            return True
        except sqlite3.Error:
            return False
    
    def get_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        IDから動画情報を取得
        
        Args:
            video_id: 動画ID
            
        Returns:
            Dict[str, Any] or None: 動画情報
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"動画情報取得エラー: {e}")
            return None
    
    def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """
        IDからプロンプトを取得
        
        Args:
            prompt_id: プロンプトID
            
        Returns:
            Optional[Dict[str, Any]]: プロンプト情報（見つからない場合はNone）
        """
        if self.conn is None:
            logger.error("データベース接続が確立されていません")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM prompts WHERE id = ?', (prompt_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"プロンプト取得エラー: {e}")
            return None 