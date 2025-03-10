# 動画プレイヤー兼、動画シーン検出・解析アプリケーション要件定義

## 1. システム概要
動画プレイヤーに、動画ファイルからシーンを自動検出し、各シーンの内容をAIで解析して結果を表示・管理するデスクトップアプリケーション。

### 1.1 技術スタック
- OS: Windows
- 言語: Python、Qt5、Windows MediaFooundation　禁止事項：DirectShow、VLCやK-liteCodecPackなどは使用禁止
- GUI: PyQt5 (Qt),　MediaFoundation使用すること必須ルール, GUIはHiDPI対応必須、メッセージウィンドウやボタン、メニュ含む表示する文字列全般もHiDPI対応すること。またモダンアプリケーションUIを目指すこと。
- 画像処理: OpenCV
- 画像解析: Google Gemini API model: gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro　
要厳守ルール：Gemini APIでエラーになったとき、すぐGemini-pro-visionやGemini1.0などここに記載されているモデルより古いモデルへ変更することは禁止します
- データ保存: SQLite, JSON

## 2. 機能要件

### 2.1 動画入力
- 対応フォーマット: H.264/MP4
- ドラッグ＆ドロップによるファイル入力対応
- Openボタンからの読み込み　（すでに解析済みのシーン検出＆解析セッションデータがある動画を読み込んだ場合は、シーンパネル上部にあるセッションデータ選択プルダウンメニューから、セッションを選択して表示できる）

### 2.2 シーン検出とシーン解析
- シーン検出とシーン解析はセッションとして処理する、一つの動画に複数のセッションを保持することが可能
- セッション開始時、シーン検出＆解析ボタンでセッション開始するとき、ダイアログを表示し、セッション名、各パラメータを設定編集可能



### 2.3 シーン解析＆シーン解析　パラメータなど
- OpenCV + 高速シーン検出
- 調整可能なパラメータ:
  - 検出感度
  - 最小シーン長

- シーン検出で検出シーンの先頭フレームをキャプチャ
- Gemini APIによる画像内容の解析
- Gemini APIへ渡すプロンプトは、設定画面であらかじめ作成したものから選択可能
- 解析結果とシーンの紐付けし、セッションとしてデータベース保存

### 2.4 GUI表示
- 動画プレーヤー
- 動画プレビューの右サイドパネル、シーンリスト表示（サムネイル、タイムコード、解析コメント）
- 再生位置に応じたシーンハイライト
- 進捗表示:
  - シーン検出の進捗バー
  - 画像解析の進捗バー
  - 処理ログ表示

### 2.5 データ管理
- 動画ファイル　シーン検出とシーン解析はセッションとして複数保持可能
- 解析結果の永続化（SQLite）
- エクスポート機能:
  - JSON形式
  - CSV形式
- 設定の保存（JSON）

### 2.6 設定画面
- 別ウィンドウでの表示
- 設定項目:
  - シーン検出感度
  - 最小シーン長
  - バッチサイズ
  - 信頼度閾値
  - Gemini　プロンプト　（プルダウンで選択可能、カスタムプロンプトを追加可能）
  - Gemini API Key (ユーザーにAPI-Keyは入力してもらう)
  - エクスポートパス
- デフォルト値へのリセット機能
- データベースのクリア機能

## 3. 非機能要件

### 3.1 パフォーマンス
- 効率的なメモリ管理
- マルチスレッド処理の最適化

### 3.2 エラー処理
- 詳細なエラーログの表示
- エラー発生時のユーザー通知
- 処理の中断・再開機能

### 3.3 ユーザビリティ
- 直感的なGUIレイアウト
- リアルタイムの進捗表示
- キーボードショートカット対応

## 4. データ構造

### 4.1 データベース設計
sql
CREATE TABLE videos (
id INTEGER PRIMARY KEY,
file_path TEXT,
duration REAL,
created_at TIMESTAMP
);
CREATE TABLE scenes (
id INTEGER PRIMARY KEY,
video_id INTEGER,
timestamp REAL,
duration REAL,
frame_path TEXT,
description TEXT,
confidence REAL,
FOREIGN KEY (video_id) REFERENCES videos(id)
);
json
{
"scene_detection": {
"threshold": 0.3,
"min_scene_duration": 2.0,
"cuda_device_id": 0
},
"analysis": {
"batch_size": 10,
"confidence_threshold": 0.7
},
"export": {
"default_path": "./exports",
"format": "json"
}
}

### 4.2 設定ファイル構造
json
{
"scene_detection": {
"threshold": 0.3,
"min_scene_duration": 2.0,
"cuda_device_id": 0
},
"analysis": {
"batch_size": 10,
"confidence_threshold": 0.7
},
"export": {
"default_path": "./exports",
"format": "json"
}
}

## 5. 制約事項
- 対応OS: Windows11
- 必要メモリ: 8GB以上推奨
- GPU: CUDA対応NVIDIAグラフィックスカード必須
- ストレージ: キャプチャ画像保存用の十分な空き容量

## 6. 将来の拡張性
- 追加の動画フォーマット対応
- 異なる画像解析APIへの対応
- バッチ処理機能の追加
- シーン編集機能の追加


このRequirements.mdは、これまでの議論を整理し、アプリケーションの要件を包括的にまとめたものです。開発チームの新規参加者やステークホルダーとの共有に活用できます。
追加や修正が必要な項目はございますか？

# Scene Analyzer - インストール手順

## 必要要件
- Windows 10/11 (64bit)
- Python 3.8以上（開発時のみ）

## インストール手順

### 1. Scene Analyzerのインストール
1. インストーラーを実行
2. 画面の指示に従ってインストール
3. インストール完了後、アプリケーションを起動


