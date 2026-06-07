#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

APP_TITLE = "IrodoriTTS Studio Web UI"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
WEB_DIR = APP_DIR / "web"
ASSETS_DIR = APP_DIR / "assets"

from app.irodori_app import OUTPUT_ROOT as IRODORI_OUTPUT_ROOT

OUTPUT_ROOT = IRODORI_OUTPUT_ROOT
PROJECT_EXPORTS = PROJECT_ROOT / "project_exports"

OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
PROJECT_EXPORTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_TITLE)

app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_ROOT)), name="outputs")
app.mount("/project_exports", StaticFiles(directory=str(PROJECT_EXPORTS)), name="project_exports")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "app": APP_TITLE,
        "python": sys.version.split()[0],
        "project_root": str(PROJECT_ROOT),
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/project/export")
async def export_project(
    project_name: str = Form("irodori_project"),
    script_text: str = Form(""),
    split_method: str = Form("auto"),
    max_chars: int = Form(150),
    cfg_scale_speaker: float = Form(7.0),
    cfg_scale_text: float = Form(2.5),
    num_steps: int = Form(60),
    seed: int = Form(42),
    mp3_bitrate: int = Form(192),
) -> JSONResponse:
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in project_name.strip()) or "irodori_project"
    filename = f"{safe_name}_{datetime.now():%Y%m%d_%H%M%S}_project.json"
    path = PROJECT_EXPORTS / filename

    data = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "project_name": project_name,
        "script_text": script_text,
        "split_method": split_method,
        "max_chars": int(max_chars),
        "cfg_scale_speaker": float(cfg_scale_speaker),
        "cfg_scale_text": float(cfg_scale_text),
        "num_steps": int(num_steps),
        "seed": int(seed),
        "mp3_bitrate": int(mp3_bitrate),
    }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return JSONResponse(
        {
            "ok": True,
            "message": "プロジェクトを書き出しました。",
            "filename": filename,
            "download_url": f"/project_exports/{filename}",
            "data": data,
        }
    )


@app.post("/api/project/import")
async def import_project(file: UploadFile = File(...)) -> JSONResponse:
    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "message": f"JSONを読み込めませんでした: {exc}"},
            status_code=400,
        )

    return JSONResponse(
        {
            "ok": True,
            "message": "プロジェクトJSONを読み込みました。",
            "data": data,
        }
    )


def _split_by_length(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
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


@app.post("/api/chunks/preview")
async def chunks_preview(
    script_text: str = Form(""),
    split_method: str = Form("auto"),
    max_chars: int = Form(150),
) -> JSONResponse:
    text = script_text.strip()
    if not text:
        return JSONResponse({"ok": True, "chunks": [], "count": 0})

    if split_method == "manual":
        chunks = [part.strip() for part in text.replace("[BREAK]", "\n[BREAK]\n").split("[BREAK]") if part.strip()]
    else:
        chunks = _split_by_length(text, int(max_chars))

    return JSONResponse(
        {
            "ok": True,
            "count": len(chunks),
            "chunks": [
                {
                    "index": i + 1,
                    "text": chunk,
                    "chars": len(chunk),
                    "status": "待機中",
                }
                for i, chunk in enumerate(chunks)
            ],
        }
    )



@app.post("/api/generate")
async def generate_audio(
    project_name: str = Form("irodori_project"),
    script_text: str = Form(""),
    split_method: str = Form("auto"),
    max_chars: int = Form(150),
    cfg_scale_speaker: float = Form(7.0),
    cfg_scale_text: float = Form(2.5),
    num_steps: int = Form(60),
    seed: int = Form(42),
    mp3_bitrate: int = Form(192),
) -> JSONResponse:
    """Web UIから実生成を実行する。まずは参照音声なしで既存生成処理へ接続する。"""
    try:
        from app.irodori_app import DEFAULT_HF_CHECKPOINT, _generate_all_chunks

        chunks, log = _generate_all_chunks(
            project_name=project_name,
            script_text=script_text,
            split_method=split_method,
            max_chars=int(max_chars),
            ref_path_text=None,
            uploaded_audio=None,
            recorded_audio=None,
            ref_drive_audio=None,
            cfg_scale_speaker=float(cfg_scale_speaker),
            cfg_scale_text=float(cfg_scale_text),
            num_steps=int(num_steps),
            seed=int(seed),
            mp3_bitrate=int(mp3_bitrate),
            hf_checkpoint=DEFAULT_HF_CHECKPOINT,
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "message": f"生成に失敗しました: {exc}",
            },
            status_code=500,
        )

    ok_count = sum(1 for item in chunks if item.get("status") == "ok")
    return JSONResponse(
        {
            "ok": ok_count == len(chunks),
            "message": f"生成完了: {ok_count}/{len(chunks)} チャンク成功",
            "chunks": chunks,
            "log": log,
        }
    )


@app.post("/api/generate/mock")
async def generate_mock(script_text: str = Form("")) -> JSONResponse:
    # まずはUI接続確認用。実生成接続は次フェーズ。
    job_id = str(uuid.uuid4())
    time.sleep(0.5)
    return JSONResponse(
        {
            "ok": True,
            "job_id": job_id,
            "message": "生成処理のモックを実行しました。次フェーズでinfer.pyへ接続します。",
            "script_chars": len(script_text or ""),
        }
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.api_server:app",
        host="0.0.0.0",
        port=7860,
        reload=False,
    )


if __name__ == "__main__":
    main()
