#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import gradio as gr

APP_TITLE = "IrodoriTTS SNS Video Converter"
OUTPUT_ROOT = Path("outputs/video_converter")

CUSTOM_CSS = r"""
body,
.gradio-container,
.gr-markdown,
.markdown,
.prose,
.gr-markdown p,
.gr-markdown span,
label,
.block label,
.form label,
.label-wrap span,
p,
span,
h1, h2, h3, h4,
[role="tab"],
.tab-nav button {
    color: #000000 !important;
}

body,
.gradio-container {
    background: #ffffff !important;
    color: #000000 !important;
}

.gradio-container {
    max-width: 1080px !important;
    margin: 0 auto !important;
    padding: 0 24px 60px !important;
}

.hero,
.studio-card,
.input-subcard,
.gr-accordion,
.gr-group,
.gr-box,
.gr-panel {
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #000000 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}

.hero {
    padding: 28px 32px 24px !important;
    margin-bottom: 24px !important;
}

.hero h1 {
    color: #000000 !important;
    font-size: clamp(1.8rem, 3.5vw, 3rem) !important;
    font-weight: 800 !important;
    line-height: 1.1 !important;
    margin: 0 0 8px !important;
    text-shadow: none !important;
}

.hero p {
    color: #000000 !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
}

.studio-card {
    padding: 20px 22px 18px !important;
    margin: 14px 0 !important;
}

.section-title h2,
.section-title h3,
.gr-markdown h2,
.gr-markdown h3,
.gr-markdown h4 {
    color: #000000 !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
    font-weight: 700 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    margin: 0 0 10px !important;
    padding-bottom: 8px !important;
    border-bottom: 1px solid #000000 !important;
}

label,
.block label,
.form label,
.label-wrap span {
    color: #000000 !important;
    font-size: 15px !important;
    line-height: 1.5 !important;
    font-weight: 600 !important;
}

textarea,
input[type=text],
input[type=number],
select,
.wrap,
.gr-input,
.gr-text-input {
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #000000 !important;
    box-shadow: none !important;
}

textarea::placeholder,
input::placeholder {
    color: #000000 !important;
    opacity: 1 !important;
}

button.secondary {
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #000000 !important;
    box-shadow: none !important;
}

button.primary,
button.btn-primary,
.btn-primary button,
.hero-generate button {
    background: #111111 !important;
    color: #ffffff !important;
    border: 1px solid #111111 !important;
    box-shadow: none !important;
    font-weight: 700 !important;
}

.log-area textarea {
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #000000 !important;
}

body::before,
body::after,
.hero::before,
.hero::after {
    display: none !important;
}
"""


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        cmd,
        cwd=str(_project_root()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        startupinfo=_startupinfo(),
    )


def _check_environment() -> str:
    ffmpeg = shutil.which("ffmpeg") or "未検出"
    python_status = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ffmpeg_run = "未確認"
    if shutil.which("ffmpeg"):
        result = _run_command(["ffmpeg", "-version"])
        if result.returncode == 0:
            ffmpeg_run = (result.stdout or "").splitlines()[0]
        else:
            ffmpeg_run = "実行失敗"
    return "\n".join(
        [
            f"python: {python_status}",
            f"ffmpeg: {ffmpeg}",
            f"ffmpeg_run: {ffmpeg_run}",
        ]
    )


def _size_to_resolution(size_label: str) -> tuple[int, int]:
    mapping = {
        "9:16 縦動画 / Shorts・TikTok・Reels": (1080, 1920),
        "1:1 正方形 / Threads・Instagram": (1080, 1080),
        "16:9 横動画 / YouTube・X": (1920, 1080),
    }
    return mapping.get(size_label, (1080, 1920))


