# Scene Analyzer リリースビルド作成手順

このドキュメントでは、Scene Analyzerのリリースビルドを作成する手順を説明します。

## 前提条件

リリースビルドを作成するには、以下のソフトウェアが必要です：

1. **Python 3.6以上**
2. **PyInstaller**：`pip install pyinstaller`
3. **Inno Setup 6**：[ダウンロードページ](https://jrsoftware.org/isdl.php)からダウンロードしてインストール
4. **Windows SDK**：コード署名ツール（signtool.exe）を使用するために必要

### Windows SDKのインストール

1. [Windows SDK ダウンロードページ](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)にアクセス
2. 「Windows SDK をダウンロード」ボタンをクリック
3. ダウンロードしたインストーラーを実行
4. インストールオプションで、少なくとも「Windows SDK Signing Tools for Desktop Apps」を選択
5. インストール完了後、以下のコマンドでsigntoolが利用可能か確認：
   ```
   where signtool
   ```

## ビルド手順

### 方法1：自動ビルド（推奨）

1. 管理者権限でコマンドプロンプトを開く
2. プロジェクトのルートディレクトリに移動
3. 初回のみ、以下のコマンドを実行してspec ファイルを作成：
   ```
   create_spec.bat
   ```
4. 以下のコマンドを実行してビルドを開始：
   ```
   build_release.bat
   ```
5. 画面の指示に従ってビルドを完了

### 方法2：手動ビルド

#### ステップ1：PyInstaller Spec ファイルの作成

1. 管理者権限でコマンドプロンプトを開く
2. プロジェクトのルートディレクトリに移動
3. 以下のコマンドを実行：
   ```
   create_spec.bat
   ```
4. 必要に応じて、生成された `scene_analyzer.spec` ファイルを編集

#### ステップ2：Windows Defenderの除外設定とビルド

1. 管理者権限でコマンドプロンプトを開く
2. プロジェクトのルートディレクトリに移動
3. 以下のコマンドを実行：
   ```
   build_with_defender_exclusion.bat
   ```

#### ステップ3：実行ファイルにデジタル署名を追加

1. 以下のコマンドを実行：
   ```
   sign_executable.bat
   ```
2. 画面の指示に従って署名を完了

#### ステップ4：インストーラーの作成

1. Inno Setupがインストールされていることを確認
2. 以下のコマンドを実行：
   ```
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" create_installer.iss
   ```
3. 生成されたインストーラーは `installer` ディレクトリに保存されます

## 各スクリプトの説明

| スクリプト名 | 説明 |
|-------------|------|
| `create_spec.bat` | PyInstallerのspec ファイルを作成します。アプリケーションのビルド設定を定義します。 |
| `build_with_defender_exclusion.bat` | Windows Defenderの除外設定を追加し、PyInstallerでビルドを実行します。 |
| `sign_executable.bat` | ビルドされた実行ファイルにデジタル署名を追加します。 |
| `build_release.bat` | 上記のスクリプトを順番に実行し、インストーラーの作成まで行う統合スクリプトです。 |

## トラブルシューティング

### Windows Defenderによる削除

ビルドされた実行ファイルがWindows Defenderによって削除される場合：

1. `build_with_defender_exclusion.bat` を実行して、ビルドディレクトリをWindows Defenderの除外リストに追加
2. デジタル署名を追加するために `sign_executable.bat` を実行

### デジタル署名エラー

signtoolでエラーが発生する場合：

1. Windows SDKが正しくインストールされていることを確認
2. 管理者権限でコマンドプロンプトを実行していることを確認
3. 有効なコード署名証明書を使用していることを確認

### インストーラー作成エラー

Inno Setupでエラーが発生する場合：

1. Inno Setup 6が正しくインストールされていることを確認
2. `create_installer.iss` ファイルの構文エラーを確認

### PyInstallerのエラー

PyInstallerでエラーが発生する場合：

1. PyInstallerが最新バージョンであることを確認：`pip install --upgrade pyinstaller`
2. 必要な依存関係がすべてインストールされていることを確認
3. `scene_analyzer.spec` ファイルの `hiddenimports` リストに不足しているモジュールを追加

## 配布方法

リリースビルドの配布方法は以下の通りです：

1. **インストーラー配布**（推奨）：
   - `installer/SceneAnalyzer_Setup_1.0.0.exe` を配布
   - ユーザーはインストーラーを実行してアプリケーションをインストール可能

2. **スタンドアロン配布**：
   - `dist/SceneAnalyzer` ディレクトリ全体をZIPファイルなどで圧縮して配布
   - ユーザーは解凍後に `SceneAnalyzer.exe` を実行するだけで利用可能

## 注意事項

- デジタル署名されていないアプリケーションは、Windows SmartScreenによって警告が表示される場合があります
- 自己署名証明書を使用した場合、ユーザーは初回実行時に警告を受け取る可能性があります
- 商用配布の場合は、信頼された認証局から取得した証明書を使用することを強く推奨します
- アプリケーションデータは `%USERPROFILE%\.scene_analyzer` に保存されます。アンインストール時に完全に削除したい場合は、このディレクトリを手動で削除する必要があります 