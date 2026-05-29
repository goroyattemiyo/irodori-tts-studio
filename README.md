@"
# IrodoriTTS Studio

IrodoriTTSをブラウザGUIで連続生成するための補助ツールです。

## 使い方

1. Colabノートブックを開く
2. ランタイムをGPUに変更する
3. セルを上から順番に実行する
4. 表示されたGradio URLを開く
5. 台本と参照音声を入れて生成する

## 注意

- このリポジトリにはIrodori-TTS本体は含みません。
- Colab上で公式Irodori-TTSをcloneし、このGUIを配置して使います。
- 生成物はproject.jsonと一緒に保存してください。
"@ | Set-Content README.md -Encoding UTF8
