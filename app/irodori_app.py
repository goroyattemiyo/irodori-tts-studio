#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import gradio as gr

APP_TITLE = "IrodoriTTS 連続生成GUI"
DEFAULT_HF_CHECKPOINT = "Aratako/Irodori-TTS-500M-v2"
def _detect_project_root() -> Path:
    """
    app/irodori_app.py から起動しても、リポジトリ直下から起動しても、
    infer.py があるプロジェクトルートを安定して取得する。
    """
    here = Path(__file__).resolve().parent
    if (here / "infer.py").is_file():
        return here
    if (here.parent / "infer.py").is_file():
        return here.parent
    return here


PROJECT_ROOT = _detect_project_root()
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
MAX_CHUNKS = 20
_CANCEL_REQUESTED = False

CUSTOM_CSS = """

:root {
    /* ── Stitch カラーパレット ── */
    --bg-base:       #111318;
    --bg-surface:    #111318;
    --bg-container:  #1e1f25;
    --bg-container-low:  #1a1b21;
    --bg-container-high: #282a2f;
    --bg-container-lowest: #0c0e13;
    --bg-dim:        #111318;
    --accent:        #bcd20e;
    --accent-bright: #d8ee36;
    --accent-dim:    #596400;
    --accent-glow:   rgba(188,210,14,0.18);
    --accent-glow-strong: rgba(188,210,14,0.38);
    --text-primary:  #e2e2e9;
    --text-secondary:#c7c8ae;
    --text-muted:    #91937a;
    --border:        #33353a;
    --border-soft:   #464834;
    --border-accent: rgba(188,210,14,0.25);
    --surface-variant: #33353a;
    --on-primary:    #2d3400;
    --danger:        #ffb4ab;
    --radius:        4px;
    --radius-lg:     8px;
    --radius-full:   12px;
}

/* ───────── ベース ───────── */
body, .gradio-container {
    background:
        radial-gradient(circle at 85% 5%,  rgba(188,210,14,0.05), transparent 40%),
        radial-gradient(circle at 10% 90%, rgba(188,210,14,0.03), transparent 35%),
        var(--bg-base) !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    color: var(--text-primary) !important;
    min-height: 100vh;
}
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding: 0 24px 60px !important;
}

/* ───────── ヘッダー（Stitch TopAppBar風） ───────── */
.hero {
    padding: 28px 32px 24px;
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-lg);
    background: rgba(17,19,24,0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 0 30px var(--accent-glow), inset 0 0 5px rgba(188,210,14,0.06);
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1.5px;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(188,210,14,0.6) 30%,
        rgba(216,238,54,0.9) 50%,
        rgba(188,210,14,0.6) 70%,
        transparent 100%);
}
/* ウェーブフォームデコレーション */
.hero::after {
    content: '';
    position: absolute;
    bottom: 12px; right: 32px;
    width: 120px; height: 28px;
    background: repeating-linear-gradient(
        90deg,
        transparent 0, transparent 2px,
        rgba(188,210,14,0.15) 2px, rgba(188,210,14,0.15) 3px,
        transparent 3px, transparent 6px
    );
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 28'%3E%3Cpath d='M0,14 Q10,4 20,14 Q30,24 40,14 Q50,4 60,14 Q70,24 80,14 Q90,4 100,14 Q110,24 120,14' fill='none' stroke='white' stroke-width='3'/%3E%3C/svg%3E");
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 28'%3E%3Cpath d='M0,14 Q10,4 20,14 Q30,24 40,14 Q50,4 60,14 Q70,24 80,14 Q90,4 100,14 Q110,24 120,14' fill='none' stroke='white' stroke-width='3'/%3E%3C/svg%3E");
    mask-size: contain;
    -webkit-mask-size: contain;
    mask-repeat: no-repeat;
    -webkit-mask-repeat: no-repeat;
}
.hero h1 {
    font-family: 'Syne', 'Noto Sans JP', sans-serif !important;
    font-size: clamp(1.8rem, 3.5vw, 3rem) !important;
    font-weight: 800 !important;
    line-height: 1.1 !important;
    letter-spacing: -0.02em !important;
    margin: 0 0 8px !important;
    color: var(--accent) !important;
    text-shadow:
        0 0 10px var(--accent-glow-strong),
        0 0 30px var(--accent-glow) !important;
}
.hero p {
    color: var(--text-secondary) !important;
    font-size: 0.88rem !important;
    margin: 0 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase;
    font-weight: 500;
}

/* ───────── セクションカード（Stitch glass-panel） ───────── */
.studio-card {
    background: rgba(17,21,34,0.75) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: var(--radius-lg) !important;
    padding: 20px 22px 18px !important;
    margin: 14px 0 !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35) !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}
.studio-card:hover {
    border-color: rgba(188,210,14,0.2) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4),
                0 0 20px rgba(188,210,14,0.1) !important;
}

/* セクション見出し（Stitch: UPPERCASE TRACKING） */
.section-title h3,
.section-title h2 {
    color: var(--text-primary) !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    margin: 0 0 14px !important;
    padding-bottom: 10px !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}

/* Gradio標準ブロックの背景を透明に統一 */
.gr-group, .gr-box, .gr-form, .gr-panel,
.block, .form, .wrap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ───────── ラベル ───────── */
label, .block label, .form label, .label-wrap span {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.03em !important;
}

/* 補足テキスト */
.prose, .markdown, .gr-markdown, .secondary-text,
.gr-markdown p, .info {
    color: var(--text-secondary) !important;
}

/* ───────── ボタン ───────── */
button {
    border-radius: var(--radius) !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    transition: all 0.2s ease !important;
}

/* プライマリ（Stitch: bg-surface-tint + neon glow） */
button.primary, button.btn-primary,
.btn-primary button, .hero-generate button {
    background: var(--accent) !important;
    color: var(--on-primary) !important;
    font-family: 'Syne', 'Noto Sans JP', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    border: none !important;
    min-height: 52px !important;
    box-shadow: 0 0 30px rgba(188,210,14,0.4),
                0 4px 16px rgba(0,0,0,0.35) !important;
}
button.primary:hover, button.btn-primary:hover,
.btn-primary button:hover, .hero-generate button:hover {
    box-shadow: 0 0 50px rgba(188,210,14,0.6),
                0 4px 20px rgba(0,0,0,0.4) !important;
    transform: scale(0.99) !important;
}
button.primary:active, .btn-primary button:active {
    transform: scale(0.98) !important;
}

/* セカンダリ（Stitch: border + surface-tint色） */
button.secondary {
    background: rgba(188,210,14,0.08) !important;
    color: var(--accent) !important;
    border: 1px solid rgba(188,210,14,0.4) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}
button.secondary:hover {
    background: rgba(188,210,14,0.14) !important;
    border-color: var(--accent) !important;
    color: var(--accent-bright) !important;
    box-shadow: 0 0 14px rgba(188,210,14,0.2) !important;
}

/* 無効ボタン */
.disabled-note button,
button:disabled {
    opacity: 0.35 !important;
    cursor: not-allowed !important;
    box-shadow: none !important;
}

/* ───────── 入力欄 ───────── */
textarea, input[type=text], input[type=number] {
    background: rgba(12,14,19,0.7) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius) !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    box-shadow: none !important;
}
textarea:focus, input:focus {
    background: rgba(12,14,19,0.85) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(188,210,14,0.2),
                0 0 12px rgba(188,210,14,0.12) !important;
    outline: none !important;
}
textarea::placeholder, input::placeholder {
    color: var(--text-muted) !important;
}

/* ───────── タブ ───────── */
.tab-nav, .tabs > div:first-child, [role="tablist"] {
    background: var(--bg-container-low) !important;
    border-bottom: 1px solid var(--border-accent) !important;
    border-radius: var(--radius) var(--radius) 0 0 !important;
    gap: 0 !important;
}
.tab-nav button, [role="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 12px 22px !important;
    transition: all 0.2s !important;
}
.tab-nav button:hover, [role="tab"]:hover {
    color: var(--accent) !important;
    background: rgba(188,210,14,0.05) !important;
}
.tab-nav button.selected, [role="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: transparent !important;
}

/* ───────── アコーディオン ───────── */
.gr-accordion {
    background: rgba(17,21,34,0.6) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: var(--radius) !important;
}
.gr-accordion summary,
.gr-accordion .label-wrap {
    color: var(--text-primary) !important;
    font-family: 'Noto Sans JP', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

/* ───────── スライダー（Stitch: ライム色のシャドウ付きつまみ） ───────── */
input[type=range] { accent-color: var(--accent) !important; }
input[type=range]::-webkit-slider-runnable-track {
    background: var(--bg-container-high) !important;
    border-radius: 4px !important;
    height: 4px !important;
}
input[type=range]::-webkit-slider-thumb {
    background: var(--accent) !important;
    box-shadow: 0 0 10px var(--accent),
                0 0 20px rgba(188,210,14,0.3) !important;
    width: 4px !important;
    height: 16px !important;
    border-radius: 2px !important;
    border: 1px solid var(--accent) !important;
}

/* ───────── 必須マーク ───────── */
.required-label label::after {
    content: ' ✱';
    color: var(--accent);
    font-size: 0.75em;
    text-shadow: 0 0 6px var(--accent);
}

/* ───────── ログ・出力エリア（Stitch: terminal風） ───────── */
.log-area textarea {
    font-family: 'Courier New', 'Noto Sans JP', monospace !important;
    font-size: 0.80rem !important;
    color: var(--accent) !important;
    background: rgba(0,0,0,0.5) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: var(--radius) !important;
    line-height: 1.6 !important;
}

/* ───────── プログレスバー ───────── */
.progress-bar, .progress {
    background: var(--accent) !important;
    box-shadow: 0 0 12px var(--accent-glow) !important;
}

/* ───────── スクロールバー ───────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--accent-dim);
}

/* ───────── 区切り線 ───────── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.05) !important;
    margin: 16px 0 !important;
}

/* ───────── ステータスバッジ（モデル状態表示エリア） ───────── */
.model-status textarea {
    background: rgba(0,0,0,0.4) !important;
    border: 1px solid var(--border-accent) !important;
    border-left: 3px solid var(--accent) !important;
    color: var(--text-primary) !important;
    font-size: 0.83rem !important;
}

/* ───────── 参照音声ボタン群（Stitch: Path/Upload/Record の3択ボタン風） ───────── */
.ref-audio-row .gr-audio label {
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
}

/* ───────── 背景グロー装飾 ───────── */
body::before {
    content: '';
    position: fixed;
    top: -10%;
    right: -10%;
    width: 40%;
    height: 40%;
    background: rgba(188,210,14,0.04);
    border-radius: 50%;
    filter: blur(120px);
    pointer-events: none;
    z-index: 0;
}
body::after {
    content: '';
    position: fixed;
    bottom: -5%;
    left: -5%;
    width: 30%;
    height: 30%;
    background: rgba(188,210,14,0.02);
    border-radius: 50%;
    filter: blur(100px);
    pointer-events: none;
    z-index: 0;
}
"""

