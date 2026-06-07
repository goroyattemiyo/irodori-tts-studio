#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

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


def _output_file_url(path_value: str | None) -> str | None:
    """OUTPUT_ROOT配下のファイルパスを /outputs/... URL に変換する。"""
    if not path_value:
        return None

    path = Path(str(path_value)).expanduser()
    try:
        resolved = path.resolve()
        relative = resolved.relative_to(OUTPUT_ROOT.resolve())
    except (OSError, ValueError):
        return None

    if not resolved.is_file():
        return None

    return "/outputs/" + "/".join(quote(part) for part in relative.parts)


def _attach_output_urls(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """生成結果チャンクにWeb UI用の wav_url / mp3_url を追加する。"""
    updated: list[dict[str, Any]] = []
    for item in chunks:
        row = dict(item)
        row["wav_url"] = _output_file_url(row.get("wav"))
        row["mp3_url"] = _output_file_url(row.get("mp3"))
        updated.append(row)
    return updated


_GENERATE_JOBS: dict[str, dict[str, Any]] = {}
_GENERATE_JOBS_LOCK = threading.Lock()


def _update_generate_job(job_id: str, **values: Any) -> None:
    with _GENERATE_JOBS_LOCK:
        job = _GENERATE_JOBS.setdefault(job_id, {})
        job.update(values)
        job["updated_at"] = datetime.now().isoformat(timespec="seconds")


def _get_generate_job(job_id: str) -> dict[str, Any] | None:
    with _GENERATE_JOBS_LOCK:
        job = _GENERATE_JOBS.get(job_id)
        return dict(job) if job is not None else None


def _run_generate_job(job_id: str, params: dict[str, Any]) -> None:
    _update_generate_job(
        job_id,
        status="running",
        message="生成を開始しました。",
        log=["生成ジョブを開始しました。"],
    )

    started_at = time.monotonic()

    try:
        from app.irodori_app import DEFAULT_HF_CHECKPOINT, _generate_all_chunks

        chunks, log_text = _generate_all_chunks(
            project_name=params["project_name"],
            script_text=params["script_text"],
            split_method=params["split_method"],
            max_chars=int(params["max_chars"]),
            ref_path_text=None,
            uploaded_audio=None,
            recorded_audio=None,
            ref_drive_audio=None,
            cfg_scale_speaker=float(params["cfg_scale_speaker"]),
            cfg_scale_text=float(params["cfg_scale_text"]),
            num_steps=int(params["num_steps"]),
            seed=int(params["seed"]),
            mp3_bitrate=int(params["mp3_bitrate"]),
            hf_checkpoint=DEFAULT_HF_CHECKPOINT,
        )

        chunks_with_urls = _attach_output_urls(chunks)
        ok_count = sum(1 for item in chunks_with_urls if item.get("status") == "ok")
        elapsed_sec = int(time.monotonic() - started_at)
        log_lines = str(log_text or "").splitlines()

        _update_generate_job(
            job_id,
            status="done",
            ok=ok_count == len(chunks_with_urls),
            message=f"生成完了: {ok_count}/{len(chunks_with_urls)} チャンク成功",
            chunks=chunks_with_urls,
            log=log_lines,
            elapsed_sec=elapsed_sec,
        )
    except Exception as exc:
        elapsed_sec = int(time.monotonic() - started_at)
        _update_generate_job(
            job_id,
            status="error",
            ok=False,
            message=f"生成に失敗しました: {exc}",
            error=str(exc),
            traceback=traceback.format_exc(),
            elapsed_sec=elapsed_sec,
        )


@app.post("/api/generate/start")
async def generate_audio_start(
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
    """長時間生成用。生成ジョブを開始し、すぐjob_idを返す。"""
    job_id = str(uuid.uuid4())
    params = {
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

    _update_generate_job(
        job_id,
        status="queued",
        ok=None,
        message="生成ジョブを受け付けました。",
        chunks=[],
        log=["生成ジョブを受け付けました。"],
        elapsed_sec=0,
    )

    thread = threading.Thread(
        target=_run_generate_job,
        args=(job_id, params),
        daemon=True,
    )
    thread.start()

    return JSONResponse(
        {
            "ok": True,
            "job_id": job_id,
            "status": "queued",
            "message": "生成ジョブを開始しました。",
        }
    )


@app.get("/api/generate/status/{job_id}")
async def generate_audio_status(job_id: str) -> JSONResponse:
    """生成ジョブの状態を返す。Web UIはこのAPIを定期的に確認する。"""
    job = _get_generate_job(job_id)
    if job is None:
        return JSONResponse(
            {
                "ok": False,
                "status": "not_found",
                "message": "指定された生成ジョブが見つかりません。",
            },
            status_code=404,
        )

    return JSONResponse(
        {
            "ok": job.get("ok"),
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "message": job.get("message", ""),
            "chunks": job.get("chunks", []),
            "log": job.get("log", []),
            "elapsed_sec": job.get("elapsed_sec", 0),
            "error": job.get("error"),
        }
    )


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

    chunks_with_urls = _attach_output_urls(chunks)
    ok_count = sum(1 for item in chunks_with_urls if item.get("status") == "ok")
    return JSONResponse(
        {
            "ok": ok_count == len(chunks_with_urls),
            "message": f"生成完了: {ok_count}/{len(chunks_with_urls)} チャンク成功",
            "chunks": chunks_with_urls,
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
