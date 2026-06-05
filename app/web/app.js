const $ = (id) => document.getElementById(id);

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
  $("projectName").value = p.project_name || "";
  $("scriptText").value = p.script_text || "";
  $("scriptCount").textContent = `${$("scriptText").value.length}文字`;
  $("maxChars").value = p.max_chars || 150;
  $("maxCharsValue").textContent = $("maxChars").value;

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

$("generateBtn").addEventListener("click", async () => {
  const res = await fetch("/api/generate/mock", {
    method: "POST",
    body: formDataFromState(),
  });
  const data = await res.json();
  toast("生成モック完了", data.message);
  log(`生成モック完了: ${data.job_id}`);
});

$("cancelBtn").addEventListener("click", () => {
  toast("中断リクエスト", "現在はモックUIです。");
  log("生成中断リクエストを受け付けました。");
});

$("clearLogBtn").addEventListener("click", () => {
  $("logOutput").textContent = "[system] log cleared.";
});