CUSTOM_CSS += r"""

/* ===== Colab visible UI override: no gray text, black font, white panels ===== */
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
    box-shadow: none !important;
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

.section-title h2,
.section-title h3,
.gr-markdown h2,
.gr-markdown h3,
.gr-markdown h4 {
    color: #000000 !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    border-bottom: 1px solid #000000 !important;
}

.reference-card .audio-container,
.reference-card .wrap,
.reference-card [data-testid="audio"],
.reference-card .file-preview,
.reference-card .upload-container,
.gr-file,
.file-preview,
.upload-container {
    background: #ffffff !important;
    color: #000000 !important;
    border-color: #000000 !important;
}

button.secondary {
    background: #ffffff !important;
    color: #000000 !important;
    border: 1px solid #000000 !important;
}

button.primary,
button.btn-primary,
.btn-primary button,
.hero-generate button {
    background: #111111 !important;
    color: #ffffff !important;
    border: 1px solid #111111 !important;
}

.danger-button button,
button.danger-button {
    background: #d93025 !important;
    color: #ffffff !important;
    border: 1px solid #b3261e !important;
}

body::before,
body::after,
.hero::before,
.hero::after {
    display: none !important;
}
"""


CUSTOM_CSS += r"""

/* ===== UI fix: selected tab must be black, textbox focus must stay white ===== */

/* 選択中タブの文字色を黒に固定 */
[role="tab"],
[role="tab"].selected,
[role="tab"][aria-selected="true"],
button[role="tab"],
button[role="tab"].selected,
button[role="tab"][aria-selected="true"] {
    color: #000000 !important;
    background: #ffffff !important;
    border-color: #000000 !important;
    box-shadow: none !important;
}

/* 選択中タブの下線も黒にする */
[role="tab"][aria-selected="true"],
button[role="tab"][aria-selected="true"],
.tab-nav button.selected {
    color: #000000 !important;
    border-bottom: 2px solid #000000 !important;
}

/* テキストエリア・入力欄がフォーカス時に黒くなる問題を防ぐ */
textarea,
textarea:focus,
textarea:focus-visible,
input[type=text],
input[type=text]:focus,
input[type=text]:focus-visible,
input[type=number],
input[type=number]:focus,
input[type=number]:focus-visible {
    background: #ffffff !important;
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    caret-color: #000000 !important;
    border: 1px solid #000000 !important;
    box-shadow: none !important;
    outline: 2px solid transparent !important;
}

/* 台本テキストエリアの見やすさ調整 */
textarea {
    line-height: 1.7 !important;
    font-size: 15px !important;
}

/* プロジェクト欄の説明文を少し読みやすく */
.project-help,
.project-help p,
.project-help li {
    color: #000000 !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
}

"""

def _project_root() -> Path:
    return PROJECT_ROOT


def _startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def _request_cancel() -> str:
    global _CANCEL_REQUESTED
    _CANCEL_REQUESTED = True
    return "中断リクエストを受け付けました。現在のsubprocessを停止中です..."


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


def _safe_project_name(raw_name: str | None) -> str:
    name = (raw_name or "").strip()
    if name == "":
        name = "irodori_project"
    # Windows reserved characters are replaced, while Japanese names are kept as-is.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(" .")
    return name or "irodori_project"


def _create_project_dir(project_name: str) -> Path:
    base = OUTPUT_ROOT / f"{_safe_project_name(project_name)}_{datetime.now():%Y%m%d}"
    if not base.exists():
        base.mkdir(parents=True, exist_ok=False)
        return base

    for index in range(2, 1000):
        candidate = base.with_name(f"{base.name}_{index:02d}")
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
    raise RuntimeError("出力フォルダの連番作成に失敗しました。プロジェクト名を変えてください。")


# ─────────────────────────────────────────────
#  プロジェクト保存・再開（Phase 4B）
# ─────────────────────────────────────────────
PROJECT_FILE = "project.json"


def _resolve_project_dir(project_name: str, *, force_new: bool = False) -> Path:
    """
    生成・再開で使うプロジェクトフォルダを決める。

    - force_new=False（既定）: 同名・同日付のフォルダが既にあればそれを再利用する。
      これにより、PCが落ちても同じプロジェクト名で「全チャンク生成」を押せば続きから走る。
    - force_new=True: 必ず新しい連番フォルダを作る。
    """
    if force_new:
        return _create_project_dir(project_name)

    base = OUTPUT_ROOT / f"{_safe_project_name(project_name)}_{datetime.now():%Y%m%d}"
    if base.exists():
        return base
    base.mkdir(parents=True, exist_ok=True)
    return base


def _save_project_json(
    project_dir: Path,
    *,
    project_name: str,
    script_text: str,
    split_method: str,
    max_chars: int,
    ref_path_text: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    mp3_bitrate: int,
    hf_checkpoint: str,
) -> Path:
    """台本・分割方式・全パラメータを project.json に書き出す。"""
    data = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "project_name": project_name,
        "script_text": script_text,
        "split_method": split_method,
        "max_chars": int(max_chars),
        "ref_path_text": ref_path_text or "",
        "cfg_scale_speaker": float(cfg_scale_speaker),
        "cfg_scale_text": float(cfg_scale_text),
        "num_steps": int(num_steps),
        "seed": int(seed),
        "mp3_bitrate": int(mp3_bitrate),
        "hf_checkpoint": hf_checkpoint or DEFAULT_HF_CHECKPOINT,
    }
    target = project_dir / PROJECT_FILE
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def _load_project_json(project_dir: Path) -> dict:
    """project.json を読み込んで dict で返す。なければ空 dict。"""
    target = project_dir / PROJECT_FILE
    if not target.is_file():
        return {}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _list_saved_projects() -> list[str]:
    """project.json を持つプロジェクトフォルダ名の一覧（新しい順）。"""
    if not OUTPUT_ROOT.is_dir():
        return []
    dirs = [
        d
        for d in OUTPUT_ROOT.iterdir()
        if d.is_dir() and (d / PROJECT_FILE).is_file()
    ]
    dirs.sort(key=lambda d: (d / PROJECT_FILE).stat().st_mtime, reverse=True)
    return [d.name for d in dirs]