def _make_video(
    audio_path: str | None,
    image_path: str | None,
    size_label: str,
    output_name: str,
    bg_color: str,
) -> tuple[str | None, str]:
    if not audio_path or not str(audio_path).strip():
        raise gr.Error("音声ファイルを指定してください。")

    audio = Path(str(audio_path).strip())
    if not audio.is_file():
        raise gr.Error(f"音声ファイルが見つかりません: {audio}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise gr.Error("ffmpegが見つかりません。Colabのセットアップセルでffmpegを導入してください。")

    width, height = _size_to_resolution(size_label)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    safe_name = str(output_name or "").strip()
    if not safe_name:
        safe_name = f"sns_video_{datetime.now():%Y%m%d_%H%M%S}"
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in safe_name)
    if not safe_name.lower().endswith(".mp4"):
        safe_name += ".mp4"
    output = OUTPUT_ROOT / safe_name

    if image_path and str(image_path).strip():
        image = Path(str(image_path).strip())
        if not image.is_file():
            raise gr.Error(f"背景画像が見つかりません: {image}")

        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,format=yuv420p"
        )

        cmd = [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            str(image),
            "-i",
            str(audio),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-tune",
            "stillimage",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ]
    else:
        color = str(bg_color or "white").strip() or "white"
        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:r=30",
            "-i",
            str(audio),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ]

    result = _run_command(cmd)

    if result.returncode != 0:
        raise gr.Error("MP4変換に失敗しました。\n\n" + (result.stderr or result.stdout))

    if not output.is_file():
        raise gr.Error("ffmpegは終了しましたが、MP4ファイルが見つかりませんでした。")

    log = "\n".join(
        [
            "MP4変換が完了しました。",
            f"audio: {audio.resolve()}",
            f"image: {image_path or '背景色のみ'}",
            f"size: {width}x{height}",
            f"output: {output.resolve()}",
            "",
            "--- ffmpeg stderr ---",
            (result.stderr or "").strip(),
        ]
    )

    return str(output), log


def _copy_to_drive(video_path: str | None) -> str:
    if not video_path or not str(video_path).strip():
        raise gr.Error("先にMP4を生成してください。")

    src = Path(str(video_path).strip())
    if not src.is_file():
        raise gr.Error(f"MP4ファイルが見つかりません: {src}")

    if not Path("/content/drive").exists():
        raise gr.Error("Google Driveがマウントされていません。Colab側でDriveマウントセルを実行してください。")

    drive_dir = Path("/content/drive/MyDrive/IrodoriTTS_Videos")
    drive_dir.mkdir(parents=True, exist_ok=True)
    dst = drive_dir / src.name
    shutil.copy2(src, dst)

    return f"Google Driveへ保存しました。\n{dst}"


def build_ui() -> gr.Blocks:
    with gr.Blocks(title=APP_TITLE) as demo:
        gr.Markdown(
            """
            # IrodoriTTS SNS Video Converter
            生成した音声をSNS投稿用のMP4動画に変換します
            """,
            elem_classes=["hero"],
        )

        with gr.Group(elem_classes=["studio-card"]):
            gr.Markdown("### 入力", elem_classes=["section-title"])
            audio_input = gr.Audio(
                label="音声ファイル（WAV / MP3 / M4A）",
                type="filepath",
            )
            image_input = gr.Image(
                label="背景画像（任意）",
                type="filepath",
            )

        with gr.Group(elem_classes=["studio-card"]):
            gr.Markdown("### 出力設定", elem_classes=["section-title"])
            size = gr.Radio(
                label="動画サイズ",
                choices=[
                    "9:16 縦動画 / Shorts・TikTok・Reels",
                    "1:1 正方形 / Threads・Instagram",
                    "16:9 横動画 / YouTube・X",
                ],
                value="9:16 縦動画 / Shorts・TikTok・Reels",
            )
            output_name = gr.Textbox(
                label="出力ファイル名",
                placeholder="空欄なら sns_video_年月日時.mp4",
            )
            bg_color = gr.Textbox(
                label="背景色（画像なしの場合）",
                value="white",
                placeholder="white / black / #ffffff など",
            )

        generate_btn = gr.Button(
            "🎬 MP4を生成",
            variant="primary",
            elem_classes=["btn-primary", "hero-generate"],
        )

        with gr.Group(elem_classes=["studio-card"]):
            gr.Markdown("### 結果", elem_classes=["section-title"])
            video_output = gr.Video(label="生成MP4", interactive=False)
            save_drive_btn = gr.Button("Google Driveへ保存", variant="secondary")
            run_log = gr.Textbox(label="変換ログ", lines=12, interactive=False, elem_classes=["log-area"])
            save_log = gr.Textbox(label="保存ログ", lines=3, interactive=False, elem_classes=["log-area"])

        with gr.Accordion("環境チェック", open=False, elem_classes=["studio-card"]):
            env_status = gr.Textbox(label="環境状態", value=_check_environment(), lines=5, interactive=False)
            check_env_btn = gr.Button("環境チェック", variant="secondary")

        generate_btn.click(
            _make_video,
            inputs=[audio_input, image_input, size, output_name, bg_color],
            outputs=[video_output, run_log],
        )
        save_drive_btn.click(_copy_to_drive, inputs=[video_output], outputs=[save_log])
        check_env_btn.click(_check_environment, outputs=[env_status])

    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="IrodoriTTS SNS Video Converter.")
    parser.add_argument("--server-name", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    demo = build_ui()
    demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=bool(args.share),
        debug=bool(args.debug),
        css=CUSTOM_CSS,
        theme=gr.themes.Base(),
    )


if __name__ == "__main__":
    main()
