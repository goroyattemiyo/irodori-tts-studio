# IrodoriTTS Studio

IrodoriTTSをGoogle Colab上で起動し、ブラウザGUIから音声生成するための補助ツールです。

## Open in Colab

### 1. VoiceDesignで声を作る

[![Open VoiceDesign In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/goroyattemiyo/irodori-tts-studio/blob/main/colab/IrodoriTTS_VoiceDesign.ipynb)

### 2. Studioで台本を連続生成する

[![Open Studio In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/goroyattemiyo/irodori-tts-studio/blob/main/colab/IrodoriTTS_Studio.ipynb)

### 3. Video ConverterでSNS投稿用MP4にする

[![Open Video Converter In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/goroyattemiyo/irodori-tts-studio/blob/main/colab/IrodoriTTS_VideoConverter.ipynb)

## VoiceDesignで作った音声をStudioで使う方法

1. VoiceDesignでサンプル音声を生成する
2. 「Google Driveへ保存（Studioで参照可）」を押す
3. Studioを開いて同じGoogle Driveをマウントする
4. 「参照音声」→「Google Driveから参照音声を選択」を開く
5. `IrodoriTTS_VoiceDesign` フォルダ内のWAVを選ぶ
6. その音声を参照音声として台本を生成する

## 使い方の流れ

1. VoiceDesignで好みの声を作る
2. 気に入った音声をWAVで保存する
3. Studioで台本を入力する
4. チャンク分割を確認する
5. 音声生成を行う
6. 生成結果を保存・活用する
7. 必要に応じてVideo ConverterでSNS投稿用MP4にする

## できること / 整備中の機能

### VoiceDesign

- 声の雰囲気をテキスト指示から作る
- seedを変えながら好みの声を探す
- 生成したWAVを保存する
- 保存したWAVをStudio側の参照音声として使う

### Studio

現在整備中の機能:

- 台本入力
- チャンク分割プレビュー
- project.jsonによるプロジェクト保存・読み込み
- Web UIからの音声生成API接続
- WAV/MP3生成

今後整備予定:

- 参照音声アップロード導線の改善
- 生成結果のWAV/MP3表示
- ブラウザ上での音声試聴・ダウンロード
- 生成チャンクごとの確認・再生成
- 生成済みチャンクの結合
- 任意音声ファイルの順番指定結合

## リポジトリ構成

- app/irodori_app.py
- colab/IrodoriTTS_VoiceDesign.ipynb
- colab/IrodoriTTS_Studio.ipynb
- docs/usage.md
- scripts/setup_colab.sh

## 重要

このリポジトリには、Irodori-TTS本体は含まれていません。

Colabノートブックの中で、公式Irodori-TTSリポジトリをcloneして使用します。

公式Irodori-TTS:  
https://github.com/Aratako/Irodori-TTS

## Colabでの基本手順

1. Open in Colabボタンからノートブックを開く
2. ランタイムをGPUに変更する
3. セルを上から順番に実行する
4. 表示された gradio.live URLを開く
5. GUIから生成する

## GPU設定

Colab上部メニューから以下を設定してください。

ランタイム → ランタイムのタイプを変更 → ハードウェア アクセラレータ → GPU → 保存

T4 GPUでOKです。  
CPUでも起動できる場合がありますが、音声生成にかなり時間がかかるため、GPU推奨です。

## 保存について

Colabの /content 配下は、セッション終了後に消える場合があります。

生成した音声や project.json を残したい場合は、Google Driveへ保存してください。

## 注意事項

- 初回起動時は、モデルや依存関係のダウンロードに時間がかかります。
- Colabの無料枠では、実行時間やGPU利用に制限があります。
- 生成物を残したい場合は、Google Driveなどに保存してください。
- 他人の声や権利のある音声を扱う場合は、利用許諾や権利関係に注意してください。

## License

未定
