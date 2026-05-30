#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import gradio as gr

APP_TITLE = "IrodoriTTS VoiceDesign"
VOICEDESIGN_HF_CHECKPOINT = "Aratako/Irodori-TTS-500M-v2-VoiceDesign"
OUTPUT_ROOT = Path("outputs")
_CANCEL_REQUESTED = False

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
.gr-panel,
.tab-nav,
.tabs > div:first-child,
[role="tablist"] {
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

.input-subcard {
    padding: 12px 14px !important;
    margin: 10px 0 !important;
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

textarea,
input[type=text],
input[type=number] {
    font-size: 15px !important;
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

.danger-button button,
button.danger-button {
    background: #d93025 !important;
    color: #ffffff !important;
    border: 1px solid #b3261e !important;
    font-weight: 700 !important;
}

.log-area textarea,
.model-status textarea {
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


/* ===== Mobile stability fixes ===== */
.audio-output-card {
    min-height: 170px !important;
    overflow: hidden !important;
}

.audio-output-card audio,
.audio-output-card .audio-container,
.audio-output-card [data-testid="audio"] {
    width: 100% !important;
    min-height: 54px !important;
}

.mobile-stable-card {
    min-height: 120px !important;
}

.short-log textarea {
    min-height: 72px !important;
    max-height: 120px !important;
    overflow-y: auto !important;
}

.detail-log textarea {
    min-height: 220px !important;
    max-height: 360px !important;
    overflow-y: auto !important;
}

@media (max-width: 768px) {
    .gradio-container {
        padding: 0 12px 40px !important;
        max-width: 100% !important;
    }

    .hero {
        padding: 20px 16px 18px !important;
        margin-bottom: 14px !important;
    }

    .hero h1 {
        font-size: 1.55rem !important;
        line-height: 1.2 !important;
    }

    .studio-card {
        padding: 14px 12px !important;
        margin: 10px 0 !important;
    }

    .section-title h2,
    .section-title h3,
    .gr-markdown h2,
    .gr-markdown h3,
    .gr-markdown h4 {
        font-size: 15px !important;
        line-height: 1.45 !important;
    }

    textarea,
    input[type=text],
    input[type=number] {
        font-size: 16px !important;
    }

    .audio-output-card {
        min-height: 190px !important;
    }

    .audio-output-card audio,
    .audio-output-card .audio-container,
    .audio-output-card [data-testid="audio"] {
        min-height: 64px !important;
    }

    .detail-log textarea {
        max-height: 300px !important;
    }
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


def _request_cancel() -> str:
    global _CANCEL_REQUESTED
    _CANCEL_REQUESTED = True
    return "中断リクエストを受け付けました。現在の生成を停止中です..."


def _reset_cancel() -> None:
    global _CANCEL_REQUESTED
    _CANCEL_REQUESTED = False


def _is_cancel_requested() -> bool:
    return _CANCEL_REQUESTED


def _run_command(
    cmd: list[str],
    timeout: int | None = None,
    cancellable: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    if not cancellable:
        return subprocess.run(
            cmd,
            cwd=str(_project_root()),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            startupinfo=_startupinfo(),
        )

    process = subprocess.Popen(
        cmd,
        cwd=str(_project_root()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        startupinfo=_startupinfo(),
    )

    started_at = time.monotonic()
    while process.poll() is None:
        if _is_cancel_requested():
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            stderr = (stderr or "") + "\nユーザー操作により生成を中断しました。"
            return subprocess.CompletedProcess(cmd, -15, stdout, stderr)

        if timeout is not None and time.monotonic() - started_at > timeout:
            process.kill()
            stdout, stderr = process.communicate()
            stderr = (stderr or "") + f"\nタイムアウトしました: {timeout}秒"
            return subprocess.CompletedProcess(cmd, -9, stdout, stderr)

        time.sleep(0.25)

    stdout, stderr = process.communicate()
    return subprocess.CompletedProcess(cmd, int(process.returncode or 0), stdout, stderr)


def _check_environment() -> str:
    ffmpeg_status = shutil.which("ffmpeg") or "未検出"
    uv_status = shutil.which("uv") or "未検出"
    infer_status = "OK" if (_project_root() / "infer.py").is_file() else "NG"
    python_status = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    torch_status = "未確認"
    cuda_status = "未確認"
    if shutil.which("uv"):
        result = _run_command(
            [
                "uv",
                "run",
                "python",
                "-c",
                (
                    "import torch; "
                    "print(torch.__version__); "
                    "print('cuda=' + str(torch.cuda.is_available())); "
                    "print('device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'))"
                ),
            ]
        )
        if result.returncode == 0:
            lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
            torch_status = lines[0] if lines else "OK"
            cuda_status = " / ".join(lines[1:]) if len(lines) > 1 else "確認不可"
        else:
            torch_status = "確認失敗"
            cuda_status = (result.stderr or result.stdout or "").strip()[:200]

    return "\n".join(
        [
            f"python: {python_status}",
            f"uv: {uv_status}",
            f"ffmpeg: {ffmpeg_status}",
            f"infer.py: {infer_status}",
            f"torch: {torch_status}",
            f"cuda: {cuda_status}",
            f"checkpoint: {VOICEDESIGN_HF_CHECKPOINT}",
        ]
    )


def _load_model() -> str:
    code = (
        "from huggingface_hub import hf_hub_download; "
        f"path = hf_hub_download(repo_id={VOICEDESIGN_HF_CHECKPOINT!r}, filename='model.safetensors'); "
        "print(path)"
    )
    result = _run_command(["uv", "run", "python", "-c", code])
    if result.returncode != 0:
        raise gr.Error("モデル準備に失敗しました。\n\n" + (result.stderr or result.stdout))
    model_path = (result.stdout or "").strip().splitlines()[-1]
    return (
        "VoiceDesignモデルを準備しました。\n"
        f"checkpoint: {VOICEDESIGN_HF_CHECKPOINT}\n"
        f"cached_path: {model_path}"
    )


def _generate_voicedesign(
    test_text: str,
    caption: str,
    seed: int,
    num_steps: int,
    progress: gr.Progress = gr.Progress(track_tqdm=False),
) -> tuple[str, str, str]:
    text = str(test_text or "").strip()
    caption_text = str(caption or "").strip()

    if not text:
        raise gr.Error("テスト文を入力してください。")
    if not caption_text:
        raise gr.Error("声の指示を入力してください。")

    _reset_cancel()

    out_dir = OUTPUT_ROOT / "voicedesign_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_wav = out_dir / f"voicedesign_{int(seed)}_{timestamp}.wav"

    cmd = [
        "uv",
        "run",
        "python",
        "infer.py",
        "--hf-checkpoint",
        VOICEDESIGN_HF_CHECKPOINT,
        "--text",
        text,
        "--caption",
        caption_text,
        "--no-ref",
        "--num-steps",
        str(int(num_steps)),
        "--seed",
        str(int(seed)),
        "--output-wav",
        str(output_wav),
    ]

    progress(0.1, desc="VoiceDesign生成準備中...")
    result = _run_command(cmd, cancellable=True)
    progress(0.9, desc="音声ファイル確認中...")

    if _is_cancel_requested():
        raise gr.Error("VoiceDesign生成を中断しました。")

    if result.returncode != 0:
        raise gr.Error("VoiceDesign生成に失敗しました。\n\n" + (result.stderr or result.stdout))

    if not output_wav.is_file():
        raise gr.Error("infer.pyは正常終了しましたが、音声ファイルが見つかりませんでした。")

    progress(1.0, desc="生成完了")

    log = "\n".join(
        [
            "VoiceDesign生成が完了しました。",
            f"checkpoint: {VOICEDESIGN_HF_CHECKPOINT}",
            f"output_wav: {output_wav.resolve()}",
            f"seed: {int(seed)}",
            f"num_steps: {int(num_steps)}",
            f"caption: {caption_text}",
            "",
            "--- infer.py stdout ---",
            (result.stdout or "").strip(),
            "",
            "--- infer.py stderr ---",
            (result.stderr or "").strip(),
        ]
    )

    short_log = "\n".join(
        [
            "VoiceDesign生成が完了しました。",
            f"seed: {int(seed)}",
            f"num_steps: {int(num_steps)}",
            f"output: {output_wav.name}",
        ]
    )

    return str(output_wav), short_log, log


def _clear_results() -> tuple[None, str, str, str]:
    """生成結果とログをクリアする。"""
    return None, "", "", ""


def _copy_latest_to_drive(generated_wav: str | None) -> str:
    if not generated_wav or not str(generated_wav).strip():
        raise gr.Error("先に音声を生成してください。")

    src = Path(str(generated_wav).strip())
    if not src.is_file():
        raise gr.Error(f"生成音声が見つかりません: {src}")

    drive_dir = Path("/content/drive/MyDrive/IrodoriTTS_VoiceDesign")
    if not Path("/content/drive").exists():
        raise gr.Error("Google Driveがマウントされていません。Colab側でDriveマウントセルを実行してください。")

    drive_dir.mkdir(parents=True, exist_ok=True)
    dst = drive_dir / src.name
    shutil.copy2(src, dst)

    return f"Google Driveへ保存しました。\n{dst}"


def build_ui() -> gr.Blocks:
    with gr.Blocks(title=APP_TITLE) as demo:
        gr.Markdown(
            """
            # IrodoriTTS VoiceDesign
            声の雰囲気をテキスト指示で作り、サンプル音声を生成します
            """,
            elem_classes=["hero"],
        )

        with gr.Accordion("環境・モデル確認", open=False, elem_classes=["studio-card"]):
            gr.Markdown("### 環境・モデル確認", elem_classes=["section-title"])
            with gr.Row():
                check_env_btn = gr.Button("環境チェック", variant="secondary")
                load_model_btn = gr.Button("モデルロード（初回準備）", variant="secondary")
            env_status = gr.Textbox(label="環境状態", value=_check_environment(), lines=7, interactive=False)
            model_status = gr.Textbox(label="モデル状態", lines=4, interactive=False)

        with gr.Group(elem_classes=["studio-card"]):
            gr.Markdown("### テスト文", elem_classes=["section-title"])
            test_text = gr.Textbox(
                label="読み上げテキスト",
                value="こんにちは。これはVoiceDesignのテストです。",
                lines=3,
                placeholder="短めの文章がおすすめです。",
            )

        with gr.Group(elem_classes=["studio-card"]):
            gr.Markdown("### 声の指示", elem_classes=["section-title"])
            caption = gr.Textbox(
                label="声の雰囲気を文章で指定",
                value="明るく元気な若い女性の声で、はきはきと自然に話している。",
                lines=4,
                placeholder="例：落ち着いた大人の女性の声で、やさしく語りかけるように話している。",
            )
            with gr.Accordion("指示文の例", open=True):
                gr.Markdown(
                    """
                    - 明るく元気な若い女性の声で、はきはきと自然に話している。
                    - 落ち着いた大人の女性の声で、やさしく語りかけるように話している。
                    - 低めの男性の声で、穏やかで安心感のある口調で話している。
                    - やや高めの少女の声で、楽しそうにテンポよく話している。
                    """
                )

        with gr.Group(elem_classes=["studio-card"]):
            gr.Markdown("### パラメータ", elem_classes=["section-title"])
            with gr.Row():
                seed = gr.Number(
                    label="seed（変えると違う声になります）",
                    value=42,
                    precision=0,
                )
                num_steps = gr.Slider(
                    label="num-steps",
                    minimum=20,
                    maximum=100,
                    value=40,
                    step=1,
                    info="20〜40=高速、60=バランス、80〜100=高品質寄り",
                )

        generate_btn = gr.Button(
            "🎨 この声で生成",
            variant="primary",
            elem_classes=["btn-primary", "hero-generate"],
        )
        cancel_btn = gr.Button(
            "⏹ 生成中断",
            variant="secondary",
            elem_classes=["danger-button"],
        )

        with gr.Group(elem_classes=["studio-card", "mobile-stable-card"]):
            gr.Markdown("### 生成結果", elem_classes=["section-title"])
            with gr.Group(elem_classes=["audio-output-card"]):
                output_wav = gr.Audio(label="生成WAV", type="filepath", interactive=False)

            with gr.Row():
                save_drive_btn = gr.Button("Google Driveへ保存", variant="secondary")
                clear_result_btn = gr.Button("結果をクリア", variant="secondary")

            run_log = gr.Textbox(
                label="生成ログ",
                lines=3,
                interactive=False,
                elem_classes=["log-area", "short-log"],
            )

            with gr.Accordion("詳細ログ", open=False):
                detail_log = gr.Textbox(
                    label="詳細ログ",
                    lines=10,
                    interactive=False,
                    elem_classes=["log-area", "detail-log"],
                )

            save_log = gr.Textbox(
                label="保存ログ",
                lines=3,
                interactive=False,
                elem_classes=["log-area", "short-log"],
            )

        check_env_btn.click(_check_environment, outputs=[env_status])
        load_model_btn.click(_load_model, outputs=[model_status])
        generate_btn.click(
            _generate_voicedesign,
            inputs=[test_text, caption, seed, num_steps],
            outputs=[output_wav, run_log, detail_log],
        )
        cancel_btn.click(_request_cancel, outputs=[run_log], queue=False)
        save_drive_btn.click(_copy_latest_to_drive, inputs=[output_wav], outputs=[save_log])
        clear_result_btn.click(
            _clear_results,
            outputs=[output_wav, run_log, detail_log, save_log],
            queue=False,
        )

    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="IrodoriTTS VoiceDesign GUI.")
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
