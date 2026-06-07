# IrodoriTTS Studio Custom Web UI

FastAPI + HTML/CSS/JS によるカスタムWeb UIです。

IrodoriTTSをブラウザから操作し、台本入力、チャンク分割、プロジェクト保存、音声生成を行うためのUIです。

## 起動コマンド

リポジトリ直下で実行してください。

Windows / Colab 共通:

```bash
python -m app.api_server
```

## ブラウザ

ローカル環境では、以下を開きます。

```text
http://localhost:7860
```

Colabで使う場合も、`irodori-tts-studio` のリポジトリ直下に移動してから実行してください。

例:

```bash
cd /content/irodori-tts-studio
python -m app.api_server
```

Colabでは、実行環境に応じて外部公開URLを開いて使用します。

## 現段階

- JSON書き出し
- JSON読み込み
- チャンク分割プレビュー
- プロジェクト保存
- Web UIから本生成API `/api/generate` を呼び出し
- 生成開始ログ表示
- 生成中の経過ログ表示
- 生成ボタンの連打防止
- WAV生成確認
- 生成WAVのWeb UI上での試聴・ダウンロード表示
- MP3は自動生成せず、必要な場合に変換する方針

## 今後の候補

- MP3任意変換ボタン
- 結合後音声のMP3変換
- 生成チャンクの管理UI改善
- 参照音声アップロード導線の改善
- 生成中断ボタンの本実装
- Colab環境での起動手順とエラー対処の整理

## 注意

このWeb UIは開発中です。

ローカルPC環境で検証しつつ、Colab上でも使いやすい形に整備していきます。