def _save_project_for_ui(
    project_name: str,
    script_text: str,
    split_method: str,
    max_chars: int,
    ref_path_text: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    mp3_bitrate: int,
    hf_checkpoint: str,
) -> tuple[object, str]:
    """手動「💾 プロジェクト保存」ボタンのハンドラ。"""
    if not str(script_text or "").strip():
        raise gr.Error("台本が空です。保存する内容がありません。")

    project_dir = _resolve_project_dir(project_name, force_new=False)
    target = _save_project_json(
        project_dir,
        project_name=project_name,
        script_text=script_text,
        split_method=split_method,
        max_chars=max_chars,
        ref_path_text=ref_path_text,
        cfg_scale_speaker=cfg_scale_speaker,
        cfg_scale_text=cfg_scale_text,
        num_steps=num_steps,
        seed=seed,
        mp3_bitrate=mp3_bitrate,
        hf_checkpoint=hf_checkpoint,
    )
    log = (
        f"プロジェクトを保存しました。\n"
        f"  {target.resolve()}\n"
        f"project.json を保存しました。読み込み時はこの project.json を選択してください。"
    )
    return gr.update(choices=_list_saved_projects()), log


def _load_project_for_ui(selected_dir: str | None) -> tuple[object, ...]:
    """「📂 プロジェクト読込」ハンドラ。台本・設定を画面に復元する。"""
    if not selected_dir:
        raise gr.Error("読み込むプロジェクトを選択してください。")

    project_dir = OUTPUT_ROOT / selected_dir
    data = _load_project_json(project_dir)
    if not data:
        raise gr.Error(f"{selected_dir} に project.json が見つかりませんでした。")

    # 既存チャンク数を数えて状況を伝える
    existing = sorted(project_dir.glob("chunk_*.wav"))
    log_lines = [
        f"プロジェクトを読み込みました: {selected_dir}",
        f"  保存日時: {data.get('saved_at', '不明')}",
    ]
    if existing:
        log_lines.append(
            f"  生成済みチャンク: {len(existing)}件 "
            f"（同じプロジェクト名で「全チャンクを生成」を押すと未生成分だけ生成します）"
        )
    else:
        log_lines.append("  生成済みチャンク: なし")
    if not data.get("ref_path_text"):
        log_lines.append(
            "  ※参照音声がアップロード/録音だった場合、パスは復元されません。"
            "未生成チャンクがあるなら参照音声を再設定してください。"
        )

    return (
        data.get("project_name", selected_dir),
        data.get("script_text", ""),
        data.get("split_method", "auto"),
        int(data.get("max_chars", 150)),
        data.get("ref_path_text", ""),
        float(data.get("cfg_scale_speaker", 7.0)),
        float(data.get("cfg_scale_text", 2.5)),
        int(data.get("num_steps", 60)),
        int(data.get("seed", 42)),
        int(data.get("mp3_bitrate", 192)),
        data.get("hf_checkpoint", DEFAULT_HF_CHECKPOINT),
        "\n".join(log_lines),
    )


def _load_project_from_json_file_for_ui(project_json_file: str | None) -> tuple[object, ...]:
    """project.json ファイル選択からプロジェクトを読み込む。"""
    if not project_json_file or not str(project_json_file).strip():
        raise gr.Error("読み込む project.json を選択してください。")

    json_path = Path(str(project_json_file).strip().strip('"')).expanduser()
    if not json_path.is_file():
        raise gr.Error(f"project.json が見つかりません: {json_path}")
    if json_path.name.lower() != PROJECT_FILE:
        raise gr.Error("project.json を選択してください。")

    project_dir = json_path.parent
    data = _load_project_json(project_dir)
    if not data:
        raise gr.Error(f"project.json を読み込めませんでした: {json_path}")

    restored_ref = project_dir / "reference.wav"
    restored_ref_text = str(restored_ref.resolve()) if restored_ref.is_file() else data.get("ref_path_text", "")

    existing_wav = sorted(project_dir.glob("chunk_*.wav"))
    existing_mp3 = sorted(project_dir.glob("chunk_*.mp3"))
    log_lines = [
        f"プロジェクトを読み込みました: {project_dir.resolve()}",
        f"  保存日時: {data.get('saved_at', '不明')}",
        f"  生成済みWAV: {len(existing_wav)}件 / MP3: {len(existing_mp3)}件",
    ]

    return (
        data.get("project_name", ""),
        data.get("script_text", ""),
        data.get("split_method", "auto"),
        int(data.get("max_chars", 150)),
        restored_ref_text,
        float(data.get("cfg_scale_speaker", 7.0)),
        float(data.get("cfg_scale_text", 2.5)),
        int(data.get("num_steps", 60)),
        int(data.get("seed", 42)),
        int(data.get("mp3_bitrate", 192)),
        data.get("hf_checkpoint", DEFAULT_HF_CHECKPOINT),
        "\\n".join(log_lines),
    )


def _is_valid_wav(path: Path) -> bool:
    """生成済みWAVとして有効か（存在し、サイズが0より大きい）。"""
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _trim_for_preview(text: str, max_chars: int = 220) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."


def _first_chunk(script_text: str) -> str:
    text = str(script_text or "").strip()
    if text == "":
        raise gr.Error("台本を入力してください。")
    return text


def _split_by_length(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    remaining = str(text).strip()
    limit = max(40, int(max_chars))
    while len(remaining) > limit:
        window = remaining[: limit + 1]
        split_at = max(window.rfind("。"), window.rfind("、"))
        if split_at <= 0:
            split_at = limit
        else:
            split_at += 1
        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.findall(r".+?。|.+$", text, flags=re.S) if part.strip()]


def _split_chunks(text: str, method: str, max_chars: int = 150) -> list[str]:
    """
    台本テキストをチャンクに分割する。

    method:
        "auto"   : 句点・段落で自動分割（推奨）
        "chars"  : max_chars文字超えで句点/読点分割
        "manual" : [BREAK]タグで手動分割
    """
    source = _first_chunk(text)
    if method == "manual":
        chunks = [part.strip() for part in re.split(r"\[break\]", source, flags=re.I)]
        return [chunk for chunk in chunks if chunk]

    if method == "chars":
        return _split_by_length(source, int(max_chars))

    chunks: list[str] = []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", source) if part.strip()]
    for paragraph in paragraphs:
        current = ""
        for sentence in _split_sentences(paragraph):
            if len(sentence) > 250:
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(_split_by_length(sentence, 200))
                continue
            candidate = f"{current}{sentence}" if current else sentence
            if current and len(candidate) > 250:
                chunks.append(current.strip())
                current = sentence
            else:
                current = candidate
        if current:
            chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def _normalize_file_selection(value: object) -> str:
    """FileExplorerなどの選択値を文字列パスに正規化する。"""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        if not value:
            return ""
        value = value[0]
    cleaned = str(value).strip().strip('"')
    return cleaned


def _show_selected_drive_reference(ref_drive_audio: object) -> tuple[str, str]:
    """Driveで選択した参照音声を表示し、パス指定欄にも反映する。"""
    selected = _normalize_file_selection(ref_drive_audio)
    if not selected:
        return "未選択です。Drive内の音声ファイルを選択してください。", ""

    path = Path(selected)
    message = "\n".join(
        [
            "このDrive音声を参照音声として使います。",
            f"ファイル名: {path.name}",
            f"パス: {selected}",
        ]
    )
    return message, selected


