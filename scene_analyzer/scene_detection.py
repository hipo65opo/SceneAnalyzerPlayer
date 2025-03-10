#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
シーン検出と解析のためのモジュール
"""

import os
import cv2
import numpy as np
import logging
import time
from datetime import datetime
import google.generativeai as genai
from PIL import Image
from PyQt5.QtCore import QObject, QThread, pyqtSignal as Signal, pyqtSlot as Slot
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class SceneDetectorWorker(QObject):
    """シーン検出ワーカークラス（バックグラウンドスレッド用）"""
    
    # シグナル定義
    progress_updated = Signal(int)  # 進捗更新シグナル (0-100)
    scene_detected = Signal(dict)   # シーン検出シグナル
    detection_completed = Signal(list)  # 検出完了シグナル（検出されたシーンのリストを返す）
    error_occurred = Signal(str)    # エラーシグナル
    log_message = Signal(str)       # ログメッセージシグナル
    progress_label_updated = Signal(str)  # 進捗ラベル更新シグナル
    
    def __init__(self, video_path: str, threshold: float = 30.0, min_scene_duration: float = 2.0, use_cuda: bool = False):
        """
        初期化
        
        Args:
            video_path: 動画ファイルのパス
            threshold: シーン検出の閾値（大きいほど検出感度が低下）
            min_scene_duration: 最小シーン長（秒）
            use_cuda: CUDAを使用するかどうか
        """
        super().__init__()
        self.video_path = video_path
        self.threshold = threshold
        self.min_scene_duration = min_scene_duration
        self.use_cuda = use_cuda
        self.should_stop = False
    
    @Slot()
    def run(self):
        """ワーカースレッドのメイン処理"""
        try:
            scenes = self.detect_scenes()
            self.detection_completed.emit(scenes)
        except Exception as e:
            error_msg = f"シーン検出中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
    
    def detect_scenes(self) -> List[Dict[str, Any]]:
        """
        動画からシーンを検出
        
        Returns:
            検出されたシーンのリスト
        """
        if not os.path.exists(self.video_path):
            error_msg = f"動画ファイルが見つかりません: {self.video_path}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
        
        try:
            # 動画の読み込み
            cap = cv2.VideoCapture(self.video_path)
            
            # 動画の情報を取得
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps
            
            logger.info(f"動画情報: {frame_count}フレーム, {fps}fps, 長さ: {duration:.2f}秒")
            self.log_message.emit(f"動画情報: {frame_count}フレーム, {fps}fps, 長さ: {duration:.2f}秒")
            
            # CUDAの設定
            if self.use_cuda:
                try:
                    # OpenCVのCUDA機能を有効化（利用可能な場合）
                    if hasattr(cv2, 'cuda'):
                        # CUDA対応デバイスの数を確認
                        cuda_device_count = cv2.cuda.getCudaEnabledDeviceCount()  # type: ignore[attr-defined]
                        if cuda_device_count > 0:
                            cv2.cuda.setDevice(0)  # type: ignore[attr-defined]
                            logger.info(f"CUDA処理を有効化しました（利用可能なデバイス数: {cuda_device_count}）")
                            self.log_message.emit(f"CUDA処理を有効化しました（利用可能なデバイス数: {cuda_device_count}）")
                        else:
                            logger.warning("CUDA対応デバイスが見つかりません。CPU処理を使用します。")
                            self.log_message.emit("CUDA対応デバイスが見つかりません。CPU処理を使用します。")
                            self.use_cuda = False
                    else:
                        logger.warning("このOpenCVビルドではCUDAがサポートされていません")
                        self.log_message.emit("このOpenCVビルドではCUDAがサポートされていません")
                        self.use_cuda = False
                except Exception as e:
                    logger.warning(f"CUDA処理の有効化に失敗しました: {str(e)}")
                    self.log_message.emit(f"CUDA処理の有効化に失敗しました: {str(e)}")
                    self.use_cuda = False
            
            # シーン検出
            scenes = []
            prev_frame = None
            current_scene_start = 0
            frame_idx = 0
            
            while not self.should_stop:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # グレースケールに変換
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # フレーム間の差分を計算
                    if self.use_cuda and hasattr(cv2, 'cuda'):
                        # CUDA処理（高速）
                        try:
                            # CUDA機能が利用可能かどうかを実行時に確認
                            cuda_device = cv2.cuda.getCudaEnabledDeviceCount()
                            if cuda_device > 0:
                                prev_gpu = cv2.cuda.GpuMat()
                                prev_gpu.upload(prev_frame)
                                curr_gpu = cv2.cuda.GpuMat()
                                curr_gpu.upload(gray)
                                # 型チェックエラーを抑制
                                diff_gpu = cv2.cuda.absdiff(prev_gpu, curr_gpu)  # type: ignore[attr-defined]
                                diff = diff_gpu.download()
                            else:
                                # CUDA対応デバイスがない場合はCPU処理にフォールバック
                                diff = cv2.absdiff(prev_frame, gray)
                        except Exception as e:
                            logger.warning(f"CUDA処理中にエラーが発生しました: {str(e)}、CPU処理にフォールバックします")
                            self.log_message.emit(f"CUDA処理中にエラーが発生しました: {str(e)}、CPU処理にフォールバックします")
                            diff = cv2.absdiff(prev_frame, gray)
                    else:
                        # CPU処理
                        diff = cv2.absdiff(prev_frame, gray)
                    
                    # 差分の平均値を計算
                    score = np.mean(diff)
                    
                    # 閾値を超えた場合、シーンの境界と判断
                    if score > self.threshold:
                        current_time = frame_idx / fps
                        scene_duration = current_time - current_scene_start
                        
                        # 最小シーン長を超えている場合のみ登録
                        if scene_duration >= self.min_scene_duration:
                            scene_info = {
                                "timestamp": current_scene_start,
                                "end_time": current_time,
                                "duration": scene_duration,
                                "score": float(score)
                            }
                            scenes.append(scene_info)
                            current_scene_start = current_time
                            logger.debug(f"シーン検出: {current_time:.2f}秒, スコア: {score:.2f}")
                            self.scene_detected.emit(scene_info)
                
                # 現在のフレームを前フレームとして保存
                prev_frame = gray
                frame_idx += 1
                
                # 進捗状況を更新
                if frame_count > 0:
                    progress = int((frame_idx / frame_count) * 100)
                    self.progress_updated.emit(progress)
                    
                    # プログレスダイアログのラベルテキストを更新
                    detected_scenes_count = len(scenes)
                    self.progress_label_updated.emit(f"シーン検出中... ({detected_scenes_count}シーン検出済み)")
                    
                    # ログ出力（10%ごと）
                    if frame_idx % max(1, frame_count // 10) == 0:
                        logger.info(f"シーン検出進捗: {progress:.1f}%")
                        self.log_message.emit(f"シーン検出進捗: {progress:.1f}%")
            
            # 最後のシーンを追加
            if frame_idx > 0 and not self.should_stop:
                last_time = frame_idx / fps
                if last_time - current_scene_start >= self.min_scene_duration:
                    scene_info = {
                        "timestamp": current_scene_start,
                        "end_time": last_time,
                        "duration": last_time - current_scene_start,
                        "score": 0.0
                    }
                    scenes.append(scene_info)
                    self.scene_detected.emit(scene_info)
            
            # リソースの解放
            cap.release()
            
            logger.info(f"シーン検出完了: {len(scenes)}シーンを検出しました")
            self.log_message.emit(f"シーン検出完了: {len(scenes)}シーンを検出しました")
            return scenes
        
        except Exception as e:
            error_msg = f"シーン検出中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return []
    
    def stop(self):
        """処理を停止"""
        self.should_stop = True
        self.log_message.emit("シーン検出を停止しています...")

class SceneAnalyzerWorker(QObject):
    """シーン解析ワーカークラス（バックグラウンドスレッド用）"""
    
    # シグナル定義
    progress_updated = Signal(int)  # 進捗更新シグナル (0-100)
    scene_analyzed = Signal(dict)   # シーン解析シグナル
    analysis_completed = Signal(list)  # 解析完了シグナル（解析されたシーンのリストを返す）
    error_occurred = Signal(str)    # エラーシグナル
    log_message = Signal(str)       # ログメッセージシグナル
    progress_label_updated = Signal(str)  # 進捗ラベル更新シグナル
    
    def __init__(self, scenes, api_key=None, model_name="gemini-2.0-flash", prompt=None, batch_size=5):
        """
        初期化
        
        Args:
            scenes: 解析するシーンのリスト
            api_key: Gemini API Key
            model_name: 使用するモデル名
            prompt: 解析に使用するプロンプト
            batch_size: バッチサイズ
        """
        super().__init__()
        self.scenes = scenes
        self.api_key = api_key
        self.model_name = model_name
        self.prompt = prompt
        self.batch_size = batch_size
        self.should_stop = False
        self.genai_configured = False
    
    @Slot()
    def run(self):
        """ワーカースレッドのメイン処理"""
        try:
            # APIキーが設定されているか確認
            if not self.api_key:
                error_msg = "APIキーが設定されていません。設定ダイアログでAPIキーを設定してください。"
                self.log_message.emit(error_msg)
                self.error_occurred.emit(error_msg)
                self.analysis_completed.emit(self.scenes)
                return
                
            # シーンを解析
            analyzed_scenes = self.analyze_scenes()
            
            # 完了シグナルを発行
            self.analysis_completed.emit(analyzed_scenes)
            
        except Exception as e:
            error_msg = f"シーン解析中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.analysis_completed.emit(self.scenes)
    
    def configure_genai(self, api_key):
        """
        Gemini APIを設定
        
        Args:
            api_key: API Key
            
        Returns:
            bool: 設定が成功したかどうか
        """
        try:
            if not api_key:
                error_msg = "APIキーが空です。設定ダイアログでAPIキーを設定してください。"
                self.log_message.emit(error_msg)
                self.genai_configured = False
                return False
                
            self.log_message.emit(f"Gemini APIを設定します。APIキー: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
            genai.configure(api_key=api_key)
            self.genai_configured = True
            self.log_message.emit("Gemini APIを設定しました")
            return True
        except Exception as e:
            error_msg = f"Gemini APIの設定に失敗しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.genai_configured = False
            return False
    
    def analyze_scenes(self):
        """
        シーンを解析
        
        Returns:
            list: 解析結果を含むシーン情報のリスト
        """
        # APIキーが設定されているか確認
        if not self.api_key:
            error_msg = "APIキーが設定されていません。設定ダイアログでAPIキーを設定してください。"
            logger.error(error_msg)
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            return self.scenes
            
        if not self.genai_configured and self.api_key:
            if not self.configure_genai(self.api_key):
                error_msg = "Gemini APIの設定に失敗しました。APIキーを確認してください。"
                logger.error(error_msg)
                self.log_message.emit(error_msg)
                self.error_occurred.emit(error_msg)
                return self.scenes
        
        if not self.genai_configured:
            error_msg = "Gemini APIが設定されていません。APIキーを設定してください。"
            logger.error(error_msg)
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            return self.scenes
        
        # デフォルトプロンプト
        prompt = self.prompt
        if prompt is None:
            prompt = "この画像に写っているものを一言で説明してください。必ず日本語で回答してください。"
        
        self.log_message.emit(f"シーン解析を開始します。シーン数: {len(self.scenes)}")
        # プロンプトをログに出力（ダークモード対応）
        self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>使用するプロンプト:</b> {prompt}</div>")
        
        self.is_running = True
        self.should_stop = False
        
        try:
            # モデルの生成
            self.log_message.emit(f"モデルを生成します: {self.model_name}")
            model = genai.GenerativeModel(self.model_name)
            self.log_message.emit(f"モデルの生成に成功しました: {self.model_name}")
            
            # 有効なシーンのみを処理
            valid_scenes = []
            for scene in self.scenes:
                frame_path = scene.get('frame_path')
                if frame_path and os.path.exists(frame_path):
                    valid_scenes.append(scene)
                else:
                    if not frame_path:
                        self.log_message.emit(f"警告: シーン {scene.get('id')} のフレーム画像のパスが設定されていません")
                    else:
                        self.log_message.emit(f"警告: フレーム画像が見つかりません: {frame_path}")
            
            if not valid_scenes:
                self.log_message.emit("有効なフレーム画像を持つシーンがありません。シーン解析をスキップします。")
                return self.scenes
            
            self.log_message.emit(f"有効なシーン数: {len(valid_scenes)}/{len(self.scenes)}")
            
            # バッチ処理
            for i in range(0, len(valid_scenes), self.batch_size):
                if self.should_stop:
                    break
                
                batch = valid_scenes[i:i+self.batch_size]
                
                for j, scene in enumerate(batch):
                    if self.should_stop:
                        break
                    
                    try:
                        # 進捗更新
                        progress = int(((i + j) / len(valid_scenes)) * 100)
                        self.progress_updated.emit(progress)
                        
                        # 画像の読み込み
                        frame_path = scene.get('frame_path')
                        self.log_message.emit(f"シーン {i+j+1}/{len(valid_scenes)} を解析中... パス: {frame_path}")
                        
                        # プログレスダイアログのラベルテキストを更新
                        self.progress_label_updated.emit(f"シーン {i+j+1}/{len(valid_scenes)} 解析中...")
                        
                        # 画像の解析
                        image = Image.open(frame_path)
                        
                        # APIリクエスト前にプロンプトとモデル名をログに出力（ダークモード対応）
                        self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>Geminiモデル:</b> {self.model_name}</div>")
                        self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>Geminiに送信するプロンプト:</b> {prompt}</div>")
                        
                        # APIリクエスト
                        response = model.generate_content([prompt, image])
                        
                        # 結果の取得
                        description = response.text
                        
                        # レスポンスの最初の100文字をログに出力（長すぎる場合は省略）（ダークモード対応）
                        log_description = description[:100] + "..." if len(description) > 100 else description
                        self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>Geminiからの応答:</b> {log_description}</div>")
                        
                        # シーン情報の更新
                        scene['description'] = description
                        scene['confidence'] = 1.0  # 信頼度（現在のAPIでは提供されていない）
                        
                        self.scene_analyzed.emit(scene)
                        
                        # 処理速度の調整（API制限対策）
                        time.sleep(0.5)
                    
                    except FileNotFoundError as e:
                        error_msg = f"フレーム画像の読み込みに失敗しました: {frame_path} - {str(e)}"
                        logger.error(error_msg)
                        self.log_message.emit(f"エラー: {error_msg}")
                        scene['description'] = f"解析エラー: フレーム画像の読み込みに失敗しました"
                        scene['confidence'] = 0.0
                    
                    except Exception as e:
                        error_msg = f"シーン {i+j+1} の解析中にエラーが発生しました: {str(e)}"
                        logger.error(error_msg)
                        self.log_message.emit(error_msg)
                        scene['description'] = f"解析エラー: {str(e)}"
                        scene['confidence'] = 0.0
                        
                        # モデルのフォールバック
                        try:
                            if "gemini-2.0" in self.model_name:
                                self.log_message.emit("gemini-1.5-flashモデルに切り替えます...")
                                self.model_name = "gemini-1.5-flash"
                                model = genai.GenerativeModel(self.model_name)
                            elif "gemini-1.5-flash" in self.model_name:
                                self.log_message.emit("gemini-1.5-proモデルに切り替えます...")
                                self.model_name = "gemini-1.5-pro"
                                model = genai.GenerativeModel(self.model_name)
                        except Exception:
                            self.log_message.emit("モデルの切り替えに失敗しました")
            
            self.log_message.emit("シーン解析が完了しました")
            return self.scenes
        
        except Exception as e:
            error_msg = f"シーン解析中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return self.scenes
    
    def stop(self):
        """処理を停止"""
        self.should_stop = True
        self.log_message.emit("シーン解析を停止しています...")

class SceneDetector(QObject):
    """シーン検出クラス"""
    
    # シグナル定義
    progress_updated = Signal(int)  # 進捗更新シグナル (0-100)
    scene_detected = Signal(dict)   # シーン検出シグナル
    detection_completed = Signal()  # 検出完了シグナル
    error_occurred = Signal(str)    # エラーシグナル
    log_message = Signal(str)       # ログメッセージシグナル
    
    def __init__(self, threshold: float = 30.0, min_scene_duration: float = 2.0):
        """
        初期化
        
        Args:
            threshold: シーン検出の閾値（大きいほど検出感度が低下）
            min_scene_duration: 最小シーン長（秒）
        """
        super().__init__()
        self.threshold = threshold
        self.min_scene_duration = min_scene_duration
        self.is_running = False
        self.should_stop = False
    
    def detect_scenes(self, video_path: str, use_cuda: bool = False) -> List[Dict[str, Any]]:
        """
        動画からシーンを検出
        
        Args:
            video_path: 動画ファイルのパス
            use_cuda: CUDAを使用するかどうか
            
        Returns:
            検出されたシーンのリスト
        """
        if not os.path.exists(video_path):
            error_msg = f"動画ファイルが見つかりません: {video_path}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
        
        try:
            # 動画の読み込み
            cap = cv2.VideoCapture(video_path)
            
            # 動画の情報を取得
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps
            
            logger.info(f"動画情報: {frame_count}フレーム, {fps}fps, 長さ: {duration:.2f}秒")
            
            # CUDAの設定
            if use_cuda:
                try:
                    # OpenCVのCUDA機能を有効化（利用可能な場合）
                    if hasattr(cv2, 'cuda'):
                        # CUDA対応デバイスの数を確認
                        cuda_device_count = cv2.cuda.getCudaEnabledDeviceCount()  # type: ignore[attr-defined]
                        if cuda_device_count > 0:
                            cv2.cuda.setDevice(0)  # type: ignore[attr-defined]
                            logger.info(f"CUDA処理を有効化しました（利用可能なデバイス数: {cuda_device_count}）")
                        else:
                            logger.warning("CUDA対応デバイスが見つかりません。CPU処理を使用します。")
                            use_cuda = False
                    else:
                        logger.warning("このOpenCVビルドではCUDAがサポートされていません")
                        use_cuda = False
                except Exception as e:
                    logger.warning(f"CUDA処理の有効化に失敗しました: {str(e)}")
                    use_cuda = False
            
            # シーン検出
            scenes = []
            prev_frame = None
            current_scene_start = 0
            frame_idx = 0
            
            self.is_running = True
            self.should_stop = False
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # グレースケールに変換
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # フレーム間の差分を計算
                    if use_cuda and hasattr(cv2, 'cuda'):
                        # CUDA処理（高速）
                        try:
                            # CUDA機能が利用可能かどうかを実行時に確認
                            cuda_device = cv2.cuda.getCudaEnabledDeviceCount()
                            if cuda_device > 0:
                                prev_gpu = cv2.cuda.GpuMat()
                                prev_gpu.upload(prev_frame)
                                curr_gpu = cv2.cuda.GpuMat()
                                curr_gpu.upload(gray)
                                # 型チェックエラーを抑制
                                diff_gpu = cv2.cuda.absdiff(prev_gpu, curr_gpu)  # type: ignore[attr-defined]
                                diff = diff_gpu.download()
                            else:
                                # CUDA対応デバイスがない場合はCPU処理にフォールバック
                                diff = cv2.absdiff(prev_frame, gray)
                        except Exception as e:
                            logger.warning(f"CUDA処理中にエラーが発生しました: {str(e)}、CPU処理にフォールバックします")
                            diff = cv2.absdiff(prev_frame, gray)
                    else:
                        # CPU処理
                        diff = cv2.absdiff(prev_frame, gray)
                    
                    # 差分の平均値を計算
                    score = np.mean(diff)
                    
                    # 閾値を超えた場合、シーンの境界と判断
                    if score > self.threshold:
                        current_time = frame_idx / fps
                        scene_duration = current_time - current_scene_start
                        
                        # 最小シーン長を超えている場合のみ登録
                        if scene_duration >= self.min_scene_duration:
                            scenes.append({
                                "start_time": current_scene_start,
                                "end_time": current_time,
                                "duration": scene_duration,
                                "score": float(score)
                            })
                            current_scene_start = current_time
                            logger.debug(f"シーン検出: {current_time:.2f}秒, スコア: {score:.2f}")
                
                # 現在のフレームを前フレームとして保存
                prev_frame = gray
                frame_idx += 1
                
                # 進捗状況を表示（10%ごと）
                if frame_count > 0 and frame_idx % max(1, frame_count // 10) == 0:
                    progress = (frame_idx / frame_count) * 100
                    logger.info(f"シーン検出進捗: {progress:.1f}%")
            
            # 最後のシーンを追加
            if frame_idx > 0:
                last_time = frame_idx / fps
                if last_time - current_scene_start >= self.min_scene_duration:
                    scenes.append({
                        "start_time": current_scene_start,
                        "end_time": last_time,
                        "duration": last_time - current_scene_start,
                        "score": 0.0
                    })
            
            # リソースの解放
            cap.release()
            
            logger.info(f"シーン検出完了: {len(scenes)}シーンを検出しました")
            return scenes
        
        except Exception as e:
            error_msg = f"シーン検出中にエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
    
    def extract_keyframes(self, video_path: str, scenes: List[Dict[str, Any]], output_dir: str) -> List[str]:
        """
        各シーンのキーフレームを抽出する
        
        Args:
            video_path: 動画ファイルのパス
            scenes: 検出されたシーンのリスト
            output_dir: キーフレームの出力先ディレクトリ
        
        Returns:
            抽出されたキーフレームのパスのリスト
        """
        if not os.path.exists(video_path):
            logger.error(f"動画ファイルが見つかりません: {video_path}")
            return []
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 動画の読み込み
            cap = cv2.VideoCapture(video_path)
            
            # 動画の情報を取得
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 各シーンのキーフレームを抽出
            keyframe_paths = []
            
            for i, scene in enumerate(scenes):
                # シーンの中央時間を計算
                mid_time = (scene["start_time"] + scene["end_time"]) / 2
                
                # 指定した時間にシーク
                cap.set(cv2.CAP_PROP_POS_MSEC, mid_time * 1000)
                
                # フレームの読み込み
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"フレームの読み込みに失敗しました: シーン {i+1}")
                    continue
                
                # キーフレームの保存
                keyframe_path = os.path.join(output_dir, f"scene_{i+1:04d}.jpg")
                cv2.imwrite(keyframe_path, frame)
                keyframe_paths.append(keyframe_path)
                
                logger.debug(f"キーフレーム抽出: シーン {i+1}, 時間: {mid_time:.2f}秒")
            
            # リソースの解放
            cap.release()
            
            logger.info(f"キーフレーム抽出完了: {len(keyframe_paths)}枚のキーフレームを抽出しました")
            return keyframe_paths
        
        except Exception as e:
            logger.error(f"キーフレーム抽出中にエラーが発生しました: {str(e)}")
            return []
    
    def set_detection_parameters(self, threshold: float, min_scene_duration: float):
        """
        検出パラメータを設定する
        
        Args:
            threshold: シーン検出の閾値
            min_scene_duration: 最小シーン長（秒）
        """
        self.threshold = threshold
        self.min_scene_duration = min_scene_duration
        logger.info(f"検出パラメータを更新しました: 閾値={threshold}, 最小シーン長={min_scene_duration}秒")
    
    def stop(self):
        """処理を停止"""
        self.should_stop = True
        self.log_message.emit("シーン検出を停止しています...")


class SceneAnalyzer(QObject):
    """シーン解析クラス"""
    
    # シグナル定義
    progress_updated = Signal(int)  # 進捗更新シグナル (0-100)
    scene_analyzed = Signal(dict)   # シーン解析シグナル
    analysis_completed = Signal()   # 解析完了シグナル
    error_occurred = Signal(str)    # エラーシグナル
    log_message = Signal(str)       # ログメッセージシグナル
    
    def __init__(self, api_key=None, model_name="gemini-2.0-flash"):
        """
        初期化
        
        Args:
            api_key (str, optional): Google Gemini API キー
            model_name (str, optional): 使用するモデル名
        """
        super().__init__()
        self.api_key = api_key
        self.model_name = model_name
        self.is_running = False
        self.should_stop = False
        self.genai_configured = False
    
    def configure_genai(self, api_key):
        """
        Google Gemini APIの設定
        
        Args:
            api_key (str): API キー
            
        Returns:
            bool: 設定が成功したかどうか
        """
        try:
            genai.configure(api_key=api_key)
            self.api_key = api_key
            self.genai_configured = True
            return True
        except Exception as e:
            error_msg = f"Gemini API設定エラー: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def analyze_scenes(self, scenes, prompt=None, batch_size=5):
        """
        シーンを解析
        
        Args:
            scenes (list): 解析するシーン情報のリスト
            prompt (str, optional): 解析に使用するプロンプト
            batch_size (int, optional): バッチサイズ
            
        Returns:
            list: 解析結果を含むシーン情報のリスト
        """
        # APIキーが設定されているか確認
        if not self.api_key:
            error_msg = "APIキーが設定されていません。設定ダイアログでAPIキーを設定してください。"
            logger.error(error_msg)
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            return scenes
            
        if not self.genai_configured and self.api_key:
            if not self.configure_genai(self.api_key):
                error_msg = "Gemini APIの設定に失敗しました。APIキーを確認してください。"
                logger.error(error_msg)
                self.log_message.emit(error_msg)
                self.error_occurred.emit(error_msg)
                return scenes
        
        if not self.genai_configured:
            error_msg = "Gemini APIが設定されていません。APIキーを設定してください。"
            logger.error(error_msg)
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            return scenes
        
        # デフォルトプロンプト
        if prompt is None:
            prompt = "この画像に写っているものを一言で説明してください。必ず日本語で回答してください。"
        
        self.log_message.emit(f"シーン解析を開始します。シーン数: {len(scenes)}")
        # プロンプトをログに出力（ダークモード対応）
        self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>使用するプロンプト:</b> {prompt}</div>")
        
        self.is_running = True
        self.should_stop = False
        
        try:
            # モデルの生成
            self.log_message.emit(f"モデルを生成します: {self.model_name}")
            model = genai.GenerativeModel(self.model_name)
            self.log_message.emit(f"モデルの生成に成功しました: {self.model_name}")
            
            # バッチ処理
            for i in range(0, len(scenes), batch_size):
                if self.should_stop:
                    break
                
                batch = scenes[i:i+batch_size]
                
                for j, scene in enumerate(batch):
                    if self.should_stop:
                        break
                    
                    try:
                        # 進捗更新
                        progress = int(((i + j) / len(scenes)) * 100)
                        self.progress_updated.emit(progress)
                        
                        # 画像の読み込み
                        frame_path = scene.get('frame_path')
                        if not frame_path:
                            logger.warning(f"フレーム画像のパスが設定されていません: {scene.get('id')}")
                            self.log_message.emit(f"警告: シーン {scene.get('id')} のフレーム画像のパスが設定されていません")
                            continue
                        
                        if not os.path.exists(frame_path):
                            logger.warning(f"フレーム画像が見つかりません: {frame_path}")
                            self.log_message.emit(f"警告: フレーム画像が見つかりません: {frame_path}")
                            continue
                        
                        self.log_message.emit(f"シーン {i+j+1}/{len(scenes)} を解析中... パス: {frame_path}")
                        
                        try:
                            # 画像の解析
                            image = Image.open(frame_path)
                            
                            # APIリクエスト前にプロンプトとモデル名をログに出力（ダークモード対応）
                            self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>Geminiモデル:</b> {self.model_name}</div>")
                            self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>Geminiに送信するプロンプト:</b> {prompt}</div>")
                            
                            # APIリクエスト
                            response = model.generate_content([prompt, image])
                            
                            # 結果の取得
                            description = response.text
                            
                            # レスポンスの最初の100文字をログに出力（長すぎる場合は省略）（ダークモード対応）
                            log_description = description[:100] + "..." if len(description) > 100 else description
                            self.log_message.emit(f"<div style='color: #e0e0e0; font-weight: bold; background-color: #333333; padding: 5px; border-left: 3px solid #666666;'><b>Geminiからの応答:</b> {log_description}</div>")
                            
                            # シーン情報の更新
                            scene['description'] = description
                            scene['confidence'] = 1.0  # 信頼度（現在のAPIでは提供されていない）
                            
                            self.scene_analyzed.emit(scene)
                            
                            # 処理速度の調整（API制限対策）
                            time.sleep(0.5)
                        
                        except FileNotFoundError as e:
                            error_msg = f"フレーム画像の読み込みに失敗しました: {frame_path} - {str(e)}"
                            logger.error(error_msg)
                            self.log_message.emit(f"エラー: {error_msg}")
                        
                        except Exception as e:
                            error_msg = f"シーン解析中にエラーが発生しました: {str(e)}"
                            logger.error(error_msg)
                            self.error_occurred.emit(error_msg)
                            
                            # モデルのフォールバック
                            if "gemini-2.0" in self.model_name:
                                self.log_message.emit("gemini-1.5-flashモデルに切り替えます...")
                                self.model_name = "gemini-1.5-flash"
                                model = genai.GenerativeModel(self.model_name)
                            elif "gemini-1.5-flash" in self.model_name:
                                self.log_message.emit("gemini-1.5-proモデルに切り替えます...")
                                self.model_name = "gemini-1.5-pro"
                                model = genai.GenerativeModel(self.model_name)
                            else:
                                # これ以上のフォールバックはなし
                                raise
                    
                    except Exception as e:
                        error_msg = f"シーン {i+j+1} の解析中にエラーが発生しました: {str(e)}"
                        logger.error(error_msg)
                        self.error_occurred.emit(error_msg)
            
        except Exception as e:
            error_msg = f"シーン解析でエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        
        finally:
            self.is_running = False
            
            if self.should_stop:
                self.log_message.emit("シーン解析が中断されました")
            else:
                self.log_message.emit("シーン解析が完了しました")
                self.analysis_completed.emit()
            
            return scenes
    
    def stop(self):
        """処理を停止"""
        self.should_stop = True
        self.log_message.emit("シーン解析を停止しています...")


class SceneSession(QObject):
    """シーンセッション管理クラス"""
    
    # シグナル定義
    progress_updated = Signal(int, str)  # 進捗更新シグナル (0-100, タイプ)
    session_completed = Signal(int)      # セッション完了シグナル (session_id)
    error_occurred = Signal(str)         # エラーシグナル
    log_message = Signal(str)            # ログメッセージシグナル
    
    def __init__(self, database, detector=None, analyzer=None):
        """
        初期化
        
        Args:
            database: データベースインスタンス
            detector (SceneDetector, optional): シーン検出インスタンス
            analyzer (SceneAnalyzer, optional): シーン解析インスタンス
        """
        super().__init__()
        self.database = database
        
        # シーン検出器の初期化
        self.detector = detector or SceneDetector()
        self.detector.progress_updated.connect(lambda p: self.progress_updated.emit(p, 'detection'))
        self.detector.scene_detected.connect(self._on_scene_detected)
        self.detector.error_occurred.connect(self.error_occurred)
        self.detector.log_message.connect(self.log_message)
        
        # シーン解析器の初期化
        self.analyzer = analyzer or SceneAnalyzer()
        self.analyzer.progress_updated.connect(lambda p: self.progress_updated.emit(p, 'analysis'))
        self.analyzer.scene_analyzed.connect(self._on_scene_analyzed)
        self.analyzer.error_occurred.connect(self.error_occurred)
        self.analyzer.log_message.connect(self.log_message)
        
        # セッション情報
        self.current_session_id = None
        self.detected_scenes = []
    
    def start_session(self, video_path, session_name, detection_threshold=None, min_scene_duration=None, 
                     api_key=None, prompt=None, batch_size=None):
        """
        セッションを開始
        
        Args:
            video_path (str): 動画ファイルのパス
            session_name (str): セッション名
            detection_threshold (float, optional): 検出感度（Noneの場合はデータベースから取得）
            min_scene_duration (float, optional): 最小シーン長（秒）（Noneの場合はデータベースから取得）
            api_key (str, optional): Gemini API キー（Noneの場合はデータベースから取得）
            prompt (str, optional): 解析プロンプト（Noneの場合はデフォルト値を使用）
            batch_size (int, optional): バッチサイズ（Noneの場合はデータベースから取得）
            
        Returns:
            int: セッションID
        """
        try:
            # 設定値がNoneの場合はデータベースから取得
            if detection_threshold is None:
                detection_threshold = float(self.database.get_setting("scene_detection.threshold", "0.3"))
                logger.info(f"データベースから検出閾値を取得しました: {detection_threshold}")
            
            if min_scene_duration is None:
                min_scene_duration = float(self.database.get_setting("scene_detection.min_scene_duration", "2.0"))
                logger.info(f"データベースから最小シーン長を取得しました: {min_scene_duration}")
            
            if api_key is None:
                api_key = self.database.get_setting("analysis.api_key", "")
                if api_key:
                    logger.info(f"データベースからAPIキーを取得しました: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
            
            if batch_size is None:
                batch_size = int(self.database.get_setting("analysis.batch_size", "5"))
                logger.info(f"データベースからバッチサイズを取得しました: {batch_size}")
            
            # 動画情報の取得
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                error_msg = f"動画ファイルを開けませんでした: {video_path}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return None
            
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            # 動画をデータベースに追加
            video_id = self.database.add_video(video_path, duration)
            
            # セッションを作成
            self.current_session_id = self.database.create_session(
                video_id, session_name, detection_threshold, min_scene_duration
            )
            
            # シーン検出器の設定
            self.detector.threshold = detection_threshold
            self.detector.min_scene_duration = min_scene_duration
            
            # シーン解析器の設定
            if api_key:
                self.analyzer.configure_genai(api_key)
            
            # 出力ディレクトリの設定
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = os.path.join(os.path.expanduser("~"), ".scene_analyzer", "sessions", 
                                      f"session_{self.current_session_id}_{timestamp}")
            os.makedirs(session_dir, exist_ok=True)
            
            # シーン検出を開始
            self.log_message.emit(f"セッション '{session_name}' を開始します")
            self.detected_scenes = self.detector.detect_scenes(video_path, True)
            
            # シーン解析を開始
            if self.detected_scenes and not self.detector.should_stop:
                self.analyzer.analyze_scenes(self.detected_scenes, prompt, batch_size)
            
            # セッション完了
            if not self.detector.should_stop and not self.analyzer.should_stop:
                self.log_message.emit(f"セッション '{session_name}' が完了しました")
                self.session_completed.emit(self.current_session_id)
            
            return self.current_session_id
        
        except Exception as e:
            error_msg = f"セッション開始エラー: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def stop_session(self):
        """セッションを停止"""
        self.detector.stop()
        self.analyzer.stop()
        self.log_message.emit("セッションを停止しています...")
    
    def _on_scene_detected(self, scene_info):
        """シーン検出時のコールバック"""
        if self.current_session_id:
            # データベースにシーンを追加（解析前）
            self.database.add_scene(
                self.current_session_id,
                scene_info['timestamp'],
                scene_info['duration'],
                scene_info['frame_path']
            )
    
    def _on_scene_analyzed(self, scene_info):
        """シーン解析時のコールバック"""
        if self.current_session_id:
            # データベースのシーン情報を更新
            # 注: 実際の実装ではシーンIDを保持して更新する必要があります
            # ここでは簡略化のため、タイムスタンプで検索して更新する例を示します
            scenes = self.database.get_scenes_for_session(self.current_session_id)
            for scene in scenes:
                if abs(scene['timestamp'] - scene_info['timestamp']) < 0.1:  # 0.1秒の誤差を許容
                    # シーンの更新処理（実際にはデータベースクラスに更新メソッドを追加する必要があります）
                    # ここでは簡略化のためコメントアウト
                    # self.database.update_scene(scene['id'], description=scene_info['description'], confidence=scene_info['confidence'])
                    break 

class KeyframeExtractorWorker(QObject):
    """キーフレーム抽出ワーカークラス（バックグラウンドスレッド用）"""
    
    # シグナル定義
    progress_updated = Signal(int)  # 進捗更新シグナル (0-100)
    keyframe_extracted = Signal(dict)  # キーフレーム抽出シグナル
    extraction_completed = Signal(list)  # 抽出完了シグナル（抽出されたキーフレームのリストを返す）
    error_occurred = Signal(str)    # エラーシグナル
    log_message = Signal(str)       # ログメッセージシグナル
    
    def __init__(self, video_path: str, scenes: List[Dict[str, Any]], output_dir: str):
        """
        初期化
        
        Args:
            video_path: 動画ファイルのパス
            scenes: 検出されたシーンのリスト
            output_dir: キーフレームの出力先ディレクトリ
        """
        super().__init__()
        self.video_path = video_path
        self.scenes = scenes
        self.output_dir = output_dir
        self.should_stop = False
    
    @Slot()
    def run(self):
        """ワーカースレッドのメイン処理"""
        try:
            extracted_scenes = self.extract_keyframes()
            self.extraction_completed.emit(extracted_scenes)
        except Exception as e:
            error_msg = f"キーフレーム抽出中にエラーが発生しました: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
    
    def extract_keyframes(self) -> List[Dict[str, Any]]:
        """
        各シーンのキーフレームを抽出する
        
        Returns:
            抽出されたキーフレーム情報を含むシーンのリスト
        """
        if not os.path.exists(self.video_path):
            error_msg = f"動画ファイルが見つかりません: {self.video_path}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        
        try:
            # 動画の読み込み
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                error_msg = f"動画ファイルを開けませんでした: {self.video_path}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return []
            
            # 動画の情報を取得
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 各シーンのキーフレームを抽出
            updated_scenes = []
            
            for i, scene in enumerate(self.scenes):
                # 停止フラグがセットされていたら処理を中断
                if self.should_stop:
                    logger.info("キーフレーム抽出を中断しました")
                    self.log_message.emit("キーフレーム抽出を中断しました")
                    break
                
                # 進捗を更新
                progress = int((i / len(self.scenes)) * 100)
                self.progress_updated.emit(progress)
                
                try:
                    # シーンの中央時間を計算
                    scene_start = scene.get("timestamp", 0)
                    scene_duration = scene.get("duration", 0)
                    mid_time = scene_start + (scene_duration / 2)
                    
                    # 指定した時間にシーク
                    cap.set(cv2.CAP_PROP_POS_MSEC, mid_time * 1000)
                    
                    # フレームの読み込み
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning(f"フレームの読み込みに失敗しました: シーン {i+1}")
                        self.log_message.emit(f"警告: フレームの読み込みに失敗しました: シーン {i+1}, 時間: {mid_time:.2f}秒")
                        continue
                    
                    # キーフレームの保存
                    frame_filename = f"scene_{scene.get('id', i+1)}.jpg"
                    frame_path = os.path.join(self.output_dir, frame_filename)
                    
                    # フレームを保存
                    success = cv2.imwrite(frame_path, frame)
                    if not success:
                        logger.warning(f"フレームの保存に失敗しました: {frame_path}")
                        self.log_message.emit(f"警告: フレームの保存に失敗しました: {frame_path}")
                        
                        # 別の形式で保存を試みる
                        alt_frame_path = frame_path.replace(".jpg", ".png")
                        self.log_message.emit(f"別の形式で保存を試みます: {alt_frame_path}")
                        alt_success = cv2.imwrite(alt_frame_path, frame)
                        
                        if alt_success:
                            self.log_message.emit(f"代替形式でフレームを保存しました: {alt_frame_path}")
                            frame_path = alt_frame_path
                        else:
                            self.log_message.emit(f"エラー: 代替形式でも保存に失敗しました")
                            continue
                    
                    # 絶対パスに変換
                    abs_frame_path = os.path.abspath(frame_path)
                    
                    # シーン情報を更新
                    scene_copy = scene.copy()
                    scene_copy["frame_path"] = abs_frame_path
                    updated_scenes.append(scene_copy)
                    
                    # シグナルを発行
                    self.keyframe_extracted.emit(scene_copy)
                    
                    logger.debug(f"キーフレーム抽出: シーン {i+1}, 時間: {mid_time:.2f}秒, パス: {abs_frame_path}")
                    self.log_message.emit(f"キーフレーム抽出: シーン {i+1}/{len(self.scenes)}, 時間: {mid_time:.2f}秒, パス: {abs_frame_path}")
                    
                except Exception as e:
                    logger.error(f"シーン {i+1} のキーフレーム抽出中にエラーが発生しました: {str(e)}", exc_info=True)
                    self.log_message.emit(f"エラー: シーン {i+1} のキーフレーム抽出中にエラーが発生しました: {str(e)}")
            
            # リソースの解放
            cap.release()
            
            # 進捗を100%に設定
            self.progress_updated.emit(100)
            
            logger.info(f"キーフレーム抽出完了: {len(updated_scenes)}/{len(self.scenes)}シーンのキーフレームを抽出しました")
            self.log_message.emit(f"キーフレーム抽出完了: {len(updated_scenes)}/{len(self.scenes)}シーンのキーフレームを抽出しました")
            
            return updated_scenes
            
        except Exception as e:
            logger.error(f"キーフレーム抽出中にエラーが発生しました: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"キーフレーム抽出中にエラーが発生しました: {str(e)}")
            return []
    
    def stop(self):
        """処理を停止する"""
        self.should_stop = True
        self.log_message.emit("キーフレーム抽出を停止しています...") 