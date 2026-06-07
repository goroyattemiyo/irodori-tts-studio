const $ = (id) => document.getElementById(id);

let latestGeneratedChunks = [];

function log(message) {
  const el = $("logOutput");
  const time = new Date().toLocaleTimeString("ja-JP", { hour12: false });
  el.textContent += `\n[${time}] ${message}`;
  el.scrollTop = el.scrollHeight;
}

function toast(title, detail = "") {
  const stack = $("toastStack");
  const div = document.createElement("div");
  div.className = "toast";
  div.innerHTML = `<strong>${title}</strong>${detail ? `<br><small>${detail}</small>` : ""}`;
  stack.appendChild(div);
  setTimeout(() => div.remove(), 4200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderGeneratedOutputs(chunks) {
  const container = $("generatedOutputs");
  if (!container) return;

  const items = Array.isArray(chunks)
    ? chunks.filter((item) => item && item.status === "ok" && item.wav_url)
    : [];

  latestGeneratedChunks = items;

  if (!items.length) {
    container.innerHTML = `<div class="empty">生成済みWAVはまだありません。</div>`;
    return;
  }

  container.innerHTML = "";

  for (const item of items) {
    const rawIndex = item.index ?? "";
    const index = String(rawIndex).padStart(2, "0");
    const cacheKey = item.cache_key ? `?v=${encodeURIComponent(item.cache_key)}` : "";
    const wavUrl = `${item.wav_url}${cacheKey}`;
    const mp3Url = item.mp3_url ? `${item.mp3_url}${cacheKey}` : null;
    const textPreview = String(item.text ?? "").slice(0, 80);

    const row = document.createElement("div");
    row.className = "generated-output-row";
    row.innerHTML = `
      <div class="generated-output-head">
        <strong>チャンク ${escapeHtml(index)}</strong>
        <small>${escapeHtml(textPreview)}${String(item.text ?? "").length > 80 ? "..." : ""}</small>
      </div>
      <audio controls src="${escapeHtml(wavUrl)}"></audio>
      <div class="generated-output-actions">
        <a class="button small" href="${escapeHtml(wavUrl)}" download>WAVをダウンロード</a>
        <button class="secondary-button small regenerate-chunk-button" type="button">このチャンクを再生成</button>
        ${
          mp3Url
            ? `<a class="button small" href="${escapeHtml(mp3Url)}" download>MP3をダウンロード</a>`
            : `<span class="muted">MP3未変換</span>`
        }
      </div>
    `;

    const regenerateButton = row.querySelector(".regenerate-chunk-button");
    regenerateButton?.addEventListener("click", () => regenerateChunk(Number(rawIndex)));

    container.appendChild(row);
  }
}


function formDataFromState() {
  const fd = new FormData();
  fd.append("project_name", $("projectName").value || "irodori_project");
  fd.append("script_text", $("scriptText").value || "");
  fd.append("split_method", document.querySelector("input[name='splitMethod']:checked")?.value || "auto");
  fd.append("max_chars", $("maxChars").value);
  fd.append("cfg_scale_speaker", $("cfgSpeaker").value);
  fd.append("cfg_scale_text", $("cfgText").value);
  fd.append("num_steps", $("numSteps").value);
  fd.append("seed", $("seed").value);
  fd.append("mp3_bitrate", $("mp3Bitrate").value);

  const refInput = $("refUpload");
  if (refInput && refInput.files && refInput.files.length > 0) {
    fd.append("uploaded_audio", refInput.files[0]);
  }

  return fd;
}

$("scriptText").addEventListener("input", () => {
  $("scriptCount").textContent = `${$("scriptText").value.length}文字`;
});

$("maxChars").addEventListener("input", () => {
  $("maxCharsValue").textContent = $("maxChars").value;
});

$("healthBtn").addEventListener("click", async () => {
  const res = await fetch("/api/health");
  const data = await res.json();
  $("healthStatus").textContent = data.ok ? "正常" : "異常";
  toast("環境チェック完了", `Python ${data.python}`);
  log("環境チェックが完了しました。");
});

$("exportProjectBtn").addEventListener("click", async () => {
  const res = await fetch("/api/project/export", {
    method: "POST",
    body: formDataFromState(),
  });
  const data = await res.json();
  if (!data.ok) {
    toast("書き出しに失敗しました", data.message || "");
    return;
  }

  const card = $("downloadCard");
  const link = $("downloadLink");
  link.href = data.download_url;
  link.download = data.filename;
  card.classList.remove("hidden");

  toast("プロジェクトを書き出しました", data.filename);
  log(`プロジェクトを書き出しました: ${data.filename}`);
});

$("importProjectBtn").addEventListener("click", async () => {
  const input = $("projectJsonInput");
  if (!input.files.length) {
    toast("JSONが選択されていません", "先にプロジェクトJSONを選んでください。");
    return;
  }

  const fd = new FormData();
  fd.append("file", input.files[0]);

  const res = await fetch("/api/project/import", {
    method: "POST",
    body: fd,
  });
  const data = await res.json();

  if (!data.ok) {
    toast("JSON読み込み失敗", data.message || "");
    return;
  }

  const p = data.data;
  $("projectName").value = p.project_name ?? "";
  $("scriptText").value = p.script_text ?? "";
  $("scriptCount").textContent = `${$("scriptText").value.length}文字`;

  const splitMethod = p.split_method ?? "auto";
  const splitRadio = document.querySelector(`input[name="splitMethod"][value="${splitMethod}"]`);
  if (splitRadio) splitRadio.checked = true;

  $("maxChars").value = p.max_chars ?? 150;
  $("maxCharsValue").textContent = $("maxChars").value;
  $("cfgSpeaker").value = p.cfg_scale_speaker ?? 7.0;
  $("cfgText").value = p.cfg_scale_text ?? 2.5;
  $("numSteps").value = p.num_steps ?? 60;
  $("seed").value = p.seed ?? -1;
  $("mp3Bitrate").value = p.mp3_bitrate ?? 192;

  toast("JSONを読み込みました", "プロジェクト設定を復元しました。");
  log("プロジェクトJSONを読み込みました。");
});

$("previewChunksBtn").addEventListener("click", async () => {
  const res = await fetch("/api/chunks/preview", {
    method: "POST",
    body: formDataFromState(),
  });
  const data = await res.json();

  $("chunkCount").textContent = `${data.count}件`;
  const list = $("chunkList");
  list.innerHTML = "";

  if (!data.chunks.length) {
    list.innerHTML = `<div class="empty">チャンクがありません。</div>`;
    return;
  }

  for (const item of data.chunks) {
    const row = document.createElement("div");
    row.className = "chunk-row";
    row.innerHTML = `
      <strong>${String(item.index).padStart(2, "0")}</strong>
      <span>${item.text.slice(0, 54)}${item.text.length > 54 ? "..." : ""}<br><small>${item.chars}文字</small></span>
      <span class="badge wait">${item.status}</span>
    `;
    list.appendChild(row);
  }

  toast("チャンク分割完了", `${data.count}件のチャンクを作成しました。`);
  log(`チャンク分割完了: ${data.count}件`);
});

async function readJsonResponse(response, label) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch (parseErr) {
    const preview = text.slice(0, 240).replace(/\s+/g, " ");
    throw new Error(`${label}がJSONではない応答を返しました: HTTP ${response.status} ${preview}`);
  }
}

async function waitForJobDone(jobId, label) {
  const startedAt = Date.now();
  let lastProgressLogSec = 0;

  while (true) {
    await new Promise((resolve) => setTimeout(resolve, 5000));

    const elapsedSec = Math.floor((Date.now() - startedAt) / 1000);
    if (elapsedSec - lastProgressLogSec >= 15) {
      lastProgressLogSec = elapsedSec;
      log(`${label}中... ${elapsedSec}秒経過`);
    }

    const statusRes = await fetch(`/api/generate/status/${encodeURIComponent(jobId)}`);
    const statusData = await readJsonResponse(statusRes, `${label}状況API`);

    if (!statusRes.ok) {
      throw new Error(statusData.message || `${label}状況の取得に失敗しました: HTTP ${statusRes.status}`);
    }

    if (statusData.status === "running" || statusData.status === "queued") {
      continue;
    }

    if (statusData.status === "done") {
      return statusData;
    }

    if (statusData.status === "error") {
      throw new Error(statusData.message || statusData.error || `${label}ジョブでエラーが発生しました。`);
    }

    throw new Error(`未知の${label}ジョブ状態です: ${statusData.status}`);
  }
}

async function regenerateChunk(chunkIndex) {
  const item = latestGeneratedChunks.find((chunk) => Number(chunk.index) === Number(chunkIndex));
  if (!item) {
    toast("再生成できません", "対象チャンクが見つかりません。");
    return;
  }

  if (!item.project_dir) {
    toast("再生成できません", "project_dir が見つかりません。");
    return;
  }

  const fd = new FormData();
  fd.append("project_dir", item.project_dir);
  fd.append("chunk_index", String(item.index));
  fd.append("chunk_text", item.text || "");
  fd.append("cfg_scale_speaker", $("cfgSpeaker").value);
  fd.append("cfg_scale_text", $("cfgText").value);
  fd.append("num_steps", $("numSteps").value);
  fd.append("seed", $("seed").value);

  log(`チャンク ${String(item.index).padStart(2, "0")} 再生成開始`);
  toast("チャンク再生成", `チャンク ${String(item.index).padStart(2, "0")} を再生成します。`);

  try {
    const startRes = await fetch("/api/chunk/regenerate/start", {
      method: "POST",
      body: fd,
    });
    const startData = await readJsonResponse(startRes, "チャンク再生成開始API");

    if (!startRes.ok || !startData.job_id) {
      throw new Error(startData.message || `チャンク再生成開始に失敗しました: HTTP ${startRes.status}`);
    }

    log(`チャンク再生成ジョブ受付: ${startData.job_id}`);

    const statusData = await waitForJobDone(startData.job_id, "チャンク再生成");

    if (Array.isArray(statusData.chunks) && statusData.chunks.length) {
      const updatedChunk = {
        ...statusData.chunks[0],
        cache_key: String(Date.now()),
      };

      const merged = latestGeneratedChunks.map((chunk) =>
        Number(chunk.index) === Number(updatedChunk.index)
          ? { ...chunk, ...updatedChunk }
          : chunk
      );

      renderGeneratedOutputs(merged);
    }

    if (Array.isArray(statusData.log)) {
      statusData.log.forEach((line) => log(line));
    }

    toast("再生成完了", statusData.message || "チャンクを再生成しました。");
    log(statusData.message || "チャンク再生成が完了しました。");
  } catch (err) {
    toast("再生成エラー", err.message || "チャンク再生成に失敗しました。");
    log(`再生成エラー: ${err.message || err}`);
  }
}

$("generateBtn").addEventListener("click", async () => {
  const btn = $("generateBtn");
  btn.disabled = true;

  const startedAt = Date.now();
  let lastProgressLogSec = 0;

  log("生成開始: 生成ジョブを開始します。");
  toast("生成開始", "音声生成ジョブを開始しました。");

  try {
    const startRes = await fetch("/api/generate/start", {
      method: "POST",
      body: formDataFromState(),
    });

    const startText = await startRes.text();
    let startData;
    try {
      startData = startText ? JSON.parse(startText) : {};
    } catch (parseErr) {
      const preview = startText.slice(0, 240).replace(/\s+/g, " ");
      throw new Error(`生成開始APIがJSONではない応答を返しました: HTTP ${startRes.status} ${preview}`);
    }

    if (!startRes.ok || !startData.job_id) {
      throw new Error(startData.message || `生成開始に失敗しました: HTTP ${startRes.status}`);
    }

    const jobId = startData.job_id;
    log(`生成ジョブ受付: ${jobId}`);

    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 5000));

      const elapsedSec = Math.floor((Date.now() - startedAt) / 1000);
      if (elapsedSec - lastProgressLogSec >= 15) {
        lastProgressLogSec = elapsedSec;
        log(`生成中... ${elapsedSec}秒経過`);
      }

      const statusRes = await fetch(`/api/generate/status/${encodeURIComponent(jobId)}`);
      const statusText = await statusRes.text();

      let statusData;
      try {
        statusData = statusText ? JSON.parse(statusText) : {};
      } catch (parseErr) {
        const preview = statusText.slice(0, 240).replace(/\s+/g, " ");
        throw new Error(`生成状況APIがJSONではない応答を返しました: HTTP ${statusRes.status} ${preview}`);
      }

      if (!statusRes.ok) {
        throw new Error(statusData.message || `生成状況の取得に失敗しました: HTTP ${statusRes.status}`);
      }

      if (statusData.status === "running" || statusData.status === "queued") {
        continue;
      }

      if (statusData.status === "done") {
        const finalElapsedSec = Math.floor((Date.now() - startedAt) / 1000);
        toast("生成完了", statusData.message || "生成が完了しました。");
        log(`${statusData.message || "生成完了"} (${finalElapsedSec}秒)`);

        if (Array.isArray(statusData.chunks)) {
          log(`生成チャンク数: ${statusData.chunks.length}`);
          renderGeneratedOutputs(statusData.chunks);
        }

        if (Array.isArray(statusData.log)) {
          statusData.log.forEach((line) => log(line));
        }
        break;
      }

      if (statusData.status === "error") {
        throw new Error(statusData.message || statusData.error || "生成ジョブでエラーが発生しました。");
      }

      throw new Error(`未知の生成ジョブ状態です: ${statusData.status}`);
    }
  } catch (err) {
    toast("生成エラー", err.message || "生成に失敗しました。");
    log(`生成エラー: ${err.message || err}`);
  } finally {
    btn.disabled = false;
  }
});

$("cancelBtn").addEventListener("click", () => {
  toast("中断リクエスト", "現在はモックUIです。");
  log("生成中断リクエストを受け付けました。");
});

$("copyLogBtn").addEventListener("click", async () => {
  const text = $("logOutput").textContent || "";
  try {
    await navigator.clipboard.writeText(text);
    toast("ログをコピーしました");
    log("ログをクリップボードにコピーしました。");
  } catch (err) {
    toast("ログコピー失敗", "ブラウザの制限でコピーできませんでした。");
    log(`ログコピー失敗: ${err.message || err}`);
  }
});

$("clearLogBtn").addEventListener("click", () => {
  $("logOutput").textContent = "[system] log cleared.";
});
