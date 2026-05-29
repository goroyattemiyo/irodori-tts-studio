以下を `README.md` にそのまま貼り替えでOKです。
`あなたのGitHubユーザー名` の部分だけ、自分のGitHubユーザー名に置き換えてください。

````markdown
# IrodoriTTS Studio

IrodoriTTSをGoogle Colab上で起動し、ブラウザGUIから台本を連続音声生成するための補助ツールです。

このリポジトリには、IrodoriTTS用のGradio GUIと、Colab起動用ノートブックを置いています。

## Open in Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/goroyattemiyo/irodori-tts-studio/blob/main/colab/IrodoriTTS_Studio.ipynb)

## できること

- 台本をチャンク分割して連続音声生成
- 参照音声のアップロード
- その場で録音した音声を参照音声として使用
- 生成チャンクごとの確認・再生成
- 生成済みチャンクの結合
- WAV → MP3変換
- 任意音声ファイルの順番指定結合
- project.jsonによるプロジェクト保存・読み込み

## リポジトリ構成

```text
irodori-tts-studio/
├─ app/
│  └─ irodori_app.py
├─ colab/
│  └─ IrodoriTTS_Studio.ipynb
├─ docs/
│  └─ usage.md
├─ scripts/
│  └─ setup_colab.sh
├─ README.md
└─ .gitignore
````

## 重要

このリポジトリには、Irodori-TTS本体は含まれていません。

Colabノートブックの中で、公式Irodori-TTSリポジトリをcloneし、このリポジトリのGUIファイルを配置して使用します。

公式Irodori-TTS:
[https://github.com/Aratako/Irodori-TTS](https://github.com/Aratako/Irodori-TTS)

## Colabでの使い方

### STEP 1：Colabを開く

上の **Open in Colab** ボタンからノートブックを開きます。

または、以下の形式のURLから直接開けます。

```text
https://colab.research.google.com/github/goroyattemiyo/irodori-tts-studio/blob/main/colab/IrodoriTTS_Studio.ipynb
```

### STEP 2：ランタイムをGPUに変更する

Colab上部メニューから、以下の順番で設定してください。

```text
ランタイム
↓
ランタイムのタイプを変更
↓
ハードウェア アクセラレータ
↓
GPU
↓
保存
```

T4 GPUでOKです。

CPUでも起動できる場合がありますが、音声生成にかなり時間がかかるため、GPU推奨です。

### STEP 3：セルを上から順番に実行する

ノートブック内のセルを、上から順番に実行してください。

主な流れは以下です。

```text
1. GPU確認
2. Google Driveマウント（任意）
3. Irodori-TTS本体とGUIを取得
4. 環境構築
5. GUI起動
```

### STEP 4：Gradio URLを開く

最後のGUI起動セルを実行すると、以下のようなURLが表示されます。

```text
https://xxxxx.gradio.live
```

このURLを開くと、IrodoriTTS StudioのGUIが表示されます。

## GUIの使い方

### 1. 台本を入力する

「台本」欄に読み上げたい文章を入力します。

文章は自動でチャンク分割されます。

### 2. 参照音声を設定する

参照音声は任意です。

基本は以下のどちらかを使います。

```text
1. 参照音声をアップロード
2. その場で録音
```

参照音声を使わない場合は、参照音声なしで生成されます。

### 3. 全チャンクを生成する

「全チャンクを生成」を押すと、台本を分割して順番に音声生成します。

生成結果はプロジェクトフォルダに保存されます。

### 4. チャンクを確認・再生成する

生成後、チャンクごとのMP3を確認できます。

必要に応じて、各チャンクのテキストを修正して再生成できます。

### 5. 生成チャンクを結合する

「生成チャンクを結合してエピソード完成」を押すと、現在のプロジェクト内の `chunk_*.wav` を番号順に結合します。

出力例：

```text
episode.wav
episode.mp3
```

### 6. 任意音声を結合する

別プロジェクトに分かれた音声や、順番を入れ替えたい音声は「任意音声結合」で結合できます。

結合順リストの行を入れ替えることで、上から順番に結合されます。

## 保存について

Colabの `/content` 配下は、セッション終了後に消える場合があります。

生成した音声や `project.json` を残したい場合は、Google Driveへ保存してください。

ノートブック内に、以下のような保存用セルを用意しています。

```python
!mkdir -p /content/drive/MyDrive/IrodoriTTS_projects
!cp -r /content/Irodori-TTS/outputs /content/drive/MyDrive/IrodoriTTS_projects/
```

## project.jsonについて

生成時には、プロジェクトフォルダ内に `project.json` が保存されます。

`project.json` には以下の情報が保存されます。

```text
台本
分割設定
生成パラメータ
参照音声パス
MP3ビットレート
モデル指定
```

保存済みプロジェクトを再開したい場合は、GUIの「project.jsonから読込」から、対象プロジェクトの `project.json` を選択してください。

## 生成ファイル例

```text
outputs/
└─ irodori_20260527_213045/
   ├─ project.json
   ├─ reference.wav
   ├─ chunk_01.txt
   ├─ chunk_01.wav
   ├─ chunk_01.mp3
   ├─ chunk_02.txt
   ├─ chunk_02.wav
   ├─ chunk_02.mp3
   ├─ episode.wav
   └─ episode.mp3
```

## 注意事項

* このGUIはIrodori-TTS本体を使うための補助ツールです。
* 初回起動時は、モデルや依存関係のダウンロードに時間がかかります。
* GPUランタイムを推奨します。
* Colabの無料枠では、実行時間やGPU利用に制限があります。
* 生成物を残したい場合は、Google Driveなどに保存してください。
* 他人の声や権利のある音声を扱う場合は、利用許諾や権利関係に注意してください。

## License

未定

```
```