def _drive_root_for_file_explorer() -> str:
    """
    Google Drive未マウント時に FileExplorer が root_dir 不存在で落ちるのを避ける。
    Driveが未マウントなら /content を表示し、マウント後は /content/drive/MyDrive を使う。
    """
    drive_root = Path("/content/drive/MyDrive")
    if drive_root.is_dir():
        return str(drive_root)
    content_root = Path("/content")
    return str(content_root if content_root.is_dir() else PROJECT_ROOT)


def _resolve_reference_audio(
    project_dir: Path,
    ref_path_text: str | None,
    uploaded_audio: str | None,
    recorded_audio: str | None,
    ref_drive_audio: str | None = None,
) -> tuple[str | None, str]:
    candidates = [
        ("アップロード", uploaded_audio),
        ("録音", recorded_audio),
        ("Google Drive", ref_drive_audio),
        ("パス入力", ref_path_text),
    ]
    for label, raw_path in candidates:
        if raw_path is None or str(raw_path).strip() == "":
            continue
        path = Path(str(raw_path).strip().strip('"')).expanduser()
        if not path.is_file():
            raise gr.Error(f"参照音声が見つかりません: {path}")
        if path.suffix.lower() == ".m4a":
            converted = project_dir / "reference_converted.wav"
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg is None:
                raise gr.Error("m4a参照音声の変換にはffmpegが必要です。先にffmpegを導入してください。")
            result = _run_command(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(path),
                    "-ar",
                    "44100",
                    "-ac",
                    "1",
                    str(converted),
                ]
            )
            if result.returncode != 0:
                raise gr.Error(f"m4a変換に失敗しました。\n{result.stderr or result.stdout}")
            return str(converted), f"{label}: {path} -> {converted}"
        return str(path), f"{label}: {path}"
    return None, "参照音声なし（--no-ref）"


def _check_environment() -> str:
    gradio_status = "OK" if importlib.util.find_spec("gradio") else "NG"
    pydub_status = "OK" if importlib.util.find_spec("pydub") else "未導入"
    ffmpeg_status = shutil.which("ffmpeg") or "未検出"
    uv_status = shutil.which("uv") or "未検出"
    infer_status = "OK" if (_project_root() / "infer.py").is_file() else "NG"
    python_status = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    model_cache_status = "未確認"
    try:
        from huggingface_hub import try_to_load_from_cache

        cached_path = try_to_load_from_cache(DEFAULT_HF_CHECKPOINT, "model.safetensors")
        model_cache_status = "OK" if isinstance(cached_path, str) else "未キャッシュ"
    except Exception:
        model_cache_status = "確認不可"

    torch_status = "未確認"
    cuda_status = "未確認"
    if shutil.which("uv"):
        torch_check = _run_command(
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
        if torch_check.returncode == 0:
            torch_lines = [
                line.strip() for line in (torch_check.stdout or "").splitlines() if line.strip()
            ]
            torch_status = torch_lines[0] if torch_lines else "OK"
            cuda_status = " / ".join(torch_lines[1:]) if len(torch_lines) > 1 else "確認不可"
        else:
            torch_status = "確認失敗"
            cuda_status = (torch_check.stderr or torch_check.stdout or "").strip()[:200]
    else:
        torch_status = "uv未検出のため未確認"
        cuda_status = "uv未検出のため未確認"

    ffmpeg_run_status = "未検出"
    if shutil.which("ffmpeg"):
        ffmpeg_check = _run_command(["ffmpeg", "-version"])
        if ffmpeg_check.returncode == 0:
            ffmpeg_run_status = (ffmpeg_check.stdout or "").splitlines()[0]
        else:
            ffmpeg_run_status = "実行失敗"

    return "\n".join(
        [
            f"python: {python_status}",
            f"gradio: {gradio_status}",
            f"pydub: {pydub_status}",
            f"ffmpeg: {ffmpeg_status}",
            f"ffmpeg_run: {ffmpeg_run_status}",
            f"uv: {uv_status}",
            f"infer.py: {infer_status}",
            f"torch: {torch_status}",
            f"cuda: {cuda_status}",
            f"model_cache({DEFAULT_HF_CHECKPOINT}): {model_cache_status}",
        ]
    )


def _install_pydub() -> str:
    result = _run_command([sys.executable, "-m", "pip", "install", "--user", "pydub"])
    if result.returncode != 0:
        return "pydubのインストールに失敗しました。\n\n" + (result.stderr or result.stdout)
    return "pydubをインストールしました。反映されない場合はGUIを再起動してください。"


def _install_ffmpeg() -> str:
    if shutil.which("winget") is None:
        return (
            "wingetが見つかりません。Windows 10/11のApp Installerを更新するか、"
            "ffmpegを手動で導入してください。"
        )
    result = _run_command(
        [
            "winget",
            "install",
            "--id=Gyan.FFmpeg",
            "-e",
            "--scope",
            "user",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
    )
    if result.returncode != 0:
        return "ffmpegのインストールに失敗しました。\n\n" + (result.stderr or result.stdout)
    return "ffmpegをインストールしました。PATH反映のため、GUIを再起動してください。"


def _load_model(hf_checkpoint: str) -> str:
    checkpoint = str(hf_checkpoint or "").strip() or DEFAULT_HF_CHECKPOINT
    code = (
        "from huggingface_hub import hf_hub_download; "
        f"path = hf_hub_download(repo_id={checkpoint!r}, filename='model.safetensors'); "
        "print(path)"
    )
    result = _run_command(["uv", "run", "python", "-c", code])
    if result.returncode != 0:
        raise gr.Error("モデル準備に失敗しました。\n\n" + (result.stderr or result.stdout))
    model_path = (result.stdout or "").strip().splitlines()[-1]
    return (
        "モデルファイルを準備しました。\n"
        f"checkpoint: {checkpoint}\n"
        f"cached_path: {model_path}\n\n"
        "注意: Phase 2ではinfer.pyをsubprocess起動するため、生成時にもランタイム初期化が走ります。"
    )


def _wav_to_mp3(wav_path: Path, mp3_bitrate: int) -> tuple[Path | None, str]:
    """WAVをMP3に変換する。ffmpegがなければスキップ。"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None, "ffmpegが見つからないためMP3変換をスキップしました。"
    mp3_path = wav_path.with_suffix(".mp3")
    result = _run_command(
        [
            ffmpeg,
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            f"{int(mp3_bitrate)}k",
            str(mp3_path),
        ]
    )
    if result.returncode != 0:
        return None, f"MP3変換に失敗しました。\n{result.stderr or result.stdout}"
    return mp3_path, f"MP3生成: {mp3_path.resolve()} ({int(mp3_bitrate)}kbps)"


def _convert_existing_wav_to_mp3(
    wav_input: str | None,
    mp3_bitrate: int,
) -> tuple[str | None, str]:
    """既存のWAVファイルをMP3に変換する。"""
    if not wav_input or not str(wav_input).strip():
        raise gr.Error("変換するWAVファイルが指定されていません。先に音声を生成してください。")
    wav_path = Path(str(wav_input).strip())
    if not wav_path.is_file():
        raise gr.Error(f"WAVファイルが見つかりません: {wav_path}")
    mp3_path, msg = _wav_to_mp3(wav_path, mp3_bitrate)
    if mp3_path is None:
        raise gr.Error(msg)
    return str(mp3_path), msg


def _latest_project_dir() -> Path | None:
    if not OUTPUT_ROOT.is_dir():
        return None
    candidates = [path for path in OUTPUT_ROOT.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _ffmpeg_concat_escape(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", r"'\''")


def _merge_chunks(
    project_dir_str: str | None,
    mp3_bitrate: int,
) -> tuple[str | None, str | None, str]:
    """
    project_dir内のchunk_*.wavを番号順に結合してepisode.wavを生成。
    その後MP3にも変換する。

    戻り値: (episode_wav_path, episode_mp3_path, log)
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise gr.Error("ffmpegが見つかりません。環境チェックからffmpegを導入してください。")

    if project_dir_str and str(project_dir_str).strip():
        project_dir = Path(str(project_dir_str).strip())
    else:
        latest = _latest_project_dir()
        if latest is None:
            raise gr.Error("結合するプロジェクトフォルダが見つかりません。先に全チャンクを生成してください。")
        project_dir = latest

    if not project_dir.is_dir():
        raise gr.Error(f"プロジェクトフォルダが見つかりません: {project_dir}")

    chunk_paths = sorted(
        project_dir.glob("chunk_*.wav"),
        key=lambda path: int(re.search(r"chunk_(\d+)", path.stem).group(1))
        if re.search(r"chunk_(\d+)", path.stem)
        else 999999,
    )
    if not chunk_paths:
        raise gr.Error(f"結合対象のchunk_*.wavが見つかりません: {project_dir}")

    chunk_list = project_dir / "chunk_list.txt"
    chunk_list.write_text(
        "\n".join(f"file '{_ffmpeg_concat_escape(path)}'" for path in chunk_paths) + "\n",
        encoding="utf-8",
    )

    episode_wav = project_dir / "episode.wav"
    result = _run_command(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(chunk_list),
            "-c",
            "copy",
            str(episode_wav),
        ]
    )
    if result.returncode != 0:
        raise gr.Error("ffmpeg結合に失敗しました。\n\n" + (result.stderr or result.stdout))
    if not episode_wav.is_file():
        raise gr.Error("ffmpegは正常終了しましたが、episode.wavが見つかりませんでした。")

    episode_mp3, mp3_msg = _wav_to_mp3(episode_wav, int(mp3_bitrate))
    log = "\n".join(
        [
            "エピソード結合が完了しました。",
            f"project_dir: {project_dir.resolve()}",
            f"chunks: {len(chunk_paths)}",
            f"chunk_list: {chunk_list.resolve()}",
            f"episode_wav: {episode_wav.resolve()}",
            mp3_msg,
            "",
            "--- ffmpeg stdout ---",
            (result.stdout or "").strip(),
            "",
            "--- ffmpeg stderr ---",
            (result.stderr or "").strip(),
        ]
    )
    return str(episode_wav), str(episode_mp3) if episode_mp3 is not None else None, log


def _run_infer_for_chunk(
    chunk_text: str,
    output_wav: Path,
    ref_wav: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    hf_checkpoint: str,
) -> subprocess.CompletedProcess[str]:
    checkpoint = str(hf_checkpoint or "").strip() or DEFAULT_HF_CHECKPOINT
    cmd = [
        "uv",
        "run",
        "python",
        "infer.py",
        "--hf-checkpoint",
        checkpoint,
        "--text",
        chunk_text,
        "--cfg-scale-speaker",
        str(float(cfg_scale_speaker)),
        "--cfg-scale-text",
        str(float(cfg_scale_text)),
        "--num-steps",
        str(int(num_steps)),
        "--seed",
        str(int(seed)),
        "--output-wav",
        str(output_wav),
    ]
    if ref_wav:
        cmd.extend(["--ref-wav", ref_wav])
    else:
        cmd.append("--no-ref")
    return _run_command(cmd, cancellable=True)


def _chunk_status_label(index: int, total: int, status: str, message: str = "") -> str:
    mark = "✅" if status == "ok" else "❌"
    suffix = "" if status == "ok" else f" エラー: {_trim_for_preview(message, 90)}"
    return f"### チャンク {index}/{total} {mark}{suffix}"


def _empty_chunk_updates() -> list[object]:
    updates: list[object] = []
    for _ in range(MAX_CHUNKS):
        updates.extend(
            [
                gr.update(visible=False),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=None),
                gr.update(value=None),
            ]
        )
    return updates


