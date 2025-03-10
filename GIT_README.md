# Gitリポジトリの使い方

このリポジトリは、シーンアナライザーのソースコードを管理するためのものです。APIキーやビルド関連のファイルは除外されています。

## 除外されているファイル

以下のファイルやディレクトリはGitリポジトリから除外されています：

- ビルド関連ファイル（`build/`, `dist/`, `*.spec`, `*.exe`, `*.bat`など）
- インストーラー関連ファイル（`installer/`）
- APIキーや秘密情報（`*.pfx`, `*.pem`, `*.key`, `*.p12`など）
- ローカル設定（`.vscode/`, `.idea/`など）
- サンプルファイル（`sample.mp4`）
- データベースファイル（`*.db`, `*.sqlite`など）
- ログファイル（`*.log`）
- バックアップファイル（`*~`, `*.bak`）
- 仮想環境（`.venv/`, `venv/`など）

## APIキーの扱い

このアプリケーションはGoogle Gemini APIを使用しています。APIキーはローカルのデータベースに保存され、Gitリポジトリには含まれません。

### APIキーの設定方法

1. アプリケーションの設定ダイアログでAPIキーを入力します。
2. APIキーはローカルのデータベースに暗号化されて保存されます。
3. APIキーはGitリポジトリにはコミットされません。

### 開発環境でのAPIキーの扱い

開発環境でAPIキーを使用する場合は、以下の方法で設定してください：

1. アプリケーションを起動し、設定ダイアログでAPIキーを入力します。
2. または、環境変数として設定することもできます（`GEMINI_API_KEY`）。

## 新しい環境でのセットアップ

新しい環境でこのリポジトリをクローンした後、以下の手順でセットアップしてください：

1. リポジトリをクローンします。

```bash
git clone <リポジトリURL>
cd <リポジトリディレクトリ>
```

2. 仮想環境を作成し、有効化します。

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

3. 必要なパッケージをインストールします。

```bash
pip install -r requirements.txt
```

4. アプリケーションを起動します。

```bash
python -m scene_analyzer
```

5. 設定ダイアログでAPIキーを設定します。

## コミット時の注意点

コミットする前に、以下の点を確認してください：

1. APIキーや秘密情報が含まれていないこと
2. ビルド関連のファイルが含まれていないこと
3. 大きなサンプルファイルが含まれていないこと

## ビルド方法

ビルドスクリプトはGitリポジトリに含まれていませんが、以下の手順でビルドできます：

1. PyInstallerをインストールします。

```bash
pip install pyinstaller
```

2. 以下のコマンドでビルドします。

```bash
pyinstaller --name SceneAnalyzer --windowed --icon=icon.ico --add-data "scene_analyzer/ui/resources;scene_analyzer/ui/resources" scene_analyzer/__main__.py
```

詳細なビルド手順については、`RELEASE.md`ファイルを参照してください。 