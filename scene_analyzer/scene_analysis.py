#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
シーン解析モジュール
"""

import os
import logging
import json
import time
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np
import google.generativeai as genai
from PIL import Image

# ロガーの設定
logger = logging.getLogger(__name__)

class SceneAnalyzer:
    """シーン解析クラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初期化
        
        Args:
            api_key: Google Gemini API キー
        """
        self.api_key = api_key
        self.model = None
        self.initialized = False
    
    def initialize(self, api_key: Optional[str] = None, model_name: str = 'gemini-1.5-flash'):
        """APIの初期化
        
        Args:
            api_key: Google Gemini API キー
            model_name: 使用するGeminiモデル名
        """
        if api_key:
            self.api_key = api_key
        
        # 環境変数からのAPIキー読み込みを削除
        
        if not self.api_key:
            error_msg = "API キーが設定されていません。シーン解析は実行できません。"
            logger.warning(error_msg)
            return False
        
        try:
            # Google Gemini APIの設定
            genai.configure(api_key=self.api_key)
            
            # モデルの取得
            self.model = genai.GenerativeModel(model_name)
            self.initialized = True
            logger.info(f"シーン解析エンジンを初期化しました（モデル: {model_name}）")
            return True
        except Exception as e:
            error_msg = f"シーン解析エンジンの初期化に失敗しました: {str(e)}"
            logger.error(error_msg)
            self.initialized = False
            return False
    
    def analyze_scene(self, 
                     image_path: str, 
                     prompt: str = "この画像に写っているものを一言で説明してください。必ず日本語で回答してください。") -> Dict[str, Any]:
        """シーンを解析する
        
        Args:
            image_path: 解析する画像のパス
            prompt: 解析に使用するプロンプト
        
        Returns:
            解析結果の辞書
        """
        if not self.initialized:
            if not self.initialize():
                return {"error": "APIが初期化されていません"}
        
        if not os.path.exists(image_path):
            return {"error": f"画像ファイルが見つかりません: {image_path}"}
        
        try:
            # モデルが初期化されているか確認
            if self.model is None:
                return {"error": "モデルが初期化されていません。API キーを確認してください。"}
                
            # 画像の読み込み
            image = Image.open(image_path)
            
            # 解析の実行
            response = self.model.generate_content([prompt, image])
            
            # 結果の整形
            result = {
                "description": response.text,
                "timestamp": time.time(),
                "prompt": prompt,
                "image_path": image_path
            }
            
            return result
        except Exception as e:
            logger.error(f"シーン解析中にエラーが発生しました: {str(e)}")
            return {"error": str(e)}
    
    def analyze_scenes_batch(self, 
                           image_paths: List[str], 
                           prompt: str = "この画像に写っているものを一言で説明してください。必ず日本語で回答してください。",
                           batch_size: int = 5) -> List[Dict[str, Any]]:
        """複数のシーンをバッチで解析する
        
        Args:
            image_paths: 解析する画像のパスのリスト
            prompt: 解析に使用するプロンプト
            batch_size: 一度に処理する画像の数
        
        Returns:
            解析結果の辞書のリスト
        """
        results = []
        
        # バッチ処理
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            logger.info(f"バッチ処理中: {i+1}〜{min(i+batch_size, len(image_paths))}/{len(image_paths)}")
            
            for image_path in batch:
                result = self.analyze_scene(image_path, prompt)
                results.append(result)
                
                # APIレート制限を考慮して少し待機
                time.sleep(1)
        
        return results
    
    def extract_scene_thumbnail(self, video_path: str, timestamp: float, output_path: str) -> Optional[str]:
        """動画からシーンのサムネイルを抽出する
        
        Args:
            video_path: 動画ファイルのパス
            timestamp: サムネイルを抽出する時間（秒）
            output_path: 出力先のパス
        
        Returns:
            サムネイル画像のパス、失敗した場合はNone
        """
        try:
            # 動画の読み込み
            cap = cv2.VideoCapture(video_path)
            
            # 指定した時間にシーク
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            
            # フレームの読み込み
            ret, frame = cap.read()
            if not ret:
                logger.error(f"フレームの読み込みに失敗しました: {video_path}, 時間: {timestamp}")
                cap.release()
                return None
            
            # サムネイルの保存
            cv2.imwrite(output_path, frame)
            
            # リソースの解放
            cap.release()
            
            return output_path
        except Exception as e:
            logger.error(f"サムネイル抽出中にエラーが発生しました: {str(e)}")
            return None
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデルのリストを取得する
        
        Returns:
            利用可能なモデルのリスト
        """
        try:
            if not self.initialized:
                if not self.initialize():
                    return []
            
            # モデルが初期化されているか確認
            if self.model is None:
                logger.warning("モデルが初期化されていません。API キーを確認してください。")
                return []
                
            # 利用可能なモデルのリスト
            return [
                "gemini-1.5-flash",
                "gemini-1.5-pro"
            ]
        except Exception as e:
            logger.error(f"モデル一覧の取得中にエラーが発生しました: {str(e)}")
            return []