def _chunk_updates_from_results(chunks: list[dict]) -> list[object]:
    updates: list[object] = []
    total = len(chunks)
    for i in range(MAX_CHUNKS):
        if i < total:
            item = chunks[i]
            updates.extend(
                [
                    gr.update(visible=True),
                    gr.update(
                        value=_chunk_status_label(
                            int(item["index"]),
                            total,
                            str(item["status"]),
                            str(item.get("error", "")),
                        )
                    ),
                    gr.update(value=str(item["text"])),
                    gr.update(value=item.get("wav") or None),
                    gr.update(value=item.get("mp3") or None),
                ]
            )
        else:
            updates.extend(
                [
                    gr.update(visible=False),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=None),
                    gr.update(value=None),
                ]
            )
    return updates


def _generate_all_chunks(
    project_name: str,
    script_text: str,
    split_method: str,
    max_chars: int,
    ref_path_text: str | None,
    uploaded_audio: str | None,
    recorded_audio: str | None,
    ref_drive_audio: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    mp3_bitrate: int,
    hf_checkpoint: str,
    progress: gr.Progress = gr.Progress(track_tqdm=False),
) -> tuple[list[dict], str]:
    """
    全チャンクを順次生成してリストで返す。

    戻り値:
        chunks: [{"index": 1, "text": "...", "wav": "path", "mp3": "path|None", "status": "ok|error"}, ...]
        log: str
    """
    _reset_cancel()

    chunks_text = _split_chunks(script_text, split_method, int(max_chars))
    if not chunks_text:
        raise gr.Error("生成できるチャンクがありません。台本を確認してください。")
    if len(chunks_text) > MAX_CHUNKS:
        raise gr.Error(f"チャンク数が{len(chunks_text)}件です。Phase 3では最大{MAX_CHUNKS}件までです。")

    # 既存フォルダがあれば再利用する（PCが落ちても続きから再開できる）
    project_dir = _resolve_project_dir(project_name, force_new=False)
    ref_wav, ref_summary = _resolve_reference_audio(
        project_dir=project_dir,
        ref_path_text=ref_path_text,
        uploaded_audio=uploaded_audio,
        recorded_audio=recorded_audio,
        ref_drive_audio=ref_drive_audio,
    )

    # 生成開始直後に project.json を自動保存（この時点でPCが落ちても条件は残る）
    _save_project_json(
        project_dir,
        project_name=project_name,
        script_text=script_text,
        split_method=split_method,
        max_chars=int(max_chars),
        ref_path_text=ref_path_text,
        cfg_scale_speaker=cfg_scale_speaker,
        cfg_scale_text=cfg_scale_text,
        num_steps=num_steps,
        seed=seed,
        mp3_bitrate=mp3_bitrate,
        hf_checkpoint=hf_checkpoint,
    )

    total = len(chunks_text)
    checkpoint = str(hf_checkpoint or "").strip() or DEFAULT_HF_CHECKPOINT
    results: list[dict] = []
    log_lines = [
        f"Phase 3: 全チャンク生成を開始しました。chunks={total}",
        f"project_dir: {project_dir.resolve()}",
        f"checkpoint: {checkpoint}",
        ref_summary,
        "project.json を保存しました（再開用）。",
        "",
    ]

    skipped_count = 0
    for index, chunk_text in enumerate(chunks_text, start=1):
        if _is_cancel_requested():
            log_lines.append("ユーザー操作により生成を中断しました。")
            break
        progress((index - 1) / total, desc=f"チャンク {index}/{total} 生成中...")
        output_wav = project_dir / f"chunk_{index:02d}.wav"
        text_file = project_dir / f"chunk_{index:02d}.txt"

        # ── 再開：既存WAVがあり台本も一致するならスキップ ──
        if _is_valid_wav(output_wav) and text_file.is_file():
            saved_text = text_file.read_text(encoding="utf-8")
            if saved_text == chunk_text:
                mp3_path = project_dir / f"chunk_{index:02d}.mp3"
                results.append(
                    {
                        "index": index,
                        "text": chunk_text,
                        "wav": str(output_wav),
                        "mp3": str(mp3_path) if mp3_path.is_file() else None,
                        "status": "ok",
                        "project_dir": str(project_dir.resolve()),
                    }
                )
                skipped_count += 1
                log_lines.append(f"[SKIP] chunk_{index:02d}: 生成済みのため再開スキップ")
                continue

        text_file.write_text(chunk_text, encoding="utf-8")

        item: dict = {
            "index": index,
            "text": chunk_text,
            "wav": str(output_wav),
            "mp3": None,
            "status": "error",
            "project_dir": str(project_dir.resolve()),
        }
        try:
            result = _run_infer_for_chunk(
                chunk_text=chunk_text,
                output_wav=output_wav,
                ref_wav=ref_wav,
                cfg_scale_speaker=cfg_scale_speaker,
                cfg_scale_text=cfg_scale_text,
                num_steps=num_steps,
                seed=int(seed) + index - 1,
                hf_checkpoint=checkpoint,
            )
            if _is_cancel_requested():
                raise RuntimeError("ユーザー操作により生成を中断しました。")
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "infer.py failed").strip())
            if not output_wav.is_file():
                raise RuntimeError("infer.pyは正常終了しましたが、音声ファイルが見つかりませんでした。")

            mp3_path, mp3_msg = _wav_to_mp3(output_wav, int(mp3_bitrate))
            item["mp3"] = str(mp3_path) if mp3_path is not None else None
            item["status"] = "ok"
            log_lines.extend(
                [
                    f"[OK] chunk_{index:02d}: {output_wav.resolve()}",
                    f"     {mp3_msg}",
                ]
            )
        except Exception as exc:
            item["wav"] = str(output_wav) if output_wav.is_file() else None
            item["error"] = str(exc)
            log_lines.append(f"[ERROR] chunk_{index:02d}: {exc}")
        results.append(item)
        if _is_cancel_requested():
            break

    progress(1.0, desc=f"チャンク {total}/{total} 完了")
    ok_count = sum(1 for item in results if item.get("status") == "ok")
    summary = f"完了: {ok_count}/{total} チャンク成功"
    if skipped_count:
        summary += f"（うち {skipped_count} 件は生成済みのためスキップ）"
    log_lines.extend(["", summary])
    return results, "\n".join(log_lines)


