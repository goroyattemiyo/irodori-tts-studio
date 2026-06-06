# IrodoriTTS Studio Custom Web UI

FastAPI + HTML/CSS/JS による新UI版です。

## 起動コマンド

リポジトリ直下で実行してください。

Windows / Colab 共通:

python -m app.api_server

## ブラウザ

http://localhost:7860

Colabで使う場合も、irodori-tts-studio のリポジトリ直下に移動してから実行してください。

例:

cd /content/irodori-tts-studio
python -m app.api_server

## 現段階

- JSON書き出し
- JSON読み込み
- チャンク分割プレビュー
- 生成モック

## 次フェーズ

- infer.py 実生成接続
- 参照音声アップロード接続
- WAV/MP3変換
- エピソード結合