def _generate_all_chunks_for_ui(
    project_name: str,
    script_text: str,
    split_method: str,
    max_chars: int,
    ref_path_text: str | None,
    uploaded_audio: str | None,
    recorded_audio: str | None,
    ref_drive_audio: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    mp3_bitrate: int,
    hf_checkpoint: str,
    progress: gr.Progress = gr.Progress(track_tqdm=False),
) -> tuple[object, ...]:
    chunks, log = _generate_all_chunks(
        project_name=project_name,
        script_text=script_text,
        split_method=split_method,
        max_chars=max_chars,
        ref_path_text=ref_path_text,
        uploaded_audio=uploaded_audio,
        recorded_audio=recorded_audio,
        cfg_scale_speaker=cfg_scale_speaker,
        cfg_scale_text=cfg_scale_text,
        num_steps=num_steps,
        seed=seed,
        mp3_bitrate=mp3_bitrate,
        hf_checkpoint=hf_checkpoint,
        progress=progress,
    )
    project_dir = str(chunks[0].get("project_dir", "")) if chunks else ""
    first_ok = next((item for item in chunks if item.get("status") == "ok"), None)
    first_wav = first_ok.get("wav") if first_ok else None
    first_mp3 = first_ok.get("mp3") if first_ok else None
    return (
        *_chunk_updates_from_results(chunks),
        project_dir,
        first_wav,
        first_mp3,
        log,
    )


def _regenerate_chunk(
    project_dir_str: str | None,
    chunk_index: int,
    chunk_text: str,
    ref_path_text: str | None,
    uploaded_audio: str | None,
    recorded_audio: str | None,
    ref_drive_audio: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    mp3_bitrate: int,
    hf_checkpoint: str,
) -> tuple[str, str, str | None, str | None, str]:
    if not project_dir_str or not str(project_dir_str).strip():
        raise gr.Error("先に全チャンクを生成してください。")
    _reset_cancel()
    text = _first_chunk(chunk_text)
    project_dir = Path(str(project_dir_str))
    if not project_dir.is_dir():
        raise gr.Error(f"プロジェクトフォルダが見つかりません: {project_dir}")

    ref_wav, ref_summary = _resolve_reference_audio(
        project_dir=project_dir,
        ref_path_text=ref_path_text,
        uploaded_audio=uploaded_audio,
        recorded_audio=recorded_audio,
        ref_drive_audio=ref_drive_audio,
    )
    output_wav = project_dir / f"chunk_{int(chunk_index):02d}.wav"
    text_file = project_dir / f"chunk_{int(chunk_index):02d}.txt"
    text_file.write_text(text, encoding="utf-8")
    result = _run_infer_for_chunk(
        chunk_text=text,
        output_wav=output_wav,
        ref_wav=ref_wav,
        cfg_scale_speaker=cfg_scale_speaker,
        cfg_scale_text=cfg_scale_text,
        num_steps=num_steps,
        seed=int(seed) + int(chunk_index),
        hf_checkpoint=hf_checkpoint,
    )
    if _is_cancel_requested():
        return (
            f"### チャンク {int(chunk_index)} ❌ 中断",
            text,
            None,
            None,
            f"チャンク {int(chunk_index):02d} の再生成を中断しました。",
        )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "infer.py failed").strip()
        return (
            _chunk_status_label(int(chunk_index), int(chunk_index), "error", msg),
            text,
            None,
            None,
            f"チャンク {int(chunk_index):02d} の再生成に失敗しました。\n{msg}",
        )
    if not output_wav.is_file():
        raise gr.Error("infer.pyは正常終了しましたが、音声ファイルが見つかりませんでした。")
    mp3_path, mp3_msg = _wav_to_mp3(output_wav, int(mp3_bitrate))
    log = "\n".join(
        [
            f"チャンク {int(chunk_index):02d} を再生成しました。",
            f"output_wav: {output_wav.resolve()}",
            mp3_msg,
            ref_summary,
        ]
    )
    return (
        f"### チャンク {int(chunk_index)} ✅ 再生成済み",
        text,
        str(output_wav),
        str(mp3_path) if mp3_path is not None else None,
        log,
    )




def _generate_one_chunk(
    project_name: str,
    script_text: str,
    ref_path_text: str | None,
    uploaded_audio: str | None,
    recorded_audio: str | None,
    ref_drive_audio: str | None,
    cfg_scale_speaker: float,
    cfg_scale_text: float,
    num_steps: int,
    seed: int,
    mp3_bitrate: int,
    hf_checkpoint: str,
    progress: gr.Progress = gr.Progress(track_tqdm=False),
) -> tuple[str, str | None, str]:
    _reset_cancel()
    chunk_text = _first_chunk(script_text)
    project_dir = _create_project_dir(project_name)
    output_wav = project_dir / "chunk_01.wav"
    text_file = project_dir / "chunk_01.txt"
    text_file.write_text(chunk_text, encoding="utf-8")

    ref_wav, ref_summary = _resolve_reference_audio(
        project_dir=project_dir,
        ref_path_text=ref_path_text,
        uploaded_audio=uploaded_audio,
        recorded_audio=recorded_audio,
        ref_drive_audio=ref_drive_audio,
    )

    checkpoint = str(hf_checkpoint or "").strip() or DEFAULT_HF_CHECKPOINT
    cmd = [
        "uv",
        "run",
        "python",
        "infer.py",
        "--hf-checkpoint",
        checkpoint,
        "--text",
        chunk_text,
        "--cfg-scale-speaker",
        str(float(cfg_scale_speaker)),
        "--cfg-scale-text",
        str(float(cfg_scale_text)),
        "--num-steps",
        str(int(num_steps)),
        "--seed",
        str(int(seed)),
        "--output-wav",
        str(output_wav),
    ]
    if ref_wav:
        cmd.extend(["--ref-wav", ref_wav])
    else:
        cmd.append("--no-ref")

    progress(0.1, desc="チャンク 1/1 生成準備中...")
    result = _run_command(cmd, cancellable=True)
    progress(0.9, desc="チャンク 1/1 保存確認中...")
    if _is_cancel_requested():
        raise gr.Error("生成を中断しました。")
    if result.returncode != 0:
        raise gr.Error("生成に失敗しました。\n\n" + (result.stderr or result.stdout))
    if not output_wav.is_file():
        raise gr.Error("infer.pyは正常終了しましたが、音声ファイルが見つかりませんでした。")

    mp3_path, mp3_msg = _wav_to_mp3(output_wav, int(mp3_bitrate))
    progress(1.0, desc="チャンク 1/1 完了")
    log = "\n".join(
        [
            "Phase 2: 1チャンク生成が完了しました。",
            f"project_dir: {project_dir.resolve()}",
            f"output_wav: {output_wav.resolve()}",
            mp3_msg,
            f"text_file: {text_file.resolve()}",
            f"checkpoint: {checkpoint}",
            ref_summary,
            f"preview: {_trim_for_preview(chunk_text)}",
            "",
            "--- infer.py stdout ---",
            (result.stdout or "").strip(),
            "",
            "--- infer.py stderr ---",
            (result.stderr or "").strip(),
        ]
    )
    return str(output_wav), str(mp3_path) if mp3_path is not None else None, log


def build_ui() -> gr.Blocks:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Base(), title=APP_TITLE) as demo:
        project_dir_state = gr.State(value=None)

        gr.Markdown(
            """
            # IrodoriTTS Studio
            Vocal Synthesis Engine — 台本をチャンク分割し、WAV/MP3を連続生成します
            """,
            elem_classes=["hero"],
        )

        with gr.Tabs():
            with gr.TabItem("🎬 連続生成"):
                with gr.Accordion("モデルロード（必要な時だけ開く）", open=False, elem_classes=["studio-card"]):
                    gr.Markdown("通常は開かなくてOKです。初回準備やモデル確認が必要な時だけ使います。")
                    with gr.Row():
                        load_model_btn = gr.Button(
                            "モデルロード（初回準備）",
                            variant="secondary",
                        )
                        model_status = gr.Textbox(label="モデル状態", lines=5, interactive=False)

                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### プロジェクト", elem_classes=["section-title"])
                    gr.Markdown(
                        "保存名を入れておくと、生成結果をあとから見つけやすくなります。\n\n"
                        "生成時に project.json が自動保存されます。再開するときは、その project.json を読み込みます。",
                        elem_classes=["project-help"],
                    )

                    # 内部処理用。通常画面には表示しない。
                    project_name = gr.Textbox(
                        label="保存名（内部用）",
                        value="",
                        visible=False,
                    )
                    hf_checkpoint = gr.Textbox(
                        label="HF checkpoint",
                        value=DEFAULT_HF_CHECKPOINT,
                        visible=False,
                    )

                    with gr.Group(elem_classes=["studio-card"]):
                        gr.Markdown("#### 1. 保存名", elem_classes=["section-title"])
                        gr.Markdown(
                            "あとで探しやすい名前を付けます。空欄でも生成できます。",
                            elem_classes=["project-help"],
                        )
                        manual_project_name = gr.Textbox(
                            label="保存名",
                            placeholder="例: chapter01_test / sample_voice / note_demo",
                        )
                        save_project_btn = gr.Button(
                            "💾 今の台本と設定を保存",
                            variant="secondary",
                        )

                    with gr.Group(elem_classes=["studio-card"]):
                        gr.Markdown("#### 2. 読み込み", elem_classes=["section-title"])
                        gr.Markdown(
                            "以前の続きから作業するときは `project.json` を選びます。",
                            elem_classes=["project-help"],
                        )

                        with gr.Tabs():
                            with gr.Tab("Colab内"):
                                gr.Markdown(
                                    "このColabで生成したプロジェクトを再開します。",
                                    elem_classes=["project-help"],
                                )
                                project_json_outputs = gr.FileExplorer(
                                    label="project.jsonを選択",
                                    root_dir=str(OUTPUT_ROOT),
                                    file_count="single",
                                )
                                load_project_from_outputs_btn = gr.Button(
                                    "📂 このColab内のproject.jsonから読込",
                                    variant="secondary",
                                )

                            with gr.Tab("Google Drive"):
                                gr.Markdown(
                                    "Driveに保存した project.json を読み込みます。先にDriveをマウントしてください。",
                                    elem_classes=["project-help"],
                                )
                                project_json_drive = gr.FileExplorer(
                                    label="Drive内のproject.json",
                                    root_dir=_drive_root_for_file_explorer(),
                                    file_count="single",
                                )
                                load_project_from_drive_btn = gr.Button(
                                    "📂 Driveのproject.jsonから読込",
                                    variant="secondary",
                                )

                            with gr.Tab("アップロード"):
                                gr.Markdown(
                                    "PCやスマホにある project.json を読み込みます。",
                                    elem_classes=["project-help"],
                                )
                                project_json_file = gr.File(
                                    label="project.json",
                                    file_types=[".json"],
                                    type="filepath",
                                )
                                load_project_from_json_btn = gr.Button(
                                    "📂 アップロードしたproject.jsonから読込",
                                    variant="secondary",
                                )

                    # 旧イベント互換用。表示しない。
                    load_project_dropdown = gr.Dropdown(
                        label="保存済みプロジェクト",
                        choices=_list_saved_projects(),
                        visible=False,
                    )
                    load_project_btn = gr.Button(
                        "📂 読込",
                        variant="secondary",
                        visible=False,
                    )
                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### 台本", elem_classes=["section-title"])
                    script_text = gr.Textbox(
                        label="📄 台本 ✱（複数行テキストエリア）",
                        lines=8,
                        placeholder="😌 こんにちは。今日はIrodoriTTSのテストです。",
                        elem_classes=["required-label"],
                    )

                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### チャンク分割", elem_classes=["section-title"])
                    split_method = gr.Radio(
                        label="分割方法",
                        choices=[
                            ("句点・段落で自動（推奨）", "auto"),
                            ("文字数で自動", "chars"),
                            ("[BREAK]タグで手動", "manual"),
                        ],
                        value="auto",
                    )
                    max_chars = gr.Slider(
                        label="最大文字数（文字数で自動分割時に使用）",
                        minimum=80,
                        maximum=300,
                        value=150,
                        step=10,
                    )

                with gr.Group(elem_classes=["studio-card", "reference-card"]):
                    gr.Markdown("### 参照音声", elem_classes=["section-title"])
                    gr.Markdown(
                        "任意です。未指定の場合は参照音声なしで生成します。\n\n"
                        "基本はアップロード、録音、またはGoogle Driveから選択してください。"
                    )
                    with gr.Group(elem_classes=["input-subcard"]):
                        uploaded_audio = gr.Audio(
                            label="1. 参照音声をアップロード",
                            type="filepath",
                        )
                    with gr.Group(elem_classes=["input-subcard"]):
                        recorded_audio = gr.Audio(
                            label="2. その場で録音",
                            sources=["microphone"],
                            type="filepath",
                        )
                    with gr.Accordion("3. Google Driveから参照音声を選択", open=False):
                        gr.Markdown("先にColabのGoogle Driveマウントセルを実行してください。")
                        ref_drive_audio = gr.FileExplorer(
                            label="Drive内の参照音声",
                            root_dir=_drive_root_for_file_explorer(),
                            file_count="single",
                        )
                        use_drive_ref_btn = gr.Button(
                            "このDrive音声を参照音声に使う",
                            variant="secondary",
                        )
                        selected_drive_ref_status = gr.Textbox(
                            label="選択中のDrive参照音声",
                            value="未選択です。",
                            lines=3,
                            interactive=False,
                            elem_classes=["log-area"],
                        )
                    with gr.Accordion("詳細：パス指定", open=False):
                        gr.Markdown("すでにDrive内の音声ファイルパスが分かっている場合だけ使います。")
                        ref_path_text = gr.Textbox(
                            label="参照音声パス",
                            placeholder=r"/content/drive/MyDrive/IrodoriTTS_VoiceDesign/voicedesign_42_20260530_123456.wav",
                        )
                with gr.Accordion("詳細設定", open=False, elem_classes=["studio-card"]):
                    with gr.Row():
                        cfg_scale_speaker = gr.Slider(
                            label="cfg-scale-speaker",
                            minimum=3.0,
                            maximum=10.0,
                            value=7.0,
                            step=0.1,
                        )
                        cfg_scale_text = gr.Slider(
                            label="cfg-scale-text",
                            minimum=1.0,
                            maximum=5.0,
                            value=2.5,
                            step=0.1,
                        )
                    with gr.Row():
                        num_steps = gr.Slider(
                            label="num-steps",
                            minimum=20,
                            maximum=100,
                            value=60,
                            step=1,
                            info="生成ステップ数。多いほど品質が上がるが生成時間も増加。20〜40=高速、60=バランス（推奨）、80〜100=高品質",
                        )
                        seed = gr.Number(label="seed", value=42, precision=0)
                    mp3_bitrate = gr.Slider(
                        label="MP3ビットレート (kbps)",
                        minimum=64,
                        maximum=320,
                        value=192,
                        step=32,
                        info="128=標準 / 192=配信向け（推奨） / 320=高品質",
                    )

                generate_btn = gr.Button(
                    "🎬 全チャンクを生成",
                    variant="primary",
                    elem_classes=["btn-primary", "hero-generate"],
                )
                cancel_btn = gr.Button("⏹ 生成中断", variant="secondary")

                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### 出力", elem_classes=["section-title"])
                    with gr.Row():
                        output_audio = gr.Audio(label="WAV", type="filepath", interactive=False)
                        output_mp3 = gr.Audio(
                            label="MP3（自動生成）",
                            type="filepath",
                            interactive=False,
                        )

                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### チャンク確認", elem_classes=["section-title"])
                    gr.Markdown(
                        f"最大{MAX_CHUNKS}チャンクまで表示します。"
                        "テキスト編集後に個別再生成できます。"
                    )
                    chunk_rows: list[dict[str, object]] = []
                    for i in range(MAX_CHUNKS):
                        with gr.Group(visible=False, elem_classes=["studio-card"]) as row:
                            chunk_label = gr.Markdown(f"### チャンク {i + 1}")
                            chunk_text_box = gr.Textbox(
                                label="テキスト編集",
                                lines=2,
                                interactive=True,
                            )
                            with gr.Row():
                                chunk_wav = gr.Audio(
                                    label="WAV",
                                    type="filepath",
                                    interactive=False,
                                )
                                chunk_mp3 = gr.Audio(
                                    label="MP3",
                                    type="filepath",
                                    interactive=False,
                                )
                            regen_btn = gr.Button("🔄 再生成", size="sm")
                        chunk_rows.append(
                            {
                                "row": row,
                                "label": chunk_label,
                                "text": chunk_text_box,
                                "wav": chunk_wav,
                                "mp3": chunk_mp3,
                                "regen": regen_btn,
                            }
                        )

                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### WAV → MP3変換", elem_classes=["section-title"])
                    with gr.Row():
                        wav_to_mp3_input = gr.Audio(label="既存WAVをMP3変換", type="filepath")
                        wav_to_mp3_btn = gr.Button("🎵 WAV → MP3変換")
                    convert_mp3_output = gr.Audio(
                        label="変換済みMP3",
                        type="filepath",
                        interactive=False,
                    )
                    merge_btn = gr.Button(
                        "🔗 結合してエピソード完成",
                        variant="primary",
                        elem_classes=["btn-primary"],
                    )
                    with gr.Row():
                        episode_wav = gr.Audio(
                            label="エピソード（WAV）",
                            type="filepath",
                            interactive=False,
                        )
                        episode_mp3 = gr.Audio(
                            label="エピソード（MP3）",
                            type="filepath",
                            interactive=False,
                        )
                    convert_log = gr.Textbox(
                        label="変換ログ",
                        lines=3,
                        interactive=False,
                        elem_classes=["log-area"],
                    )
                    merge_log = gr.Textbox(
                        label="結合ログ",
                        lines=4,
                        interactive=False,
                        elem_classes=["log-area"],
                    )

                with gr.Group(elem_classes=["studio-card"]):
                    gr.Markdown("### 進捗・ログ", elem_classes=["section-title"])
                    run_log = gr.Textbox(
                        label="生成ログ",
                        lines=14,
                        interactive=False,
                        elem_classes=["log-area"],
                    )

                with gr.Accordion(
                    "環境チェック・モジュール導入",
                    open=False,
                    elem_classes=["studio-card"],
                ):
                    env_status = gr.Textbox(label="環境状態", value=_check_environment(), lines=6)
                    with gr.Row():
                        check_env_btn = gr.Button("環境チェック")
                        install_pydub_btn = gr.Button("pydubインストール（pip --user）")
                        install_ffmpeg_btn = gr.Button("ffmpegインストール（winget）")


        load_model_btn.click(_load_model, inputs=[hf_checkpoint], outputs=[model_status])
        chunk_outputs: list[object] = []
        for row in chunk_rows:
            chunk_outputs.extend(
                [
                    row["row"],
                    row["label"],
                    row["text"],
                    row["wav"],
                    row["mp3"],
                ]
            )

        generate_btn.click(
            _generate_all_chunks_for_ui,
            inputs=[
                manual_project_name,
                script_text,
                split_method,
                max_chars,
                ref_path_text,
                uploaded_audio,
                recorded_audio,
                ref_drive_audio,
                cfg_scale_speaker,
                cfg_scale_text,
                num_steps,
                seed,
                mp3_bitrate,
                hf_checkpoint,
            ],
            outputs=[*chunk_outputs, project_dir_state, output_audio, output_mp3, run_log],
        )
        cancel_btn.click(_request_cancel, outputs=[run_log], queue=False)
        for i, row in enumerate(chunk_rows, start=1):
            row["regen"].click(
                _regenerate_chunk,
                inputs=[
                    project_dir_state,
                    gr.State(i),
                    row["text"],
                    ref_path_text,
                    uploaded_audio,
                    recorded_audio,
                    cfg_scale_speaker,
                    cfg_scale_text,
                    num_steps,
                    seed,
                    mp3_bitrate,
                    hf_checkpoint,
                ],
                outputs=[
                    row["label"],
                    row["text"],
                    row["wav"],
                    row["mp3"],
                    run_log,
                ],
            )
        wav_to_mp3_btn.click(
            _convert_existing_wav_to_mp3,
            inputs=[wav_to_mp3_input, mp3_bitrate],
            outputs=[convert_mp3_output, convert_log],
        )
        merge_btn.click(
            _merge_chunks,
            inputs=[project_dir_state, mp3_bitrate],
            outputs=[episode_wav, episode_mp3, merge_log],
        )
        save_project_btn.click(
            _save_project_for_ui,
            inputs=[
                manual_project_name,
                script_text,
                split_method,
                max_chars,
                ref_path_text,
                cfg_scale_speaker,
                cfg_scale_text,
                num_steps,
                seed,
                mp3_bitrate,
                hf_checkpoint,
            ],
            outputs=[load_project_dropdown, run_log],
        )
        load_project_btn.click(
            _load_project_for_ui,
            inputs=[load_project_dropdown],
            outputs=[
                manual_project_name,
                script_text,
                split_method,
                max_chars,
                ref_path_text,
                cfg_scale_speaker,
                cfg_scale_text,
                num_steps,
                seed,
                mp3_bitrate,
                hf_checkpoint,
                run_log,
            ],
        )

        load_project_from_json_btn.click(
            _load_project_from_json_file_for_ui,
            inputs=[project_json_file],
            outputs=[
                manual_project_name,
                script_text,
                split_method,
                max_chars,
                ref_path_text,
                cfg_scale_speaker,
                cfg_scale_text,
                num_steps,
                seed,
                mp3_bitrate,
                hf_checkpoint,
                run_log,
            ],
        )

        load_project_from_outputs_btn.click(
            _load_project_from_json_file_for_ui,
            inputs=[project_json_outputs],
            outputs=[
                manual_project_name,
                script_text,
                split_method,
                max_chars,
                ref_path_text,
                cfg_scale_speaker,
                cfg_scale_text,
                num_steps,
                seed,
                mp3_bitrate,
                hf_checkpoint,
                run_log,
            ],
        )

        load_project_from_drive_btn.click(
            _load_project_from_json_file_for_ui,
            inputs=[project_json_drive],
            outputs=[
                manual_project_name,
                script_text,
                split_method,
                max_chars,
                ref_path_text,
                cfg_scale_speaker,
                cfg_scale_text,
                num_steps,
                seed,
                mp3_bitrate,
                hf_checkpoint,
                run_log,
            ],
        )

        use_drive_ref_btn.click(
            _show_selected_drive_reference,
            inputs=[ref_drive_audio],
            outputs=[selected_drive_ref_status, ref_path_text],
            queue=False,
        )
        check_env_btn.click(_check_environment, outputs=[env_status])
        install_pydub_btn.click(_install_pydub, outputs=[env_status])
        install_ffmpeg_btn.click(_install_ffmpeg, outputs=[env_status])



    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="IrodoriTTS continuous generation GUI.")
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
    )


if __name__ == "__main__":
    main()